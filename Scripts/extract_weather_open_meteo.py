# Scripts/extract_weather_open_meteo.py
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import requests

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Variables météo à récupérer (tu peux adapter)
HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
DAILY_VARS  = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def geocode_city(name: str):
    """Retourne (lat, lon, label) pour une ville via Open-Meteo Geocoding."""
    params = {"name": name, "count": 1, "language": "fr", "format": "json"}
    r = requests.get(GEO_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Ville introuvable via géocodage: {name}")
    res = results[0]
    return float(res["latitude"]), float(res["longitude"]), res.get("name", name)

def fetch_weather(lat: float, lon: float, past_days: int = 2, forecast_days: int = 7):
    """Récupère la météo (heures + journalière) pour lat/lon."""
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": HOURLY_VARS, "daily": DAILY_VARS,
        "past_days": past_days, "forecast_days": forecast_days,
        "timezone": "Europe/Brussels",
    }
    r = requests.get(FORECAST_URL, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def clean_old_date_folders(raw_root: Path, days_to_keep: int = 7) -> int:
    """
    Supprime les dossiers de date (YYYY-MM-DD) plus vieux que N jours.
    Retourne le nombre de dossiers supprimés.
    """
    cutoff = (datetime.utcnow() - timedelta(days=days_to_keep)).date()
    deleted = 0
    for p in raw_root.iterdir():
        if p.is_dir():
            try:
                # attend un nom de dossier de type YYYY-MM-DD
                folder_date = datetime.strptime(p.name, "%Y-%m-%d").date()
            except ValueError:
                # ignorer tout dossier qui ne correspond pas au format de date
                continue
            if folder_date < cutoff:
                # supprimer récursivement le dossier et son contenu
                for f in p.rglob("*"):
                    try:
                        f.unlink()
                    except IsADirectoryError:
                        pass
                try:
                    p.rmdir()
                    deleted += 1
                except OSError:
                    # s'il reste quelque chose, on ignore
                    pass
    return deleted

def main():
    parser = argparse.ArgumentParser(description="Extraction météo Open-Meteo (Belgique) avec historique par date.")
    parser.add_argument("--cities", nargs="+", default=["Bruxelles", "Anvers", "Liège"],
                        help="Liste de villes (défaut: Bruxelles Anvers Liège)")
    parser.add_argument("--past-days", type=int, default=2, help="Jours passés à inclure (défaut: 2)")
    parser.add_argument("--forecast-days", type=int, default=7, help="Jours de prévision à inclure (défaut: 7)")
    parser.add_argument("--keep-days", type=int, default=14, help="Conserver les dossiers de date des N derniers jours (défaut: 14). Mettre 0 pour ne rien supprimer.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    raw_root = project_root / "Data" / "raw"
    ensure_dir(raw_root)

    # Dossier du jour en UTC pour une nomenclature stable
    today_folder = raw_root / datetime.utcnow().strftime("%Y-%m-%d")
    ensure_dir(today_folder)

    print(f"[INFO] Projet        : {project_root}")
    print(f"[INFO] RAW root      : {raw_root}")
    print(f"[INFO] Dossier du jour: {today_folder}")

    for city in args.cities:
        try:
            lat, lon, label = geocode_city(city)
            print(f"[GEO] {city} -> {label} (lat={lat}, lon={lon})")

            payload = fetch_weather(lat, lon, args.past_days, args.forecast_days)

            # Nom de fichier : {Ville}_{HHMMSS}.json (dans le dossier YYYY-MM-DD)
            ts = datetime.utcnow().strftime("%H%M%S")
            safe_label = label.replace(" ", "_")
            fpath = today_folder / f"{safe_label}_{ts}.json"

            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            print(f"[OK] Données sauvegardées: {fpath}")
        except Exception as e:
            print(f"[ERREUR] {city}: {e}")

    # Nettoyage des anciens dossiers de date (optionnel)
    if args.keep_days and args.keep_days > 0:
        deleted = clean_old_date_folders(raw_root, args.keep_days)
        print(f"[CLEAN] Dossiers de date supprimés (> {args.keep_days} jours): {deleted}")

if __name__ == "__main__":
    main()

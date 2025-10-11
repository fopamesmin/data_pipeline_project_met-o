# Scripts/transform_weather_to_postgres.py
# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from typing import List

import pandas as pd
import psycopg2
from psycopg2 import OperationalError, sql
from psycopg2.extras import execute_values

# ----- chemins -----
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT_ROOT / "Data" / "raw"   # Data/raw/YYYY-MM-DD/{Ville}_{HHMMSS}.json

# ----- utilitaires -----
def parse_city_from_filename(path: Path) -> str:
    """Bruxelles_083015.json -> 'Bruxelles' (remet les espaces si besoin)."""
    name = path.stem  # sans .json
    parts = name.split("_")
    if len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) in (4, 6):
        city = "_".join(parts[:-1])
    else:
        city = name
    return city.replace("_", " ")

def ensure_schema_and_table(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS silver;")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS silver.weather_daily (
            date DATE NOT NULL,
            city TEXT NOT NULL,
            temperature_2m_max DOUBLE PRECISION,
            temperature_2m_min DOUBLE PRECISION,
            precipitation_sum DOUBLE PRECISION,
            wind_speed_10m_max DOUBLE PRECISION,
            temp_range DOUBLE PRECISION,
            PRIMARY KEY (date, city)
        );
        """)

def upsert_daily(conn, df: pd.DataFrame):
    if df.empty:
        return 0
    cols = [
        "date",
        "city",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "wind_speed_10m_max",
        "temp_range",
    ]
    records = [tuple(x) for x in df[cols].itertuples(index=False, name=None)]
    sql_insert = """
    INSERT INTO silver.weather_daily
        (date, city, temperature_2m_max, temperature_2m_min,
         precipitation_sum, wind_speed_10m_max, temp_range)
    VALUES %s
    ON CONFLICT (date, city) DO UPDATE SET
        temperature_2m_max = EXCLUDED.temperature_2m_max,
        temperature_2m_min = EXCLUDED.temperature_2m_min,
        precipitation_sum  = EXCLUDED.precipitation_sum,
        wind_speed_10m_max = EXCLUDED.wind_speed_10m_max,
        temp_range         = EXCLUDED.temp_range;
    """
    with conn.cursor() as cur:
        execute_values(cur, sql_insert, records)
    return len(records)

def daily_df_from_payload(payload: dict, city: str) -> pd.DataFrame:
    daily = payload.get("daily") or {}
    if not daily:
        return pd.DataFrame()
    df = pd.DataFrame(daily)
    if "time" not in df.columns:
        return pd.DataFrame()
    df = df.rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for col in ("temperature_2m_max","temperature_2m_min","precipitation_sum","wind_speed_10m_max"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA
    df["city"] = city
    df["temp_range"] = df["temperature_2m_max"] - df["temperature_2m_min"]
    return df[["date","city","temperature_2m_max","temperature_2m_min","precipitation_sum","wind_speed_10m_max","temp_range"]]

def list_json_files(raw_root: Path, only_days: int) -> List[Path]:
    """Liste les fichiers dans Data/raw/YYYY-MM-DD des N derniers jours."""
    cutoff_date = (datetime.utcnow() - timedelta(days=only_days)).date()
    files: List[Path] = []
    if not raw_root.exists():
        return files
    for day_dir in raw_root.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            d = datetime.strptime(day_dir.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d >= cutoff_date:
            files.extend(sorted(day_dir.glob("*.json")))
    return files

# ----- Connexion Postgres avec auto-création de la DB dwh -----
def connect_db(host: str, db: str, user: str, password: str):
    return psycopg2.connect(host=host, dbname=db, user=user, password=password)

def ensure_database_exists(host: str, user: str, password: str, dbname: str = "dwh"):
    """
    Tente de se connecter à `dbname`. Si échec (db absente),
    se connecte à 'postgres', crée `dbname` avec OWNER = user, puis sort.
    """
    try:
        conn = connect_db(host, dbname, user, password)
        conn.close()
        return  # la DB existe déjà
    except OperationalError:
        # Se connecter à la DB 'postgres' pour créer la DB cible
        admin_conn = connect_db(host, "postgres", user, password)
        try:
            admin_conn.autocommit = True  # CREATE DATABASE ne peut pas être dans une transaction
            with admin_conn.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s;"),
                    [dbname],
                )
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(sql.SQL("CREATE DATABASE {} OWNER {};").format(
                        sql.Identifier(dbname),
                        sql.Identifier(user)
                    ))
                    print(f"[DB] Base créée: {dbname} (OWNER {user})")
                else:
                    print(f"[DB] Base déjà présente: {dbname}")
        finally:
            admin_conn.close()

# ----- main -----
def main():
    parser = argparse.ArgumentParser(description="Transforme Data/raw en silver.weather_daily (PostgreSQL).")
    parser.add_argument("--only-days", type=int, default=3, help="Ne traiter que les N derniers jours (défaut: 3).")
    parser.add_argument("--pg-host", default=os.getenv("PGHOST", "postgres_db"))
    parser.add_argument("--pg-db",   default=os.getenv("PGDATABASE", "dwh"))
    parser.add_argument("--pg-user", default=os.getenv("PGUSER", "airflow"))
    parser.add_argument("--pg-pass", default=os.getenv("PGPASSWORD", "airflow"))
    args = parser.parse_args()

    files = list_json_files(RAW_ROOT, args.only_days)
    if not files:
        print(f("[INFO] Aucun fichier récent trouvé dans {RAW_ROOT} (only_days={args.only_days})."))
        return

    print(f"[INFO] Fichiers détectés ({len(files)}) sur {args.only_days} jour(s).")
    frames = []
    for path in files:
        try:
            city = parse_city_from_filename(path)
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            df = daily_df_from_payload(payload, city)
            if not df.empty:
                frames.append(df)
                print(f"[OK] {path} -> {len(df)} lignes")
            else:
                print(f"[WARN] {path} : pas de données journalières.")
        except Exception as e:
            print(f"[ERR] {path} : {e}")

    if not frames:
        print("[INFO] Rien à charger.")
        return

    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["date"]).drop_duplicates(subset=["date","city"], keep="last")

    # Assure l'existence de la DB dwh, puis connecte-toi et charge
    ensure_database_exists(args.pg_host, args.pg_user, args.pg_pass, args.pg_db)
    conn = connect_db(args.pg_host, args.pg_db, args.pg_user, args.pg_pass)
    try:
        conn.autocommit = False
        ensure_schema_and_table(conn)
        n = upsert_daily(conn, out)
        conn.commit()
        print(f"[LOAD] {n} ligne(s) upsert dans {args.pg_db}.silver.weather_daily")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

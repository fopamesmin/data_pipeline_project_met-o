# Scripts/load_gold_weather_kpi.py
# -*- coding: utf-8 -*-
import psycopg2
import pandas as pd

PG = dict(host="postgres_db", dbname="dwh", user="airflow", password="airflow")

def connect_db(db=PG["dbname"]):
    return psycopg2.connect(host=PG["host"], dbname=db, user=PG["user"], password=PG["password"])

def main():
    print("[INFO] Connexion à la base dwh...")
    conn = connect_db()

    # --- Lire la Silver
    query = """
    SELECT 
        date,
        city,
        temperature_2m_max,
        temperature_2m_min,
        precipitation_sum,
        wind_speed_10m_max
    FROM silver.weather_daily;
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        print("[WARN] Aucune donnée trouvée dans silver.weather_daily.")
        conn.close()
        return

    print(f"[INFO] {len(df)} lignes récupérées de la couche Silver.")

    # --- Préparation Gold : semaine ISO + métriques
    s = pd.to_datetime(df["date"]).dt.isocalendar()
    df["iso_year"] = s.year.astype(int)
    df["iso_week"] = s.week.astype(int)
    df["week"] = df["iso_year"].astype(str) + "-W" + df["iso_week"].astype(str).str.zfill(2)
    df["temp_range"] = df["temperature_2m_max"] - df["temperature_2m_min"]

    df_gold = (
        df.groupby(["week", "city"], as_index=False)
          .agg(
              temp_max_mean=("temperature_2m_max", "mean"),
              temp_min_mean=("temperature_2m_min", "mean"),
              temp_range_mean=("temp_range", "mean"),
              precipitation_total=("precipitation_sum", "sum"),
              wind_speed_max=("wind_speed_10m_max", "max"),
              nb_days=("date", "nunique"),
          )
    )

    # --- Création idempotente du schéma et de la table
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS gold;")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS gold.weather_kpi (
            week TEXT NOT NULL,
            city TEXT NOT NULL,
            temp_max_mean DOUBLE PRECISION,
            temp_min_mean DOUBLE PRECISION,
            temp_range_mean DOUBLE PRECISION,
            precipitation_total DOUBLE PRECISION,
            wind_speed_max DOUBLE PRECISION,
            nb_days INT,
            PRIMARY KEY (week, city)
        );
        """)
        conn.commit()

    # --- Upsert des KPI
    rows = [
        (
            r.week, r.city,
            float(r.temp_max_mean) if r.temp_max_mean is not None else None,
            float(r.temp_min_mean) if r.temp_min_mean is not None else None,
            float(r.temp_range_mean) if r.temp_range_mean is not None else None,
            float(r.precipitation_total) if r.precipitation_total is not None else None,
            float(r.wind_speed_max) if r.wind_speed_max is not None else None,
            int(r.nb_days) if r.nb_days is not None else None,
        )
        for r in df_gold.itertuples(index=False)
    ]

    upsert_sql = """
    INSERT INTO gold.weather_kpi
    (week, city, temp_max_mean, temp_min_mean, temp_range_mean, precipitation_total, wind_speed_max, nb_days)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (week, city) DO UPDATE SET
        temp_max_mean = EXCLUDED.temp_max_mean,
        temp_min_mean = EXCLUDED.temp_min_mean,
        temp_range_mean = EXCLUDED.temp_range_mean,
        precipitation_total = EXCLUDED.precipitation_total,
        wind_speed_max = EXCLUDED.wind_speed_max,
        nb_days = EXCLUDED.nb_days;
    """

    with conn.cursor() as cur:
        cur.executemany(upsert_sql, rows)
        conn.commit()

    print(f"[OK] Données Gold upsertées : {len(rows)} lignes.")
    conn.close()

if __name__ == "__main__":
    main()

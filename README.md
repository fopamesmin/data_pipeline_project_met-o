# 🌦️ Belgian Weather Data Pipeline

## 🚀 Overview

This project implements a complete **ETL (Extract, Transform, Load)** data pipeline for **Belgian weather data**, using **Apache Airflow**, **Docker**, and **PostgreSQL**.  

The pipeline automatically extracts raw meteorological data from the **Open-Meteo API**, transforms it into a clean analytical format, and stores it in a PostgreSQL data warehouse.  
It is designed following a **Medallion Architecture**:
- **Bronze** → Raw JSON files  
- **Silver** → Cleaned and structured daily weather table  
- *(Gold — coming next)* → Aggregated KPIs (weekly/monthly)

---

## 🧱 Architecture

```text
data_pipeline_project/
│
├── Airflow/
│   ├── dags/
│   │   ├── extract_open_meteo_v2.py       # DAG: Extraction only
│   │   └── weather_etl_v2.py              # DAG: Extract + Transform
│   ├── logs/                              # Airflow logs
│   └── plugins/
│
├── Data/
│   ├── raw/                               # Bronze layer (YYYY-MM-DD/*.json)
│   ├── postgres_data/                     # Postgres volume
│   └── pgadmin/                           # pgAdmin volume
│
├── Scripts/
│   ├── extract_weather_open_meteo.py      # Extraction script (Open-Meteo API)
│   └── transform_weather_to_postgres.py   # Transformation script (to PostgreSQL)
│
├── docker-compose.yml                     # Full environment configuration
└── README.md



| Component              | Purpose                                 |
| ---------------------- | --------------------------------------- |
| **Python 3.8+**        | Scripts for extract and transform       |
| **Apache Airflow 2.8** | Workflow orchestration (ETL scheduling) |
| **PostgreSQL 13**      | Data warehouse                          |
| **pgAdmin 4**          | Database management GUI                 |
| **Docker Compose**     | Infrastructure setup and orchestration  |
| **Pandas + psycopg2**  | Data transformation and loading         |




⚙️ Setup & Installation
1️⃣ Clone the repository

git clone https://github.com/<your-username>/belgian-weather-pipeline.git
cd belgian-weather-pipeline

2️⃣ Launch the environment
docker compose up -d --remove-orphans

Services started:

Airflow Web UI → http://localhost:8080

☁️ ETL Workflow
🥉 Bronze – Extract

Fetches weather data from the Open-Meteo API for multiple Belgian cities.
Files are stored in Data/raw/YYYY-MM-DD/{City}_{Timestamp}.json.

Example command:

docker compose run --rm etl-worker bash -lc \
"python Scripts/extract_weather_open_meteo.py --cities Bruxelles Anvers Liège --keep-days 14"
🥈 Silver – Transform

Reads the raw JSON files, cleans and aggregates daily values,
and loads them into PostgreSQL table silver.weather_daily.

Example command:
docker compose run --rm etl-worker bash -lc \
"python Scripts/transform_weather_to_postgres.py --only-days 3"

| Column             | Type   | Description                   |
| ------------------ | ------ | ----------------------------- |
| date               | DATE   | Observation date              |
| city               | TEXT   | City name                     |
| temperature_2m_max | DOUBLE | Daily max temperature         |
| temperature_2m_min | DOUBLE | Daily min temperature         |
| precipitation_sum  | DOUBLE | Daily total precipitation     |
| wind_speed_10m_max | DOUBLE | Daily max wind speed          |
| temp_range         | DOUBLE | Temperature range (max − min) |



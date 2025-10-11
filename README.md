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

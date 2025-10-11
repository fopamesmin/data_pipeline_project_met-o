# Airflow/dags/extract_open_meteo_v2.py
from datetime import datetime
import pendulum, os
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/project"  # volume monté via docker-compose
SCRIPT_PATH  = os.path.join(PROJECT_ROOT, "Scripts", "extract_weather_open_meteo.py")

# Paramètres
CITIES    = "Bruxelles Anvers Liège"
KEEP_DAYS = 14
PAST_DAYS = 2
FORECAST_DAYS = 7

with DAG(
    dag_id="extract_open_meteo_v2",
    description="Extraction Open-Meteo -> Data/raw/YYYY-MM-DD/{Ville}_{HHMMSS}.json",
    start_date=datetime(2024, 1, 1, tzinfo=pendulum.timezone("Europe/Brussels")),
    schedule_interval="@daily",   # ou "0 6 * * *"
    catchup=False,
    tags=["weather","belgium","extract","bronze"],
) as dag:

    run_extractor = BashOperator(
        task_id="run_extractor",
        bash_command=(
            f"python {SCRIPT_PATH} "
            f"--cities {CITIES} "
            f"--past-days {PAST_DAYS} "
            f"--forecast-days {FORECAST_DAYS} "
            f"--keep-days {KEEP_DAYS}"
        ),
        cwd=PROJECT_ROOT,
    )

# Airflow/dags/weather_etl_v2.py
from datetime import datetime
import pendulum, os
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_ROOT = "/opt/project"
EXTRACT  = os.path.join(PROJECT_ROOT, "Scripts", "extract_weather_open_meteo.py")
TRANSFORM= os.path.join(PROJECT_ROOT, "Scripts", "transform_weather_to_postgres.py")

# Paramètres
CITIES         = "Bruxelles Anvers Liège"
KEEP_DAYS      = 14      # garde 14 jours de dossiers de date en bronze
PAST_DAYS      = 2
FORECAST_DAYS  = 7
ONLY_DAYS      = 3       # ne traite que les 3 derniers jours en transfo

with DAG(
    dag_id="weather_etl_v2",
    description="Extract Open-Meteo -> Data/raw/YYYY-MM-DD -> Transform Pandas -> silver.weather_daily",
    start_date=datetime(2024, 1, 1, tzinfo=pendulum.timezone("Europe/Brussels")),
    schedule_interval="@daily",     # ou "0 6 * * *"
    catchup=False,
    tags=["weather","belgium","etl","bronze","silver"],
) as dag:

    extract = BashOperator(
        task_id="extract_bronze",
        bash_command=(
            f"python {EXTRACT} "
            f"--cities {CITIES} "
            f"--past-days {PAST_DAYS} "
            f"--forecast-days {FORECAST_DAYS} "
            f"--keep-days {KEEP_DAYS}"
        ),
        cwd=PROJECT_ROOT,
    )

    transform = BashOperator(
        task_id="transform_silver",
        bash_command=f"python {TRANSFORM} --only-days {ONLY_DAYS}",
        cwd=PROJECT_ROOT,
    )

    extract >> transform

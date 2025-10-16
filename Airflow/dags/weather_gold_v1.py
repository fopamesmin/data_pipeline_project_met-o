from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime
import os

PROJECT_ROOT = "/opt/project"
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "Scripts", "load_gold_weather_kpi.py")

with DAG(
    dag_id="weather_gold_v1",
    description="Aggregation météo hebdomadaire (Gold Layer)",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@weekly",
    catchup=False,
    tags=["weather", "gold", "aggregate"],
) as dag:

    aggregate_gold = BashOperator(
        task_id="aggregate_gold",
        bash_command=f"python {SCRIPT_PATH}",
        cwd=PROJECT_ROOT,
    )

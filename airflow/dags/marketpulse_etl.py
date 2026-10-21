from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/project"

with DAG(
    dag_id="marketpulse_etl",
    description="End-to-end ETL saham: ingestion, cleaning, metrics, loading, dan quality checks",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["marketpulse", "etl", "data-quality"],
) as dag:

    ingestion = BashOperator(
        task_id="fetch_market_data",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/ingestion/fetch_market_data.py"
        ),
    )

    cleaning = BashOperator(
        task_id="clean_prices",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/transformations/clean_prices.py"
        ),
    )

    daily_metrics = BashOperator(
        task_id="calculate_daily_metrics",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/transformations/calculate_metrics.py"
        ),
    )

    monthly_metrics = BashOperator(
        task_id="calculate_monthly_metrics",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/aggregations/monthly_metrics.py"
        ),
    )

    load_gold = BashOperator(
        task_id="load_gold_to_postgres",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/storage/load_gold_to_postgres.py"
        ),
    )

    check_daily_quality = BashOperator(
        task_id="check_gold_quality",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/quality/check_gold_quality.py"
        ),
    )

    check_monthly_quality = BashOperator(
        task_id="check_monthly_metrics",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python src/marketpulse/quality/check_monthly_metrics.py"
        ),
    )

    ingestion >> cleaning >> daily_metrics >> monthly_metrics >> load_gold

    load_gold >> [check_daily_quality, check_monthly_quality]

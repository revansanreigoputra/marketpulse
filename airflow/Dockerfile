FROM apache/airflow:2.10.5-python3.12

USER airflow

RUN pip install --no-cache-dir \
    --timeout 120 \
    --retries 5 \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    psycopg2-binary

RUN pip install --no-cache-dir --no-deps pyarrow==24.0.0

# MarketPulse — Stock Market Analytics Data Pipeline

MarketPulse is an end-to-end Data Engineering portfolio project that collects stock market data, transforms it into analytical datasets, loads Gold-layer metrics into PostgreSQL, and visualizes the results through an interactive dashboard.

The project demonstrates data ingestion, data cleaning, analytical transformations, orchestration, data quality checks, relational database loading, and dashboard development.

## Project Overview

MarketPulse currently processes daily stock market data for:

- Apple (AAPL)
- IBM (IBM)
- Microsoft (MSFT)

The pipeline produces daily and monthly analytical metrics that can be queried in PostgreSQL and explored through the Streamlit dashboard.

## Architecture

```text
Stock Market API
       |
       v
Raw Data
       |
       v
Data Cleaning
       |
       v
Silver Data
       |
       +---------------------+
       |                     |
       v                     v
Daily Metrics          Monthly Metrics
       |                     |
       +----------+----------+
                  |
                  v
        Gold Data (Parquet)
                  |
                  v
             PostgreSQL
                  |
                  v
        Streamlit + Plotly
             Dashboard

Apache Airflow orchestrates the pipeline
and runs data quality checks.
```

## Technology Stack

| Technology     | Purpose                                     |
| -------------- | ------------------------------------------- |
| Python         | Data ingestion and transformation           |
| Pandas         | Data processing and analytical calculations |
| Apache Airflow | Pipeline orchestration and task monitoring  |
| PostgreSQL     | Storage for Gold-layer analytical data      |
| SQLAlchemy     | Database connectivity                       |
| Streamlit      | Interactive dashboard                       |
| Plotly         | Interactive charts                          |
| Pytest         | Automated testing                           |
| Docker Compose | Container management                        |
| WSL Ubuntu     | Development environment                     |

## Data Pipeline

The `marketpulse_etl` DAG contains seven tasks:

1. `fetch_market_data` — retrieves stock market data.
2. `clean_prices` — cleans and validates price data.
3. `calculate_daily_metrics` — calculates daily analytical metrics.
4. `calculate_monthly_metrics` — aggregates data into monthly metrics.
5. `load_gold_to_postgres` — loads Gold datasets into PostgreSQL.
6. `check_gold_quality` — validates daily Gold data.
7. `check_monthly_metrics` — validates monthly analytical metrics.

Airflow manages task dependencies and exposes task execution logs and statuses through its web interface.

## Gold Data Model

### `gold_daily_metrics`

Contains daily stock prices and calculated metrics.

Key columns include:

- `symbol`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `previous_close`
- `daily_return_pct`
- `daily_range`
- `intraday_return_pct`

The primary key is `(symbol, trade_date)`.

### `gold_monthly_metrics`

Contains monthly stock performance metrics.

Key columns include:

- `symbol`
- `month`
- `month_end_close`
- `monthly_high`
- `monthly_low`
- `monthly_volume`
- `trading_days`
- `previous_month_end_close`
- `monthly_return_pct`

The primary key is `(symbol, month)`.

## Dashboard

The Streamlit dashboard provides:

- Stock symbol filtering.
- Date range filtering.
- Daily record count.
- Number of selected stocks.
- Latest available trading date.
- Average daily return.
- Daily closing-price visualization.
- Daily return analysis.
- Monthly performance visualization.
- Analytical data tables.

The dashboard reads Gold-layer data from PostgreSQL.

## Validation Results

The project has been tested with the following results:

| Validation                  |   Result |
| --------------------------- | -------: |
| Automated tests             | 7 passed |
| Python compilation check    |   Passed |
| Daily Gold records          |      300 |
| Monthly Gold records        |       18 |
| Daily Gold missing keys     |        0 |
| Daily Gold duplicate keys   |        0 |
| Monthly Gold missing keys   |        0 |
| Monthly Gold duplicate keys |        0 |

The successful Airflow run completed all seven pipeline tasks, including the PostgreSQL loading task and both data quality checks.

These figures describe the dataset and successful run observed during development; they may change when new data is ingested.

## Prerequisites

Before running the project, install or prepare:

- Docker Desktop with WSL integration.
- WSL Ubuntu.
- Python and a virtual environment.
- Git.
- An API key for the configured market data provider.

## Environment Configuration

Create a local `.env` file in the project root. Use the following structure and fill in your own credentials:

```dotenv
ALPHA_VANTAGE_API_KEY=your_api_key
POSTGRES_DB=marketpulse
POSTGRES_USER=revana
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
AIRFLOW_UID=1001
```

**Never commit the real `.env` file, API keys, or database passwords to GitHub.**

The host configuration differs by execution environment:

- Local Python and Streamlit use `127.0.0.1`.
- Airflow inside Docker uses the PostgreSQL service hostname `postgres`.

## Installation and Execution

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd marketpulse
```

Replace the placeholder with the actual repository URL.

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create the `.env` file using the configuration structure described above.

### 5. Start the Docker services

```bash
docker compose up -d --build
```

Check the service status:

```bash
docker compose ps
```

### 6. Open Airflow

Visit:

`http://localhost:8080`

Find the `marketpulse_etl` DAG and trigger a run. Check the Graph view and task logs to monitor the pipeline.

### 7. Open the dashboard

With the virtual environment activated, run:

```bash
streamlit run src/marketpulse/dashboard/app.py
```

Visit:

`http://localhost:8501`

Ensure PostgreSQL is running and the Gold tables have been populated before opening the dashboard.

### 8. Run automated tests

```bash
PYTHONPATH=src pytest -q
```

Expected result from the current test suite:

```text
7 passed
```

Check Python syntax:

```bash
python -m compileall -q src tests airflow/dags
```

## Project Structure

```text
marketpulse/
├── airflow/
│   ├── dags/
│   ├── logs/
│   ├── plugins/
│   └── config/
├── data/
│   ├── raw/
│   ├── silver/
│   └── gold/
├── src/
│   └── marketpulse/
│       ├── dashboard/
│       ├── ingestion/
│       ├── transformations/
│       ├── aggregations/
│       ├── quality/
│       └── storage/
├── tests/
├── compose.yaml
├── requirements.txt
├── .env
└── README.md
```

This structure is illustrative. Adjust it to match the directories actually committed to the repository.

## Future Improvements

- Add automated scheduling and recovery strategies.
- Improve logging and alerting for failed pipeline tasks.
- Expand data quality rules and monitoring.
- Add more stock symbols and historical data.
- Improve dashboard performance and analytical features.
- Add CI automation for tests and code quality checks.

## Learning Outcomes

Through this project, I practiced building a data pipeline from ingestion to analytics, orchestrating tasks with Apache Airflow, modeling analytical datasets, loading data into PostgreSQL, validating data quality, and presenting results through an interactive dashboard.

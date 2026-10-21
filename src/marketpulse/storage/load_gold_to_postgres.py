from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.environ["POSTGRES_DB"],
)

DATA_DIR = PROJECT_ROOT / "data" / "gold"


def clean_value(value):
    """Ubah nilai kosong dan tipe NumPy/Pandas menjadi nilai Python."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def load_parquet(engine, folder, pattern, table, columns, date_column):
    files = sorted((DATA_DIR / folder).glob(pattern))
    if not files:
        raise FileNotFoundError(f"File Parquet tidak ditemukan: {folder}/{pattern}")

    total_rows = 0

    for file in files:
        df = pd.read_parquet(file)

        if date_column == "trade_date":
            df = df.rename(columns={
                "open": "open_price",
                "high": "high_price",
                "low": "low_price",
                "close": "close_price",
            })
            df["trade_date"] = pd.to_datetime(df["timestamp"]).dt.date
        else:
            df["month"] = pd.to_datetime(
                df["month"].astype(str) + "-01"
            ).dt.date

        records = [
            {
                column: clean_value(row[column])
                for column in columns
            }
            for _, row in df.iterrows()
        ]

        if not records:
            continue

        column_sql = ", ".join(columns)
        placeholders = ", ".join(f":{column}" for column in columns)
        key_columns = (
            ["symbol", "trade_date"]
            if table == "gold_daily_metrics"
            else ["symbol", "month"]
        )
        update_columns = [
            column for column in columns
            if column not in key_columns
        ]
        updates = ", ".join(
            f"{column} = EXCLUDED.{column}"
            for column in update_columns
        )

        sql = text(f"""
            INSERT INTO {table} ({column_sql})
            VALUES ({placeholders})
            ON CONFLICT ({", ".join(key_columns)})
            DO UPDATE SET {updates}
        """)

        with engine.begin() as connection:
            connection.execute(sql, records)

        total_rows += len(records)
        print(f"OK | {file.name} | {len(records)} baris")

    print(f"TOTAL | {table} | {total_rows} baris")
    return total_rows


def main():
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as connection:
            print("Database:", connection.execute(
                text("SELECT current_database()")
            ).scalar_one())

        daily_columns = [
            "symbol", "trade_date", "open_price", "high_price",
            "low_price", "close_price", "volume", "previous_close",
            "daily_return_pct", "daily_range", "intraday_return_pct",
        ]

        monthly_columns = [
            "symbol", "month", "month_end_close", "monthly_high",
            "monthly_low", "monthly_volume", "trading_days",
            "previous_month_end_close", "monthly_return_pct",
        ]

        load_parquet(
            engine, "daily_metrics", "*_daily.parquet",
            "gold_daily_metrics", daily_columns, "trade_date",
        )

        load_parquet(
            engine, "monthly_metrics", "*_monthly.parquet",
            "gold_monthly_metrics", monthly_columns, "month",
        )

        print("LOAD GOLD BERHASIL")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
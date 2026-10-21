from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(DATABASE_URL)

CHECKS = {
    "gold_daily_metrics": """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE symbol IS NULL) AS null_symbol,
            COUNT(*) FILTER (WHERE trade_date IS NULL) AS null_date,
            COUNT(*) FILTER (WHERE close_price <= 0) AS invalid_close,
            COUNT(*) FILTER (WHERE volume < 0) AS invalid_volume,
            COUNT(*) FILTER (
                WHERE high_price < open_price
                OR high_price < close_price
                OR low_price > open_price
                OR low_price > close_price
            ) AS invalid_ohlc
        FROM gold_daily_metrics
    """,
}

failed = False

with engine.connect() as conn:
    for table, query in CHECKS.items():
        result = conn.execute(text(query)).mappings().one()
        print(f"\n=== {table} ===")

        for column, value in result.items():
            print(f"{column}: {value}")

        if result["total_rows"] == 0:
            failed = True
            print("STATUS: FAILED - tabel kosong")
        elif any(
            value > 0
            for column, value in result.items()
            if column != "total_rows"
        ):
            failed = True
            print("STATUS: FAILED - ditemukan masalah kualitas data")
        else:
            print("STATUS: PASSED")

engine.dispose()

if failed:
    raise SystemExit("DATA QUALITY CHECK FAILED")

print("\nSEMUA DATA QUALITY CHECK LOLOS")
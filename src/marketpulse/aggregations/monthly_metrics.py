from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

GOLD_DAILY_DIR = (
    PROJECT_ROOT / "data" / "gold" / "daily_metrics"
)

GOLD_MONTHLY_DIR = (
    PROJECT_ROOT / "data" / "gold" / "monthly_metrics"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def calculate_monthly_metrics(path: Path) -> int:
    """Menghitung metrik bulanan untuk satu file saham."""

    df = pd.read_parquet(path)

    required_columns = {
        "symbol",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{path.name}: kolom wajib tidak tersedia: "
            f"{sorted(missing_columns)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="raise",
    )

    df = df.sort_values(
        ["symbol", "timestamp"]
    ).reset_index(drop=True)

    df["month"] = (
        df["timestamp"]
        .dt.to_period("M")
    )

    monthly = (
        df.groupby(["symbol", "month"], as_index=False)
        .agg(
            month_end_close=("close", "last"),
            monthly_high=("high", "max"),
            monthly_low=("low", "min"),
            monthly_volume=("volume", "sum"),
            trading_days=("timestamp", "nunique"),
        )
    )

    monthly = monthly.sort_values(
        ["symbol", "month"]
    ).reset_index(drop=True)

    monthly["previous_month_end_close"] = (
        monthly.groupby("symbol")["month_end_close"]
        .shift(1)
    )

    monthly["monthly_return_pct"] = (
        (
            monthly["month_end_close"]
            / monthly["previous_month_end_close"]
        ) - 1
    ) * 100

    monthly["month"] = monthly["month"].astype(str)

    GOLD_MONTHLY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = GOLD_MONTHLY_DIR / (
        f"{path.stem.replace('_daily', '')}_monthly.parquet"
    )

    monthly.to_parquet(
        output_path,
        index=False,
    )

    logger.info(
        "%s | months=%d | output=%s",
        path.stem,
        len(monthly),
        output_path.relative_to(PROJECT_ROOT),
    )

    return len(monthly)


def main() -> None:
    if not GOLD_DAILY_DIR.exists():
        raise FileNotFoundError(
            f"Direktori Gold harian tidak ditemukan: "
            f"{GOLD_DAILY_DIR}"
        )

    files = sorted(
        GOLD_DAILY_DIR.glob("*_daily.parquet")
    )

    if not files:
        raise FileNotFoundError(
            f"Tidak ada file Gold harian di {GOLD_DAILY_DIR}"
        )

    total_months = 0

    for path in files:
        total_months += calculate_monthly_metrics(path)

    logger.info(
        "Agregasi bulanan selesai | total_rows=%d",
        total_months,
    )


if __name__ == "__main__":
    main()
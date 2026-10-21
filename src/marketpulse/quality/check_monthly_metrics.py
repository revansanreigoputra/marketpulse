from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

GOLD_MONTHLY_DIR = (
    PROJECT_ROOT / "data" / "gold" / "monthly_metrics"
)

REQUIRED_COLUMNS = {
    "symbol",
    "month",
    "month_end_close",
    "monthly_high",
    "monthly_low",
    "monthly_volume",
    "trading_days",
    "previous_month_end_close",
    "monthly_return_pct",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def check_file(path: Path) -> int:
    """Memeriksa kualitas satu file Gold bulanan."""

    df = pd.read_parquet(path)

    # 1. Periksa kolom wajib.
    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{path.name}: kolom wajib tidak tersedia: "
            f"{sorted(missing_columns)}"
        )

    # 2. Periksa apakah file berisi data.
    if df.empty:
        raise ValueError(
            f"{path.name}: file tidak memiliki baris data"
        )

    # 3. Periksa nilai kosong pada kolom wajib.
    non_nullable_columns = [
        "symbol",
        "month",
        "month_end_close",
        "monthly_high",
        "monthly_low",
        "monthly_volume",
        "trading_days",
    ]

    for column in non_nullable_columns:
        if df[column].isna().any():
            raise ValueError(
                f"{path.name}: ditemukan nilai kosong "
                f"pada kolom {column}"
            )

    # 4. Periksa duplikat simbol dan bulan.
    duplicate_count = int(
        df.duplicated(
            subset=["symbol", "month"]
        ).sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            f"{path.name}: ditemukan "
            f"{duplicate_count} duplikat simbol-bulan"
        )

    # 5. Periksa validitas nilai harga dan volume.
    if (df["month_end_close"] <= 0).any():
        raise ValueError(
            f"{path.name}: harga akhir bulan harus > 0"
        )

    if (df["monthly_high"] <= 0).any():
        raise ValueError(
            f"{path.name}: harga tertinggi harus > 0"
        )

    if (df["monthly_low"] <= 0).any():
        raise ValueError(
            f"{path.name}: harga terendah harus > 0"
        )

    if (df["monthly_volume"] < 0).any():
        raise ValueError(
            f"{path.name}: volume tidak boleh negatif"
        )

    if (df["trading_days"] <= 0).any():
        raise ValueError(
            f"{path.name}: trading_days harus > 0"
        )

    if (
        df["monthly_high"] < df["monthly_low"]
    ).any():
        raise ValueError(
            f"{path.name}: monthly_high lebih kecil "
            "daripada monthly_low"
        )

    if (
        df["month_end_close"] > df["monthly_high"]
    ).any() or (
        df["month_end_close"] < df["monthly_low"]
    ).any():
        raise ValueError(
            f"{path.name}: harga akhir bulan berada "
            "di luar rentang harga bulanan"
        )

    # 6. Periksa urutan periode.
    df = df.sort_values(
        ["symbol", "month"]
    ).reset_index(drop=True)

    month_periods = pd.PeriodIndex(
        df["month"],
        freq="M",
    )

    if month_periods.has_duplicates:
        raise ValueError(
            f"{path.name}: periode bulan duplikat"
        )

    if not month_periods.is_monotonic_increasing:
        raise ValueError(
            f"{path.name}: periode bulan tidak berurutan"
        )

    # 7. Periksa hubungan harga akhir bulan sebelumnya.
    expected_previous_close = (
        df.groupby("symbol")["month_end_close"]
        .shift(1)
    )

    previous_close_matches = (
        df["previous_month_end_close"]
        .isna()
        .eq(expected_previous_close.isna())
    )

    both_present = (
        df["previous_month_end_close"].notna()
        & expected_previous_close.notna()
    )

    previous_close_matches = (
        previous_close_matches
        | (
            both_present
            & (
                (
                    df["previous_month_end_close"]
                    - expected_previous_close
                ).abs() <= 0.01
            )
        )
    )

    if not previous_close_matches.all():
        raise ValueError(
            f"{path.name}: previous_month_end_close "
            "tidak sesuai dengan bulan sebelumnya"
        )

    # 8. Periksa perhitungan return bulanan.
    expected_return = (
        (
            df["month_end_close"]
            / df["previous_month_end_close"]
        ) - 1
    ) * 100

    both_returns_present = (
        df["monthly_return_pct"].notna()
        & expected_return.notna()
    )

    return_matches = (
        df["monthly_return_pct"]
        .isna()
        .eq(expected_return.isna())
    )

    return_matches = (
        return_matches
        | (
            both_returns_present
            & (
                (
                    df["monthly_return_pct"]
                    - expected_return
                ).abs() <= 0.000001
            )
        )
    )

    if not return_matches.all():
        raise ValueError(
            f"{path.name}: monthly_return_pct "
            "tidak sesuai dengan perhitungan"
        )

    logger.info(
        "PASS | %s | rows=%d | months=%d",
        path.name,
        len(df),
        df["month"].nunique(),
    )

    return len(df)


def main() -> None:
    if not GOLD_MONTHLY_DIR.exists():
        raise FileNotFoundError(
            f"Direktori Gold bulanan tidak ditemukan: "
            f"{GOLD_MONTHLY_DIR}"
        )

    files = sorted(
        GOLD_MONTHLY_DIR.glob("*_monthly.parquet")
    )

    if not files:
        raise FileNotFoundError(
            f"Tidak ada file bulanan di {GOLD_MONTHLY_DIR}"
        )

    total_rows = 0

    for path in files:
        total_rows += check_file(path)

    logger.info(
        "QUALITY CHECK BERHASIL | files=%d | rows=%d",
        len(files),
        total_rows,
    )


if __name__ == "__main__":
    main()
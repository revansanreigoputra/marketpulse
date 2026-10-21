from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


# Menentukan direktori utama proyek MarketPulse.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Lokasi data hasil transformasi dan keluaran metrik.
SILVER_DIR = PROJECT_ROOT / "data" / "silver" / "prices"
GOLD_DIR = PROJECT_ROOT / "data" / "gold" / "daily_metrics"

# Mengatur logging untuk memantau proses.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_file(path: Path) -> int:
    """Menghitung metrik harian untuk satu simbol saham."""

    # Membaca data Silver dari format Parquet.
    df = pd.read_parquet(path)

    # Memastikan kolom yang dibutuhkan tersedia.
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

    # Mengurutkan tanggal agar return membandingkan
    # harga hari ini dengan observasi sebelumnya.
    df = df.sort_values(
        ["symbol", "timestamp"]
    ).reset_index(drop=True)

    # Menghitung harga penutupan pada observasi sebelumnya.
    df["previous_close"] = (
        df.groupby("symbol")["close"].shift(1)
    )

    # Return dalam persen. Baris pertama setiap simbol
    # tidak memiliki previous_close sehingga hasilnya kosong.
    df["daily_return_pct"] = (
        (df["close"] / df["previous_close"]) - 1
    ) * 100

    # Rentang harga selama hari tersebut.
    df["daily_range"] = df["high"] - df["low"]

    # Perubahan harga pembukaan ke penutupan dalam persen.
    df["intraday_return_pct"] = (
        (df["close"] / df["open"]) - 1
    ) * 100

    # Membuat folder keluaran jika belum tersedia.
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # Menggunakan nama file yang konsisten agar bisa dijalankan ulang.
    output_path = GOLD_DIR / path.name

    # Menyimpan hasil dalam format Parquet.
    df.to_parquet(output_path, index=False)

    logger.info(
        "%s | rows=%d | output=%s",
        path.stem,
        len(df),
        output_path.relative_to(PROJECT_ROOT),
    )

    return len(df)


def main() -> None:
    """Memproses seluruh file Silver menjadi metrik harian."""

    if not SILVER_DIR.exists():
        raise FileNotFoundError(
            f"Direktori Silver tidak ditemukan: {SILVER_DIR}"
        )

    files = sorted(SILVER_DIR.glob("*_daily.parquet"))

    if not files:
        raise FileNotFoundError(
            f"Tidak ada file Parquet di {SILVER_DIR}"
        )

    total_rows = 0

    for path in files:
        total_rows += calculate_file(path)

    logger.info(
        "Perhitungan metrik harian selesai | total_rows=%d",
        total_rows,
    )


if __name__ == "__main__":
    main()
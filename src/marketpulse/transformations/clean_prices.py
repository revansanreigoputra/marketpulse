from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


# Direktori utama proyek berdasarkan lokasi file ini.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
SILVER_DIR = PROJECT_ROOT / "data" / "silver" / "prices"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"

REQUIRED_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

PRICE_COLUMNS = ["open", "high", "low", "close"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def clean_file(path: Path) -> tuple[int, int]:
    """Membersihkan satu file raw dan menyimpan hasil validasi."""

    # Nama file menjadi identitas simbol, misalnya ibm_daily.csv -> IBM.
    symbol = path.name.removesuffix("_daily.csv").upper()

    # Membaca data sumber tanpa mengubah file raw.
    df = pd.read_csv(path)

    # Memastikan kolom wajib tersedia.
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{path.name}: kolom wajib tidak tersedia: "
            f"{sorted(missing_columns)}"
        )

    # Menambahkan identitas simbol agar data beberapa saham bisa digabung.
    df["symbol"] = symbol

    # Mengubah tanggal dan kolom angka ke tipe yang sesuai.
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    for column in PRICE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    # Menyiapkan alasan validasi untuk setiap baris.
    reasons = pd.Series("", index=df.index, dtype="string")

    def add_reason(condition: pd.Series, message: str) -> None:
        """Mencatat alasan jika suatu baris melanggar aturan."""
        nonlocal reasons
        reasons = reasons.mask(
            condition,
            reasons + message + "; ",
        )

    # Aturan 1: seluruh kolom wajib harus terisi dan dapat dikonversi.
    add_reason(
        df[REQUIRED_COLUMNS].isna().any(axis=1),
        "missing_or_invalid_value",
    )

    # Aturan 2: harga harus positif.
    add_reason(
        df[PRICE_COLUMNS].le(0).any(axis=1),
        "non_positive_price",
    )

    # Aturan 3: volume tidak boleh negatif.
    add_reason(
        df["volume"].lt(0),
        "negative_volume",
    )

    # Aturan 4: high tidak boleh lebih rendah daripada low.
    add_reason(
        df["high"].lt(df["low"]),
        "high_below_low",
    )

    # Aturan 5: open harus berada dalam rentang low sampai high.
    add_reason(
        (df["open"] < df["low"]) | (df["open"] > df["high"]),
        "open_outside_daily_range",
    )

    # Aturan 6: close harus berada dalam rentang low sampai high.
    add_reason(
        (df["close"] < df["low"]) | (df["close"] > df["high"]),
        "close_outside_daily_range",
    )

    # Menentukan duplikat berdasarkan simbol dan tanggal.
    duplicate = df.duplicated(
        subset=["symbol", "timestamp"],
        keep="first",
    )

    add_reason(duplicate, "duplicate_symbol_date")

    # Memisahkan baris valid dan baris yang perlu ditinjau.
    invalid_mask = reasons.ne("")
    invalid = df.loc[invalid_mask].copy()
    valid = df.loc[~invalid_mask].copy()

    # Menambahkan alasan penolakan ke data quarantine.
    if not invalid.empty:
        invalid["rejection_reason"] = reasons.loc[invalid.index]

    # Mengurutkan data Silver dari tanggal terlama ke terbaru.
    valid = valid.sort_values(
        ["symbol", "timestamp"]
    ).reset_index(drop=True)

    # Memastikan folder keluaran tersedia.
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    # Menyimpan data Silver dan quarantine.
    silver_path = SILVER_DIR / f"{symbol.lower()}_daily.parquet"
    valid.to_parquet(silver_path, index=False)

    quarantine_path = (
        QUARANTINE_DIR / f"{symbol.lower()}_rejected.csv"
    )

    if not invalid.empty:
        invalid.to_csv(quarantine_path, index=False)
    elif quarantine_path.exists():
        # Menghindari file penolakan lama dianggap sebagai hasil terbaru.
        quarantine_path.unlink()

    logger.info(
        "%s | raw=%d | silver=%d | rejected=%d",
        symbol,
        len(df),
        len(valid),
        len(invalid),
    )

    return len(valid), len(invalid)


def main() -> None:
    """Memproses seluruh file raw secara berurutan."""

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Direktori raw tidak ditemukan: {RAW_DIR}"
        )

    files = sorted(RAW_DIR.glob("*_daily.csv"))

    if not files:
        raise FileNotFoundError(
            f"Tidak ada file *_daily.csv di {RAW_DIR}"
        )

    total_valid = 0
    total_rejected = 0

    for path in files:
        valid_count, rejected_count = clean_file(path)
        total_valid += valid_count
        total_rejected += rejected_count

    logger.info(
        "Silver selesai | valid=%d | rejected=%d",
        total_valid,
        total_rejected,
    )


if __name__ == "__main__":
    main()

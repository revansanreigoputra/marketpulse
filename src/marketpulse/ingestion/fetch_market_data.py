from __future__ import annotations

import csv
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv


# Menentukan direktori utama proyek MarketPulse.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Memuat API key dari file .env di direktori utama proyek.
load_dotenv(PROJECT_ROOT / ".env")

# Mengatur logging agar proses ingestion dapat dipantau.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Konfigurasi endpoint Alpha Vantage.
API_URL = "https://www.alphavantage.co/query"
CONFIG_PATH = PROJECT_ROOT / "config" / "symbols.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load_config() -> dict:
    """Membaca konfigurasi simbol saham dari YAML."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Format konfigurasi harus berupa mapping YAML.")

    symbols = config.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise ValueError("Konfigurasi 'symbols' harus berupa daftar yang tidak kosong.")

    if config.get("source", {}).get("name") != "alpha_vantage":
        raise ValueError("Sumber data yang didukung saat ini adalah alpha_vantage.")

    return config


def fetch_symbol(
    session: requests.Session,
    symbol: str,
    api_key: str,
) -> Path:
    """Mengambil data harian satu simbol dan menyimpan CSV mentahnya."""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",
        "datatype": "csv",
        "apikey": api_key,
    }

    response = session.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    # Alpha Vantage dapat mengembalikan JSON saat kuota habis atau
    # permintaan tidak valid, walaupun HTTP status-nya 200.
    content_type = response.headers.get("Content-Type", "").lower()
    if "json" in content_type or response.text.lstrip().startswith("{"):
        try:
            message = response.json()
        except ValueError:
            message = {"message": "Respons bukan CSV yang valid."}

        # Jangan mencetak API key atau URL lengkap yang memuat API key.
        raise RuntimeError(
            f"Alpha Vantage tidak mengembalikan CSV untuk {symbol}. "
            f"Pesan layanan: {message}"
        )

    reader = csv.DictReader(response.text.splitlines())
    expected_columns = {"timestamp", "open", "high", "low", "close", "volume"}

    if not reader.fieldnames or not expected_columns.issubset(reader.fieldnames):
        raise ValueError(
            f"Struktur CSV untuk {symbol} tidak sesuai. "
            f"Kolom yang diterima: {reader.fieldnames}"
        )

    rows = list(reader)
    if not rows:
        raise ValueError(f"CSV untuk {symbol} tidak berisi data.")

    # Validasi dasar: tanggal dan harga penutupan harus terisi.
    for row_number, row in enumerate(rows, start=2):
        if not row.get("timestamp") or not row.get("close"):
            raise ValueError(
                f"Data {symbol} tidak lengkap pada baris CSV {row_number}."
            )

        datetime.strptime(row["timestamp"], "%Y-%m-%d")
        float(row["close"])

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Nama file tetap per simbol agar proses dapat dijalankan ulang.
    output_path = RAW_DIR / f"{symbol.lower().replace('.', '_')}_daily.csv"
    output_path.write_text(response.text, encoding="utf-8")

    logger.info(
        "Simbol %s: %s baris tersimpan di %s",
        symbol,
        len(rows),
        output_path.relative_to(PROJECT_ROOT),
    )

    return output_path


def main() -> None:
    """Menjalankan ingestion untuk semua simbol pada konfigurasi."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ALPHA_VANTAGE_API_KEY tidak ditemukan. "
            "Pastikan file .env tersedia di direktori utama proyek."
        )

    config = load_config()
    symbols = config["symbols"]

    logger.info("Memulai ingestion untuk %s simbol.", len(symbols))

    # Session menggunakan koneksi HTTP yang dapat digunakan ulang.
    with requests.Session() as session:
        session.headers.update({"User-Agent": "MarketPulse/1.0"})

        for index, symbol in enumerate(symbols):
            try:
                fetch_symbol(session, symbol, api_key)
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                logger.error("Ingestion untuk %s gagal: %s", symbol, exc)
                raise

            # Beri jeda antarpanggilan agar tidak mengirim request beruntun.
            if index < len(symbols) - 1:
                time.sleep(15)

    logger.info("Ingestion selesai.")


if __name__ == "__main__":
    main()


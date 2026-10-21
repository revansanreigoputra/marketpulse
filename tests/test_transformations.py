import pandas as pd
import pytest

from marketpulse.transformations import clean_prices, calculate_metrics
from marketpulse.aggregations import monthly_metrics


def test_clean_file_valid_and_invalid_rows(tmp_path, monkeypatch):
    raw = tmp_path / "aapl_daily.csv"
    pd.DataFrame([
        {"timestamp": "2026-01-02", "open": 100, "high": 110,
         "low": 95, "close": 105, "volume": 1000},
        {"timestamp": "2026-01-03", "open": 100, "high": 90,
         "low": 95, "close": 105, "volume": 1000},
    ]).to_csv(raw, index=False)

    monkeypatch.setattr(clean_prices, "SILVER_DIR", tmp_path / "silver")
    monkeypatch.setattr(clean_prices, "QUARANTINE_DIR", tmp_path / "quarantine")

    valid, rejected = clean_prices.clean_file(raw)

    assert (valid, rejected) == (1, 1)
    assert len(pd.read_parquet(tmp_path / "silver" / "aapl_daily.parquet")) == 1
    assert len(pd.read_csv(tmp_path / "quarantine" / "aapl_rejected.csv")) == 1


def test_calculate_daily_metrics(tmp_path, monkeypatch):
    source = tmp_path / "aapl_daily.parquet"
    pd.DataFrame([
        {"symbol": "AAPL", "timestamp": "2026-01-03", "open": 110,
         "high": 120, "low": 105, "close": 110, "volume": 200},
        {"symbol": "AAPL", "timestamp": "2026-01-02", "open": 90,
         "high": 105, "low": 85, "close": 100, "volume": 100},
    ]).to_parquet(source, index=False)

    monkeypatch.setattr(calculate_metrics, "GOLD_DIR", tmp_path / "gold")
    monkeypatch.setattr(calculate_metrics, "PROJECT_ROOT", tmp_path)

    rows = calculate_metrics.calculate_file(source)
    result = pd.read_parquet(tmp_path / "gold" / source.name)

    assert rows == 2
    assert pd.isna(result.iloc[0]["previous_close"])
    assert result.iloc[1]["previous_close"] == 100
    assert result.iloc[1]["daily_return_pct"] == pytest.approx(10.0)
    assert result.iloc[1]["daily_range"] == 15
    assert result.iloc[1]["intraday_return_pct"] == pytest.approx(0.0)


def test_calculate_monthly_metrics(tmp_path, monkeypatch):
    source = tmp_path / "aapl_daily.parquet"
    pd.DataFrame([
        {"symbol": "AAPL", "timestamp": "2026-01-02", "open": 90,
         "high": 105, "low": 85, "close": 100, "volume": 100},
        {"symbol": "AAPL", "timestamp": "2026-01-03", "open": 100,
         "high": 120, "low": 95, "close": 110, "volume": 200},
        {"symbol": "AAPL", "timestamp": "2026-02-02", "open": 110,
         "high": 125, "low": 105, "close": 120, "volume": 300},
    ]).to_parquet(source, index=False)

    monkeypatch.setattr(monthly_metrics, "GOLD_MONTHLY_DIR", tmp_path / "monthly")
    monkeypatch.setattr(monthly_metrics, "PROJECT_ROOT", tmp_path)

    months = monthly_metrics.calculate_monthly_metrics(source)
    result = pd.read_parquet(tmp_path / "monthly" / "aapl_monthly.parquet")

    assert months == 2
    assert result.iloc[0]["month"] == "2026-01"
    assert result.iloc[0]["month_end_close"] == 110
    assert result.iloc[0]["monthly_high"] == 120
    assert result.iloc[0]["monthly_low"] == 85
    assert result.iloc[0]["monthly_volume"] == 300
    assert result.iloc[0]["trading_days"] == 2
    assert result.iloc[1]["previous_month_end_close"] == 110
    assert result.iloc[1]["monthly_return_pct"] == pytest.approx(
        (120 / 110 - 1) * 100
    )

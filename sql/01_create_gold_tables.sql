-- sql
-- MarketPulse: membuat tabel Gold pada PostgreSQL
-- DDL (Data Definition Language) digunakan untuk mendefinisikan struktur database.

CREATE TABLE IF NOT EXISTS gold_daily_metrics (
    symbol VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,

    open_price NUMERIC(14, 4) NOT NULL,
    high_price NUMERIC(14, 4) NOT NULL,
    low_price NUMERIC(14, 4) NOT NULL,
    close_price NUMERIC(14, 4) NOT NULL,
    volume BIGINT NOT NULL,

    previous_close NUMERIC(14, 4),
    daily_return_pct NUMERIC(12, 6),
    daily_range NUMERIC(14, 4),
    intraday_return_pct NUMERIC(12, 6),

    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_gold_daily_metrics
        PRIMARY KEY (symbol, trade_date),

    CONSTRAINT chk_daily_prices_positive
        CHECK (
            open_price > 0
            AND high_price > 0
            AND low_price > 0
            AND close_price > 0
        ),

    CONSTRAINT chk_daily_high_low
        CHECK (high_price >= low_price),

    CONSTRAINT chk_daily_volume
        CHECK (volume >= 0)
);


CREATE TABLE IF NOT EXISTS gold_monthly_metrics (
    symbol VARCHAR(10) NOT NULL,

    -- Disimpan sebagai tanggal pertama bulan, misalnya 2026-01-01.
    month DATE NOT NULL,

    month_end_close NUMERIC(14, 4) NOT NULL,
    monthly_high NUMERIC(14, 4) NOT NULL,
    monthly_low NUMERIC(14, 4) NOT NULL,
    monthly_volume BIGINT NOT NULL,
    trading_days INTEGER NOT NULL,

    previous_month_end_close NUMERIC(14, 4),
    monthly_return_pct NUMERIC(12, 6),

    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_gold_monthly_metrics
        PRIMARY KEY (symbol, month),

    CONSTRAINT chk_monthly_prices_positive
        CHECK (
            month_end_close > 0
            AND monthly_high > 0
            AND monthly_low > 0
        ),

    CONSTRAINT chk_monthly_high_low
        CHECK (monthly_high >= monthly_low),

    CONSTRAINT chk_monthly_volume
        CHECK (monthly_volume >= 0),

    CONSTRAINT chk_monthly_trading_days
        CHECK (trading_days > 0)
);
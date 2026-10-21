import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Baca konfigurasi database dari .env di root proyek.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)


def get_engine():
    """Membuat koneksi SQLAlchemy ke PostgreSQL."""
    required = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Konfigurasi .env belum lengkap: " + ", ".join(missing)
        )

    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB"),
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=60)
def load_daily_data():
    """Membaca data Gold harian."""
    query = text("""
        SELECT
            symbol,
            trade_date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            previous_close,
            daily_return_pct,
            daily_range,
            intraday_return_pct
        FROM gold_daily_metrics
        ORDER BY trade_date, symbol
    """)
    with get_engine().connect() as conn:
        df = pd.read_sql_query(query, conn)

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


@st.cache_data(ttl=60)
def load_monthly_data():
    """Membaca data Gold bulanan."""
    query = text("""
        SELECT
            symbol,
            month,
            month_end_close,
            monthly_high,
            monthly_low,
            monthly_volume,
            trading_days,
            previous_month_end_close,
            monthly_return_pct
        FROM gold_monthly_metrics
        ORDER BY month, symbol
    """)
    with get_engine().connect() as conn:
        df = pd.read_sql_query(query, conn)

    df["month"] = pd.to_datetime(df["month"])
    return df


st.set_page_config(
    page_title="MarketPulse Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 MarketPulse")
st.caption("Dashboard analitik harga saham berbasis data Gold PostgreSQL.")

try:
    daily = load_daily_data()
    monthly = load_monthly_data()
except Exception as exc:
    st.error(
        "Dashboard gagal membaca data PostgreSQL. "
        "Periksa status container, konfigurasi .env, dan nama tabel."
    )
    st.exception(exc)
    st.stop()

if daily.empty:
    st.warning("Tabel gold_daily_metrics belum memiliki data.")
    st.stop()

# Filter di sidebar.
st.sidebar.header("Filter Data")

symbols = sorted(daily["symbol"].dropna().unique().tolist())
selected_symbols = st.sidebar.multiselect(
    "Pilih simbol saham",
    options=symbols,
    default=symbols,
)

min_date = daily["trade_date"].min().date()
max_date = daily["trade_date"].max().date()

date_range = st.sidebar.date_input(
    "Rentang tanggal",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if not selected_symbols:
    st.info("Pilih minimal satu simbol saham pada sidebar.")
    st.stop()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, date):
    start_date = end_date = date_range
else:
    st.warning("Pilih rentang tanggal yang valid.")
    st.stop()

filtered_daily = daily[
    daily["symbol"].isin(selected_symbols)
    & daily["trade_date"].dt.date.between(start_date, end_date)
].copy()

filtered_monthly = monthly[
    monthly["symbol"].isin(selected_symbols)
    & monthly["month"].dt.date.between(start_date, end_date)
].copy()

# KPI.
total_rows = len(filtered_daily)
symbol_count = filtered_daily["symbol"].nunique()
latest_date = (
    filtered_daily["trade_date"].max().strftime("%d %b %Y")
    if total_rows
    else "-"
)

valid_returns = filtered_daily["daily_return_pct"].dropna()
avg_return = valid_returns.mean() if not valid_returns.empty else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("Data harian", f"{total_rows:,}")
k2.metric("Jumlah saham", symbol_count)
k3.metric("Tanggal terbaru", latest_date)
k4.metric(
    "Rata-rata return harian",
    f"{avg_return:.4f}%" if avg_return is not None else "N/A",
)

st.divider()

# Grafik harga penutupan.
st.subheader("Harga Penutupan Harian")
if filtered_daily.empty:
    st.info("Tidak ada data pada filter yang dipilih.")
else:
    fig_price = px.line(
        filtered_daily,
        x="trade_date",
        y="close_price",
        color="symbol",
        markers=True,
        labels={
            "trade_date": "Tanggal",
            "close_price": "Harga penutupan",
            "symbol": "Simbol",
        },
    )
    fig_price.update_layout(legend_title_text="Saham")
    st.plotly_chart(fig_price, use_container_width=True)

# Return harian.
st.subheader("Return Harian")
if filtered_daily["daily_return_pct"].notna().any():
    fig_return = px.line(
        filtered_daily,
        x="trade_date",
        y="daily_return_pct",
        color="symbol",
        labels={
            "trade_date": "Tanggal",
            "daily_return_pct": "Return (%)",
            "symbol": "Simbol",
        },
    )
    fig_return.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_return, use_container_width=True)
else:
    st.info("Belum ada nilai return harian pada rentang ini.")

# Ringkasan bulanan.
st.subheader("Kinerja Bulanan")
if filtered_monthly.empty:
    st.info("Tidak ada data bulanan pada filter yang dipilih.")
else:
    fig_monthly = px.bar(
        filtered_monthly,
        x="month",
        y="monthly_return_pct",
        color="symbol",
        barmode="group",
        labels={
            "month": "Periode",
            "monthly_return_pct": "Return bulanan (%)",
            "symbol": "Simbol",
        },
    )
    fig_monthly.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_monthly, use_container_width=True)

# Tabel data harian.
with st.expander("Lihat data Gold harian"):
    st.dataframe(
        filtered_daily.sort_values(
            ["trade_date", "symbol"], ascending=[False, True]
        ),
        use_container_width=True,
        hide_index=True,
    )

# Tabel data bulanan.
with st.expander("Lihat data Gold bulanan"):
    st.dataframe(
        filtered_monthly.sort_values(
            ["month", "symbol"], ascending=[False, True]
        ),
        use_container_width=True,
        hide_index=True,
    )

st.caption("Data ditarik dari PostgreSQL. Cache dashboard berlaku selama 60 detik.")

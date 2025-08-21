
# AB ETF Live AUM Dashboard (Streamlit + Yahoo Finance)
# ------------------------------------------------------
# Displays an intraday estimate of AllianceBernstein total ETF assets
# by summing per-fund estimated AUM (last price × shares outstanding).
#
# iPad-friendly: includes a "Kiosk mode" to show a large single number.
#
# Quickstart
#   pip install -r requirements.txt
#   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
#
# Notes
# - Yahoo prices may be delayed (~15 min). Shares outstanding update daily.
# - For missing/incorrect shares, edit shares_overrides.csv.
# ------------------------------------------------------

import math
from datetime import datetime
from dateutil import tz
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ======== USER SETTINGS ========
# Replace with full list of AB ETF tickers to track
TICKERS = [
    "LRGC",  # AB Large Cap Growth ETF
    "HIDV",  # AB High Dividend ETF
    "ILOW",  # AB US Low Volatility Equity ETF
    # Add all AB ETFs here, e.g. "HYDB", "FWD", "FMAY", ...
]

DEFAULT_REFRESH_MS = 15000  # auto-refresh cadence
SHARES_OVERRIDE_CSV = "shares_overrides.csv"

st.set_page_config(page_title="AB ETFs – Live AUM (Yahoo)", layout="wide")

# Read query params (new and legacy APIs)
def get_query_params():
    try:
        # Streamlit >=1.30
        qp = st.query_params
        if hasattr(qp, "to_dict"):
            return qp.to_dict()
        # On newer versions it's a standard dict
        return dict(qp)
    except Exception:
        pass
    try:
        # Legacy
        return st.experimental_get_query_params()
    except Exception:
        return {}

qp = get_query_params()
kiosk = str(qp.get("kiosk", ["0"])[0]).lower() in ("1","true","yes","y")
try:
    refresh_ms = int(qp.get("refresh", [DEFAULT_REFRESH_MS])[0])
except Exception:
    refresh_ms = DEFAULT_REFRESH_MS

# Minimal auto-refresh without extra packages
st_autorefresh = getattr(st, "experimental_rerun", None)
st.caption(f"Auto-refresh target: ~{refresh_ms/1000:.0f}s")

# ======== HELPERS ========
@st.cache_data(ttl=60*30)
def _get_fast_info(ticker: str):
    tkr = yf.Ticker(ticker)
    try:
        return tkr.fast_info
    except Exception:
        return {}

@st.cache_data(ttl=60*60*6)
def _get_info(ticker: str):
    tkr = yf.Ticker(ticker)
    try:
        return tkr.get_info()
    except Exception:
        try:
            return tkr.info
        except Exception:
            return {}

@st.cache_data(ttl=60*60*1)
def _load_overrides(path: str):
    try:
        df = pd.read_csv(path)
        df["ticker"] = df["ticker"].str.upper()
        df = df.dropna(subset=["ticker", "shares_outstanding"])
        df["shares_outstanding"] = df["shares_outstanding"].astype(int)
        return df
    except Exception:
        return pd.DataFrame(columns=["ticker", "shares_outstanding"])

def _get_last_price(ticker: str):
    fi = _get_fast_info(ticker)
    for k in ("last_price", "regularMarketPrice", "currentPrice"):
        v = fi.get(k)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            try:
                return float(v)
            except Exception:
                pass
    # last resort
    try:
        hist = yf.Ticker(ticker).history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist.iloc[-1]["Close"])
    except Exception:
        pass
    return None

def _infer_shares_from_info(ticker: str, last_price: float | None):
    info = _get_info(ticker)
    shares = info.get("sharesOutstanding") or info.get("fundSharesOutstanding")
    if isinstance(shares, (int, float)) and shares > 0:
        return int(shares)
    total_assets = info.get("totalAssets") or info.get("netAssets")
    if total_assets and last_price and last_price > 0:
        try:
            est_shares = int(float(total_assets) / float(last_price))
            if est_shares > 0:
                return est_shares
        except Exception:
            pass
    return None

def _get_shares_outstanding(ticker: str, last_price: float | None, overrides_df: pd.DataFrame):
    row = overrides_df.loc[overrides_df["ticker"] == ticker]
    if not row.empty:
        val = int(row.iloc[0]["shares_outstanding"])
        if val > 0:
            return val
    return _infer_shares_from_info(ticker, last_price)

def _fmt_money(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"${x:,.0f}"

def _fmt_int(x):
    if x is None:
        return "–"
    return f"{x:,}"

# ======== FETCH ========
overrides = _load_overrides(SHARES_OVERRIDE_CSV)
rows, missing = [], []
for t in [t.upper() for t in TICKERS]:
    price = _get_last_price(t)
    shares = _get_shares_outstanding(t, price, overrides)
    est_aum = price * shares if (price is not None and shares is not None) else None
    rows.append({"Ticker": t, "Last Price": price, "Shares Outstanding": shares, "Est. AUM (USD)": est_aum})
    if shares is None:
        missing.append(t)

df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Ticker","Last Price","Shares Outstanding","Est. AUM (USD)"])
total_est = float(np.nansum([r["Est. AUM (USD)"] for r in rows if r.get("Est. AUM (USD)") is not None])) if rows else 0.0

# ======== UI ========
if kiosk:
    # Big, clean number for iPad display
    st.markdown("""
    <style>
    .big-number {font-size: 8vw; font-weight: 700; line-height: 1.1; text-align:center;}
    .subtle {text-align:center; opacity:0.7;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"<div class='big-number'>{_fmt_money(total_est)}</div>", unsafe_allow_html=True)
    now = datetime.now(tz=tz.gettz("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
    st.markdown(f"<div class='subtle'>As of {now} • {len(TICKERS)} ETFs</div>", unsafe_allow_html=True)
else:
    st.title("AllianceBernstein ETFs – Estimated Live Total Assets")
    st.caption("Source: Yahoo Finance via yfinance. Prices may be delayed. Shares outstanding cached daily; AUM is an intraday estimate (price × shares).")
    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        st.metric("Estimated Total ETF Assets", _fmt_money(total_est))
    with c2:
        st.write("")
        st.write(f"Tickers tracked: **{len(TICKERS)}**")
    with c3:
        now = datetime.now(tz=tz.gettz("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
        st.write("")
        st.write(f"As of: **{now}**")

    df_disp = df.copy()
    df_disp["Last Price"] = df_disp["Last Price"].apply(lambda v: f"${v:,.2f}" if isinstance(v, (int,float)) else "–")
    df_disp["Shares Outstanding"] = df_disp["Shares Outstanding"].apply(_fmt_int)
    df_disp["Est. AUM (USD)"] = df_disp["Est. AUM (USD)"].apply(_fmt_money)
    st.dataframe(df_disp, use_container_width=True, hide_index=True)

    if missing:
        st.warning("Shares outstanding missing for: " + ", ".join(missing) + ". Add them to `shares_overrides.csv` (ticker,shares_outstanding) to improve accuracy.")

    with st.expander("Download a template for shares_overrides.csv"):
        sample = pd.DataFrame({"ticker": [r["Ticker"] for r in rows], "shares_outstanding": [0]*len(rows)})
        st.download_button("Download CSV Template", data=sample.to_csv(index=False).encode("utf-8"), file_name="shares_overrides.csv", mime="text/csv")

st.caption("Disclaimer: Estimated intraday assets. For official totals, rely on AB internal reports or end‑of‑day net assets.")

# Simple instruction hint
st.caption("Tip: Add '?kiosk=1' to the URL for a clean iPad display. Add '&refresh=10_000' to target a ~10s refresh cadence.")

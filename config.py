"""
config.py
Central configuration for the Indian Equity Swing Trading Analyst system.
Edit the values in this file to change account parameters or the stock universe.
Secrets (Telegram token, chat id, broker keys) are NOT stored here — they are read
from environment variables / GitHub Actions secrets. See README.md.
"""

import os

# ---------------------------------------------------------------------------
# ACCOUNT PARAMETERS (from the master trading prompt)
# ---------------------------------------------------------------------------
TOTAL_CAPITAL = 30_000
MAX_RISK_PER_TRADE = 1_500          # 5% of capital, absolute ceiling
MAX_POSITIONS = 2
MAX_CAPITAL_PER_STOCK = 21_000       # 70% of capital
MIN_REWARD_RISK = 2.0

# ---------------------------------------------------------------------------
# SCORING WEIGHTS (Step 5 of the master prompt) — must sum to 100
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "market_regime": 15,
    "sector_strength": 15,
    "trend": 20,
    "relative_strength": 15,
    "price_structure": 15,
    "volume_confirmation": 10,
    "fundamental_catalyst": 10,
}

SCORE_ACTIONABLE_MIN = 75
SCORE_WATCHLIST_MIN = 70

# ---------------------------------------------------------------------------
# TELEGRAM (secrets pulled from environment — see README)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# DATA SOURCE
# ---------------------------------------------------------------------------
# "yfinance"  -> free, ~15-20 min delayed, no key needed
# "dhan"      -> Dhan API, needs DHAN_CLIENT_ID + DHAN_ACCESS_TOKEN env vars
DATA_SOURCE = os.environ.get("DATA_SOURCE", "yfinance")

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN", "")

# ---------------------------------------------------------------------------
# INDEX / BENCHMARK
# ---------------------------------------------------------------------------
NIFTY_TICKER = "^NSEI"

# ---------------------------------------------------------------------------
# STOCK UNIVERSE
# A curated list of liquid NSE large & mid-cap stocks (Nifty 200-ish universe).
# Trim or extend this list freely. Tickers use the Yahoo Finance ".NS" suffix.
# Grouped loosely by sector so sector-relative-strength ranking works.
# ---------------------------------------------------------------------------
STOCK_UNIVERSE = {
    "Banking & Financials": [
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS",
        "INDUSINDBK.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS",
        "SBILIFE.NS", "ICICIGI.NS", "ICICIPRULI.NS", "CHOLAFIN.NS", "PFC.NS", "RECLTD.NS",
    ],
    "IT": [
        "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS",
        "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS",
    ],
    "Auto": [
        "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
        "HEROMOTOCO.NS", "TVSMOTOR.NS", "ASHOKLEY.NS", "BHARATFORG.NS",
    ],
    "Pharma & Healthcare": [
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS",
        "LUPIN.NS", "AUROPHARMA.NS", "TORNTPHARM.NS", "MAXHEALTH.NS",
    ],
    "FMCG": [
        "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS",
        "DABUR.NS", "MARICO.NS", "GODREJCP.NS", "VBL.NS",
    ],
    "Energy & Oil/Gas": [
        "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS",
        "BPCL.NS", "GAIL.NS", "IOC.NS", "ADANIGREEN.NS", "TATAPOWER.NS",
    ],
    "Metals & Mining": [
        "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "JINDALSTEL.NS",
        "SAIL.NS", "NMDC.NS",
    ],
    "Capital Goods & Infra": [
        "LT.NS", "SIEMENS.NS", "ABB.NS", "CUMMINSIND.NS", "BHEL.NS",
        "ADANIPORTS.NS", "GMRINFRA.NS", "IRCTC.NS",
    ],
    "Cement & Building Materials": [
        "ULTRACEMCO.NS", "SHREECEM.NS", "AMBUJACEM.NS", "ACC.NS", "DALBHARAT.NS",
    ],
    "Consumer Durables & Retail": [
        "TITAN.NS", "DMART.NS", "TRENT.NS", "HAVELLS.NS", "VOLTAS.NS",
        "PIDILITIND.NS", "ASIANPAINT.NS",
    ],
    "Telecom": [
        "BHARTIARTL.NS", "IDEA.NS",
    ],
    "Chemicals": [
        "PIIND.NS", "SRF.NS", "UPL.NS", "DEEPAKNTR.NS", "AARTIIND.NS",
    ],
}

def all_tickers():
    tickers = []
    for group in STOCK_UNIVERSE.values():
        tickers.extend(group)
    return tickers

def sector_of(ticker):
    for sector, tickers in STOCK_UNIVERSE.items():
        if ticker in tickers:
            return sector
    return "Unknown"
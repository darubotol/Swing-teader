"""
data_fetcher.py
Handles pulling OHLCV history for the NIFTY index and the stock universe.

Two data sources:
- "yfinance" (default): free, end-of-day, no key required.
- "dhan": your Dhan account's market data via their v2 API. Needs
  DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN set as GitHub Actions secrets, and
  DATA_SOURCE=dhan in the workflow's env block.

Honesty note on the Dhan path: this was built from Dhan's documented API
structure but has NOT been tested against their live service (no network
access during development). Field names or response shape may need small
adjustments once you run it for real — if it errors, copy the exact message
and it's a quick fix, not a sign of a deeper problem.
"""

import io
import time
import datetime
import pandas as pd
import requests
import yfinance as yf

import config


class DataUnavailableError(Exception):
    """Raised when reliable current data cannot be obtained for a ticker."""
    pass


# ---------------------------------------------------------------------------
# yfinance path (default, free, no key)
# ---------------------------------------------------------------------------

def _fetch_history_yfinance(ticker: str, period: str = "1y", interval: str = "1d", retries: int = 3) -> pd.DataFrame:
    last_err = None
    for attempt in range(retries):
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
            if df is None or df.empty or len(df) < 60:
                raise DataUnavailableError(f"Insufficient history for {ticker}")
            return df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5)
    raise DataUnavailableError(f"Could not fetch data for {ticker}: {last_err}")


# ---------------------------------------------------------------------------
# Dhan v2 API path
# ---------------------------------------------------------------------------

SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
DHAN_HISTORICAL_URL = "https://api.dhan.co/v2/charts/historical"

# Dhan's Security ID for the NIFTY 50 index (IDX_I segment). Commonly
# documented as "13" — if NIFTY data comes back empty on the Dhan path,
# this is the first thing to verify against Dhan's own docs or scrip master.
NIFTY_SECURITY_ID = "13"
NIFTY_EXCHANGE_SEGMENT = "IDX_I"

_scrip_master_cache = None


def _load_scrip_master() -> pd.DataFrame:
    global _scrip_master_cache
    if _scrip_master_cache is not None:
        return _scrip_master_cache
    resp = requests.get(SCRIP_MASTER_URL, timeout=30)
    resp.raise_for_status()
    _scrip_master_cache = pd.read_csv(io.StringIO(resp.text))
    return _scrip_master_cache


def _dhan_security_id(ticker: str) -> str:
    """Map a ticker like 'RELIANCE.NS' to Dhan's numeric Security ID for NSE equity."""
    symbol = ticker.replace(".NS", "")
    master = _load_scrip_master()
    match = master[
        (master["SEM_EXM_EXCH_ID"] == "NSE")
        & (master["SEM_SEGMENT"] == "E")
        & (master["SEM_TRADING_SYMBOL"] == symbol)
    ]
    if match.empty:
        raise DataUnavailableError(f"No Dhan security ID found for {ticker} in scrip master")
    return str(match.iloc[0]["SEM_SMST_SECURITY_ID"])


def _parse_dhan_response(data: dict) -> pd.DataFrame:
    required = ["open", "high", "low", "close", "volume", "timestamp"]
    missing = [k for k in required if k not in data]
    if missing:
        raise DataUnavailableError(f"Unexpected Dhan response shape, missing keys: {missing}")
    dates = pd.to_datetime([datetime.datetime.fromtimestamp(t) for t in data["timestamp"]])
    df = pd.DataFrame({
        "Open": data["open"], "High": data["high"], "Low": data["low"],
        "Close": data["close"], "Volume": data["volume"],
    }, index=dates)
    return df


def _fetch_history_dhan(ticker: str, period: str = "1y", is_index: bool = False, retries: int = 3) -> pd.DataFrame:
    if not config.DHAN_CLIENT_ID or not config.DHAN_ACCESS_TOKEN:
        raise DataUnavailableError("DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN not set")

    years = {"1y": 1, "2y": 2, "5y": 5}.get(period, 1)
    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=365 * years + 10)

    if is_index:
        security_id, exchange_segment, instrument = NIFTY_SECURITY_ID, NIFTY_EXCHANGE_SEGMENT, "INDEX"
    else:
        security_id = _dhan_security_id(ticker)
        exchange_segment, instrument = "NSE_EQ", "EQUITY"

    headers = {
        "access-token": config.DHAN_ACCESS_TOKEN,
        "client-id": config.DHAN_CLIENT_ID,
        "Content-Type": "application/json",
    }
    body = {
        "securityId": security_id,
        "exchangeSegment": exchange_segment,
        "instrument": instrument,
        "expiryCode": 0,
        "fromDate": from_date.isoformat(),
        "toDate": to_date.isoformat(),
    }

    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.post(DHAN_HISTORICAL_URL, json=body, headers=headers, timeout=30)
            resp.raise_for_status()
            df = _parse_dhan_response(resp.json())
            if len(df) < 60:
                raise DataUnavailableError(f"Insufficient history for {ticker}")
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5)
    raise DataUnavailableError(f"Could not fetch Dhan data for {ticker}: {last_err}")


# ---------------------------------------------------------------------------
# Public dispatch — everything else in the codebase calls only these
# ---------------------------------------------------------------------------

def fetch_history(ticker: str, period: str = "1y", interval: str = "1d", retries: int = 3) -> pd.DataFrame:
    """
    Fetch OHLCV history for a single ticker, using whichever source is
    configured in config.DATA_SOURCE. Returns a DataFrame with columns:
    Open, High, Low, Close, Volume. Raises DataUnavailableError on failure.
    """
    if config.DATA_SOURCE == "dhan":
        return _fetch_history_dhan(ticker, period=period, retries=retries)
    return _fetch_history_yfinance(ticker, period=period, interval=interval, retries=retries)


def fetch_nifty(period: str = "1y") -> pd.DataFrame:
    if config.DATA_SOURCE == "dhan":
        return _fetch_history_dhan(config.NIFTY_TICKER, period=period, is_index=True)
    return _fetch_history_yfinance(config.NIFTY_TICKER, period=period)


def fetch_universe(period: str = "1y") -> dict:
    """
    Fetch history for every ticker in the configured universe.
    Returns {ticker: DataFrame}. Tickers that fail are skipped (logged, not invented).
    """
    data = {}
    failed = []
    for ticker in config.all_tickers():
        try:
            data[ticker] = fetch_history(ticker, period=period)
        except DataUnavailableError:
            failed.append(ticker)
    if failed:
        print(f"[data_fetcher] WARNING — no reliable data for: {', '.join(failed)}")
    return data


def data_timestamp() -> str:
    """
    Human-readable note on data freshness. Daily-bar data reflects the most
    recently completed session; it is NOT live intraday data (the intraday
    monitor script is the only part of this system using finer-grained data).
    """
    now = datetime.datetime.now()
    return f"{now.strftime('%Y-%m-%d %H:%M')} IST (source: {config.DATA_SOURCE}, end-of-day data, not live intraday)"

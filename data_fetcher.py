"""
data_fetcher.py
Handles pulling OHLCV history for the NIFTY index and the stock universe.

Default source: yfinance (free, end-of-day / ~15-20 min delayed, no key required).
A Dhan API path is stubbed out for later — Dhan gives you real broker-grade data,
but you should NEVER paste API keys into a chat. Store them as GitHub Actions
secrets (DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN) and set DATA_SOURCE=dhan when ready.
"""

import time
import pandas as pd
import yfinance as yf

import config


class DataUnavailableError(Exception):
    """Raised when reliable current data cannot be obtained for a ticker."""
    pass


def fetch_history(ticker: str, period: str = "1y", interval: str = "1d", retries: int = 3) -> pd.DataFrame:
    """
    Fetch OHLCV history for a single ticker.
    Returns a DataFrame with columns: Open, High, Low, Close, Volume.
    Raises DataUnavailableError if data can't be retrieved after retries.
    """
    last_err = None
    for attempt in range(retries):
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
            if df is None or df.empty or len(df) < 60:
                raise DataUnavailableError(f"Insufficient history for {ticker}")
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5)
    raise DataUnavailableError(f"Could not fetch data for {ticker}: {last_err}")


def fetch_nifty(period: str = "1y") -> pd.DataFrame:
    return fetch_history(config.NIFTY_TICKER, period=period)


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
    Human-readable note on data freshness. yfinance daily data reflects the
    most recently completed session; it is NOT live intraday data.
    """
    import datetime
    now = datetime.datetime.now()
    return f"{now.strftime('%Y-%m-%d %H:%M')} IST (source: {config.DATA_SOURCE}, end-of-day data, not live intraday)"

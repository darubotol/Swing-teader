"""
analysis.py
Implements STEP 2 (sector strength), STEP 3 (universe filter), STEP 4 (setup
detection) and STEP 5 (scoring model) of the master prompt.

This is a rule-based, technical-only engine. It does NOT invent fundamentals,
news, or catalysts — Step 6 (fundamental/event check) and Step 7 (devil's
advocate) still require a human read of any 75+ candidate before acting,
because that information isn't reliably available from free price data alone.
The report explicitly flags this.
"""

import pandas as pd
import config


# ---------------------------------------------------------------------------
# STEP 2 — SECTOR STRENGTH
# ---------------------------------------------------------------------------

def rank_sectors(universe_data: dict, lookback: int = 20) -> list:
    """
    Rank sectors by average N-day return of their constituent stocks.
    Returns list of (sector, avg_return_pct) sorted strongest first.
    Stocks with a NaN return (occasional Yahoo Finance data gaps) are
    skipped rather than poisoning the sector average.
    """
    sector_returns = {}
    for sector, tickers in config.STOCK_UNIVERSE.items():
        rets = []
        for t in tickers:
            df = universe_data.get(t)
            if df is None or len(df) <= lookback:
                continue
            r = (df["Close"].iloc[-1] / df["Close"].iloc[-lookback - 1] - 1) * 100
            if r != r:  # NaN check (NaN is never equal to itself)
                continue
            rets.append(r)
        if rets:
            sector_returns[sector] = sum(rets) / len(rets)
    return sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# STEP 3 / STEP 4 — PER-STOCK TECHNICAL ANALYSIS + SETUP DETECTION
# ---------------------------------------------------------------------------

def _atr(df: pd.DataFrame, window: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean().iloc[-1]


def analyze_stock(ticker: str, df: pd.DataFrame, nifty_df: pd.DataFrame) -> dict:
    """
    Analyze a single stock and detect the best-fit setup (breakout, breakout
    retest, or trend pullback). Returns None if the stock fails basic
    liquidity/trend filters and isn't worth scoring.
    """
    if len(df) < 60:
        return None

    close = df["Close"].iloc[-1]
    dma20 = df["Close"].rolling(20).mean().iloc[-1]
    dma50 = df["Close"].rolling(50).mean().iloc[-1]
    dma200 = df["Close"].rolling(200).mean().iloc[-1] if len(df) >= 200 else None
    dma50_series = df["Close"].rolling(50).mean()
    dma50_rising = dma50_series.diff().iloc[-1] > 0

    avg_vol_20 = df["Volume"].tail(20).mean()
    avg_vol_50 = df["Volume"].tail(50).mean()
    last_vol = df["Volume"].iloc[-1]

    # --- Liquidity filter ---------------------------------------------------
    # Rough free-float turnover proxy: skip very low-traded names.
    if avg_vol_20 < 50_000:
        return None

    # --- Relative strength vs NIFTY -----------------------------------------
    def ret(series, n):
        if len(series) <= n:
            return None
        return (series.iloc[-1] / series.iloc[-n - 1] - 1) * 100

    stock_ret_20 = ret(df["Close"], 20)
    nifty_ret_20 = ret(nifty_df["Close"], 20)
    stock_ret_50 = ret(df["Close"], 50)
    nifty_ret_50 = ret(nifty_df["Close"], 50)

    rs_20 = (stock_ret_20 - nifty_ret_20) if (stock_ret_20 is not None and nifty_ret_20 is not None) else None
    rs_50 = (stock_ret_50 - nifty_ret_50) if (stock_ret_50 is not None and nifty_ret_50 is not None) else None

    # --- Trend filter ---------------------------------------------------------
    above_50 = close > dma50
    above_200 = (close > dma200) if dma200 else None

    trend_score = 0
    if above_50:
        trend_score += 10
    if dma50_rising:
        trend_score += 5
    if above_200:
        trend_score += 5

    if trend_score < 10:
        # Doesn't meet minimum trend requirement (Step 3A) — skip entirely.
        return None

    # --- Setup detection --------------------------------------------------
    high_20 = df["High"].tail(21)[:-1].max()   # prior 20-day high, excluding today
    low_20 = df["Low"].tail(20).min()
    consolidation_range = (high_20 - low_20) / close if close else 0

    setup = None
    entry = stop = target = None
    structure_notes = []

    breakout_today = close > high_20 and last_vol > 1.3 * avg_vol_20
    near_resistance_retest = (
        high_20 * 0.97 <= close <= high_20 * 1.02
        and df["Close"].iloc[-5:-1].max() > high_20  # broke out within last few days
    )
    pullback_to_support = (
        above_50 and dma50_rising
        and (abs(close - dma20) / close < 0.02 or abs(close - dma50) / close < 0.02)
        and last_vol < avg_vol_20  # controlled/lighter volume on the pullback
    )

    atr = _atr(df)

    if breakout_today and consolidation_range < 0.18:
        setup = "Breakout"
        entry = round(high_20 * 1.003, 2)  # confirmation buffer above resistance
        stop = round(min(low_20, close - 1.5 * atr), 2)
        target = round(entry + 2.2 * (entry - stop), 2)
        structure_notes.append(f"Breakout above {high_20:.1f} resistance with volume {last_vol/avg_vol_20:.1f}x the 20-day average.")
    elif near_resistance_retest:
        setup = "Breakout Retest"
        entry = round(close * 1.005, 2)
        stop = round(min(low_20, high_20 * 0.96), 2)
        target = round(entry + 2.2 * (entry - stop), 2)
        structure_notes.append(f"Price retesting prior breakout zone near {high_20:.1f}.")
    elif pullback_to_support:
        setup = "Trend Pullback"
        support_level = dma20 if abs(close - dma20) / close < abs(close - dma50) / close else dma50
        entry = round(close * 1.005, 2)
        stop = round(support_level * 0.975, 2)
        target = round(entry + 2.2 * (entry - stop), 2)
        structure_notes.append(f"Pullback toward {'20' if support_level==dma20 else '50'}-DMA in an established uptrend.")
    else:
        return None  # no qualifying setup — do not manufacture one

    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return None
    reward_risk = (target - entry) / risk_per_share

    return {
        "ticker": ticker,
        "sector": config.sector_of(ticker),
        "close": close,
        "dma20": dma20,
        "dma50": dma50,
        "dma200": dma200,
        "above_200": above_200,
        "dma50_rising": dma50_rising,
        "rs_20": rs_20,
        "rs_50": rs_50,
        "avg_vol_20": avg_vol_20,
        "vol_ratio": last_vol / avg_vol_20 if avg_vol_20 else None,
        "atr": atr,
        "setup": setup,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_per_share": round(risk_per_share, 2),
        "reward_risk": round(reward_risk, 2),
        "trend_score_raw": trend_score,
        "structure_notes": structure_notes,
    }


# ---------------------------------------------------------------------------
# STEP 5 — SCORING MODEL
# ---------------------------------------------------------------------------

def score_candidate(stock_info: dict, regime: dict, sector_rank: int, num_sectors: int) -> dict:
    w = config.SCORE_WEIGHTS
    score = 0
    breakdown = {}

    # Market regime (15)
    regime_pts = {"GREEN": w["market_regime"], "YELLOW": w["market_regime"] * 0.6, "RED": 0}
    breakdown["market_regime"] = round(regime_pts[regime["regime"]], 1)
    score += breakdown["market_regime"]

    # Sector strength (15) — top-ranked sector gets full points, scaled down by rank
    if num_sectors > 0:
        sector_pct = max(0, 1 - (sector_rank / num_sectors))
        breakdown["sector_strength"] = round(w["sector_strength"] * sector_pct, 1)
    else:
        breakdown["sector_strength"] = 0
    score += breakdown["sector_strength"]

    # Trend (20) — from trend_score_raw (max 20 in our detection: 10+5+5)
    breakdown["trend"] = round(w["trend"] * (stock_info["trend_score_raw"] / 20), 1)
    score += breakdown["trend"]

    # Relative strength (15)
    rs20 = stock_info.get("rs_20") or 0
    rs_pts = 0
    if rs20 > 5:
        rs_pts = w["relative_strength"]
    elif rs20 > 0:
        rs_pts = w["relative_strength"] * 0.6
    elif rs20 > -3:
        rs_pts = w["relative_strength"] * 0.3
    breakdown["relative_strength"] = round(rs_pts, 1)
    score += breakdown["relative_strength"]

    # Price structure / setup quality (15) — flat award since a setup was found;
    # breakout retest scores slightly higher (more confirmation) than raw breakout
    structure_pts = {"Breakout": 0.8, "Breakout Retest": 1.0, "Trend Pullback": 0.85}
    breakdown["price_structure"] = round(w["price_structure"] * structure_pts.get(stock_info["setup"], 0.7), 1)
    score += breakdown["price_structure"]

    # Volume confirmation (10)
    vol_ratio = stock_info.get("vol_ratio") or 1
    if stock_info["setup"] == "Breakout":
        vol_pts = w["volume_confirmation"] if vol_ratio >= 1.3 else w["volume_confirmation"] * (vol_ratio / 1.3)
    else:
        # for pullback/retest, controlled (lighter) volume is the good sign
        vol_pts = w["volume_confirmation"] if vol_ratio <= 1.0 else w["volume_confirmation"] * max(0, 1 - (vol_ratio - 1))
    breakdown["volume_confirmation"] = round(max(0, min(vol_pts, w["volume_confirmation"])), 1)
    score += breakdown["volume_confirmation"]

    # Fundamental/catalyst support (10) — cannot be verified from price data alone.
    # Awarded 0 by default and flagged as "not assessed" rather than invented,
    # per the master prompt's data-integrity rule. A human should fill this in
    # for any candidate that scores 65+ on the technical-only components.
    breakdown["fundamental_catalyst"] = 0

    total = round(sum(breakdown.values()), 1)
    return {"total": total, "breakdown": breakdown}

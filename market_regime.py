"""
market_regime.py
Implements STEP 1 of the master prompt: classify the Indian market as
GREEN / YELLOW / RED for new long swing trades, using NIFTY price structure,
moving averages, and breadth computed from the stock universe.
"""

import pandas as pd


def _dma(df: pd.DataFrame, window: int) -> float:
    return df["Close"].rolling(window).mean().iloc[-1]


def classify_market_regime(nifty_df: pd.DataFrame, universe_data: dict) -> dict:
    close = nifty_df["Close"].iloc[-1]
    dma20 = _dma(nifty_df, 20)
    dma50 = _dma(nifty_df, 50)
    dma200 = _dma(nifty_df, 200) if len(nifty_df) >= 200 else None

    above_20 = close > dma20
    above_50 = close > dma50
    above_200 = (close > dma200) if dma200 else None
    dma50_rising = nifty_df["Close"].rolling(50).mean().diff().iloc[-1] > 0

    # 20-day return, used as a simple momentum / volatility proxy
    ret_20d = (close / nifty_df["Close"].iloc[-21] - 1) * 100 if len(nifty_df) > 21 else 0
    daily_returns = nifty_df["Close"].pct_change().dropna()
    volatility_20d = daily_returns.tail(20).std() * (252 ** 0.5) * 100  # annualised %

    # Breadth: % of universe stocks above their 50 DMA
    above_50_count, total = 0, 0
    for ticker, df in universe_data.items():
        if len(df) < 50:
            continue
        total += 1
        if df["Close"].iloc[-1] > df["Close"].rolling(50).mean().iloc[-1]:
            above_50_count += 1
    breadth_pct = (above_50_count / total * 100) if total else None

    # --- Scoring the regime -------------------------------------------------
    points = 0
    reasons = []

    if above_50:
        points += 2
        reasons.append(f"NIFTY ({close:.0f}) is above its 50-DMA ({dma50:.0f}).")
    else:
        reasons.append(f"NIFTY ({close:.0f}) is below its 50-DMA ({dma50:.0f}) — caution.")

    if above_200 is not None:
        if above_200:
            points += 2
            reasons.append(f"NIFTY is above its 200-DMA ({dma200:.0f}), long-term trend intact.")
        else:
            reasons.append(f"NIFTY is below its 200-DMA ({dma200:.0f}) — long-term trend impaired.")

    if dma50_rising:
        points += 1
        reasons.append("50-DMA is rising.")
    else:
        reasons.append("50-DMA is flat/falling.")

    if breadth_pct is not None:
        reasons.append(f"Breadth: {breadth_pct:.0f}% of tracked universe above their 50-DMA.")
        if breadth_pct >= 55:
            points += 2
        elif breadth_pct >= 40:
            points += 1

    if volatility_20d < 15:
        points += 1
        reasons.append(f"20-day annualised volatility is moderate ({volatility_20d:.1f}%).")
    elif volatility_20d > 25:
        reasons.append(f"20-day annualised volatility is elevated ({volatility_20d:.1f}%) — reduces regime quality.")

    reasons.append(f"NIFTY 20-day return: {ret_20d:+.1f}%.")

    # Map points (max 8) to regime
    if points >= 6:
        regime = "GREEN"
        confidence = "High" if points >= 7 else "Medium"
    elif points >= 3:
        regime = "YELLOW"
        confidence = "Medium"
    else:
        regime = "RED"
        confidence = "Medium" if points <= 1 else "Low"

    return {
        "regime": regime,
        "confidence": confidence,
        "reasons": reasons[:5],
        "nifty_close": close,
        "dma20": dma20,
        "dma50": dma50,
        "dma200": dma200,
        "breadth_pct": breadth_pct,
        "volatility_20d": volatility_20d,
    }

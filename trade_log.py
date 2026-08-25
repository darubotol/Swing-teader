"""
trade_log.py
Maintains a persistent record of every ACTIONABLE trade the system has ever
recommended, and checks each open trade against subsequent price data to see
whether its target or stop was hit first (or neither yet).

The log lives in trade_log.json at the repo root (committed by the workflow
alongside docs/, so it survives between runs).
"""

import json
import os
import datetime

LOG_PATH = "trade_log.json"
MAX_HOLDING_SESSIONS = 20  # matches the master prompt's 2-20 session holding window


def load_log() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_log(log: list) -> None:
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def add_new_trades(log: list, buckets: dict, today_str: str) -> list:
    """Append today's ACTIONABLE trades, skipping a ticker that's already open."""
    open_tickers = {t["ticker"] for t in log if t["status"] == "OPEN"}
    for s in buckets.get("actionable", []):
        info, pos = s["info"], s["position"]
        if info["ticker"] in open_tickers:
            continue
        log.append({
            "ticker": info["ticker"],
            "sector": info["sector"],
            "setup": info["setup"],
            "score": s["score"]["total"],
            "date_added": today_str,
            "entry": info["entry"],
            "stop": info["stop"],
            "target": info["target"],
            "qty": pos["qty"],
            "capital_deployed": pos["capital_deployed"],
            "status": "OPEN",
            "date_closed": None,
            "exit_price": None,
            "pnl": None,
        })
    return log


def update_open_trades(log: list, universe_data: dict, today_str: str) -> list:
    """
    For every OPEN trade, walk forward through price bars after its entry
    date and check whether target or stop was touched first. If both are
    touched on the same bar, conservatively assume the stop was hit first
    (can't know intraday sequencing from daily OHLC). If neither is hit
    within MAX_HOLDING_SESSIONS trading sessions, mark it EXPIRED at the
    latest close (matches "if the original thesis becomes invalid, exit").
    """
    for trade in log:
        if trade["status"] != "OPEN":
            continue
        df = universe_data.get(trade["ticker"])
        if df is None or df.empty:
            continue

        entry_date = datetime.date.fromisoformat(trade["date_added"])
        recent = df[df.index.date > entry_date]
        if recent.empty:
            continue

        outcome = exit_price = exit_date = None
        sessions_seen = 0
        for idx, row in recent.iterrows():
            sessions_seen += 1
            hit_target = row["High"] >= trade["target"]
            hit_stop = row["Low"] <= trade["stop"]
            if hit_stop:
                outcome, exit_price = "STOP_HIT", trade["stop"]
                exit_date = idx.date().isoformat()
                break
            if hit_target:
                outcome, exit_price = "TARGET_HIT", trade["target"]
                exit_date = idx.date().isoformat()
                break
            if sessions_seen >= MAX_HOLDING_SESSIONS:
                outcome, exit_price = "EXPIRED", round(float(row["Close"]), 2)
                exit_date = idx.date().isoformat()
                break

        if outcome:
            trade["status"] = outcome
            trade["date_closed"] = exit_date
            trade["exit_price"] = exit_price
            trade["pnl"] = round((exit_price - trade["entry"]) * trade["qty"], 2)

    return log


def summary_stats(log: list) -> dict:
    closed = [t for t in log if t["status"] != "OPEN"]
    target_hits = [t for t in closed if t["status"] == "TARGET_HIT"]
    stop_hits = [t for t in closed if t["status"] == "STOP_HIT"]
    expired = [t for t in closed if t["status"] == "EXPIRED"]
    open_trades = [t for t in log if t["status"] == "OPEN"]
    total_pnl = round(sum(t["pnl"] for t in closed if t["pnl"] is not None), 2)
    win_rate = round(len(target_hits) / len(closed) * 100, 1) if closed else None

    # Average R-multiple realised per closed trade (risk = entry - stop, so this
    # is directly comparable to the backtest's R-multiple stat).
    r_multiples = []
    for t in closed:
        risk = t["entry"] - t["stop"]
        if risk and t.get("exit_price") is not None:
            r_multiples.append((t["exit_price"] - t["entry"]) / risk)
    avg_r = round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else None

    # Current streak: consecutive wins or losses ending with the most recently
    # closed trade, in the order trades were actually closed.
    closed_by_date = sorted(
        [t for t in closed if t.get("date_closed")], key=lambda t: t["date_closed"]
    )
    streak_count, streak_type = 0, None
    for t in reversed(closed_by_date):
        outcome = "win" if t["status"] == "TARGET_HIT" else ("loss" if t["status"] == "STOP_HIT" else None)
        if outcome is None:
            break
        if streak_type is None:
            streak_type = outcome
        if outcome != streak_type:
            break
        streak_count += 1

    return {
        "total": len(log),
        "open": len(open_trades),
        "target_hit": len(target_hits),
        "stop_hit": len(stop_hits),
        "expired": len(expired),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_r": avg_r,
        "streak_count": streak_count,
        "streak_type": streak_type,
    }

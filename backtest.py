"""
backtest.py
Walk-forward backtest of the full trading engine (regime, sector ranking,
setup detection, scoring) against historical data, so you can see the
strategy's actual historical performance instead of trusting it on faith.

IMPORTANT — what this is and isn't:
- This does NOT predict future performance. Markets change; a strategy that
  worked over the last 2 years may not work the same way going forward.
- It IS a legitimate sanity check: if the strategy has no edge historically
  (win rate/expectancy at or below breakeven), that's important to know
  before trusting it with real money.
- No lookahead bias: at each simulated date, only data up to and including
  that date is used to generate signals. Outcomes are checked using only
  data AFTER the signal date.

Methodology:
1. Fetch ~2 years of history for NIFTY + the stock universe.
2. Step through trading dates (skipping the first ~220 days so DMA200 has
   enough history, and the last ~25 days so trades have room to resolve).
3. On each simulated date, run the exact same engine as the live system
   (market_regime -> rank_sectors -> analyze_stock -> score -> position
   sizing -> ACTIONABLE filter) using only data available up to that date.
4. For every ACTIONABLE signal, walk forward through the real subsequent
   price bars to see whether target or stop was hit first (or neither,
   within the max holding window) — same logic as trade_log.py.
5. Aggregate: win rate, expectancy in R-multiples, and an equity curve.

Runtime note: evaluating every single trading day across the full universe
is computationally heavy. STRIDE_DAYS controls how often we evaluate
(default 3 = roughly twice a week) to keep this finishing in a reasonable
time on GitHub Actions' free runners. Lower it for a more thorough (but
slower) backtest.
"""

import datetime
import json
import os

import config
import data_fetcher
import market_regime
import analysis
import position_sizing
import report_generator

STRIDE_DAYS = 3
MIN_LOOKBACK_DAYS = 220   # enough history for 200-DMA
FORWARD_BUFFER_DAYS = 30  # leave room at the end for trades to resolve
MAX_HOLDING_SESSIONS = 20
RESULTS_PATH = "backtest_results.json"


def _slice_up_to(df, idx):
    """Return only the rows up to and including position idx (no lookahead)."""
    return df.iloc[: idx + 1]


def simulate_outcome(entry_row_idx: int, df, entry: float, stop: float, target: float):
    """
    Walk forward from the bar AFTER entry_row_idx to find whether target or
    stop was hit first. Mirrors trade_log.update_open_trades's logic exactly,
    so backtest results are directly comparable to live trade_log outcomes.
    """
    forward = df.iloc[entry_row_idx + 1: entry_row_idx + 1 + MAX_HOLDING_SESSIONS]
    if forward.empty:
        return None  # no forward data at all — inconclusive

    for i, (_, row) in enumerate(forward.iterrows()):
        hit_stop = row["Low"] <= stop
        hit_target = row["High"] >= target
        if hit_stop:
            return {"outcome": "STOP_HIT", "exit_price": stop, "sessions_held": i + 1}
        if hit_target:
            return {"outcome": "TARGET_HIT", "exit_price": target, "sessions_held": i + 1}

    # Neither hit within the holding window — mark expired at the last close seen
    last_close = float(forward["Close"].iloc[-1])
    return {"outcome": "EXPIRED", "exit_price": last_close, "sessions_held": len(forward)}


def run_backtest(period: str = "2y", stride_days: int = STRIDE_DAYS) -> dict:
    print(f"Fetching ~{period} of history for backtest universe...")
    nifty_df = data_fetcher.fetch_nifty(period=period)
    universe_data = data_fetcher.fetch_universe(period=period)
    print(f"Got data for {len(universe_data)} tickers.")

    n_dates = len(nifty_df)
    start_idx = MIN_LOOKBACK_DAYS
    end_idx = n_dates - FORWARD_BUFFER_DAYS
    if end_idx <= start_idx:
        raise ValueError("Not enough history fetched to run a meaningful backtest.")

    signals = []
    eval_dates = list(range(start_idx, end_idx, stride_days))
    print(f"Evaluating {len(eval_dates)} dates (every {stride_days} trading days)...")

    for n, idx in enumerate(eval_dates):
        nifty_slice = _slice_up_to(nifty_df, idx)
        as_of_date = nifty_slice.index[-1]

        # Slice every ticker's history up to this date — no lookahead.
        universe_slice = {}
        for ticker, df in universe_data.items():
            sliced = df[df.index <= as_of_date]
            if len(sliced) >= 60:
                universe_slice[ticker] = sliced

        if len(universe_slice) < 10:
            continue

        regime = market_regime.classify_market_regime(nifty_slice, universe_slice)
        sector_ranking = analysis.rank_sectors(universe_slice)
        rank_lookup = {s: i for i, (s, _) in enumerate(sector_ranking)}

        scored = []
        for ticker, df in universe_slice.items():
            info = analysis.analyze_stock(ticker, df, nifty_slice)
            if info is None:
                continue
            score = analysis.score_candidate(
                info, regime, rank_lookup.get(info["sector"], len(sector_ranking)), len(sector_ranking)
            )
            pos = position_sizing.size_position(info["entry"], info["stop"], info["target"])
            scored.append({"info": info, "score": score, "position": pos})

        buckets = report_generator.build_candidates(scored)

        for s in buckets["actionable"]:
            info = s["info"]
            ticker = info["ticker"]
            full_df = universe_data[ticker]
            # Find this date's row position in the FULL (unsliced) dataframe
            # so we can walk forward into real future bars.
            try:
                row_idx = full_df.index.get_loc(as_of_date)
            except KeyError:
                continue

            result = simulate_outcome(row_idx, full_df, info["entry"], info["stop"], info["target"])
            if result is None:
                continue

            risk = info["entry"] - info["stop"]
            r_multiple = (result["exit_price"] - info["entry"]) / risk if risk else 0

            signals.append({
                "date": str(as_of_date.date()),
                "ticker": ticker,
                "setup": info["setup"],
                "score": s["score"]["total"],
                "entry": info["entry"],
                "stop": info["stop"],
                "target": info["target"],
                "outcome": result["outcome"],
                "exit_price": round(result["exit_price"], 2),
                "sessions_held": result["sessions_held"],
                "r_multiple": round(r_multiple, 2),
            })

        if (n + 1) % 20 == 0:
            print(f"  ...{n + 1}/{len(eval_dates)} dates evaluated, {len(signals)} signals so far")

    return summarize(signals)


def summarize(signals: list) -> dict:
    target_hits = [s for s in signals if s["outcome"] == "TARGET_HIT"]
    stop_hits = [s for s in signals if s["outcome"] == "STOP_HIT"]
    expired = [s for s in signals if s["outcome"] == "EXPIRED"]

    resolved_win_loss = target_hits + stop_hits
    win_rate = round(len(target_hits) / len(resolved_win_loss) * 100, 1) if resolved_win_loss else None

    all_r = [s["r_multiple"] for s in signals]
    expectancy_r = round(sum(all_r) / len(all_r), 3) if all_r else None

    # Equity curve: cumulative R-multiple, in chronological order, 1 unit risk per trade
    ordered = sorted(signals, key=lambda s: s["date"])
    equity = []
    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for s in ordered:
        running += s["r_multiple"]
        peak = max(peak, running)
        max_drawdown = min(max_drawdown, running - peak)
        equity.append(round(running, 2))

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "total_signals": len(signals),
        "target_hit": len(target_hits),
        "stop_hit": len(stop_hits),
        "expired": len(expired),
        "win_rate_pct": win_rate,
        "expectancy_r": expectancy_r,
        "max_drawdown_r": round(max_drawdown, 2),
        "final_equity_r": round(running, 2),
        "equity_curve": equity,
        "signals": ordered,
    }


def main():
    results = run_backtest()
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== BACKTEST SUMMARY ===")
    print(f"Total signals:     {results['total_signals']}")
    print(f"Target hit:        {results['target_hit']}")
    print(f"Stop hit:          {results['stop_hit']}")
    print(f"Expired (no hit):  {results['expired']}")
    print(f"Win rate:          {results['win_rate_pct']}%  (target vs stop, excludes expired)")
    print(f"Expectancy:        {results['expectancy_r']} R per trade")
    print(f"Max drawdown:      {results['max_drawdown_r']} R")
    print(f"Final equity:      {results['final_equity_r']} R")
    print(f"\nFull results written to {RESULTS_PATH}")

    if results["expectancy_r"] is not None and results["expectancy_r"] <= 0:
        print(
            "\nWARNING: expectancy is at or below zero over this test period. "
            "That means, historically, this rule set would not have made money "
            "even before costs. Treat live signals with extra caution and "
            "consider this a prompt to revisit the scoring/setup rules."
        )


if __name__ == "__main__":
    main()

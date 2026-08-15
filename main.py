"""
main.py
Orchestrates the full daily pipeline:
  1. Fetch NIFTY + universe data
  2. Classify market regime (Step 1)
  3. Rank sectors (Step 2)
  4. Analyze + detect setups for every stock in the universe (Steps 3-4)
  5. Score candidates (Step 5)
  6. Size positions and apply the final ACTIONABLE/WATCH/REJECT filter (Steps 10-13)
  7. Build the full report + Telegram summary
  8. Send to Telegram, save full report to disk

Run manually with: python main.py
Runs automatically via .github/workflows/daily-analysis.yml
"""

import os
import sys
import datetime

import config
import data_fetcher
import market_regime
import analysis
import position_sizing
import report_generator
import html_report
import trade_log
import telegram_bot


def main():
    print("=== Indian Equity Swing Trading Analyst — daily run ===")
    print(f"Data source: {config.DATA_SOURCE}")

    if config.DATA_SOURCE != "yfinance":
        print("NOTE: only the yfinance data path is implemented so far. "
              "Falling back to yfinance for this run.")

    # 1. Fetch data --------------------------------------------------------
    print("Fetching NIFTY history...")
    try:
        nifty_df = data_fetcher.fetch_nifty()
    except data_fetcher.DataUnavailableError as e:
        print(f"INSUFFICIENT CURRENT DATA — NO LIVE TRADE RECOMMENDATION. ({e})")
        telegram_bot.send_message(
            "*Indian Equity Swing Report*\n\nINSUFFICIENT CURRENT DATA — "
            "NIFTY data could not be retrieved today. No recommendations generated."
        )
        sys.exit(0)

    print("Fetching stock universe history (this can take a few minutes)...")
    universe_data = data_fetcher.fetch_universe()
    if len(universe_data) < 10:
        print("INSUFFICIENT CURRENT DATA — too few stocks returned reliable data.")
        telegram_bot.send_message(
            "*Indian Equity Swing Report*\n\nINSUFFICIENT CURRENT DATA — "
            "most of the stock universe failed to fetch today. No recommendations generated."
        )
        sys.exit(0)

    data_ts = data_fetcher.data_timestamp()

    # 2. Market regime -------------------------------------------------------
    regime = market_regime.classify_market_regime(nifty_df, universe_data)
    print(f"Market regime: {regime['regime']} ({regime['confidence']})")

    # 3. Sector ranking -------------------------------------------------------
    sector_ranking = analysis.rank_sectors(universe_data)
    sector_rank_lookup = {sector: i for i, (sector, _) in enumerate(sector_ranking)}
    num_sectors = len(sector_ranking)

    # 4-5. Per-stock analysis + scoring --------------------------------------
    scored_stocks = []
    for ticker, df in universe_data.items():
        info = analysis.analyze_stock(ticker, df, nifty_df)
        if info is None:
            continue
        sector_rank = sector_rank_lookup.get(info["sector"], num_sectors)
        score = analysis.score_candidate(info, regime, sector_rank, num_sectors)
        pos = position_sizing.size_position(info["entry"], info["stop"], info["target"])
        scored_stocks.append({"info": info, "score": score, "position": pos})

    print(f"Candidates with a detected setup: {len(scored_stocks)}")

    # 6. Bucket into ACTIONABLE / WATCH / REJECT ------------------------------
    buckets = report_generator.build_candidates(scored_stocks)
    print(f"Actionable: {len(buckets['actionable'])}  Watch: {len(buckets['watch'])}  Reject: {len(buckets['reject'])}")

    # 7. Build reports ---------------------------------------------------------
    full_md = report_generator.full_report_markdown(regime, sector_ranking, buckets, data_ts)
    short_msg = report_generator.telegram_summary(regime, buckets)

    os.makedirs("reports", exist_ok=True)
    today = datetime.date.today().isoformat()
    report_path = f"reports/swing_report_{today}.md"
    with open(report_path, "w") as f:
        f.write(full_md)
    print(f"Full report saved to {report_path}")

    # 7b. Build the mobile-friendly website (docs/ = GitHub Pages source) ----
    os.makedirs("docs/reports", exist_ok=True)

    html_page = html_report.build_html(regime, sector_ranking, buckets, data_ts)
    with open("docs/index.html", "w") as f:
        f.write(html_page)

    # Archive today's page under docs/reports/<date>.html and rebuild the
    # history index from whatever archived pages exist on disk.
    with open(f"docs/reports/{today}.html", "w") as f:
        f.write(html_page)

    archived_dates = sorted(
        [fn[:-5] for fn in os.listdir("docs/reports") if fn.endswith(".html")],
        reverse=True,
    )
    history_html = html_report.build_history_index(archived_dates)
    with open("docs/reports/index.html", "w") as f:
        f.write(history_html)

    print("Website pages written to docs/ (published via GitHub Pages).")

    # 7c. Trade log — update existing open trades, then log today's new ones ---
    log = trade_log.load_log()
    log = trade_log.update_open_trades(log, universe_data, today)
    log = trade_log.add_new_trades(log, buckets, today)
    trade_log.save_log(log)
    stats = trade_log.summary_stats(log)
    print(f"Trade log: {stats}")

    trades_html = html_report.build_trades_html(log, stats)
    with open("docs/trades.html", "w") as f:
        f.write(trades_html)
    print("Trade record page written to docs/trades.html.")

    # 8. Send to Telegram --------------------------------------------------
    telegram_bot.send_message(short_msg)
    telegram_bot.send_document(report_path, caption=f"Full report — {today}")

    print("Done.")


if __name__ == "__main__":
    main()
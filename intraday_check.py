"""
intraday_check.py
Runs frequently during NSE market hours (9:15-15:30 IST, Mon-Fri) to check
existing OPEN trades against intraday price action, so a target or stop hit
gets flagged the same day instead of waiting for the next scheduled daily
run. This does NOT scan for new trade ideas or re-run the full engine — it
only monitors positions already sitting in trade_log.json as OPEN. Re-running
the full daily/multi-day scan every few minutes wouldn't produce meaningful
new signals (the day's candle isn't complete until close) and would just add
noise, so this stays deliberately narrow.
"""

import datetime
import zoneinfo
import yfinance as yf

import trade_log
import html_report
import telegram_bot

IST = zoneinfo.ZoneInfo("Asia/Kolkata")
MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 30)


def within_market_hours() -> bool:
    now = datetime.datetime.now(IST)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def fetch_intraday(ticker: str, period: str = "5d", interval: str = "15m"):
    return yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)


def check_trades(log: list, fetch_fn=fetch_intraday) -> list:
    """Returns the list of trades that newly closed this run (target/stop hit)."""
    open_trades = [t for t in log if t["status"] == "OPEN"]
    newly_closed = []

    for trade in open_trades:
        try:
            df = fetch_fn(trade["ticker"])
        except Exception as e:  # noqa: BLE001
            print(f"Could not fetch intraday data for {trade['ticker']}: {e}")
            continue
        if df is None or df.empty:
            continue

        entry_date = datetime.date.fromisoformat(trade["date_added"])
        recent = df[df.index.date > entry_date]
        if recent.empty:
            continue

        for idx, row in recent.iterrows():
            hit_stop = row["Low"] <= trade["stop"]
            hit_target = row["High"] >= trade["target"]
            if hit_stop:
                trade["status"], trade["exit_price"] = "STOP_HIT", trade["stop"]
            elif hit_target:
                trade["status"], trade["exit_price"] = "TARGET_HIT", trade["target"]
            else:
                continue
            trade["date_closed"] = idx.date().isoformat()
            trade["pnl"] = round((trade["exit_price"] - trade["entry"]) * trade["qty"], 2)
            newly_closed.append(trade)
            break

    return newly_closed


def main():
    if not within_market_hours():
        print("Outside NSE market hours (9:15-15:30 IST, Mon-Fri) — skipping.")
        return

    log = trade_log.load_log()
    if not any(t["status"] == "OPEN" for t in log):
        print("No open trades to monitor right now.")
        return

    newly_closed = check_trades(log)

    if not newly_closed:
        print("Checked open trades — no target/stop hits yet this run.")
        return

    trade_log.save_log(log)
    stats = trade_log.summary_stats(log)
    trades_html = html_report.build_trades_html(log, stats)
    with open("docs/trades.html", "w") as f:
        f.write(trades_html)

    lines = ["🔔 Intraday Trade Update"]
    for t in newly_closed:
        name = t["ticker"].replace(".NS", "")
        outcome = "🎯 TARGET HIT" if t["status"] == "TARGET_HIT" else "🛑 STOP HIT"
        lines.append(f"{name}: {outcome} at ₹{t['exit_price']} (P&L ₹{t['pnl']:+.2f})")
    message = "\n".join(lines)
    telegram_bot.send_message(message)
    print(message)


if __name__ == "__main__":
    main()

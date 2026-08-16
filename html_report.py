"""
html_report.py
Renders the daily report as a single, self-contained, mobile-friendly HTML
page (no external dependencies, so it works offline / on GitHub Pages).
Designed phone-first: readable at 375px width, cards instead of wide tables,
big tap targets, dark-mode friendly.
"""

import datetime
import html as html_lib

STYLE = """
:root {
  --bg: #0b0e14; --paper: #12161f; --paper-alt: #171b27;
  --line: #262c3a; --line-strong: #3a4256;
  --ink: #ece8dd; --ink-dim: #8891a3;
  --saffron: #de8c3e; --saffron-dim: rgba(222,140,62,.14);
  --gain: #52a97c; --gain-dim: rgba(82,169,124,.14);
  --loss: #c8564f; --loss-dim: rgba(200,86,79,.14);
  --info: #6c8ee0; --info-dim: rgba(108,142,224,.14);
  --muted-badge: rgba(136,145,163,.16);
  --serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", ui-serif, serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "Courier New", monospace;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 0 48px 0;
  background: var(--bg); color: var(--ink);
  font-family: var(--sans);
  font-size: 16px; line-height: 1.55;
}
header {
  padding: 24px 20px 16px; border-bottom: 3px double var(--line-strong);
  position: sticky; top: 0; background: var(--bg); z-index: 10;
}
header .eyebrow {
  font-family: var(--mono); font-size: 0.68rem; letter-spacing: 0.12em;
  color: var(--saffron); text-transform: uppercase; margin-bottom: 6px;
}
header h1 {
  font-family: var(--serif); font-size: 1.5rem; font-weight: 700;
  letter-spacing: 0.01em; margin: 0 0 6px; color: var(--ink);
}
header .meta {
  color: var(--ink-dim); font-size: 0.78rem; font-family: var(--mono);
}
.container { max-width: 720px; margin: 0 auto; padding: 0 20px; }
.section { margin-top: 30px; }
.section h2 {
  font-family: var(--serif); font-style: italic; font-weight: 400;
  font-size: 1.02rem; color: var(--ink); margin: 0 0 14px; padding-bottom: 8px;
  border-bottom: 1px solid var(--line); letter-spacing: 0.01em;
}
.badge {
  display: inline-block; padding: 4px 12px; border-radius: 3px;
  font-family: var(--mono); font-size: 0.7rem; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; border: 1px solid transparent;
}
.badge.GREEN { background: var(--gain-dim); color: var(--gain); border-color: rgba(82,169,124,.35); }
.badge.YELLOW { background: var(--saffron-dim); color: var(--saffron); border-color: rgba(222,140,62,.35); }
.badge.RED { background: var(--loss-dim); color: var(--loss); border-color: rgba(200,86,79,.35); }

/* Stamp-style status badges — rotated, double-ring, ledger-approval feel */
.stamp {
  display: inline-block; padding: 5px 11px; border-radius: 4px;
  font-family: var(--mono); font-size: 0.66rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; border: 1.5px solid currentColor; transform: rotate(-2.5deg);
  position: relative;
}
.stamp::after {
  content: ""; position: absolute; inset: 2px; border: 1px solid currentColor;
  border-radius: 2px; opacity: 0.5; pointer-events: none;
}
.stamp.ACTIONABLE, .stamp.TARGET_HIT { color: var(--gain); background: var(--gain-dim); }
.stamp.WATCH, .stamp.OPEN { color: var(--info); background: var(--info-dim); }
.stamp.REJECT, .stamp.STOP_HIT { color: var(--loss); background: var(--loss-dim); }
.stamp.EXPIRED { color: var(--ink-dim); background: var(--muted-badge); }

.regime-line { display: flex; align-items: center; margin-bottom: 12px; }
.regime-line .badge { margin-right: 12px; }
.regime-line .dot {
  width: 8px; height: 8px; border-radius: 50%; background: currentColor; flex-shrink: 0;
  display: inline-block; margin-right: 6px;
}
ul.reasons { margin: 8px 0 0; padding-left: 0; list-style: none; color: var(--ink-dim); font-size: 0.92rem; }
ul.reasons li { margin-bottom: 6px; padding-left: 16px; position: relative; }
ul.reasons li::before { content: "—"; position: absolute; left: 0; color: var(--line-strong); }

.sector-row {
  display: flex; align-items: baseline; gap: 10px; padding: 9px 0;
  border-bottom: 1px solid var(--line); font-size: 0.95rem;
}
.sector-row:last-child { border-bottom: none; }
.sector-row .rank {
  font-family: var(--serif); color: var(--ink-dim); width: 20px; flex-shrink: 0; font-size: 0.9rem;
}
.sector-row .name { flex: 1; }
.sector-row .ret { font-family: var(--mono); font-variant-numeric: tabular-nums; font-weight: 600; }
.sector-row .ret.pos { color: var(--gain); }
.sector-row .ret.neg { color: var(--loss); }

.card {
  background: var(--paper); border: 1px solid var(--line); border-top: 2px solid var(--saffron);
  border-radius: 6px; padding: 16px 18px; margin-bottom: 14px;
}
.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; gap: 10px; }
.card-top .name { font-family: var(--serif); font-size: 1.15rem; font-weight: 700; }
.card-top .score { color: var(--ink-dim); font-size: 0.78rem; font-family: var(--mono); margin-top: 3px; }
.card .setup-line { color: var(--ink-dim); font-size: 0.82rem; font-family: var(--mono); margin-bottom: 12px; }
.figline {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 5px 0; font-size: 0.92rem; border-bottom: 1px solid var(--line);
}
.figline:last-child { border-bottom: none; }
.figline .label { color: var(--ink-dim); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.05em; }
.figline .value { font-family: var(--serif); font-variant-numeric: tabular-nums; font-weight: 700; }
.figblock { margin-bottom: 10px; padding-top: 8px; border-top: 1px solid var(--line); }
.notes { margin: 10px 0 0; padding-left: 0; list-style: none; font-size: 0.85rem; color: var(--ink-dim); font-style: italic; }
.notes li { padding-left: 14px; position: relative; }
.notes li::before { content: "❧"; position: absolute; left: 0; color: var(--saffron); font-style: normal; }

.watch-item, .reject-item {
  padding: 11px 0; border-bottom: 1px solid var(--line); font-size: 0.92rem;
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
}
.watch-item:last-child, .reject-item:last-child { border-bottom: none; }
.watch-item .name, .reject-item .name { font-family: var(--serif); font-weight: 700; }
.watch-item .detail, .reject-item .detail { color: var(--ink-dim); font-size: 0.78rem; margin-top: 3px; font-family: var(--mono); }
.watch-left, .reject-left { flex: 1; }

.empty {
  color: var(--ink-dim); font-style: italic; font-size: 0.92rem; font-family: var(--serif);
  padding: 14px 0;
}

.decision {
  font-family: var(--serif); font-size: 1.1rem; font-weight: 700; text-align: center;
  padding: 18px; border-top: 1px solid var(--line-strong); border-bottom: 1px solid var(--line-strong);
  letter-spacing: 0.02em;
}
.decision .tick { color: var(--saffron); }

.warning {
  margin-top: 30px; padding: 14px 16px; border-radius: 6px;
  background: var(--paper-alt); border-left: 3px solid var(--saffron);
  color: var(--ink-dim); font-size: 0.82rem; font-family: var(--mono); line-height: 1.6;
}

.history-link { display: block; margin-top: 22px; text-align: center; }
.history-link a {
  color: var(--saffron); text-decoration: none; font-size: 0.85rem;
  font-family: var(--mono); letter-spacing: 0.03em;
}
table.hist { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
table.hist th {
  font-family: var(--mono); text-transform: uppercase; font-size: 0.7rem;
  letter-spacing: 0.06em; color: var(--ink-dim); text-align: left; padding: 8px 6px;
  border-bottom: 1px solid var(--line-strong);
}
table.hist td { padding: 10px 6px; border-bottom: 1px solid var(--line); font-family: var(--serif); }
table.hist a { color: var(--saffron); text-decoration: none; font-family: var(--mono); font-size: 0.82rem; }

.stat-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
.stat-box {
  background: var(--paper); border: 1px solid var(--line); border-radius: 6px;
  padding: 14px 8px; text-align: center; flex: 1 1 30%; min-width: 90px;
}
.stat-box .num { font-family: var(--serif); font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat-box .lbl {
  font-size: 0.65rem; color: var(--ink-dim); margin-top: 4px; font-family: var(--mono);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.stat-box .num.win { color: var(--gain); }
.stat-box .num.loss { color: var(--loss); }
.pnl-box {
  background: var(--paper-alt); border: 1px solid var(--line-strong); border-radius: 6px;
  padding: 16px; text-align: center; margin-bottom: 24px;
}
.pnl-box .num { font-family: var(--serif); font-size: 1.8rem; font-weight: 700; }
.pnl-box .lbl { font-size: 0.68rem; color: var(--ink-dim); margin-top: 4px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.05em; }

.trade-card {
  background: var(--paper); border: 1px solid var(--line); border-radius: 6px;
  padding: 14px 18px; margin-bottom: 12px;
}
.trade-card .row1 { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.trade-card .ticker { font-family: var(--serif); font-weight: 700; font-size: 1.05rem; }
.trade-card .dates { color: var(--ink-dim); font-size: 0.76rem; margin-top: 4px; font-family: var(--mono); }
.trade-card .prices {
  display: flex; gap: 16px; font-size: 0.85rem; margin-top: 10px; padding-top: 10px;
  border-top: 1px solid var(--line); color: var(--ink-dim); font-family: var(--mono);
}
.trade-card .prices b { color: var(--ink); font-family: var(--serif); font-weight: 700; }
.trade-card .pnl { font-size: 0.92rem; font-weight: 700; margin-top: 8px; font-family: var(--serif); }
.trade-card .pnl.pos { color: var(--gain); } .trade-card .pnl.neg { color: var(--loss); }
"""


def _esc(x):
    return html_lib.escape(str(x))


def _score_bucket_html(bucket_key, buckets):
    items = buckets.get(bucket_key, [])
    if bucket_key == "actionable":
        if not items:
            return '<p class="empty">No entries clear the ledger threshold today.</p>'
        cards = []
        for s in items:
            info, pos, score = s["info"], s["position"], s["score"]
            name = _esc(info["ticker"].replace(".NS", ""))
            notes = "".join(f"<li>{_esc(n)}</li>" for n in info["structure_notes"])
            cards.append(f"""
<div class="card">
  <div class="card-top">
    <div>
      <span class="name">{name}</span>
      <div class="score">{score['total']:.0f} / 100</div>
    </div>
    <span class="stamp ACTIONABLE">Actionable</span>
  </div>
  <div class="setup-line">{_esc(info['setup'])} &middot; {_esc(info['sector'])}</div>
  <div class="figblock">
    <div class="figline"><span class="label">Entry</span><span class="value">₹{info['entry']}</span></div>
    <div class="figline"><span class="label">Stop</span><span class="value">₹{info['stop']}</span></div>
    <div class="figline"><span class="label">Target</span><span class="value">₹{info['target']}</span></div>
    <div class="figline"><span class="label">Reward : Risk</span><span class="value">{pos['reward_risk']}</span></div>
    <div class="figline"><span class="label">Quantity</span><span class="value">{pos['qty']}</span></div>
    <div class="figline"><span class="label">Capital deployed</span><span class="value">₹{pos['capital_deployed']}</span></div>
    <div class="figline"><span class="label">Max loss</span><span class="value">₹{pos['max_loss']}</span></div>
    <div class="figline"><span class="label">Holding period</span><span class="value">2–20 sessions</span></div>
  </div>
  <ul class="notes">{notes}</ul>
</div>""")
        return "".join(cards)

    if bucket_key == "watch":
        if not items:
            return '<p class="empty">Nothing pending entry right now.</p>'
        rows = []
        for s in items[:10]:
            info = s["info"]
            rows.append(f"""
<div class="watch-item">
  <div class="watch-left">
    <div class="name">{_esc(info['ticker'].replace('.NS',''))}</div>
    <div class="detail">{_esc(info['setup'])} &middot; score {s['score']['total']:.0f} &middot; trigger ₹{info['entry']} &middot; invalidation ₹{info['stop']}</div>
  </div>
  <span class="stamp WATCH">Watch</span>
</div>""")
        return "".join(rows)

    if bucket_key == "reject":
        top = sorted(items, key=lambda x: x["score"]["total"], reverse=True)[:5]
        if not top:
            return '<p class="empty">No candidates scored high enough to record.</p>'
        rows = []
        for s in top:
            info = s["info"]
            rows.append(f"""
<div class="reject-item">
  <div class="reject-left">
    <div class="name">{_esc(info['ticker'].replace('.NS',''))}</div>
    <div class="detail">score {s['score']['total']:.0f}</div>
  </div>
  <span class="stamp REJECT">Reject</span>
</div>""")
        return "".join(rows)
    return ""


def build_html(regime: dict, sector_ranking: list, buckets: dict, data_ts: str) -> str:
    today = datetime.date.today().isoformat()

    reasons_html = "".join(f"<li>{_esc(r)}</li>" for r in regime["reasons"])

    sector_rows = []
    for i, (sector, ret) in enumerate(sector_ranking[:5], 1):
        cls = "pos" if ret >= 0 else "neg"
        sector_rows.append(
            f'<div class="sector-row"><span class="rank">{i}.</span>'
            f'<span class="name">{_esc(sector)}</span><span class="ret {cls}">{ret:+.1f}%</span></div>'
        )
    sector_html = "".join(sector_rows) if sector_rows else '<p class="empty">No sector data.</p>'

    n_actionable = len(buckets["actionable"])
    if regime["regime"] == "RED":
        decision = "NO TRADE — market conditions unsuitable"
    elif n_actionable == 0:
        decision = "WATCHLIST ONLY" if buckets["watch"] else "NO TRADE"
    elif n_actionable == 1:
        decision = "TAKE ONE TRADE"
    else:
        decision = "TAKE TWO TRADES"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Swing Ledger — {today}</title>
<style>{STYLE}</style>
</head>
<body>
<header>
  <div class="eyebrow">Indian Equity &middot; Swing Desk</div>
  <h1>The Daily Ledger</h1>
  <div class="meta">{today} &middot; {_esc(data_ts)}</div>
</header>
<div class="container">

  <div class="section">
    <h2>Market Regime</h2>
    <div class="regime-line">
      <span class="badge {regime['regime']}"><span class="dot"></span> {regime['regime']}</span>
      <span class="meta" style="font-family:var(--mono); color:var(--ink-dim); font-size:0.8rem;">{regime['confidence']} confidence</span>
    </div>
    <ul class="reasons">{reasons_html}</ul>
  </div>

  <div class="section">
    <h2>Sector Leaders</h2>
    {sector_html}
  </div>

  <div class="section">
    <h2>Actionable Trades</h2>
    {_score_bucket_html('actionable', buckets)}
  </div>

  <div class="section">
    <h2>Watchlist</h2>
    {_score_bucket_html('watch', buckets)}
  </div>

  <div class="section">
    <h2>Top Rejected Candidates</h2>
    {_score_bucket_html('reject', buckets)}
  </div>

  <div class="section">
    <div class="decision"><span class="tick">§</span> {_esc(decision)} <span class="tick">§</span></div>
  </div>

  <div class="warning">
    This is an analytical trading model, not a guarantee of returns. Market conditions
    can invalidate technical setups. Verify current prices, liquidity, corporate events
    and order details before trading. Fundamentals/news are not auto-checked — confirm
    manually before entering any actionable trade.
  </div>

  <div class="history-link"><a href="reports/index.html">View past reports &rarr;</a></div>
  <div class="history-link"><a href="trades.html">View trade record &amp; win rate &rarr;</a></div>
</div>
</body>
</html>"""


def build_trades_html(log: list, stats: dict) -> str:
    """Renders the full trade record page: summary stats + a card per trade,
    newest first."""
    def badge(status):
        labels = {"OPEN": "Open", "TARGET_HIT": "Target Hit", "STOP_HIT": "Stop Hit", "EXPIRED": "Expired"}
        return f'<span class="stamp {status}">{labels.get(status, status)}</span>'

    win_rate_txt = f"{stats['win_rate']}%" if stats["win_rate"] is not None else "—"
    pnl_cls = "win" if stats["total_pnl"] > 0 else ("loss" if stats["total_pnl"] < 0 else "")

    stat_html = f"""
<div class="stat-grid">
  <div class="stat-box"><div class="num">{stats['total']}</div><div class="lbl">Entries</div></div>
  <div class="stat-box"><div class="num">{stats['open']}</div><div class="lbl">Open</div></div>
  <div class="stat-box"><div class="num win">{stats['target_hit']}</div><div class="lbl">Target Hit</div></div>
  <div class="stat-box"><div class="num loss">{stats['stop_hit']}</div><div class="lbl">Stop Hit</div></div>
  <div class="stat-box"><div class="num">{stats['expired']}</div><div class="lbl">Expired</div></div>
  <div class="stat-box"><div class="num">{win_rate_txt}</div><div class="lbl">Win Rate</div></div>
</div>
<div class="pnl-box">
  <div class="num {pnl_cls}">₹{stats['total_pnl']}</div><div class="lbl">Net Position &middot; Closed Entries</div>
</div>
"""

    if not log:
        cards_html = '<p class="empty">The ledger is empty — entries appear once the first actionable trade is issued.</p>'
    else:
        cards = []
        for t in sorted(log, key=lambda x: x["date_added"], reverse=True):
            pnl_line = ""
            if t["pnl"] is not None:
                cls = "pos" if t["pnl"] >= 0 else "neg"
                pnl_line = f'<div class="pnl {cls}">P&amp;L ₹{t["pnl"]:+.2f}</div>'
            closed_line = f' &middot; closed {_esc(t["date_closed"])}' if t.get("date_closed") else ""
            cards.append(f"""
<div class="trade-card">
  <div class="row1">
    <span class="ticker">{_esc(t['ticker'].replace('.NS',''))}</span>
    {badge(t['status'])}
  </div>
  <div class="dates">{_esc(t['setup'])} &middot; given {_esc(t['date_added'])}{closed_line}</div>
  <div class="prices">
    <span>Entry <b>₹{t['entry']}</b></span>
    <span>Stop <b>₹{t['stop']}</b></span>
    <span>Target <b>₹{t['target']}</b></span>
  </div>
  {pnl_line}
</div>""")
        cards_html = "".join(cards)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trade Ledger</title>
<style>{STYLE}</style>
</head>
<body>
<header>
  <div class="eyebrow">Indian Equity &middot; Swing Desk</div>
  <h1>Trade Ledger</h1>
  <div class="meta">Every actionable entry issued, and its outcome</div>
</header>
<div class="container">
  <div class="section">
    {stat_html}
    {cards_html}
  </div>
  <div class="history-link"><a href="index.html">&larr; Back to latest report</a></div>
</div>
</body>
</html>"""


def build_history_index(report_dates: list) -> str:
    """report_dates: list of date strings (YYYY-MM-DD), newest first."""
    rows = "".join(
        f'<tr><td>{_esc(d)}</td><td><a href="{_esc(d)}.html">Open &rarr;</a></td></tr>'
        for d in report_dates
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Report Register</title>
<style>{STYLE}</style>
</head>
<body>
<header>
  <div class="eyebrow">Indian Equity &middot; Swing Desk</div>
  <h1>Report Register</h1>
</header>
<div class="container">
  <div class="section">
    <table class="hist">
      <tr><th>Date</th><th></th></tr>
      {rows if rows else '<tr><td colspan="2" class="empty">No reports yet.</td></tr>'}
    </table>
  </div>
  <div class="history-link"><a href="../index.html">&larr; Back to latest report</a></div>
</div>
</body>
</html>"""
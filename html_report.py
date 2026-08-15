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
  --bg: #0f1115; --card: #171a21; --border: #262b36;
  --text: #e8eaed; --muted: #9aa3b2;
  --green: #2fbf71; --yellow: #e0a72e; --red: #e0524e;
  --accent: #4f8cff;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 0 40px 0;
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px; line-height: 1.5;
}
header {
  padding: 20px 16px 14px; border-bottom: 1px solid var(--border);
  position: sticky; top: 0; background: var(--bg); z-index: 10;
}
header h1 { font-size: 1.25rem; margin: 0 0 4px; }
header .meta { color: var(--muted); font-size: 0.85rem; }
.container { max-width: 720px; margin: 0 auto; padding: 0 16px; }
.section { margin-top: 24px; }
.section h2 {
  font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--muted); margin: 0 0 10px; padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.badge {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em;
}
.badge.GREEN { background: rgba(47,191,113,0.15); color: var(--green); }
.badge.YELLOW { background: rgba(224,167,46,0.15); color: var(--yellow); }
.badge.RED { background: rgba(224,82,78,0.15); color: var(--red); }
.badge.ACTIONABLE { background: rgba(47,191,113,0.15); color: var(--green); }
.badge.WATCH { background: rgba(224,167,46,0.15); color: var(--yellow); }
.badge.REJECT { background: rgba(224,82,78,0.12); color: var(--red); }
.regime-line { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
ul.reasons { margin: 8px 0 0; padding-left: 18px; color: var(--muted); font-size: 0.92rem; }
ul.reasons li { margin-bottom: 4px; }
.sector-row {
  display: flex; justify-content: space-between; padding: 8px 0;
  border-bottom: 1px solid var(--border); font-size: 0.95rem;
}
.sector-row:last-child { border-bottom: none; }
.sector-row .rank { color: var(--muted); width: 22px; flex-shrink: 0; }
.sector-row .ret.pos { color: var(--green); }
.sector-row .ret.neg { color: var(--red); }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 14px 16px; margin-bottom: 12px;
}
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card-top .name { font-size: 1.05rem; font-weight: 700; }
.card-top .score { color: var(--muted); font-size: 0.85rem; }
.card .setup-line { color: var(--muted); font-size: 0.85rem; margin-bottom: 10px; }
.grid2 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; font-size: 0.92rem; margin-bottom: 8px;
}
.grid2 .label { color: var(--muted); }
.grid2 .value { text-align: right; font-variant-numeric: tabular-nums; }
.notes { margin: 8px 0 0; padding-left: 18px; font-size: 0.88rem; color: var(--muted); }
.watch-item, .reject-item {
  padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 0.92rem;
}
.watch-item:last-child, .reject-item:last-child { border-bottom: none; }
.watch-item .name, .reject-item .name { font-weight: 600; }
.watch-item .detail, .reject-item .detail { color: var(--muted); font-size: 0.85rem; margin-top: 2px; }
.empty { color: var(--muted); font-style: italic; font-size: 0.92rem; }
.decision {
  font-size: 1.05rem; font-weight: 700; text-align: center;
  padding: 16px; border-radius: 12px; background: var(--card); border: 1px solid var(--border);
}
.warning {
  margin-top: 28px; padding: 14px 16px; border-radius: 12px;
  background: rgba(224,167,46,0.08); border: 1px solid rgba(224,167,46,0.3);
  color: var(--muted); font-size: 0.85rem;
}
.history-link { display: block; margin-top: 20px; text-align: center; }
.history-link a { color: var(--accent); text-decoration: none; font-size: 0.9rem; }
table.hist { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
table.hist td, table.hist th { padding: 8px 6px; border-bottom: 1px solid var(--border); text-align: left; }
table.hist a { color: var(--accent); text-decoration: none; }
.stat-grid {
  display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px;
}
.stat-box {
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 12px 8px; text-align: center; flex: 1 1 30%; min-width: 90px;
}
.stat-box .num { font-size: 1.3rem; font-weight: 700; }
.stat-box .lbl { font-size: 0.72rem; color: var(--muted); margin-top: 2px; }
.stat-box .num.win { color: var(--green); }
.stat-box .num.loss { color: var(--red); }
.trade-card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 12px 16px; margin-bottom: 10px;
}
.trade-card .row1 { display: flex; justify-content: space-between; align-items: center; }
.trade-card .ticker { font-weight: 700; }
.trade-card .dates { color: var(--muted); font-size: 0.78rem; margin-top: 2px; }
.trade-card .prices { display: flex; gap: 14px; font-size: 0.85rem; margin-top: 8px; color: var(--muted); }
.trade-card .prices b { color: var(--text); font-weight: 600; }
.trade-card .pnl { font-size: 0.9rem; font-weight: 700; margin-top: 6px; }
.trade-card .pnl.pos { color: var(--green); } .trade-card .pnl.neg { color: var(--red); }
.badge.OPEN { background: rgba(79,140,255,.15); color: var(--accent); }
.badge.TARGET_HIT { background: rgba(47,191,113,.15); color: var(--green); }
.badge.STOP_HIT { background: rgba(224,82,78,.15); color: var(--red); }
.badge.EXPIRED { background: rgba(154,163,178,.15); color: var(--muted); }
"""


def _esc(x):
    return html_lib.escape(str(x))


def _score_bucket_html(bucket_key, buckets):
    items = buckets.get(bucket_key, [])
    if bucket_key == "actionable":
        if not items:
            return '<p class="empty">No trades met the ACTIONABLE bar today.</p>'
        cards = []
        for s in items:
            info, pos, score = s["info"], s["position"], s["score"]
            name = _esc(info["ticker"].replace(".NS", ""))
            notes = "".join(f"<li>{_esc(n)}</li>" for n in info["structure_notes"])
            cards.append(f"""
<div class="card">
  <div class="card-top">
    <span class="name">{name}</span>
    <span class="score">{score['total']:.0f}/100</span>
  </div>
  <div class="setup-line">{_esc(info['setup'])} &middot; {_esc(info['sector'])}</div>
  <div class="grid2">
    <div class="label">Entry</div><div class="value">₹{info['entry']}</div>
    <div class="label">Stop</div><div class="value">₹{info['stop']}</div>
    <div class="label">Target</div><div class="value">₹{info['target']}</div>
    <div class="label">Reward:Risk</div><div class="value">{pos['reward_risk']}</div>
    <div class="label">Qty</div><div class="value">{pos['qty']}</div>
    <div class="label">Capital deployed</div><div class="value">₹{pos['capital_deployed']}</div>
    <div class="label">Max loss</div><div class="value">₹{pos['max_loss']}</div>
    <div class="label">Holding period</div><div class="value">2–20 sessions</div>
  </div>
  <ul class="notes">{notes}</ul>
</div>""")
        return "".join(cards)

    if bucket_key == "watch":
        if not items:
            return '<p class="empty">None.</p>'
        rows = []
        for s in items[:10]:
            info = s["info"]
            rows.append(f"""
<div class="watch-item">
  <div class="name">{_esc(info['ticker'].replace('.NS',''))} <span class="badge WATCH">WATCH</span></div>
  <div class="detail">{_esc(info['setup'])} &middot; score {s['score']['total']:.0f} &middot; trigger ₹{info['entry']} &middot; invalidation ₹{info['stop']}</div>
</div>""")
        return "".join(rows)

    if bucket_key == "reject":
        top = sorted(items, key=lambda x: x["score"]["total"], reverse=True)[:5]
        if not top:
            return '<p class="empty">None scored high enough to be worth listing.</p>'
        rows = []
        for s in top:
            info = s["info"]
            rows.append(f"""
<div class="reject-item">
  <div class="name">{_esc(info['ticker'].replace('.NS',''))} <span class="badge REJECT">REJECT</span></div>
  <div class="detail">score {s['score']['total']:.0f}</div>
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
            f'<span>{_esc(sector)}</span><span class="ret {cls}">{ret:+.1f}%</span></div>'
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
<title>Swing Report — {today}</title>
<style>{STYLE}</style>
</head>
<body>
<header>
  <h1>Indian Equity Swing Report</h1>
  <div class="meta">{today} &middot; data: {_esc(data_ts)}</div>
</header>
<div class="container">

  <div class="section">
    <h2>Market Regime</h2>
    <div class="regime-line">
      <span class="badge {regime['regime']}">{regime['regime']}</span>
      <span class="meta">{regime['confidence']} confidence</span>
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
    <div class="decision">Final decision: {_esc(decision)}</div>
  </div>

  <div class="warning">
    This is an analytical trading model, not a guarantee of returns. Market conditions
    can invalidate technical setups. Verify current prices, liquidity, corporate events
    and order details before trading. Fundamentals/news are not auto-checked — confirm
    manually before entering any ACTIONABLE trade.
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
        labels = {"OPEN": "OPEN", "TARGET_HIT": "TARGET HIT", "STOP_HIT": "STOP HIT", "EXPIRED": "EXPIRED"}
        return f'<span class="badge {status}">{labels.get(status, status)}</span>'

    win_rate_txt = f"{stats['win_rate']}%" if stats["win_rate"] is not None else "—"
    pnl_cls = "win" if stats["total_pnl"] > 0 else ("loss" if stats["total_pnl"] < 0 else "")

    stat_html = f"""
<div class="stat-grid">
  <div class="stat-box"><div class="num">{stats['total']}</div><div class="lbl">Total trades</div></div>
  <div class="stat-box"><div class="num">{stats['open']}</div><div class="lbl">Open</div></div>
  <div class="stat-box"><div class="num win">{stats['target_hit']}</div><div class="lbl">Target hit</div></div>
  <div class="stat-box"><div class="num loss">{stats['stop_hit']}</div><div class="lbl">Stop hit</div></div>
  <div class="stat-box"><div class="num">{stats['expired']}</div><div class="lbl">Expired</div></div>
  <div class="stat-box"><div class="num">{win_rate_txt}</div><div class="lbl">Win rate</div></div>
</div>
<div class="stat-box" style="margin-bottom:20px;">
  <div class="num {pnl_cls}">₹{stats['total_pnl']}</div><div class="lbl">Total P&amp;L (closed trades)</div>
</div>
"""

    if not log:
        cards_html = '<p class="empty">No trades logged yet — check back after the first ACTIONABLE trade is issued.</p>'
    else:
        cards = []
        for t in sorted(log, key=lambda x: x["date_added"], reverse=True):
            pnl_line = ""
            if t["pnl"] is not None:
                cls = "pos" if t["pnl"] >= 0 else "neg"
                pnl_line = f'<div class="pnl {cls}">P&amp;L: ₹{t["pnl"]:+.2f}</div>'
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
<title>Trade Record</title>
<style>{STYLE}</style>
</head>
<body>
<header><h1>Trade Record</h1><div class="meta">Every ACTIONABLE trade the system has issued</div></header>
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
        f'<tr><td>{_esc(d)}</td><td><a href="{_esc(d)}.html">Open report</a></td></tr>'
        for d in report_dates
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Report History</title>
<style>{STYLE}</style>
</head>
<body>
<header><h1>Report History</h1></header>
<div class="container">
  <div class="section">
    <table class="hist">
      <tr><th>Date</th><th></th></tr>
      {rows if rows else '<tr><td colspan="2" class="empty">No reports yet.</td></tr>'}
    </table>
  </div>
  <div class="history-link"><a href="../index.html">← Back to latest report</a></div>
</div>
</body>
</html>"""
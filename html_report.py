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
  --bg-top: #131530; --bg: #09090f; --paper: #171a2e; --paper-alt: #1d2138;
  --line: #2b3050; --line-strong: #4a5182;
  --ink: #f3f0e4; --ink-dim: #9aa2c4;
  --saffron: #f5a83f; --saffron-dim: rgba(245,168,63,.20);
  --gain: #3ed492; --gain-dim: rgba(62,212,146,.20);
  --loss: #ff6161; --loss-dim: rgba(255,97,97,.20);
  --info: #8298ff; --info-dim: rgba(130,152,255,.20);
  --muted-badge: rgba(154,162,196,.18);
  --serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", ui-serif, serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "Courier New", monospace;
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0; padding: 0 0 48px 0;
  background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg) 480px);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 16px; line-height: 1.55;
}
header {
  padding: 26px 20px 18px; border-bottom: 3px double var(--line-strong);
  position: sticky; top: 0; background: linear-gradient(180deg, var(--bg-top) 0%, rgba(19,21,48,0.97) 100%); z-index: 10;
}
header .eyebrow {
  font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.14em;
  color: var(--saffron); text-transform: uppercase; margin-bottom: 8px; font-weight: 700;
}
header h1 {
  font-family: var(--serif); font-size: 1.6rem; font-weight: 700;
  letter-spacing: 0.01em; margin: 0 0 8px; color: var(--ink);
  background: linear-gradient(90deg, var(--ink) 0%, #d8c9a8 100%);
  -webkit-background-clip: text; background-clip: text;
}
header .meta {
  color: var(--ink-dim); font-size: 0.78rem; font-family: var(--mono);
}
.container { max-width: 720px; margin: 0 auto; padding: 0 20px; }
.section { margin-top: 32px; }
.section h2 {
  font-family: var(--serif); font-style: italic; font-weight: 400;
  font-size: 1.08rem; color: var(--ink); margin: 0 0 14px; padding-bottom: 9px;
  border-bottom: 1px solid var(--line); letter-spacing: 0.01em;
  display: flex; align-items: center; gap: 8px;
}
.section h2::before { content: ""; width: 4px; height: 16px; background: var(--saffron); border-radius: 2px; display: inline-block; }

.badge {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 4px;
  font-family: var(--mono); font-size: 0.72rem; font-weight: 800; letter-spacing: 0.06em;
  text-transform: uppercase;
}
.badge.GREEN { background: var(--gain); color: #05261a; }
.badge.YELLOW { background: var(--saffron); color: #2b1704; }
.badge.RED { background: var(--loss); color: #2b0606; }

/* Stamp-style status badges — rotated, solid-fill, ledger-approval feel */
.stamp {
  display: inline-block; padding: 6px 12px; border-radius: 4px;
  font-family: var(--mono); font-size: 0.68rem; font-weight: 800; letter-spacing: 0.08em;
  text-transform: uppercase; border: 1.5px solid currentColor; transform: rotate(-2.5deg);
  position: relative;
}
.stamp::after {
  content: ""; position: absolute; inset: 2px; border: 1px solid currentColor;
  border-radius: 2px; opacity: 0.55; pointer-events: none;
}
.stamp.ACTIONABLE, .stamp.TARGET_HIT { color: var(--gain); background: var(--gain-dim); }
.stamp.WATCH, .stamp.OPEN { color: var(--info); background: var(--info-dim); }
.stamp.REJECT, .stamp.STOP_HIT { color: var(--loss); background: var(--loss-dim); }
.stamp.EXPIRED { color: var(--ink-dim); background: var(--muted-badge); }

.regime-line { display: flex; align-items: center; margin-bottom: 14px; }
.regime-line .badge { margin-right: 12px; }
.regime-line .dot {
  width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex-shrink: 0;
  display: inline-block;
}
ul.reasons { margin: 8px 0 0; padding-left: 0; list-style: none; color: var(--ink-dim); font-size: 0.92rem; }
ul.reasons li { margin-bottom: 7px; padding-left: 16px; position: relative; }
ul.reasons li::before { content: "—"; position: absolute; left: 0; color: var(--saffron); opacity: 0.6; }

.sector-row {
  position: relative; overflow: hidden;
  display: flex; align-items: baseline; gap: 10px; padding: 11px 10px;
  margin-bottom: 4px; border-radius: 5px; font-size: 0.95rem;
  background: var(--paper);
}
.sector-row .bar {
  position: absolute; left: 0; top: 0; bottom: 0; z-index: 0; opacity: 0.22;
}
.sector-row .bar.pos { background: var(--gain); }
.sector-row .bar.neg { background: var(--loss); }
.sector-row .rank {
  font-family: var(--serif); color: var(--ink-dim); width: 18px; flex-shrink: 0; font-size: 0.9rem;
  position: relative; z-index: 1;
}
.sector-row .name { flex: 1; position: relative; z-index: 1; font-weight: 600; }
.sector-row .ret { font-family: var(--mono); font-variant-numeric: tabular-nums; font-weight: 700; position: relative; z-index: 1; }
.sector-row .ret.pos { color: var(--gain); }
.sector-row .ret.neg { color: var(--loss); }

.card {
  background: linear-gradient(155deg, var(--paper) 0%, var(--paper-alt) 100%);
  border: 1px solid var(--line); border-top: 3px solid var(--saffron);
  border-radius: 8px; padding: 18px 20px; margin-bottom: 16px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.25);
}
.card.setup-breakout { border-top-color: var(--saffron); }
.card.setup-breakout-retest { border-top-color: var(--info); }
.card.setup-trend-pullback { border-top-color: var(--gain); }
.card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; gap: 10px; }
.card-top .name { font-family: var(--serif); font-size: 1.2rem; font-weight: 700; }
.card-top .score {
  display: inline-block; margin-top: 5px; padding: 2px 8px; border-radius: 3px;
  font-size: 0.74rem; font-family: var(--mono); font-weight: 700;
}
.card-top .score.tier-a { background: var(--gain-dim); color: var(--gain); }
.card-top .score.tier-b { background: var(--saffron-dim); color: var(--saffron); }
.card .setup-line { color: var(--ink-dim); font-size: 0.82rem; font-family: var(--mono); margin-bottom: 12px; }
.figline {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 6px 0; font-size: 0.92rem; border-bottom: 1px solid var(--line);
}
.figline:last-child { border-bottom: none; }
.figline .label { color: var(--ink-dim); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.05em; }
.figline .value { font-family: var(--serif); font-variant-numeric: tabular-nums; font-weight: 700; color: var(--ink); }
.figblock { margin-bottom: 10px; padding-top: 8px; border-top: 1px solid var(--line); }
.notes { margin: 10px 0 0; padding-left: 0; list-style: none; font-size: 0.85rem; color: var(--ink-dim); font-style: italic; }
.notes li { padding-left: 16px; position: relative; }
.notes li::before { content: "❧"; position: absolute; left: 0; color: var(--saffron); font-style: normal; }

.watch-item, .reject-item {
  padding: 12px 14px; margin-bottom: 6px; border-radius: 6px; font-size: 0.92rem;
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
  background: var(--paper); border-left: 3px solid var(--info);
}
.reject-item { border-left-color: var(--loss); opacity: 0.85; }
.watch-item .name, .reject-item .name { font-family: var(--serif); font-weight: 700; }
.watch-item .detail, .reject-item .detail { color: var(--ink-dim); font-size: 0.78rem; margin-top: 3px; font-family: var(--mono); }
.watch-left, .reject-left { flex: 1; }

.empty {
  color: var(--ink-dim); font-style: italic; font-size: 0.92rem; font-family: var(--serif);
  padding: 14px 0;
}

.decision {
  font-family: var(--serif); font-size: 1.15rem; font-weight: 700; text-align: center;
  padding: 20px; border-radius: 8px; letter-spacing: 0.02em;
  background: linear-gradient(155deg, var(--paper) 0%, var(--paper-alt) 100%);
  border: 1px solid var(--line-strong);
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
  font-family: var(--mono); letter-spacing: 0.03em; font-weight: 600;
}
table.hist { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
table.hist th {
  font-family: var(--mono); text-transform: uppercase; font-size: 0.7rem;
  letter-spacing: 0.06em; color: var(--ink-dim); text-align: left; padding: 8px 6px;
  border-bottom: 1px solid var(--line-strong);
}
table.hist td { padding: 12px 10px; border-bottom: 1px solid var(--line); font-family: var(--serif); background: var(--paper); }
table.hist tr td:first-child { border-radius: 6px 0 0 6px; }
table.hist tr td:last-child { border-radius: 0 6px 6px 0; }
table.hist a { color: var(--saffron); text-decoration: none; font-family: var(--mono); font-size: 0.82rem; font-weight: 600; }

.stat-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
.stat-box {
  background: linear-gradient(155deg, var(--paper) 0%, var(--paper-alt) 100%);
  border: 1px solid var(--line); border-radius: 8px;
  padding: 16px 8px; text-align: center; flex: 1 1 30%; min-width: 90px;
}
.stat-box .num { font-family: var(--serif); font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.stat-box .lbl {
  font-size: 0.65rem; color: var(--ink-dim); margin-top: 5px; font-family: var(--mono);
  text-transform: uppercase; letter-spacing: 0.05em;
}
.stat-box .num.win { color: var(--gain); }
.stat-box .num.loss { color: var(--loss); }
.pnl-box {
  background: linear-gradient(155deg, var(--paper) 0%, var(--paper-alt) 100%);
  border: 1px solid var(--line-strong); border-radius: 8px;
  padding: 18px; text-align: center; margin-bottom: 26px;
}
.pnl-box .num { font-family: var(--serif); font-size: 1.9rem; font-weight: 700; }
.pnl-box .lbl { font-size: 0.68rem; color: var(--ink-dim); margin-top: 5px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.05em; }

.trade-card {
  background: linear-gradient(155deg, var(--paper) 0%, var(--paper-alt) 100%);
  border: 1px solid var(--line); border-radius: 8px;
  padding: 16px 20px; margin-bottom: 14px;
}
.trade-card .row1 { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.trade-card .ticker { font-family: var(--serif); font-weight: 700; font-size: 1.08rem; }
.trade-card .dates { color: var(--ink-dim); font-size: 0.76rem; margin-top: 4px; font-family: var(--mono); }
.trade-card .prices {
  display: flex; gap: 16px; font-size: 0.85rem; margin-top: 10px; padding-top: 10px;
  border-top: 1px solid var(--line); color: var(--ink-dim); font-family: var(--mono);
}
.trade-card .prices b { color: var(--ink); font-family: var(--serif); font-weight: 700; }
.trade-card .pnl { font-size: 0.94rem; font-weight: 700; margin-top: 8px; font-family: var(--serif); }
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
            setup_slug = info["setup"].lower().replace(" ", "-")
            tier = "tier-a" if score["total"] >= 80 else "tier-b"
            cards.append(f"""
<div class="card setup-{setup_slug}">
  <div class="card-top">
    <div>
      <span class="name">{name}</span>
      <div class="score {tier}">{score['total']:.0f} / 100</div>
    </div>
    <span class="stamp ACTIONABLE">Actionable</span>
  </div>
  <div class="setup-line">{_esc(info['setup'])} &middot; {_esc(info['sector'])}</div>
  <div class="figblock">
    <div class="figline"><span class="label">Entry</span><span class="value">₹{info['entry']}</span></div>
    <div class="figline"><span class="label">Stop</span><span class="value">₹{info['stop']}</span></div>
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
    top5 = [(s, r) for s, r in sector_ranking[:5] if r == r]  # drop any stray NaN defensively
    max_abs = max((abs(r) for _, r in top5), default=1) or 1
    for i, (sector, ret) in enumerate(top5, 1):
        cls = "pos" if ret >= 0 else "neg"
        bar_pct = min(100, round(abs(ret) / max_abs * 100))
        sector_rows.append(
            f'<div class="sector-row"><div class="bar {cls}" style="width:{bar_pct}%;"></div>'
            f'<span class="rank">{i}.</span>'
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
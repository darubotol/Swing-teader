"""
html_report.py
Renders the daily report as a single, self-contained, mobile-friendly HTML
page (no external dependencies, so it works offline / on GitHub Pages).
Designed phone-first: readable at 375px width, cards instead of wide tables,
big tap targets, dark-mode friendly.
"""

import datetime
import html as html_lib

SCORE_MAX = {
    "market_regime": 15, "sector_strength": 15, "trend": 20,
    "relative_strength": 15, "price_structure": 15,
    "volume_confirmation": 10, "fundamental_catalyst": 10,
}
SCORE_LABELS = {
    "market_regime": "Regime", "sector_strength": "Sector", "trend": "Trend",
    "relative_strength": "Rel. Strength", "price_structure": "Structure",
    "volume_confirmation": "Volume", "fundamental_catalyst": "Fundamentals",
}

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

.hero-strip { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.hero-box {
  flex: 1 1 21%; min-width: 72px; text-align: center; padding: 12px 6px;
  background: linear-gradient(155deg, var(--paper) 0%, var(--paper-alt) 100%);
  border: 1px solid var(--line); border-radius: 8px;
}
.hero-box .num { font-family: var(--serif); font-size: 1.25rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.hero-box .lbl { font-size: 0.62rem; color: var(--ink-dim); margin-top: 3px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.04em; }
.hero-box .num.win { color: var(--gain); } .hero-box .num.loss { color: var(--loss); }

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
.sparkline { display: block; margin: 4px 0 12px; }
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

.score-breakdown { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.score-chip {
  font-family: var(--mono); font-size: 0.68rem; background: var(--paper-alt);
  border: 1px solid var(--line); border-radius: 4px; padding: 3px 8px; color: var(--ink-dim);
}
.score-chip b { color: var(--ink); font-weight: 700; }
"""


def _esc(x):
    return html_lib.escape(str(x))


def _sparkline_svg(closes: list, width: int = 280, height: int = 44, stroke: str = None) -> str:
    """Small inline price sparkline — no external chart library needed."""
    if not closes or len(closes) < 2:
        return ""
    lo, hi = min(closes), max(closes)
    span = (hi - lo) or 1
    pad = 3
    n = len(closes)
    step = (width - 2 * pad) / (n - 1)

    def x(i):
        return pad + i * step

    def y(v):
        return height - pad - ((v - lo) / span) * (height - 2 * pad)

    coords = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(closes))
    trending_up = closes[-1] >= closes[0]
    color = stroke or ("var(--gain)" if trending_up else "var(--loss)")
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none"><polyline points="{coords}" fill="none" '
        f'stroke="{color}" stroke-width="2"/></svg>'
    )


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
            spark = _sparkline_svg(info.get("recent_closes", []))
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
  {spark}
  <div class="score-breakdown">{"".join(f'<span class="score-chip">{SCORE_LABELS.get(k,k)} <b>{v:.0f}/{SCORE_MAX.get(k,"?")}</b></span>' for k, v in score["breakdown"].items())}</div>
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
            extra = f" &middot; {_esc(s['watch_reason'])}" if s.get("watch_reason") else ""
            rows.append(f"""
<div class="watch-item">
  <div class="watch-left">
    <div class="name">{_esc(info['ticker'].replace('.NS',''))}</div>
    <div class="detail">{_esc(info['setup'])} &middot; score {s['score']['total']:.0f} &middot; trigger ₹{info['entry']} &middot; invalidation ₹{info['stop']}{extra}</div>
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


def build_html(regime: dict, sector_ranking: list, buckets: dict, data_ts: str, trade_stats: dict = None) -> str:
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

    hero_html = ""
    if trade_stats:
        wr = f"{trade_stats['win_rate']}%" if trade_stats.get("win_rate") is not None else "—"
        hero_html = f"""
<div class="hero-strip">
  <div class="hero-box"><div class="num">{n_actionable}</div><div class="lbl">Today</div></div>
  <div class="hero-box"><div class="num">{trade_stats.get('open', 0)}</div><div class="lbl">Open</div></div>
  <div class="hero-box"><div class="num win">{wr}</div><div class="lbl">Win Rate</div></div>
  <div class="hero-box"><div class="num">{trade_stats.get('total', 0)}</div><div class="lbl">All-Time</div></div>
</div>"""

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
  {hero_html}
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
  <div class="history-link"><a href="backtest.html">View backtest results &rarr;</a></div>
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
    avg_r_txt = f"{stats['avg_r']:+.2f} R" if stats.get("avg_r") is not None else "—"
    avg_r_cls = "win" if (stats.get("avg_r") or 0) > 0 else ("loss" if (stats.get("avg_r") or 0) < 0 else "")
    streak_txt = "—"
    streak_cls = ""
    if stats.get("streak_count"):
        streak_txt = f"{stats['streak_count']} {stats['streak_type']}{'s' if stats['streak_count'] != 1 else ''}"
        streak_cls = "win" if stats["streak_type"] == "win" else "loss"

    stat_html = f"""
<div class="stat-grid">
  <div class="stat-box"><div class="num">{stats['total']}</div><div class="lbl">Entries</div></div>
  <div class="stat-box"><div class="num">{stats['open']}</div><div class="lbl">Open</div></div>
  <div class="stat-box"><div class="num win">{stats['target_hit']}</div><div class="lbl">Target Hit</div></div>
  <div class="stat-box"><div class="num loss">{stats['stop_hit']}</div><div class="lbl">Stop Hit</div></div>
  <div class="stat-box"><div class="num">{stats['expired']}</div><div class="lbl">Expired</div></div>
  <div class="stat-box"><div class="num">{win_rate_txt}</div><div class="lbl">Win Rate</div></div>
  <div class="stat-box"><div class="num {avg_r_cls}">{avg_r_txt}</div><div class="lbl">Avg R / Trade</div></div>
  <div class="stat-box"><div class="num {streak_cls}">{streak_txt}</div><div class="lbl">Current Streak</div></div>
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


def _equity_curve_svg(equity_curve: list, width: int = 640, height: int = 180) -> str:
    if not equity_curve:
        return '<p class="empty">No resolved signals yet.</p>'
    pts = [0.0] + list(equity_curve)
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1
    pad = 10
    n = len(pts)
    step = (width - 2 * pad) / max(1, n - 1)

    def x(i):
        return pad + i * step

    def y(v):
        return height - pad - ((v - lo) / span) * (height - 2 * pad)

    coords = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(pts))
    zero_y = y(0)
    final_positive = pts[-1] >= 0
    line_color = "var(--gain)" if final_positive else "var(--loss)"
    fill_color = "var(--gain)" if final_positive else "var(--loss)"
    area_pts = f"{x(0):.1f},{zero_y:.1f} " + coords + f" {x(n-1):.1f},{zero_y:.1f}"

    return f"""
<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" preserveAspectRatio="none" style="display:block;">
  <line x1="{pad}" y1="{zero_y:.1f}" x2="{width-pad}" y2="{zero_y:.1f}" stroke="var(--line-strong)" stroke-width="1" stroke-dasharray="3,3"/>
  <polygon points="{area_pts}" fill="{fill_color}" opacity="0.12"/>
  <polyline points="{coords}" fill="none" stroke="{line_color}" stroke-width="2.5"/>
</svg>"""


def build_backtest_html(results: dict) -> str:
    win_rate_txt = f"{results['win_rate_pct']}%" if results["win_rate_pct"] is not None else "—"
    exp_r = results["expectancy_r"]
    exp_cls = "win" if (exp_r or 0) > 0 else ("loss" if (exp_r or 0) < 0 else "")
    exp_txt = f"{exp_r:+.2f} R" if exp_r is not None else "—"

    stat_html = f"""
<div class="stat-grid">
  <div class="stat-box"><div class="num">{results['total_signals']}</div><div class="lbl">Signals Tested</div></div>
  <div class="stat-box"><div class="num win">{results['target_hit']}</div><div class="lbl">Target Hit</div></div>
  <div class="stat-box"><div class="num loss">{results['stop_hit']}</div><div class="lbl">Stop Hit</div></div>
  <div class="stat-box"><div class="num">{results['expired']}</div><div class="lbl">Expired</div></div>
  <div class="stat-box"><div class="num">{win_rate_txt}</div><div class="lbl">Win Rate</div></div>
  <div class="stat-box"><div class="num {exp_cls}">{exp_txt}</div><div class="lbl">Expectancy / Trade</div></div>
</div>
"""

    warning_html = ""
    if exp_r is not None and exp_r <= 0:
        warning_html = """
  <div class="warning">
    Expectancy is at or below zero over this test period. Historically, this rule
    set would not have made money here even before real-world costs (slippage,
    brokerage, taxes). This doesn't mean it will always fail, but it's a genuine
    signal to treat live actionable trades with extra caution, and worth revisiting
    the scoring/setup rules before relying on them further.
  </div>"""

    recent = results["signals"][-15:][::-1]
    rows = "".join(f"""
<div class="trade-card">
  <div class="row1">
    <span class="ticker">{_esc(t['ticker'].replace('.NS',''))}</span>
    <span class="stamp {t['outcome']}">{t['outcome'].replace('_',' ').title()}</span>
  </div>
  <div class="dates">{_esc(t['setup'])} &middot; signal {_esc(t['date'])} &middot; held {t['sessions_held']} sessions</div>
  <div class="prices">
    <span>Entry <b>₹{t['entry']}</b></span>
    <span>Exit <b>₹{t['exit_price']}</b></span>
    <span>R <b>{t['r_multiple']:+.2f}</b></span>
  </div>
</div>""" for t in recent) or '<p class="empty">No signals were generated during this test window.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backtest Results</title>
<style>{STYLE}</style>
</head>
<body>
<header>
  <div class="eyebrow">Indian Equity &middot; Swing Desk</div>
  <h1>Backtest Results</h1>
  <div class="meta">Generated {_esc(results['generated_at'])} &middot; walk-forward, no lookahead</div>
</header>
<div class="container">
  <div class="section">
    {stat_html}
  </div>
  <div class="section">
    <h2>Equity Curve (R-multiples)</h2>
    {_equity_curve_svg(results['equity_curve'])}
  </div>
  {warning_html}
  <div class="section">
    <h2>Most Recent Signals</h2>
    {rows}
  </div>
  <div class="warning" style="margin-top:20px;">
    This is a historical simulation, not a guarantee of future results. Market
    conditions change. Use this to sanity-check the strategy's rules, not as a
    promise of what will happen next.
  </div>
  <div class="history-link"><a href="index.html">&larr; Back to latest report</a></div>
</div>
</body>
</html>"""

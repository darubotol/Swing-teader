"""
report_generator.py
Assembles the full "INDIAN EQUITY SWING REPORT" per the master prompt's
FINAL OUTPUT FORMAT (steps 13 + final output section), and a condensed
version formatted for Telegram (Markdown, message-length aware).
"""

import datetime
import config
import position_sizing


def build_candidates(scored_stocks: list) -> dict:
    """
    Sort scored candidates and bucket them into ACTIONABLE / WATCH / REJECT
    per STEP 13's final trade filter. scored_stocks items must already have
    'score' and 'position' keys attached.

    Risk control: a sector already represented among ACTIONABLE picks is
    blocked from taking a second ACTIONABLE slot. Two "different" trades in
    the same sector are not really diversified — they tend to move together,
    quietly doubling real risk beyond what the position-sizing math assumes.
    """
    actionable, watch, reject = [], [], []
    positions_used = 0
    actionable_sectors = set()

    for s in sorted(scored_stocks, key=lambda x: x["score"]["total"], reverse=True):
        total = s["score"]["total"]
        pos = s["position"]
        sector = s["info"].get("sector")

        if total >= config.SCORE_ACTIONABLE_MIN:
            sector_already_taken = sector is not None and sector in actionable_sectors
            if (
                pos["valid"]
                and pos.get("meets_min_rr")
                and positions_used < config.MAX_POSITIONS
                and not sector_already_taken
            ):
                s["status"] = "ACTIONABLE"
                actionable.append(s)
                positions_used += 1
                actionable_sectors.add(sector)
            else:
                s["status"] = "WATCH"
                if sector_already_taken:
                    s["watch_reason"] = f"Sector '{sector}' already has an actionable trade today"
                watch.append(s)
        elif total >= config.SCORE_WATCHLIST_MIN:
            s["status"] = "WATCH"
            watch.append(s)
        else:
            s["status"] = "REJECT"
            reject.append(s)

    return {"actionable": actionable, "watch": watch, "reject": reject}


def full_report_markdown(regime: dict, sector_ranking: list, buckets: dict, data_ts: str) -> str:
    today = datetime.date.today().isoformat()
    lines = []
    lines.append("# INDIAN EQUITY SWING REPORT")
    lines.append(f"**DATE:** {today}")
    lines.append(f"**DATA TIMESTAMP:** {data_ts}\n")

    lines.append("## 1. Market Regime")
    lines.append(f"**Regime:** {regime['regime']}  |  **Confidence:** {regime['confidence']}")
    for r in regime["reasons"]:
        lines.append(f"- {r}")
    lines.append("")

    lines.append("## 2. Sector Leaders")
    for i, (sector, ret) in enumerate(sector_ranking[:5], 1):
        lines.append(f"{i}. {sector} ({ret:+.1f}% / 20d avg)")
    lines.append("")

    lines.append("## 3. Top Candidates")
    lines.append("| Rank | Stock | Setup | Score | Entry | Stop | Target | R:R | Qty | Status |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    all_ranked = buckets["actionable"] + buckets["watch"] + buckets["reject"]
    for i, s in enumerate(all_ranked[:15], 1):
        info = s["info"]
        pos = s["position"]
        qty = pos["qty"] if pos.get("valid") else "-"
        lines.append(
            f"| {i} | {info['ticker'].replace('.NS','')} | {info['setup']} | "
            f"{s['score']['total']:.0f} | {info['entry']} | {info['stop']} | "
            f"{info['target']} | {info['reward_risk']} | {qty} | {s['status']} |"
        )
    lines.append("")

    lines.append("## 4. Detailed Actionable Trades")
    if not buckets["actionable"]:
        lines.append("_No trades met the ACTIONABLE bar today._\n")
    for s in buckets["actionable"]:
        info, pos, score = s["info"], s["position"], s["score"]
        name = info["ticker"].replace(".NS", "")
        lines.append(f"### {name} — {score['total']:.0f}/100")
        lines.append(f"**Setup:** {info['setup']}")
        lines.append(f"**Sector:** {info['sector']}")
        lines.append(f"**Entry:** ₹{info['entry']}  **Stop:** ₹{info['stop']}  **Target:** ₹{info['target']}")
        lines.append(f"**Risk/share:** ₹{pos['risk_per_share']}  **Reward/Risk:** {pos['reward_risk']}")
        lines.append(f"**Qty:** {pos['qty']}  **Capital deployed:** ₹{pos['capital_deployed']}  **Max loss:** ₹{pos['max_loss']}")
        lines.append(f"**Expected holding period:** 2–20 sessions")
        lines.append("**Why it qualifies:**")
        for n in info["structure_notes"]:
            lines.append(f"- {n}")
        lines.append(f"**Score breakdown:** {score['breakdown']}")
        lines.append(
            "**Note:** fundamental/catalyst and devil's-advocate checks (Steps 6–7 of "
            "the framework) are NOT automated here — verify latest results, news and "
            "event risk manually before entering.\n"
        )

    lines.append("## 5. Watchlist")
    if not buckets["watch"]:
        lines.append("_None._\n")
    for s in buckets["watch"][:10]:
        info = s["info"]
        lines.append(f"- **{info['ticker'].replace('.NS','')}** ({info['setup']}, score {s['score']['total']:.0f}) — entry trigger ₹{info['entry']}, invalidation ₹{info['stop']}")
    lines.append("")

    lines.append("## 6. Rejected Top Candidates")
    top_rejects = sorted(buckets["reject"], key=lambda x: x["score"]["total"], reverse=True)[:5]
    if not top_rejects:
        lines.append("_None scored high enough to be worth listing._\n")
    for s in top_rejects:
        info = s["info"]
        lines.append(f"- **{info['ticker'].replace('.NS','')}** (score {s['score']['total']:.0f}) — did not meet the actionable bar (see breakdown: {s['score']['breakdown']}).")
    lines.append("")

    lines.append("## 7. Final Decision")
    n_actionable = len(buckets["actionable"])
    if regime["regime"] == "RED":
        decision = "NO TRADE — market conditions unsuitable."
    elif n_actionable == 0:
        decision = "WATCHLIST ONLY" if buckets["watch"] else "NO TRADE"
    elif n_actionable == 1:
        decision = "A. TAKE ONE TRADE"
    else:
        decision = "B. TAKE TWO TRADES"
    lines.append(decision)
    lines.append("")

    lines.append("## 8. Risk Warning")
    lines.append(
        "_This is an analytical trading model, not a guarantee of returns. Market "
        "conditions can invalidate technical setups. Verify current prices, "
        "liquidity, corporate events and order details before trading._"
    )
    return "\n".join(lines)


def telegram_summary(regime: dict, buckets: dict) -> str:
    """Short-form message for Telegram (kept well under the 4096 char limit)."""
    today = datetime.date.today().isoformat()
    lines = [f"*Indian Equity Swing Report — {today}*"]
    lines.append(f"Regime: *{regime['regime']}* ({regime['confidence']} confidence)")
    lines.append("")

    if buckets["actionable"]:
        lines.append("*ACTIONABLE:*")
        for s in buckets["actionable"]:
            info, pos = s["info"], s["position"]
            name = info["ticker"].replace(".NS", "")
            lines.append(
                f"• *{name}* ({info['setup']}, {s['score']['total']:.0f}/100)\n"
                f"  Entry ₹{info['entry']} | Stop ₹{info['stop']} | Target ₹{info['target']} | "
                f"R:R {pos['reward_risk']} | Qty {pos['qty']} | Deploy ₹{pos['capital_deployed']}"
            )
    else:
        lines.append("*No ACTIONABLE trades today.*")

    if buckets["watch"]:
        lines.append("\n*Watchlist:*")
        for s in buckets["watch"][:5]:
            info = s["info"]
            lines.append(f"• {info['ticker'].replace('.NS','')} ({info['setup']}, {s['score']['total']:.0f}) — trigger ₹{info['entry']}")

    lines.append(
        "\n_Not financial advice. Fundamentals/news not auto-checked — verify "
        "before entering. Full report attached._"
    )
    return "\n".join(lines)

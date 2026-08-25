"""
position_sizing.py
Implements STEP 10 (position sizing) and STEP 11 (reward/risk) of the master
prompt. Enforces both the ₹1,500 max-risk ceiling and the ₹21,000 max
capital-per-stock ceiling, rounds down to whole shares, and rejects trades
that can't satisfy both constraints.
"""

import math
import config


def size_position(entry: float, stop: float, target: float) -> dict:
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return {"valid": False, "reason": "Stop is not below entry — invalid structure."}

    qty_by_risk = math.floor(config.MAX_RISK_PER_TRADE / risk_per_share)
    qty_by_capital = math.floor(config.MAX_CAPITAL_PER_STOCK / entry)
    qty = min(qty_by_risk, qty_by_capital)

    if qty <= 0:
        return {
            "valid": False,
            "reason": (
                f"No viable position size: risk/share ₹{risk_per_share:.2f} vs "
                f"₹{config.MAX_RISK_PER_TRADE} max risk, or entry ₹{entry:.2f} "
                f"vs ₹{config.MAX_CAPITAL_PER_STOCK} max allocation."
            ),
        }

    capital_deployed = round(qty * entry, 2)
    max_loss = round(qty * risk_per_share, 2)
    reward_risk = round((target - entry) / risk_per_share, 2)

    return {
        "valid": True,
        "qty": qty,
        "capital_deployed": capital_deployed,
        "max_loss": max_loss,
        "risk_per_share": round(risk_per_share, 2),
        "reward_risk": reward_risk,
        "meets_min_rr": reward_risk >= config.MIN_REWARD_RISK,
    }

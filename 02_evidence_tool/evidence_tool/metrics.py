"""Users, transactions, funnel, money and costs.

Counting rules (from the assignment):
  * users by user_id, purchases by transaction_id;
  * exact duplicate events were already dropped by event_id in inputs.py;
  * several verification events for one transaction = one sale;
  * a pending purchase (no verification) is not collected cash;
  * unrefunded delivered payer = verified + delivered + no known full refund at cutoff;
  * a user's channel is the channel of their first first_open (first touch, not causal);
  * shared tools and inference are counted once, at the overall level only.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .inputs import Issue

STAGES = [
    ("first_open", "First open"),
    ("qualified", "Qualified"),
    ("qualified_scan", "Qualified scan"),
    ("free_suggestion_viewed", "Free suggestion viewed"),
    ("first_time_payer", "Verified first-time payer"),
    ("delivered_guide", "Delivered guide"),
    ("unrefunded_delivered", "Unrefunded delivered payer"),
]
BEHAVIOUR_STAGES = ["first_open", "qualified", "qualified_scan", "free_suggestion_viewed"]
OVERALL = "Overall"
ZERO = Decimal("0")


def attribute_users(events, issues):
    """user_id → first-touch channel (channel of the earliest first_open)."""
    by_user = defaultdict(list)
    for e in events:
        by_user[e["user_id"]].append(e)
    channel_of = {}
    for uid, evs in by_user.items():
        evs.sort(key=lambda e: (e["ts"], e["event_id"]))
        opens = [e for e in evs if e["type"] == "first_open"]
        anchor = opens[0] if opens else evs[0]
        if not opens:
            issues.append(Issue("warning", "user.no_first_open",
                                f"{uid} has no first_open; attributed to the channel of its earliest event "
                                f"({anchor['event_id']}).", f"event_log.csv:{anchor['line']}"))
        channel_of[uid] = anchor["channel_attribution"]
        others = sorted({e["channel_attribution"] for e in evs} - {channel_of[uid]})
        if others:
            issues.append(Issue("info", "user.channel_conflict",
                                f"{uid} also has events tagged {', '.join(others)}; first-touch "
                                f"{channel_of[uid]} used.", "event_log.csv"))
    return channel_of, by_user


def build_transactions(events, cutoff, issues):
    """transaction_id → reconciled state. Verification is the source of truth for payment."""
    txs = {}
    for e in sorted(events, key=lambda e: (e["ts"], e["event_id"])):
        if e["type"] not in ("purchase", "verification", "delivery", "refund"):
            continue
        t = txs.setdefault(e["transaction_id"], {
            "id": e["transaction_id"], "user_id": e["user_id"],
            "purchase": [], "verification": [], "delivery": [], "refund": [],
        })
        if e["user_id"] != t["user_id"]:
            issues.append(Issue("error", "tx.user_mismatch",
                                f"{e['transaction_id']}: event {e['event_id']} belongs to {e['user_id']}, "
                                f"transaction belongs to {t['user_id']}; event ignored.",
                                f"event_log.csv:{e['line']}"))
            continue
        t[e["type"]].append(e)

    for t in txs.values():
        in_time = lambda evs: [e for e in evs if e["ts"] <= cutoff]
        ver, dlv, ref = in_time(t["verification"]), in_time(t["delivery"]), in_time(t["refund"])
        t["verified"] = bool(ver)
        t["verified_at"] = ver[0]["ts"] if ver else None
        t["delivered"] = t["verified"] and bool(dlv)
        t["refunded"] = t["verified"] and bool(ref)
        t["pending"] = bool(t["purchase"]) and not t["verified"]
        t["undelivered"] = t["verified"] and not t["delivered"] and not t["refunded"]
        t["event_ids"] = [e["event_id"] for k in ("purchase", "verification", "delivery", "refund") for e in t[k]]
        notes = []
        if len(t["verification"]) > 1:
            notes.append(f"{len(t['verification'])} verification events "
                         f"({', '.join(e['event_id'] for e in t['verification'])}) — counted as one sale")
        if t["verification"] and not t["purchase"]:
            notes.append("verified without a purchase event")
        if dlv and not t["verified"]:
            notes.append("delivery without verified payment — not counted as delivered")
        if ref and not t["verified"]:
            notes.append("refund without verified payment — ignored")
        late = [e["event_id"] for k in ("verification", "delivery", "refund") for e in t[k] if e["ts"] > cutoff]
        if late:
            notes.append(f"events after cutoff ignored: {', '.join(late)}")
        t["notes"] = notes
        t["status"] = ("refunded" if t["refunded"] else "delivered" if t["delivered"]
                       else "paid, not delivered" if t["verified"] else "pending" if t["pending"] else "unknown")
    return txs


def compute(inp):
    """Return the full analysis dict used by the report and the exports."""
    p, issues = inp.params, inp.issues
    events = inp.events
    if not events:
        raise ValueError("No valid events after validation; nothing to analyse.")
    cutoff = p["cutoff"] or max(e["ts"] for e in events)

    channel_of, by_user = attribute_users(events, issues)
    txs = build_transactions(events, cutoff, issues)
    for t in txs.values():
        t["channel"] = channel_of.get(t["user_id"], "(unknown)")

    # channel list: config order first, then any channel seen only in events
    channels = list(inp.channel_order)
    for ch in sorted(set(channel_of.values()) - set(channels)):
        channels.append(ch)
        issues.append(Issue("warning", "channel.no_cost_row",
                            f"{ch} appears in events but not in channel_data.csv; its cost is unknown.",
                            "channel_data.csv"))

    # ── user stages ──
    reached = {ch: {s: set() for s, _ in STAGES} for ch in channels + [OVERALL]}
    for uid, evs in by_user.items():
        types = {e["type"] for e in evs}
        ch = channel_of[uid]
        # behaviour stages are cumulative: a stage counts only if every earlier stage happened
        for i, stage in enumerate(BEHAVIOUR_STAGES):
            if stage in types and all(s in types for s in BEHAVIOUR_STAGES[:i]):
                reached[ch][stage].add(uid)
            elif stage in types:
                issues.append(Issue("warning", "user.out_of_sequence",
                                    f"{uid} has '{stage}' without every earlier stage; not counted at "
                                    f"'{stage}'.", "event_log.csv"))
        user_txs = sorted((t for t in txs.values() if t["user_id"] == uid and t["verified"]),
                          key=lambda t: (t["verified_at"], t["id"]))
        if user_txs:
            reached[ch]["first_time_payer"].add(uid)
            if "free_suggestion_viewed" not in types:
                issues.append(Issue("info", "user.paid_without_free_view",
                                    f"{uid} paid without a free suggestion viewed event.", "event_log.csv"))
            if any(t["delivered"] for t in user_txs):
                reached[ch]["delivered_guide"].add(uid)
            if any(t["delivered"] and not t["refunded"] for t in user_txs):
                reached[ch]["unrefunded_delivered"].add(uid)
    for ch in channels:
        for s, _ in STAGES:
            reached[OVERALL][s] |= reached[ch][s]
    funnel = {ch: {s: len(reached[ch][s]) for s, _ in STAGES} for ch in reached}
    users = {ch: {s: sorted(reached[ch][s]) for s, _ in STAGES} for ch in reached}

    # ── money (per transaction, so a repeat purchase is still collected cash) ──
    price, rate = p["price"], p["commission_rate"]

    def money_for(tx_list):
        verified = [t for t in tx_list if t["verified"]]
        refunded = [t for t in verified if t["refunded"]]
        kept = [t for t in verified if not t["refunded"]]
        gross = price * len(verified)
        refunds = price * len(refunded)
        commission = price * rate * len(kept)          # reversed on full refund
        return {
            "verified_tx": len(verified),
            "refunded_tx": len(refunded),
            "pending_tx": sum(t["pending"] for t in tx_list),
            "undelivered_tx": sum(t["undelivered"] for t in tx_list),
            "duplicate_verification_tx": sum(len(t["verification"]) > 1 for t in tx_list),
            "collected_cash": gross,
            "refunds": refunds,
            "commission": commission,
            "net_after_commission": gross - refunds - commission,
            "pending_not_collected": price * sum(t["pending"] for t in tx_list),
            "paid_not_delivered": price * sum(t["undelivered"] for t in tx_list),
        }

    money = {ch: money_for([t for t in txs.values() if t["channel"] == ch]) for ch in channels}
    money[OVERALL] = money_for(list(txs.values()))

    # ── costs, CAC, contribution ──
    shared = {
        "inference": p["inference_calls"] * p["inference_unit"],
        "tools": p["shared_tools"],
    }
    shared["total"] = shared["inference"] + shared["tools"]

    def div(num, den):
        return None if (num is None or not den) else num / den

    costs = {}
    for ch in channels:
        cash = inp.channels.get(ch, {}).get("cash")
        hours = p["hours"].get(ch)
        if hours is None and ch in inp.channels:
            issues.append(Issue("warning", "params.hours_missing",
                                f"No production hours for {ch} in params.json; labor treated as $0.",
                                "params.json"))
        labor = (hours or ZERO) * p["labor_rate"]
        f, m = funnel[ch], money[ch]
        costs[ch] = {
            "cash": cash, "hours": hours, "labor": labor,
            "first_pay_cac_cash": div(cash, f["first_time_payer"]),
            "delivered_cac_cash": div(cash, f["unrefunded_delivered"]),
            "delivered_cac_loaded": div(None if cash is None else cash + labor, f["unrefunded_delivered"]),
            "cash_contribution": None if cash is None else m["net_after_commission"] - cash,
            "contribution_after_labor": None if cash is None else m["net_after_commission"] - cash - labor,
        }
    known = [costs[ch]["cash"] for ch in channels if costs[ch]["cash"] is not None]
    cash_total = sum(known, ZERO)
    labor_total = sum((costs[ch]["labor"] for ch in channels), ZERO)
    hours_total = sum((costs[ch]["hours"] or ZERO for ch in channels), ZERO)
    f, m = funnel[OVERALL], money[OVERALL]
    all_cash_known = len(known) == len(channels)
    costs[OVERALL] = {
        "cash": cash_total, "hours": hours_total, "labor": labor_total, "shared": shared["total"],
        "first_pay_cac_cash": div(cash_total + shared["total"], f["first_time_payer"]),
        "delivered_cac_cash": div(cash_total + shared["total"], f["unrefunded_delivered"]),
        "delivered_cac_loaded": div(cash_total + shared["total"] + labor_total, f["unrefunded_delivered"]),
        "cash_contribution": m["net_after_commission"] - cash_total - shared["total"],
        "contribution_after_labor": m["net_after_commission"] - cash_total - shared["total"] - labor_total,
        "complete": all_cash_known,
    }

    return {
        "cutoff": cutoff,
        "channels": channels,
        "funnel": funnel,
        "users": users,
        "transactions": [txs[k] for k in sorted(txs)],
        "money": money,
        "costs": costs,
        "shared": shared,
        "user_channel": channel_of,
        "totals": {
            "users": len(by_user),
            "transactions": len(txs),
        },
    }

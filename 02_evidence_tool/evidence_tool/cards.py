"""Exactly two experiment cards: one ASO / store value card, one short-content card.

Card wording lives in config/experiments.json (editable). This module fills in
everything that must come from data — cited quotes, baselines, prerequisite
checks, readiness status, budget check, copy compliance — so a card can never
claim more than the data supports.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .inputs import InputError, Issue
from .metrics import OVERALL

REQUIRED = ("id", "type", "title", "target_problem", "hypothesis", "copy", "channel", "primary_metric",
            "guardrails", "budget_cap_usd", "stop_rule", "continue_rule", "owner", "evidence", "prerequisites",
            "product_facts", "unsupported_capabilities", "marketing_hypotheses")
TYPE_REQUIRED = {"aso": ("keyword_intent_groups", "screenshot_concept"), "short_content": ("script",)}
TYPE_LABEL = {"aso": "ASO / store value expression", "short_content": "Short content · 3-shot script"}

BLOCKED, DRAFT, REVIEW = "BLOCKED", "DRAFT", "READY FOR REVIEW"


def _fmt_rate(num, den):
    return "N/A (0 in denominator)" if not den else f"{num / den:.0%} ({num}/{den})"


def _fmt_money(v):
    return "N/A" if v is None else f"${v:,.2f}"


def resolve_citation(ref, sessions_by_id, issues, card_id):
    sid, fld = ref.get("session", ""), ref.get("field", "user_statements")
    s = sessions_by_id.get(sid)
    if s is None or fld not in ("observed_behavior", "user_statements", "researcher_inferences"):
        issues.append(Issue("error", "card.bad_citation",
                            f"{card_id}: citation {sid}/{fld} does not match any feedback record.",
                            "experiments.json"))
        return {"session_id": sid, "field": fld, "text": "(citation not found)", "broken": True}
    if not s.get(fld):
        issues.append(Issue("warning", "card.empty_citation", f"{card_id}: {sid}/{fld} is empty.",
                            "experiments.json"))
    return {"session_id": sid, "participant_id": s["participant_id"], "field": fld, "kind": s["kind"],
            "line": s["line"], "text": s.get(fld, ""), "broken": False}


def baselines(card, analysis, issues):
    ch = card.get("baseline_channel", OVERALL)
    if ch not in analysis["funnel"]:
        issues.append(Issue("error", "card.unknown_channel",
                            f"{card['id']}: baseline_channel {ch} is not in the data.", "experiments.json"))
        return ch, {}
    f, m, c = analysis["funnel"][ch], analysis["money"][ch], analysis["costs"][ch]
    budget = Decimal(str(card.get("budget_cap_usd", 0)))
    out = {"budget_cap": {"label": "Budget cap", "value": _fmt_money(budget)}}
    for b in card.get("baseline_metrics", []):
        kind = b.get("kind")
        if kind == "rate":
            value = _fmt_rate(f[b["num"]], f[b["den"]])
        elif kind == "refund_rate":
            value = _fmt_rate(m["refunded_tx"], m["verified_tx"])
        elif kind == "cash_per":
            value = _fmt_money(None if c["cash"] is None or not f[b["per"]] else c["cash"] / f[b["per"]])
            if f[b["per"]] == 0:
                value = "N/A (0 in denominator)"
        elif kind == "reach":
            # how many of `per` the budget buys at this channel's observed cash cost per `per`
            n = f[b["per"]]
            if c["cash"] is None or not n or not c["cash"]:
                value = "N/A (no observed cost per user)"
            else:
                unit = c["cash"] / n
                value = f"≈{int(budget / unit)} {b['per'].replace('_', ' ')}s at ${unit:,.2f} cash each"
        else:
            issues.append(Issue("error", "card.bad_baseline", f"{card['id']}: unknown baseline kind {kind!r}.",
                                "experiments.json"))
            continue
        out[b["key"]] = {"label": b["label"], "value": value}
    return ch, out


def fill(text, values, issues, card_id):
    def sub(m):
        key = m.group(1)
        if key not in values:
            issues.append(Issue("error", "card.bad_placeholder", f"{card_id}: unknown placeholder {{{key}}}.",
                                "experiments.json"))
            return m.group(0)
        return values[key]["value"]
    return re.sub(r"\{(\w+)\}", sub, text) if isinstance(text, str) else text


def _texts(obj):
    """All string leaves of a nested structure — used for the copy compliance scan."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _texts(v)


def _has_volume_key(obj):
    if isinstance(obj, dict):
        return any("volume" in k.lower() or _has_volume_key(v) for k, v in obj.items())
    if isinstance(obj, list):
        return any(_has_volume_key(v) for v in obj)
    return False


def build_cards(cfg, sessions, analysis, priorities, params, issues):
    raw_cards = cfg.get("cards", [])
    types = sorted(c.get("type", "?") for c in raw_cards)
    if types != ["aso", "short_content"]:
        raise InputError("experiments.json must define exactly 2 cards: one of type 'aso' and one of type "
                         f"'short_content'. Found types: {types or 'none'}.")

    sessions_by_id = {s["session_id"]: s for s in sessions}
    m = analysis["money"][OVERALL]
    priority_status = {p["id"]: p["current_status"] for p in priorities}

    data_ready = m["undelivered_tx"] == 0 and m["pending_tx"] == 0
    flag = params["commercial_delivery_ready"]
    if flag and not data_ready:
        issues.append(Issue("warning", "readiness.flag_contradicts_data",
                            f"readiness flag is true, but the data shows {m['undelivered_tx']} undelivered and "
                            f"{m['pending_tx']} pending transactions; cards stay BLOCKED.", "params.json"))
    delivery_ready = flag and data_ready

    plural = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    checks = {
        "readiness_flag": (flag, "given flag is " + ("true" if flag else "false")),
        "no_undelivered": (m["undelivered_tx"] == 0, plural(m["undelivered_tx"], "verified payment") + " undelivered"),
        "no_pending": (m["pending_tx"] == 0, plural(m["pending_tx"], "purchase") + " pending"),
    }

    cards = []
    for raw in sorted(raw_cards, key=lambda c: 0 if c["type"] == "aso" else 1):
        cid = raw.get("id", "?")
        missing = [k for k in REQUIRED + TYPE_REQUIRED.get(raw.get("type"), ()) if k not in raw or raw[k] in ("", [], {})]
        if missing:
            issues.append(Issue("error", "card.incomplete", f"{cid}: missing required field(s): {', '.join(missing)}.",
                                "experiments.json"))

        channel, base = baselines(raw, analysis, issues)
        cite = lambda refs: [resolve_citation(r, sessions_by_id, issues, cid) for r in refs or []]

        prereqs = []
        for pr in raw.get("prerequisites", []):
            chk = pr.get("check", "manual")
            if chk in checks:
                ok, detail = checks[chk]
            elif chk.startswith("priority_pass:"):
                pid = chk.split(":", 1)[1]
                st = priority_status.get(pid)
                ok = st == "PASS"
                detail = f"{pid} currently {st or 'not selected'}"
            else:
                ok = True if pr.get("confirmed") else None
                detail = "confirmed in config" if ok else "needs human confirmation"
            prereqs.append({"text": pr["text"], "met": ok, "detail": detail})

        # copy compliance: forbidden claims and invented keyword volumes
        scan_targets = {k: raw.get(k) for k in ("title", "copy", "keyword_intent_groups", "script",
                                                "screenshot_concept", "hypothesis")}
        violations = sorted({term for text in _texts(scan_targets) for term in params["forbidden_claims"]
                             if term in text.lower()})
        if _has_volume_key(raw):
            violations.append("keyword volume field present (volumes must not be invented)")
        for v in violations:
            issues.append(Issue("error", "card.copy_violation", f"{cid}: copy contains a forbidden claim: '{v}'.",
                                "experiments.json"))

        if not delivery_ready:
            status = BLOCKED
            reason = ("Commercial delivery is not ready: " +
                      "; ".join(d for k, (ok, d) in checks.items() if not ok) +
                      ". Draft only — not approved for launch.")
        elif violations or missing or any(p["met"] is not True for p in prereqs):
            status = DRAFT
            reason = "Prerequisites or copy checks open. Not approved for launch."
        else:
            status = REVIEW
            reason = "All checks pass. Needs owner sign-off before launch."

        f = lambda t: fill(t, base, issues, cid)
        card = {
            "id": cid, "type": raw["type"], "type_label": TYPE_LABEL[raw["type"]], "title": raw.get("title", ""),
            "status": status, "status_reason": reason, "approved_for_launch": False,
            "owner": raw.get("owner", ""), "channel": raw.get("channel", ""), "baseline_channel": channel,
            "target_problem": f(raw.get("target_problem", "")),
            "linked_priorities": [{"id": p, "status": priority_status.get(p, "not selected")}
                                  for p in raw.get("linked_priorities", [])],
            "evidence": cite(raw.get("evidence")),
            "prerequisites": prereqs,
            "hypothesis": f(raw.get("hypothesis", "")),
            "copy": raw.get("copy", {}),
            "product_facts": [{"text": x["text"], "evidence": cite(x.get("evidence"))}
                              for x in raw.get("product_facts", [])],
            "unsupported_capabilities": [{"text": x["text"], "evidence": cite(x.get("evidence"))}
                                         for x in raw.get("unsupported_capabilities", [])],
            "marketing_hypotheses": raw.get("marketing_hypotheses", []),
            "baselines": base,
            "primary_metric": {k: f(v) for k, v in raw.get("primary_metric", {}).items()},
            "guardrails": [{**g, "rule": f(g.get("rule", ""))} for g in raw.get("guardrails", [])],
            "budget_cap_usd": Decimal(str(raw.get("budget_cap_usd", 0))),
            "stop_rule": f(raw.get("stop_rule", "")),
            "continue_rule": f(raw.get("continue_rule", "")),
            "copy_check": {"passed": not violations, "violations": violations,
                           "terms_checked": params["forbidden_claims"]},
        }
        if raw["type"] == "aso":
            card["keyword_intent_groups"] = [
                {**{k: v for k, v in g.items() if k != "evidence"}, "evidence": cite(g.get("evidence")),
                 "search_volume": "not provided — not estimated"}
                for g in raw.get("keyword_intent_groups", [])]
            card["screenshot_concept"] = raw.get("screenshot_concept", {})
        else:
            card["script"] = [{**{k: v for k, v in s.items() if k != "evidence"}, "evidence": cite(s.get("evidence"))}
                              for s in raw.get("script", [])]
            if len(card["script"]) != 3:
                issues.append(Issue("error", "card.script_length",
                                    f"{cid}: script must have exactly 3 shots, has {len(card['script'])}.",
                                    "experiments.json"))
        cards.append(card)

    total_budget = sum((c["budget_cap_usd"] for c in cards), Decimal("0"))
    budget = {"total": total_budget, "cap": params["budget_cap"], "days": params["trial_days"],
              "within_cap": total_budget <= params["budget_cap"]}
    if not budget["within_cap"]:
        issues.append(Issue("error", "card.budget_over_cap",
                            f"Card budgets total ${total_budget:,.2f}, above the ${params['budget_cap']:,.2f} "
                            f"{params['trial_days']}-day cap.", "experiments.json"))
    return cards, budget, delivery_ready

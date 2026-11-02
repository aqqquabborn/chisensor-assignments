"""Exactly two experiment cards: one ASO / store value card, one short-content card.

Card wording lives in config/experiments.json (editable). This module fills in
everything that must come from data — cited quotes, baselines, prerequisite
checks, readiness status, budget check, copy compliance — so a card can never
claim more than the data supports.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .i18n import join, t, tn
from .inputs import InputError, Issue
from .metrics import OVERALL

REQUIRED = ("id", "type", "title", "target_problem", "hypothesis", "copy", "channel", "primary_metric",
            "guardrails", "budget_cap_usd", "stop_rule", "continue_rule", "owner", "evidence", "prerequisites",
            "product_facts", "unsupported_capabilities", "marketing_hypotheses")
TYPE_REQUIRED = {"aso": ("keyword_intent_groups", "screenshot_concept"), "short_content": ("script",)}

BLOCKED, DRAFT, REVIEW = "BLOCKED", "DRAFT", "READY FOR REVIEW"


def _fmt_rate(num, den):
    return t("na.zero_den") if not den else f"{num / den:.0%} ({num}/{den})"


def _fmt_money(v):
    return "N/A" if v is None else f"${v:,.2f}"


def resolve_citation(ref, sessions_by_id, issues, card_id):
    sid, fld = ref.get("session", ""), ref.get("field", "user_statements")
    s = sessions_by_id.get(sid)
    if s is None or fld not in ("observed_behavior", "user_statements", "researcher_inferences"):
        issues.append(Issue("error", "card.bad_citation",
                            t("issue.card.bad_citation", card=card_id, sid=sid, field=fld),
                            "experiments.json"))
        return {"session_id": sid, "field": fld, "text": t("cite.missing"), "broken": True}
    if not s.get(fld):
        issues.append(Issue("warning", "card.empty_citation", t("issue.card.empty_citation", card=card_id, sid=sid, field=fld),
                            "experiments.json"))
    return {"session_id": sid, "participant_id": s["participant_id"], "field": fld, "kind": s["kind"],
            "line": s["line"], "text": s.get(fld, ""), "broken": False}


def baselines(card, analysis, issues):
    ch = card.get("baseline_channel", OVERALL)
    if ch not in analysis["funnel"]:
        issues.append(Issue("error", "card.unknown_channel",
                            t("issue.card.unknown_channel", card=card['id'], ch=ch), "experiments.json"))
        return ch, {}
    f, m, c = analysis["funnel"][ch], analysis["money"][ch], analysis["costs"][ch]
    budget = Decimal(str(card.get("budget_cap_usd", 0)))
    out = {"budget_cap": {"label": t("budget.label"), "value": _fmt_money(budget)}}
    for b in card.get("baseline_metrics", []):
        kind = b.get("kind")
        if kind == "rate":
            value = _fmt_rate(f[b["num"]], f[b["den"]])
        elif kind == "refund_rate":
            value = _fmt_rate(m["refunded_tx"], m["verified_tx"])
        elif kind == "cash_per":
            value = _fmt_money(None if c["cash"] is None or not f[b["per"]] else c["cash"] / f[b["per"]])
            if f[b["per"]] == 0:
                value = t("na.zero_den")
        elif kind == "reach":
            # how many of `per` the budget buys at this channel's observed cash cost per `per`
            n = f[b["per"]]
            if c["cash"] is None or not n or not c["cash"]:
                value = t("na.no_cost")
            else:
                unit = c["cash"] / n
                value = t("reach", n=int(budget / unit), per=t(f"per.{b['per']}"), unit=_fmt_money(unit))
        else:
            issues.append(Issue("error", "card.bad_baseline", t("issue.card.bad_baseline", card=card['id'], kind=repr(kind)),
                                "experiments.json"))
            continue
        out[b["key"]] = {"label": b["label"], "value": value}
    return ch, out


def fill(text, values, issues, card_id):
    def sub(m):
        key = m.group(1)
        if key not in values:
            issues.append(Issue("error", "card.bad_placeholder", t("issue.card.bad_placeholder", card=card_id, ph="{" + key + "}"),
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


def build_cards(cfg, sessions, analysis, priorities, params, issues, raw_cfg=None):
    """cfg is already localised; raw_cfg (all languages) is what the copy check scans."""
    raw_by_id = {c.get("id"): c for c in (raw_cfg or cfg).get("cards", [])}
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
                            t("issue.readiness.flag_contradicts_data", u=m['undelivered_tx'], p=m['pending_tx']),
                            "params.json"))
    delivery_ready = flag and data_ready

    checks = {
        "readiness_flag": (flag, t("chk.flag", v=t("chk.true") if flag else t("chk.false"))),
        "no_undelivered": (m["undelivered_tx"] == 0, tn("chk.undelivered", m["undelivered_tx"])),
        "no_pending": (m["pending_tx"] == 0, tn("chk.pending", m["pending_tx"])),
    }

    cards = []
    for raw in sorted(raw_cards, key=lambda c: 0 if c["type"] == "aso" else 1):
        cid = raw.get("id", "?")
        missing = [k for k in REQUIRED + TYPE_REQUIRED.get(raw.get("type"), ()) if k not in raw or raw[k] in ("", [], {})]
        if missing:
            issues.append(Issue("error", "card.incomplete", t("issue.card.incomplete", card=cid, fields=join(missing)),
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
                detail = t("chk.priority", id=pid, status=t(f"pstatus.{st or 'NOT SELECTED'}"))
            else:
                ok = True if pr.get("confirmed") else None
                detail = t("chk.confirmed") if ok else t("chk.manual")
            prereqs.append({"text": pr["text"], "met": ok, "detail": detail})

        # copy compliance: forbidden claims and invented keyword volumes
        lint_src = raw_by_id.get(cid, raw)
        scan_targets = {k: lint_src.get(k) for k in ("title", "copy", "keyword_intent_groups", "script",
                                                     "screenshot_concept", "hypothesis")}
        violations = sorted({term for text in _texts(scan_targets) for term in params["forbidden_claims"]
                             if term in text.lower()})
        if _has_volume_key(lint_src):
            violations.append("keyword volume field present (volumes must not be invented)")
        for v in violations:
            issues.append(Issue("error", "card.copy_violation", t("issue.card.copy_violation", card=cid, v=v),
                                "experiments.json"))

        if not delivery_ready:
            status = BLOCKED
            reason = t("reason.blocked", list=t("sep.semi").join(d for k, (ok, d) in checks.items() if not ok))
        elif violations or missing or any(p["met"] is not True for p in prereqs):
            status = DRAFT
            reason = t("reason.draft")
        else:
            status = REVIEW
            reason = t("reason.review")

        f = lambda t: fill(t, base, issues, cid)
        card = {
            "id": cid, "type": raw["type"], "type_label": t(f"type.{raw['type']}"), "title": raw.get("title", ""),
            "status": status, "status_label": t(f"cstatus.{status}"), "status_reason": reason, "approved_for_launch": False,
            "owner": raw.get("owner", ""), "channel": raw.get("channel", ""), "baseline_channel": channel,
            "target_problem": f(raw.get("target_problem", "")),
            "linked_priorities": [{"id": p, "status": priority_status.get(p, "NOT SELECTED")}
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
                 "search_volume": t("kw.novolume")}
                for g in raw.get("keyword_intent_groups", [])]
            card["screenshot_concept"] = raw.get("screenshot_concept", {})
        else:
            card["script"] = [{**{k: v for k, v in s.items() if k != "evidence"}, "evidence": cite(s.get("evidence"))}
                              for s in raw.get("script", [])]
            if len(card["script"]) != 3:
                issues.append(Issue("error", "card.script_length",
                                    t("issue.card.script_length", card=cid, n=len(card['script'])),
                                    "experiments.json"))
        cards.append(card)

    total_budget = sum((c["budget_cap_usd"] for c in cards), Decimal("0"))
    budget = {"total": total_budget, "cap": params["budget_cap"], "days": params["trial_days"],
              "within_cap": total_budget <= params["budget_cap"]}
    if not budget["within_cap"]:
        issues.append(Issue("error", "card.budget_over_cap",
                            t("issue.card.budget_over_cap", total=_fmt_money(total_budget),
                              cap=_fmt_money(params['budget_cap']), days=params['trial_days']), "experiments.json"))
    return cards, budget, delivery_ready

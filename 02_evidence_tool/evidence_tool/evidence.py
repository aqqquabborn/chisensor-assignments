"""Feedback sessions → up to N evidence-linked product priorities.

Evidence rule: a session supports a priority only through what was OBSERVED or
what the user SAID. Researcher inferences are shown next to it as
interpretation but never count as evidence. Participants are counted by
participant_id, so a re-test session never adds a participant.
"""
from __future__ import annotations

import re

from .inputs import Issue
from .metrics import OVERALL

EVIDENCE_FIELDS = ("observed_behavior", "user_statements")
FIELD_LABELS = {
    "observed_behavior": "Observed",
    "user_statements": "Said",
    "researcher_inferences": "Researcher inference",
}
REQUIRED_PRIORITY_KEYS = ("id", "title", "user_problem", "match_terms", "event_evidence",
                          "proposed_change", "acceptance_pass", "acceptance_fail")


def _natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def classify_sessions(sessions):
    """Mark each session as first observation or re-test of the same participant."""
    order_key = (lambda s: (s.get("session_date") or "", _natural(s["session_id"])))
    seen = {}
    for s in sorted(sessions, key=order_key):
        pid = s["participant_id"]
        seen[pid] = seen.get(pid, 0) + 1
        s["visit"] = seen[pid]
        s["kind"] = "first observation" if seen[pid] == 1 else f"re-test #{seen[pid] - 1}"
    return {
        "sessions": len(sessions),
        "participants": len(seen),
        "retests": sum(1 for s in sessions if s["visit"] > 1),
        "multi_session_participants": sorted(p for p, n in seen.items() if n > 1),
    }


def event_evidence(kind, analysis):
    """Quantitative evidence from the event log for one priority type.

    Returns (summary dict, current_pass: bool | None). current_pass compares the
    current data with the priority's pass condition where it can be measured.
    """
    f = analysis["funnel"][OVERALL]
    m = analysis["money"][OVERALL]
    if kind == "payment_delivery":
        txs = analysis["transactions"]
        ids = lambda pred: [t["id"] for t in txs if pred(t)]
        lines = [
            ("Verified but not delivered", ids(lambda t: t["undelivered"])),
            ("Pending, never verified", ids(lambda t: t["pending"])),
            ("Full refund after delivery", ids(lambda t: t["refunded"])),
            ("Duplicate verification events", ids(lambda t: len(t["verification"]) > 1)),
        ]
        magnitude = m["undelivered_tx"] + m["pending_tx"] + m["refunded_tx"]
        return {
            "headline": f"{magnitude} of {analysis['totals']['transactions']} transactions did not end as a "
                        f"kept, delivered purchase",
            "rows": [{"label": l, "count": len(v), "ids": v} for l, v in lines],
            "magnitude": magnitude,
            "baseline": f"{m['undelivered_tx']} undelivered, {m['pending_tx']} pending",
        }, (m["undelivered_tx"] == 0 and m["pending_tx"] == 0)
    if kind == "scan_capture":
        lost = f["qualified"] - f["qualified_scan"]
        return {
            "headline": f"{lost} of {f['qualified']} qualified users never completed a qualified scan",
            "rows": [{"label": "Qualified → qualified scan", "count": f["qualified_scan"],
                      "of": f["qualified"], "ids": []}],
            "magnitude": lost,
            "baseline": f"{f['qualified_scan']}/{f['qualified']} qualified users scanned",
        }, None
    if kind == "free_to_paid":
        lost = f["free_suggestion_viewed"] - f["first_time_payer"]
        return {
            "headline": f"{lost} of {f['free_suggestion_viewed']} users who saw the free suggestion did not pay",
            "rows": [
                {"label": "Free suggestion → verified first-time payer", "count": f["first_time_payer"],
                 "of": f["free_suggestion_viewed"], "ids": []},
                {"label": "Verified purchases fully refunded", "count": m["refunded_tx"],
                 "of": m["verified_tx"], "ids": []},
            ],
            "magnitude": lost,
            "baseline": f"{f['first_time_payer']}/{f['free_suggestion_viewed']} paid; "
                        f"{m['refunded_tx']}/{m['verified_tx']} refunded",
        }, None
    return {"headline": "No related events in the event log", "rows": [], "magnitude": 0, "baseline": "—"}, None


def derive_priorities(sessions, analysis, cfg, issues):
    total_participants = len({s["participant_id"] for s in sessions})
    max_n = int(cfg.get("max_priorities", 3))
    min_p = int(cfg.get("min_participants", 2))
    candidates = []

    for raw in cfg.get("candidates", []):
        missing = [k for k in REQUIRED_PRIORITY_KEYS if not raw.get(k)]
        if missing:
            issues.append(Issue("error", "priority.incomplete",
                                f"Candidate {raw.get('id', '?')} is missing {', '.join(missing)}; skipped.",
                                "priorities.json"))
            continue
        terms = [t.lower() for t in raw["match_terms"]]
        cites = []
        for s in sessions:
            hits = {}
            for fld in EVIDENCE_FIELDS:
                text = s.get(fld, "").lower()
                found = [t for t in terms if t in text]
                if found:
                    hits[fld] = found
            if hits:
                cites.append({
                    "session_id": s["session_id"], "participant_id": s["participant_id"],
                    "kind": s["kind"], "line": s["line"], "matched": hits,
                    "observed_behavior": s["observed_behavior"], "user_statements": s["user_statements"],
                    "researcher_inferences": s["researcher_inferences"],
                    "product_version": s.get("product_version") or "not recorded",
                })
        participants = sorted({c["participant_id"] for c in cites})
        ev, passing = event_evidence(raw["event_evidence"], analysis)
        first = sum(c["kind"] == "first observation" for c in cites)
        uncertainty = [
            f"{len(participants)} of {total_participants} research participants; "
            f"{first} first-observation and {len(cites) - first} re-test session(s).",
            "Research participants are a separate cohort from event-log users, so event evidence is related, "
            "not the same people.",
        ]
        if any(c["product_version"] == "not recorded" and c["kind"] != "first observation" for c in cites):
            uncertainty.append("Product version is not recorded, so re-tests may reflect a different build.")
        candidates.append({
            "id": raw["id"], "title": raw["title"], "user_problem": raw["user_problem"],
            "proposed_change": raw["proposed_change"],
            "acceptance_pass": raw["acceptance_pass"], "acceptance_fail": raw["acceptance_fail"],
            "match_terms": raw["match_terms"], "event_evidence_kind": raw["event_evidence"],
            "participants": participants, "citations": cites,
            "event_evidence": ev,
            "current_status": ("PASS" if passing else "FAIL") if passing is not None else "BASELINE SET",
            "uncertainty": uncertainty,
            "analyst_note": raw.get("analyst_note", ""),
            "eligible": len(participants) >= min_p,
        })

    ranked = sorted(candidates, key=lambda c: (-len(c["participants"]), -c["event_evidence"]["magnitude"], c["id"]))
    selected = [c for c in ranked if c["eligible"]][:max_n]
    for i, c in enumerate(selected, 1):
        c["rank"] = i
    rejected = []
    for c in ranked:
        if c in selected:
            continue
        if not c["eligible"]:
            reason = f"{len(c['participants'])} participant(s); minimum is {min_p}"
        else:
            reason = (f"ranked below the top {max_n}: {len(c['participants'])} participants, "
                      f"event evidence {c['event_evidence']['magnitude']}")
        rejected.append({"id": c["id"], "title": c["title"], "participants": c["participants"],
                         "sessions": [x["session_id"] for x in c["citations"]], "reason": reason})
    return selected, rejected, total_participants

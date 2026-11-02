"""Run order from the assignment: read & validate → keep source IDs → de-duplicate
events and transactions → user stages and costs → feedback to ≤3 priorities →
exactly 2 experiment cards → export the report and the cards."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import __version__
from .cards import build_cards
from .evidence import classify_sessions, derive_priorities
from .inputs import load_all
from .metrics import OVERALL, STAGES, compute
from .render import render_html, render_markdown

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def run(data_dir, config_dir):
    inp = load_all(Path(data_dir), Path(config_dir))
    analysis = compute(inp)
    research = classify_sessions(inp.sessions)
    priorities, rejected, total_participants = derive_priorities(
        inp.sessions, analysis, inp.priorities_cfg, inp.issues)
    cards, budget, delivery_ready = build_cards(
        inp.experiments_cfg, inp.sessions, analysis, priorities, inp.params, inp.issues)

    issues = sorted((i.as_dict() for i in inp.issues),
                    key=lambda i: (SEVERITY_ORDER[i["severity"]], i["code"], i["source"]))
    return {
        "version": __version__,
        "fingerprints": dict(sorted(inp.fingerprints.items())),
        "params": inp.params,
        "counts": inp.counts,
        "issues": issues,
        "analysis": analysis,
        "stages": STAGES,
        "overall": OVERALL,
        "research": research,
        "sessions": sorted(inp.sessions, key=lambda s: s["line"]),
        "priorities": priorities,
        "rejected_priorities": rejected,
        "priorities_cfg": inp.priorities_cfg,
        "total_participants": total_participants,
        "cards": cards,
        "budget": budget,
        "delivery_ready": delivery_ready,
    }


def to_jsonable(obj):
    if isinstance(obj, Decimal):
        return float(round(obj, 2))
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    return obj


def _strip_tx(t):
    """Transaction for export: keep IDs and states, drop the raw event dicts."""
    return {k: v for k, v in t.items() if k not in ("purchase", "verification", "delivery", "refund")}


def export_payload(result):
    a = result["analysis"]
    return {
        "version": result["version"],
        "input_sha256": result["fingerprints"],
        "cutoff": a["cutoff"],
        "issues": result["issues"],
        "input_counts": result["counts"],
        "funnel": a["funnel"],
        "funnel_user_ids": a["users"],
        "money": a["money"],
        "costs": a["costs"],
        "shared_costs_counted_once": a["shared"],
        "transactions": [_strip_tx(t) for t in a["transactions"]],
        "research": result["research"],
        "priorities": result["priorities"],
        "not_selected": result["rejected_priorities"],
        "experiment_cards": result["cards"],
        "experiment_budget": result["budget"],
    }


def write_outputs(result, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dump = lambda obj: json.dumps(to_jsonable(obj), indent=2, ensure_ascii=False) + "\n"
    files = {
        "report.html": render_html(result),
        "analysis.json": dump(export_payload(result)),
        "experiment_cards.json": dump({"input_sha256": result["fingerprints"],
                                       "budget": result["budget"], "cards": result["cards"]}),
        "experiment_cards.md": render_markdown(result),
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    return [out / n for n in files]

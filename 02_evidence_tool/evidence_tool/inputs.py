"""Read and validate the three CSV inputs and the JSON config.

Every problem becomes an `Issue` (shown in the report) instead of a crash.
Only structural problems that make the run meaningless — a missing file or a
missing required column — raise `InputError`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

EVENT_COLUMNS = ["event_id", "user_id", "transaction_id", "timestamp", "event_type", "channel_attribution"]
CHANNEL_COLUMNS = ["channel_name", "cash_costs", "first_touch_attribution"]
FEEDBACK_COLUMNS = ["session_id", "participant_id", "observed_behavior", "user_statements", "researcher_inferences"]

# Raw event_type spellings → canonical type. Normalised with lower() and "_" → " ".
EVENT_TYPE_ALIASES = {
    "first open": "first_open",
    "qualified": "qualified",
    "scan": "qualified_scan",
    "qualified scan": "qualified_scan",
    "free suggestion viewed": "free_suggestion_viewed",
    "complete free suggestion viewed": "free_suggestion_viewed",
    "purchase": "purchase", "purchases": "purchase",
    "verification": "verification", "verifications": "verification",
    "delivery": "delivery", "delivered": "delivery",
    "refund": "refund", "refunds": "refund",
}
PAYMENT_TYPES = {"purchase", "verification", "delivery", "refund"}
TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


class InputError(Exception):
    """A fatal input problem: the report cannot be produced."""


@dataclass
class Issue:
    severity: str          # "error" | "warning" | "info"
    code: str              # stable machine code, e.g. "event.duplicate_conflict"
    message: str
    source: str = ""       # "event_log.csv:14" — file and physical line

    def as_dict(self):
        return {"severity": self.severity, "code": self.code, "message": self.message, "source": self.source}


@dataclass
class Inputs:
    events: list = field(default_factory=list)       # valid, de-duplicated event dicts
    channels: dict = field(default_factory=dict)     # channel → {"cash": Decimal|None, "line": int}
    channel_order: list = field(default_factory=list)
    sessions: list = field(default_factory=list)     # valid feedback session dicts
    params: dict = field(default_factory=dict)
    priorities_cfg: dict = field(default_factory=dict)
    experiments_cfg: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)       # per-file row accounting
    fingerprints: dict = field(default_factory=dict)  # file → sha256


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_text(path: Path, fingerprints: dict) -> str:
    if not path.exists():
        raise InputError(f"Missing input file: {path}")
    raw = path.read_bytes()
    fingerprints[path.name] = _sha(raw)
    return raw.decode("utf-8-sig")  # tolerate a BOM from Excel exports


def _require_columns(header, required, fname):
    header = [h.strip() for h in (header or [])]
    missing = [c for c in required if c not in header]
    if missing:
        raise InputError(
            f"{fname}: missing required column(s): {', '.join(missing)}. "
            f"Found: {', '.join(header) or '(empty header)'}"
        )
    return header


def parse_timestamp(value: str):
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


# ─── events ─────────────────────────────────────────────────────────

def load_events(path: Path, issues: list, counts: dict, fingerprints: dict):
    text = _read_text(path, fingerprints)
    reader = csv.reader(io.StringIO(text))
    header = _require_columns(next(reader, None), EVENT_COLUMNS, path.name)
    idx = {name: header.index(name) for name in EVENT_COLUMNS}

    seen = {}            # event_id → normalised tuple of the first occurrence
    events = []
    c = {"rows": 0, "exact_duplicates": 0, "conflicting_duplicates": 0, "invalid": 0, "valid": 0}
    duplicate_ids = []

    for row in reader:
        line = reader.line_num
        if not any(cell.strip() for cell in row):
            continue
        c["rows"] += 1
        src = f"{path.name}:{line}"
        if len(row) != len(header):
            c["invalid"] += 1
            issues.append(Issue("error", "event.bad_row", f"Expected {len(header)} fields, got {len(row)}; row skipped.", src))
            continue
        rec = {k: row[i].strip() for k, i in idx.items()}

        eid = rec["event_id"]
        if not eid:
            c["invalid"] += 1
            issues.append(Issue("error", "event.missing_id", "event_id is empty; row skipped.", src))
            continue
        fingerprint = tuple(rec[k] for k in EVENT_COLUMNS)
        if eid in seen:
            if seen[eid] == fingerprint:
                c["exact_duplicates"] += 1
                duplicate_ids.append(eid)
            else:
                c["conflicting_duplicates"] += 1
                issues.append(Issue("error", "event.duplicate_conflict",
                                    f"{eid} reused with different content; first occurrence kept.", src))
            continue
        seen[eid] = fingerprint

        problems = []
        if not rec["user_id"]:
            problems.append("user_id is empty")
        ts = parse_timestamp(rec["timestamp"]) if rec["timestamp"] else None
        if ts is None:
            problems.append(f"timestamp '{rec['timestamp']}' is not a valid date-time")
        etype = EVENT_TYPE_ALIASES.get(rec["event_type"].lower().replace("_", " ").strip())
        if etype is None:
            problems.append(f"unknown event_type '{rec['event_type']}'")
        if not rec["channel_attribution"]:
            problems.append("channel_attribution is empty")
        if etype in PAYMENT_TYPES and not rec["transaction_id"]:
            problems.append(f"{etype} event has no transaction_id")
        if problems:
            c["invalid"] += 1
            issues.append(Issue("error", "event.invalid", f"{eid}: " + "; ".join(problems) + "; row skipped.", src))
            continue

        rec.update({"type": etype, "ts": ts, "line": line})
        events.append(rec)

    c["valid"] = len(events)
    if duplicate_ids:
        issues.append(Issue("info", "event.exact_duplicates_removed",
                            f"{len(duplicate_ids)} exact duplicate event rows removed: {', '.join(duplicate_ids)}.",
                            path.name))
    counts[path.name] = c
    return events


# ─── channels ───────────────────────────────────────────────────────

def load_channels(path: Path, issues: list, counts: dict, fingerprints: dict):
    text = _read_text(path, fingerprints)
    reader = csv.reader(io.StringIO(text))
    header = _require_columns(next(reader, None), CHANNEL_COLUMNS, path.name)
    idx = {name: header.index(name) for name in CHANNEL_COLUMNS}
    channels, order = {}, []
    c = {"rows": 0, "invalid": 0, "valid": 0}

    for row in reader:
        line = reader.line_num
        if not any(cell.strip() for cell in row):
            continue
        c["rows"] += 1
        src = f"{path.name}:{line}"
        rec = {k: (row[i].strip() if i < len(row) else "") for k, i in idx.items()}
        name = rec["channel_name"]
        if not name:
            c["invalid"] += 1
            issues.append(Issue("error", "channel.missing_name", "channel_name is empty; row skipped.", src))
            continue
        if name in channels:
            c["invalid"] += 1
            issues.append(Issue("error", "channel.duplicate", f"{name} listed twice; first row kept.", src))
            continue
        cash = None
        try:
            cash = Decimal(rec["cash_costs"])
            if cash < 0 or not cash.is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            cash = None
            issues.append(Issue("error", "channel.invalid_cost",
                                f"{name}: cash_costs '{rec['cash_costs']}' is not a non-negative number; "
                                f"CAC for this channel shown as N/A.", src))
        if rec["first_touch_attribution"] and rec["first_touch_attribution"] != name:
            issues.append(Issue("warning", "channel.attribution_mismatch",
                                f"{name}: first_touch_attribution is '{rec['first_touch_attribution']}'; "
                                f"events are matched on channel_name.", src))
        channels[name] = {"cash": cash, "line": line}
        order.append(name)
    c["valid"] = len(channels)
    counts[path.name] = c
    return channels, order


# ─── feedback ───────────────────────────────────────────────────────
# The feedback file supplied with the assignment is not valid CSV: free-text
# fields contain unquoted commas. The only reliably quoted field is
# user_statements, so a row with too many fields is rebuilt around it.
_REPAIR = re.compile(r'^([^,]*),([^,]*),(.*?),"((?:[^"]|"")*)",(.*)$')


def load_feedback(path: Path, issues: list, counts: dict, fingerprints: dict):
    text = _read_text(path, fingerprints)
    physical = text.splitlines()
    reader = csv.reader(io.StringIO(text))
    header = _require_columns(next(reader, None), FEEDBACK_COLUMNS, path.name)
    idx = {name: header.index(name) for name in FEEDBACK_COLUMNS}
    optional = [h for h in ("product_version", "session_date") if h in header]

    sessions, seen = [], {}
    repaired = []
    c = {"rows": 0, "repaired": 0, "duplicates": 0, "invalid": 0, "valid": 0}

    for row in reader:
        line = reader.line_num
        if not any(cell.strip() for cell in row):
            continue
        c["rows"] += 1
        src = f"{path.name}:{line}"
        if len(row) == len(header):
            rec = {k: row[i].strip() for k, i in idx.items()}
            for opt in optional:
                rec[opt] = row[header.index(opt)].strip()
        else:
            m = _REPAIR.match(physical[line - 1]) if len(header) == 5 else None
            if not m:
                c["invalid"] += 1
                issues.append(Issue("error", "feedback.bad_row",
                                    f"Expected {len(header)} fields, got {len(row)} and the row could not be "
                                    f"repaired; quote free-text fields that contain commas.", src))
                continue
            rec = dict(zip(FEEDBACK_COLUMNS, (g.strip().replace('""', '"') for g in m.groups())))
            c["repaired"] += 1
            repaired.append(rec["session_id"])
        rec["line"] = line
        rec["repaired"] = rec["session_id"] in repaired

        missing = [k for k in ("session_id", "participant_id") if not rec[k]]
        if missing:
            c["invalid"] += 1
            issues.append(Issue("error", "feedback.missing_id", f"{', '.join(missing)} empty; row skipped.", src))
            continue
        if not rec["observed_behavior"] and not rec["user_statements"]:
            issues.append(Issue("warning", "feedback.no_evidence",
                                f"{rec['session_id']}: no observed behavior and no user statement; "
                                f"it cannot support a priority.", src))
        key = rec["session_id"]
        sig = tuple(rec[k] for k in FEEDBACK_COLUMNS)
        if key in seen:
            c["duplicates"] += 1
            sev = "info" if seen[key] == sig else "error"
            issues.append(Issue(sev, "feedback.duplicate_session",
                                f"{key} appears again; first occurrence kept.", src))
            continue
        seen[key] = sig
        sessions.append(rec)

    if repaired:
        issues.append(Issue("warning", "feedback.repaired_rows",
                            f"{len(repaired)} rows had unquoted commas in free text and were repaired "
                            f"around the quoted user statement: {', '.join(repaired)}. Please quote these "
                            f"fields at the source.", path.name))
    if "product_version" not in header:
        issues.append(Issue("info", "feedback.no_product_version",
                            "No product_version column: first observations and re-tests cannot be tied to a "
                            "build, so re-test results may reflect a different version.", path.name))
    c["valid"] = len(sessions)
    counts[path.name] = c
    return sessions


# ─── config ─────────────────────────────────────────────────────────

def load_json(path: Path, fingerprints: dict):
    text = _read_text(path, fingerprints)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"{path.name}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc


def _num(params, key, issues, minimum=0, maximum=None):
    value = params.get(key)
    try:
        d = Decimal(str(value))
        if not d.is_finite() or d < minimum or (maximum is not None and d >= maximum):
            raise InvalidOperation
        return d
    except (InvalidOperation, ValueError, TypeError):
        raise InputError(f"params.json: '{key}' must be a number"
                         f"{' ≥ ' + str(minimum) if minimum is not None else ''}"
                         f"{' and < ' + str(maximum) if maximum is not None else ''}; got {value!r}")


def validate_params(raw: dict, issues: list):
    p = {
        "price": _num(raw, "price_usd", issues),
        "commission_rate": _num(raw, "commission_rate", issues, 0, 1),
        "labor_rate": _num(raw, "labor_rate_usd_per_hour", issues),
        "inference_calls": _num(raw, "inference_calls", issues),
        "inference_unit": _num(raw, "inference_cost_per_call_usd", issues),
        "shared_tools": _num(raw, "shared_tools_usd", issues),
        "low_n": int(_num(raw, "low_sample_threshold", issues)),
    }
    trial = raw.get("next_trial") or {}
    p["budget_cap"] = _num(trial, "budget_cap_usd", issues)
    p["trial_days"] = int(_num(trial, "days", issues))

    hours = raw.get("production_hours_by_channel") or {}
    p["hours_source"] = hours.get("_source", "")
    p["hours"] = {}
    for k, v in hours.items():
        if k.startswith("_"):
            continue
        try:
            d = Decimal(str(v))
            if d < 0:
                raise InvalidOperation
            p["hours"][k] = d
        except (InvalidOperation, ValueError):
            issues.append(Issue("error", "params.invalid_hours", f"Production hours for {k} = {v!r} is invalid; "
                                f"treated as missing.", "params.json"))

    cutoff = raw.get("cutoff")
    p["cutoff"] = None
    if cutoff:
        p["cutoff"] = parse_timestamp(str(cutoff))
        if p["cutoff"] is None:
            raise InputError(f"params.json: cutoff {cutoff!r} is not a valid date-time")

    readiness = raw.get("readiness") or {}
    flag = readiness.get("commercial_delivery_ready")
    if not isinstance(flag, bool):
        issues.append(Issue("error", "params.readiness_missing",
                            "readiness.commercial_delivery_ready must be true or false; treated as false.",
                            "params.json"))
        flag = False
    p["commercial_delivery_ready"] = flag
    p["readiness_note"] = readiness.get("_note", "")
    p["forbidden_claims"] = [s.lower() for s in raw.get("forbidden_claims", [])]
    return p


def load_all(data_dir: Path, config_dir: Path) -> Inputs:
    inp = Inputs()
    fp, issues, counts = inp.fingerprints, inp.issues, inp.counts
    inp.events = load_events(data_dir / "event_log.csv", issues, counts, fp)
    inp.channels, inp.channel_order = load_channels(data_dir / "channel_data.csv", issues, counts, fp)
    inp.sessions = load_feedback(data_dir / "feedback_sessions.csv", issues, counts, fp)
    inp.params = validate_params(load_json(config_dir / "params.json", fp), issues)
    inp.priorities_cfg = load_json(config_dir / "priorities.json", fp)
    inp.experiments_cfg = load_json(config_dir / "experiments.json", fp)
    return inp

#!/usr/bin/env python3
"""ChiSensor evidence → experiments tool.

    python analyze.py                      # data/ + config/ → out/
    python analyze.py --data other_data --out other_out
    python analyze.py --strict             # exit 1 if any error-level input issue
    python analyze.py --lang zh            # only the Chinese report (default: both en and zh)

Exit codes: 0 ok · 1 --strict and input errors found · 2 fatal input problem.
Standard library only (Python 3.9+). No network, keys or accounts.
"""
import argparse
import sys
from pathlib import Path

from evidence_tool.inputs import InputError
from evidence_tool.metrics import OVERALL
from evidence_tool.pipeline import run, write_outputs
from evidence_tool.render import money


HERE = Path(__file__).resolve().parent


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(HERE / "data"), help="folder with event_log.csv, channel_data.csv, feedback_sessions.csv")
    ap.add_argument("--config", default=str(HERE / "config"), help="folder with params.json, priorities.json, experiments.json")
    ap.add_argument("--out", default=str(HERE / "out"), help="output folder")
    ap.add_argument("--strict", action="store_true", help="fail when any error-level input issue is found")
    ap.add_argument("--lang", choices=["en", "zh", "all"], default="all",
                    help="report language: en, zh, or all (default) — writes report.html and report.zh-CN.html")
    args = ap.parse_args(argv)

    langs = ["en", "zh"] if args.lang == "all" else [args.lang]
    paths = []
    try:
        for lang in reversed(langs):  # English last, so the summary below is printed in English
            result = run(args.data, args.config, lang)
            paths += write_outputs(result, args.out)
    except (InputError, ValueError) as exc:
        print(f"Input problem: {exc}", file=sys.stderr)
        return 2

    a = result["analysis"]
    f, m, c = a["funnel"][OVERALL], a["money"][OVERALL], a["costs"][OVERALL]
    sev = {s: sum(i["severity"] == s for i in result["issues"]) for s in ("error", "warning", "info")}
    n = lambda k, word: f"{sev[k]} {word}{'' if sev[k] == 1 else 's'}"
    print(f"Inputs: {n('error', 'error')}, {n('warning', 'warning')}, {n('info', 'note')}")
    print(f"Funnel: {f['first_open']} first opens → {f['qualified_scan']} qualified scans → "
          f"{f['first_time_payer']} first-time payers → {f['unrefunded_delivered']} unrefunded delivered")
    print(f"Cash: collected {money(m['collected_cash'])}, refunds {money(m['refunds'])}, "
          f"net after commission {money(m['net_after_commission'])}, pending (not collected) "
          f"{money(m['pending_not_collected'])}")
    print(f"Contribution: cash {money(c['cash_contribution'])}, after labor {money(c['contribution_after_labor'])}")
    for p in result["priorities"]:
        print(f"Priority {p['rank']}: {p['id']} — {len(p['participants'])} participants ({p['current_status']})")
    for cd in result["cards"]:
        print(f"Card {cd['id']}: {cd['status']}")
    for pth in paths:
        print(f"Wrote {pth}")
    if args.strict and sev["error"]:
        for i in result["issues"]:
            if i["severity"] == "error":
                print(f"ERROR {i['code']}: {i['message']} [{i['source']}]", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

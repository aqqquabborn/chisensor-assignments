#!/usr/bin/env bash
# 3-minute demo: run, test, then show that changed inputs change the results.
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

step "1. Run on the supplied inputs"
python3 analyze.py --out "$TMP/base" | sed -n '1,9p'

step "2. Repeatable checks"
python3 -m unittest 2>&1 | tail -3

step "3. Re-import every event a second time (users and sales must not change)"
cp -r data "$TMP/dup"; tail -n +2 data/event_log.csv >> "$TMP/dup/event_log.csv"
python3 analyze.py --data "$TMP/dup" --out "$TMP/o3" | sed -n '2,3p'

step "4. Add a full refund for TX_U001_01 (unrefunded delivered 6 → 5, refunds +\$9.99)"
cp -r data "$TMP/ref"; cp -r config "$TMP/cfg"
echo "E09001,U001,TX_U001_01,2026-06-21 13:00:00,refunds,ASA_Brand" >> "$TMP/ref/event_log.csv"
python3 analyze.py --data "$TMP/ref" --out "$TMP/o4" | sed -n '2,3p'

step "5. Double the labor rate (cash CAC unchanged, contribution after labor drops)"
python3 - "$TMP/cfg/params.json" <<'EOF'
import json, sys; p = json.load(open(sys.argv[1])); p["labor_rate_usd_per_hour"] = 50
json.dump(p, open(sys.argv[1], "w"), indent=2)
EOF
python3 analyze.py --config "$TMP/cfg" --out "$TMP/o5" | sed -n '4p'

step "6. Same input twice → identical report"
python3 analyze.py --out "$TMP/again" >/dev/null
cmp "$TMP/base/report.html" "$TMP/again/report.html" && echo "report.html identical"

echo; echo "Open out/report.html (python3 analyze.py writes it there)."

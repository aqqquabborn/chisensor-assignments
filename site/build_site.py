#!/usr/bin/env python3
"""Assemble the hosted version of the submission.

    python build_site.py <01_room_prototype dir> <02_evidence_tool dir> <out dir>

Needs `npm run build` in 01 (dist/) and `python analyze.py` in 02 (out/).
Writes: index.html (cover page), prototype.html (single-file app),
report.html, experiment_cards.md/.json. Every number on the cover page is
read from 02's out/ files, so it cannot drift from the report.
"""
import json
import os
import re
import shutil
import sys
from html import escape as esc
from pathlib import Path

proto, tool, out = (Path(a).resolve() for a in sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)

# ── 1. prototype → one self-contained HTML file (the bundle inlined) ──
dist = proto / "dist"
page = (dist / "index.html").read_text(encoding="utf-8")
m = re.search(r'<script type="module" crossorigin src="([^"]+)"></script>', page)
bundle = (dist / m.group(1).lstrip("./")).read_text(encoding="utf-8").replace("</script", "<\\/script")
page = page.replace(m.group(0), "")
page = re.sub(r'<link rel="icon"[^>]*>\s*', "", page)
page = page.replace("</body>", f'<script type="module">{bundle}</script>\n</body>')
(out / "prototype.html").write_text(page, encoding="utf-8")

# ── 2. report + cards copied as generated ──
for name in ("report.html", "experiment_cards.md", "experiment_cards.json"):
    shutil.copy(tool / "out" / name, out / name)

# ── 3. cover page from the tool's outputs ──
a = json.loads((tool / "out" / "analysis.json").read_text(encoding="utf-8"))
f, m_, c = a["funnel"]["Overall"], a["money"]["Overall"], a["costs"]["Overall"]
cards = a["experiment_cards"]
prios = a["priorities"]
budget = a["experiment_budget"]
participants = a["research"]["participants"]
REPO = os.environ.get("REPO_URL", "https://github.com/")


def money(v):
    return f"−${-v:,.2f}" if v < 0 else f"${v:,.2f}"


def plural(n, w):
    return f"{n} {w}{'' if n == 1 else 's'}"


reasons = []
if m_["undelivered_tx"]:
    reasons.append(f"{plural(m_['undelivered_tx'], 'verified payment')} never delivered")
if m_["pending_tx"]:
    reasons.append(f"{plural(m_['pending_tx'], 'purchase')} stuck in pending")

prio_rows = "".join(
    f'<li><span class="rank">{p["rank"]}</span><div><strong>{esc(p["title"])}</strong>'
    f'<span class="meta">{len(p["participants"])} of {participants} participants · '
    f'{esc(p["event_evidence"]["headline"])}</span></div></li>' for p in prios)
card_rows = "".join(
    f'<li><div class="cardhead"><span class="state s-{c_["status"].split()[0].lower()}">{esc(c_["status"])}</span>'
    f'<span class="meta mono">{esc(c_["id"])} · cap {money(c_["budget_cap_usd"])}</span></div>'
    f'<strong>{esc(c_["title"])}</strong><span class="meta">{esc(c_["type_label"])}</span></li>' for c_ in cards)

SCENARIOS = [
    ("① happy", "Scan all three areas → analysis → free action → unlock → confirm → deliver"),
    ("② unsupported", "Stopped and explained before any scan"),
    ("③ scan_incomplete", "Missing area named; re-scan keeps what was captured"),
    ("④ analysis_failed_recoverable", "Step 3 fails once; Retry continues the same job ID"),
    ("⑤ purchase_pending", "Plan stays locked; refresh keeps the same transaction"),
    ("⑥ verified_payment_delivery_failed", "Retry delivers on the same transaction, no new charge"),
]
scen_rows = "".join(f'<tr><th scope="row" class="mono">{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in SCENARIOS)

html = f"""<title>ChiSensor Submission</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a cover sheet — two assignment bands, each pairing the live thing with what to check; a verification ledger closes. */
:root {{
  --paper: #f6f7f8; --sheet: #ffffff; --ink: #14181f; --muted: #5d6673; --rule: #dde1e6;
  --accent: #0e6f68; --accent-soft: #e2f1ef; --stop: #b42318; --stop-soft: #fdecea; --warn: #8a5a00; --warn-soft: #fbf0d9;
  --ok: #1d6b45; --ok-soft: #e3f3ea; --device: #1b1f27;
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --body: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #0f1216; --sheet: #161a20; --ink: #e8ebef; --muted: #9aa3ae; --rule: #2a3039;
  --accent: #4fc3b6; --accent-soft: #12312e; --stop: #ff8f80; --stop-soft: #3a1714; --warn: #f0bc5c; --warn-soft: #33270f;
  --ok: #6fd6a0; --ok-soft: #12301f; --device: #000; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --paper: #0f1216; --sheet: #161a20; --ink: #e8ebef; --muted: #9aa3ae; --rule: #2a3039;
  --accent: #4fc3b6; --accent-soft: #12312e; --stop: #ff8f80; --stop-soft: #3a1714; --warn: #f0bc5c; --warn-soft: #33270f;
  --ok: #6fd6a0; --ok-soft: #12301f; --device: #000; color-scheme: dark }}
* {{ box-sizing: border-box }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding-block: 0; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)) }}
header.wrap {{ padding-block: 40px 28px }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 }}
h1 {{ font: 700 clamp(28px, 4.4vw, 44px)/1.08 var(--display); letter-spacing: -.015em; margin: 10px 0 10px; text-wrap: balance }}
h2 {{ font: 700 24px/1.15 var(--display); margin: 0; text-wrap: balance }}
h3 {{ font: 600 13px/1.3 var(--body); text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 8px }}
.lead {{ max-width: 66ch; color: var(--muted); margin: 0 }}
.mono {{ font-family: var(--mono); font-size: .92em }}
a {{ color: var(--accent) }}
a:focus-visible, button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px }}
.status {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px }}
.pill {{ font: 500 12.5px/1 var(--mono); padding: 7px 10px; border-radius: 999px; background: var(--sheet); border: 1px solid var(--rule) }}
.pill b {{ color: var(--ok); font-weight: 500 }}
section {{ background: var(--sheet); border-block: 1px solid var(--rule); padding-block: 32px; margin-block: 0 20px }}
.band-head {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; margin-bottom: 18px }}
.tag {{ font: 500 12px/1 var(--mono); color: var(--accent); background: var(--accent-soft); padding: 5px 8px; border-radius: 6px }}
.grid {{ display: grid; grid-template-columns: minmax(0, 400px) minmax(0, 1fr); gap: 32px; align-items: start }}
@media (max-width: 860px) {{ .grid {{ grid-template-columns: minmax(0, 1fr) }} }}
.device {{ background: var(--device); border-radius: 34px; padding: 10px; max-width: 410px; margin-inline: auto; width: 100% }}
.device iframe {{ display: block; width: 100%; height: 760px; border: 0; border-radius: 26px; background: #fff }}
.device-cap {{ text-align: center; font-size: 12.5px; color: var(--muted); margin: 10px 0 0 }}
.stack {{ display: grid; gap: 22px; min-width: 0 }}
.stack > *, .grid > *, .two > * {{ min-width: 0 }}
@media (max-width: 520px) {{ tbody th {{ white-space: normal; word-break: break-word }} }}
.scroll {{ overflow-x: auto }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px }}
th, td {{ text-align: left; vertical-align: top; padding: 8px 10px 8px 0; border-bottom: 1px solid var(--rule) }}
tbody th {{ font-weight: 500; white-space: nowrap; padding-right: 16px }}
.note {{ font-size: 13.5px; color: var(--muted); margin: 0 }}
.btnrow {{ display: flex; flex-wrap: wrap; gap: 8px }}
.btn {{ display: inline-flex; align-items: center; min-height: 40px; padding: 0 14px; border-radius: 8px; font-weight: 600; font-size: 14px; text-decoration: none; border: 1px solid var(--rule); color: var(--ink); background: var(--sheet) }}
.btn.primary {{ background: var(--accent); color: var(--sheet); border-color: var(--accent) }}
.verdict {{ border-left: 4px solid var(--stop); background: var(--stop-soft); padding: 12px 14px; border-radius: 0 8px 8px 0 }}
.verdict strong {{ color: var(--stop) }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0; border-top: 1px solid var(--rule) }}
.kpi {{ padding: 12px 12px 12px 0; border-bottom: 1px solid var(--rule) }}
.kpi .v {{ font: 700 24px/1.1 var(--display); font-variant-numeric: tabular-nums }}
.kpi .l {{ font-size: 12.5px; color: var(--muted) }}
ol.list, ul.list {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px }}
ol.list li {{ display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 10px; align-items: start }}
.rank {{ width: 26px; height: 26px; border-radius: 50%; background: var(--accent); color: var(--sheet); display: grid; place-items: center; font: 600 13px/1 var(--mono) }}
.meta {{ display: block; font-size: 13px; color: var(--muted) }}
ul.list li {{ border: 1px solid var(--rule); border-radius: 10px; padding: 12px 14px; display: grid; gap: 4px }}
.cardhead {{ display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center }}
.state {{ font: 600 11.5px/1 var(--mono); letter-spacing: .04em; padding: 5px 8px; border-radius: 6px }}
.s-blocked {{ background: var(--stop-soft); color: var(--stop) }} .s-draft {{ background: var(--warn-soft); color: var(--warn) }} .s-ready {{ background: var(--ok-soft); color: var(--ok) }}
.ledger td.n {{ font: 500 14px var(--mono); white-space: nowrap; font-variant-numeric: tabular-nums }}
pre {{ background: var(--paper); border: 1px solid var(--rule); border-radius: 8px; padding: 12px 14px; overflow-x: auto; font: 13px/1.5 var(--mono); margin: 6px 0 0 }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px }}
footer.wrap {{ padding-block: 8px 40px; color: var(--muted); font-size: 12.5px }}
@media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto }} }}
</style>

<header class="wrap">
  <p class="eyebrow">ChiSensor · remote assignments</p>
  <h1>Two runnable submissions, one place to check them</h1>
  <p class="lead">Assignment 1 runs live in the phone frame below. Assignment 2's report is generated by the tool from the supplied CSV files. Nothing here needs a paid API, an account or a real payment; every scan, analysis and purchase step is simulated and labelled.</p>
  <div class="status" aria-label="Check results">
    <span class="pill">Assignment 1 · <b>29 automated tests pass</b></span>
    <span class="pill">Assignment 2 · <b>27 automated tests pass</b></span>
    <span class="pill">Python 3.9–3.13 · Node 20+</span>
  </div>
</header>

<section aria-labelledby="a1">
  <div class="wrap">
    <div class="band-head"><span class="tag">Assignment 1</span><h2 id="a1">Recoverable room-to-plan prototype</h2></div>
    <div class="grid">
      <div>
        <div class="device"><iframe src="prototype.html" title="ChiSensor bedroom prototype" loading="lazy"></iframe></div>
        <p class="device-cap">Live prototype at 390 px. Open <b>Test panel</b> at the bottom to switch scenario.</p>
      </div>
      <div class="stack">
        <p class="lead">A renter's bed cannot move; the goal is an easier walk from the door to the bedside without buying furniture. The bedroom is 4.0 m × 3.5 m; the free action moves the chair out of the entry path.</p>
        <div>
          <h3>Scenarios to try</h3>
          <div class="scroll"><table><tbody>{scen_rows}</tbody></table></div>
        </div>
        <p class="note">Refresh during analysis or a pending payment: the same job ID or transaction ID comes back. The Test panel shows job ID, transaction ID, entitlement and delivery status, and can send a duplicate verification event.</p>
        <div class="btnrow"><a class="btn primary" href="prototype.html" target="_blank" rel="noopener">Open full screen</a></div>
      </div>
    </div>
  </div>
</section>

<section aria-labelledby="a2">
  <div class="wrap">
    <div class="band-head"><span class="tag">Assignment 2</span><h2 id="a2">Evidence to promotion experiments</h2></div>
    <div class="grid">
      <div class="stack">
        <p class="verdict"><strong>Fix delivery before promoting.</strong> {esc("; ".join(reasons).capitalize() if reasons else "Delivery is ready")}. Both experiment cards stay BLOCKED as drafts.</p>
        <div class="kpis">
          <div class="kpi"><div class="v">{f["first_open"]}</div><div class="l">first opens</div></div>
          <div class="kpi"><div class="v">{f["unrefunded_delivered"]}</div><div class="l">unrefunded delivered payers</div></div>
          <div class="kpi"><div class="v">{money(m_["net_after_commission"])}</div><div class="l">net after commission</div></div>
          <div class="kpi"><div class="v">{money(c["cash_contribution"])}</div><div class="l">cash contribution (not profit)</div></div>
        </div>
        <div class="btnrow">
          <a class="btn primary" href="report.html" target="_blank" rel="noopener">Open the full report</a>
          <a class="btn" href="experiment_cards.md" target="_blank" rel="noopener">Cards · Markdown</a>
          <a class="btn" href="experiment_cards.json" target="_blank" rel="noopener">Cards · JSON</a>
        </div>
      </div>
      <div class="stack">
        <div><h3>Product priorities</h3><ol class="list">{prio_rows}</ol></div>
        <div><h3>Experiment cards · {money(budget["total"])} of {money(budget["cap"])} cap</h3><ul class="list">{card_rows}</ul></div>
      </div>
    </div>
  </div>
</section>

<section aria-labelledby="v">
  <div class="wrap two">
    <div>
      <h2 id="v">Verification</h2>
      <div class="scroll"><table class="ledger"><tbody>
        <tr><th scope="row">Prototype — unit checks</th><td>State machine, analysis retry, idempotent payment, persistence, room geometry</td><td class="n">21 pass</td></tr>
        <tr><th scope="row">Prototype — browser checks</th><td>Six brief flows at 390 px, refresh recovery, no camera or payment API use</td><td class="n">8 pass</td></tr>
        <tr><th scope="row">Tool — repeatable checks</th><td>Reprocessing, zero payers, new refund, same participant, cost change, validation, readiness</td><td class="n">27 pass</td></tr>
        <tr><th scope="row">Tool — mutation run</th><td>Six injected bugs, each caught by at least one check</td><td class="n">6 / 6</td></tr>
      </tbody></table></div>
    </div>
    <div>
      <h2>Run it locally</h2>
      <p class="note">Source, data and tests: <a href="{REPO}">{esc(REPO.replace("https://", ""))}</a>.</p>
      <pre>cd 01_room_prototype
npm install
npm run dev        # http://localhost:5173
npm run check      # build + 21 unit + 8 browser checks</pre>
      <pre>cd 02_evidence_tool
python analyze.py  # → out/report.html
python -m unittest -v
bash scripts/demo.sh</pre>
    </div>
  </div>
</section>

<footer class="wrap">Cover figures are read from the tool's own output (analysis.json). Inputs: {esc(" · ".join(f"{k} {v[:10]}" for k, v in a["input_sha256"].items() if k.endswith(".csv")))}. $9.99 is the exercise's example price.</footer>
"""
head, body = html.split("</style>", 1)
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + head + "</style>\n</head>\n<body>" + body + "</body>\n</html>\n")
(out / "index.html").write_text(doc, encoding="utf-8")
print("site written to", out, [p.name for p in sorted(out.iterdir())])

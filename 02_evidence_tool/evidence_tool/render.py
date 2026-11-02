"""Self-contained HTML report + Markdown experiment cards.

Every string that comes from input or config passes through esc(). The output
is deterministic (no clock, no random IDs): same inputs → identical bytes.
"""
from __future__ import annotations

import json
from decimal import Decimal
from html import escape

from .metrics import OVERALL


def esc(x):
    return escape("" if x is None else str(x), quote=True)


def money(v, na="N/A"):
    if v is None:
        return na
    v = Decimal(v).quantize(Decimal("0.01"))
    return f"−${-v:,.2f}" if v < 0 else f"${v:,.2f}"


def pct(num, den):
    return "—" if not den else f"{num / den:.0%}"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def badge(text, kind="neutral", title=""):
    t = f' title="{esc(title)}"' if title else ""
    return f'<span class="badge b-{kind}"{t}>{esc(text)}</span>'


def cite_link(sid, extra=""):
    return f'<a class="cite" href="#{esc(sid)}">{esc(sid)}{esc(extra)}</a>'


def tx_link(tid):
    return f'<a class="cite mono" href="#tx-{esc(tid)}">{esc(tid)}</a>'


FIELD_LABEL = {"observed_behavior": "Observed", "user_statements": "Said",
               "researcher_inferences": "Researcher inference"}


# ─── sections ───────────────────────────────────────────────────────

def section_summary(r):
    a, o = r["analysis"], r["overall"]
    f, m, c = a["funnel"][o], a["money"][o], a["costs"][o]
    stages = r["stages"]

    # biggest adjacent drop in the overall funnel
    drops = [(f[stages[i][0]] - f[stages[i + 1][0]], stages[i][1], stages[i + 1][1], f[stages[i][0]])
             for i in range(len(stages) - 1)]
    lost, s_from, s_to, base = max(drops, key=lambda d: d[0])

    # channel CAC extremes (cash, unrefunded delivered payer)
    with_cac = [(a["costs"][ch]["delivered_cac_cash"], ch) for ch in a["channels"]
                if a["costs"][ch]["delivered_cac_cash"] is not None]
    no_payer = [ch for ch in a["channels"] if a["funnel"][ch]["unrefunded_delivered"] == 0]
    largest = max((a["funnel"][ch]["first_open"] for ch in a["channels"]), default=0)

    if r["delivery_ready"]:
        verdict = ('<div class="verdict ok"><strong>Delivery is ready.</strong> Experiments can move to review '
                   'once their own prerequisites are confirmed.</div>')
    else:
        reasons = []
        if m["undelivered_tx"]:
            reasons.append(f"{plural(m['undelivered_tx'], 'verified payment')} never delivered")
        if m["pending_tx"]:
            reasons.append(f"{plural(m['pending_tx'], 'purchase')} stuck in pending")
        if not r["params"]["commercial_delivery_ready"]:
            reasons.append("the given readiness flag is false")
        verdict = (f'<div class="verdict stop"><strong>Fix delivery before promoting.</strong> '
                   f'{esc(("; ".join(reasons))[:1].upper() + ("; ".join(reasons))[1:])}. '
                   f'Both experiment cards stay BLOCKED as drafts — '
                   f'nothing here is approved for launch.</div>')

    tiles = [
        ("First opens", f["first_open"], "users, first-touch"),
        ("Qualified scans", f["qualified_scan"], f"{pct(f['qualified_scan'], f['first_open'])} of first opens"),
        ("First-time payers", f["first_time_payer"],
         f"{pct(f['first_time_payer'], f['free_suggestion_viewed'])} of free-suggestion viewers"),
        ("Unrefunded delivered", f["unrefunded_delivered"], f"{pct(f['unrefunded_delivered'], f['first_open'])} of first opens"),
        ("Net after commission", money(m["net_after_commission"]), f"of {money(m['collected_cash'])} collected"),
        ("Cash contribution", money(c["cash_contribution"]), f"{money(c['contribution_after_labor'])} after labor"),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="t-label">{esc(l)}</div><div class="t-value">{esc(v)}</div>'
        f'<div class="t-sub">{esc(s)}</div></div>' for l, v, s in tiles)

    findings = [
        f"Largest drop: <b>{esc(s_from)} → {esc(s_to)}</b> — {lost} of {base} users "
        f"({pct(lost, base)}) did not continue.",
        f"Payments: {m['verified_tx']} verified purchases, {m['refunded_tx']} fully refunded, "
        f"{m['undelivered_tx']} paid but not delivered, {m['pending_tx']} pending (not collected).",
    ]
    if with_cac:
        lo, hi = min(with_cac), max(with_cac)
        findings.append(
            f"Cash CAC per unrefunded delivered payer ranges from <b>{money(lo[0])}</b> ({esc(lo[1])}) to "
            f"<b>{money(hi[0])}</b> ({esc(hi[1])})"
            + (f"; N/A for {esc(', '.join(no_payer))} (0 payers)" if no_payer else "")
            + f". The largest channel has {largest} first opens, so treat channel comparisons as directional.")
    if r["priorities"]:
        p0 = r["priorities"][0]
        findings.append(f"Top product priority: <b>{esc(p0['title'])}</b> — {len(p0['participants'])} of "
                        f"{r['total_participants']} research participants.")
    reach = [f"{esc(cd['id'])} {esc(cd['baselines']['reach']['value'])}"
             for cd in r["cards"] if "reach" in cd["baselines"]]
    if reach:
        findings.append("At observed costs each experiment cap buys few users (" + "; ".join(reach) +
                        "), so expect a directional read, not a significant result.")
    items = "".join(f"<li>{x}</li>" for x in findings)
    return f"""
<section id="summary">
  {verdict}
  <div class="tiles">{tiles_html}</div>
  <h2 class="h-sm">What the data says</h2>
  <ul class="findings">{items}</ul>
</section>"""


def section_quality(r):
    counts = r["counts"]
    rows = []
    labels = [("rows", "Rows read"), ("valid", "Valid"), ("exact_duplicates", "Exact duplicates removed"),
              ("conflicting_duplicates", "Conflicting duplicates"), ("duplicates", "Duplicate sessions"),
              ("repaired", "Repaired rows"), ("invalid", "Invalid, skipped")]
    for fname, c in counts.items():
        cells = "".join(f'<td class="num">{c.get(k, "—")}</td>' for k, _ in labels)
        rows.append(f'<tr><th scope="row" class="mono">{esc(fname)}</th>{cells}</tr>')
    head = "".join(f'<th scope="col" class="num">{esc(l)}</th>' for _, l in labels)

    by_sev = {"error": [], "warning": [], "info": []}
    for i in r["issues"]:
        by_sev[i["severity"]].append(i)

    def issue_list(items):
        return "".join(
            f'<li>{badge(i["severity"], {"error": "bad", "warning": "warn", "info": "neutral"}[i["severity"]])} '
            f'<span class="mono dim">{esc(i["code"])}</span> {esc(i["message"])} '
            f'<span class="src mono">{esc(i["source"])}</span></li>' for i in items)

    main = by_sev["error"] + by_sev["warning"]
    main_html = (f'<ul class="issues">{issue_list(main)}</ul>' if main
                 else '<p class="ok-line">No errors or warnings.</p>')
    info_html = (f'<details><summary>{len(by_sev["info"])} notes</summary><ul class="issues">'
                 f'{issue_list(by_sev["info"])}</ul></details>' if by_sev["info"] else "")
    fp = "".join(f'<li><span class="mono">{esc(k)}</span> <span class="mono dim">{esc(v[:16])}…</span></li>'
                 for k, v in r["fingerprints"].items())
    return f"""
<section id="quality">
  <h2>1 · Input checks</h2>
  <p class="lead">{plural(len(by_sev['error']), 'error')} · {plural(len(by_sev['warning']), 'warning')} ·
  {plural(len(by_sev['info']), 'note')}.
  Exact duplicate events are removed by <span class="mono">event_id</span> before anything is counted;
  a reused ID with different content is an error and is not merged.</p>
  <div class="scroll"><table>
    <caption>Rows per input file</caption>
    <thead><tr><th scope="col">File</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  {main_html}
  {info_html}
  <details><summary>Input fingerprints (SHA-256)</summary><ul class="fp">{fp}</ul></details>
</section>"""


def section_funnel(r):
    a, o, stages = r["analysis"], r["overall"], r["stages"]
    f = a["funnel"][o]
    top = f[stages[0][0]] or 1
    bars = []
    for i, (key, label) in enumerate(stages):
        n = f[key]
        prev = f[stages[i - 1][0]] if i else None
        step = "" if i == 0 else f'{pct(n, prev)} of previous · −{prev - n}'
        bars.append(
            f'<div class="fbar"><div class="f-label">{esc(label)}</div>'
            f'<div class="f-track"><div class="f-fill" style="width:{n / top * 100:.1f}%"></div></div>'
            f'<div class="f-num"><b>{n}</b> <span class="dim">{pct(n, top)}</span></div>'
            f'<div class="f-step dim">{esc(step)}</div></div>')

    low_n = r["params"]["low_n"]
    head = "".join(f'<th scope="col" class="num">{esc(l)}</th>' for _, l in stages)
    rows = []
    for ch in a["channels"] + [o]:
        fc = a["funnel"][ch]
        cells = []
        for i, (key, _) in enumerate(stages):
            n = fc[key]
            if i == 0:
                cells.append(f'<td class="num"><b>{n}</b></td>')
            else:
                den = fc[stages[i - 1][0]]
                sub = f"{pct(n, den)} of {den}" if den else "no denominator"
                cells.append(f'<td class="num"><b>{n}</b><span class="sub">{sub}</span></td>')
        flag = badge("low n", "warn", f"fewer than {low_n} first opens") if fc["first_open"] < low_n else ""
        cls = ' class="total"' if ch == o else ""
        rows.append(f'<tr{cls}><th scope="row">{esc(ch)} {flag}</th>{"".join(cells)}</tr>')
    return f"""
<section id="funnel">
  <h2>2 · Funnel</h2>
  <p class="lead">Users counted once by <span class="mono">user_id</span> and attributed to the channel of their
  first <span class="mono">first_open</span> (first touch — not incrementality). The first four stages are
  cumulative; payer stages come from verified transactions.</p>
  <div class="funnel" role="img" aria-label="Overall funnel">{''.join(bars)}</div>
  <div class="scroll"><table class="funnel-table">
    <caption>By channel — count, then % of the previous stage and its denominator</caption>
    <thead><tr><th scope="col">Channel</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
</section>"""


STATUS_KIND = {"delivered": "good", "refunded": "muted", "paid, not delivered": "bad", "pending": "warn",
               "unknown": "neutral"}


def section_money(r):
    a, o = r["analysis"], r["overall"]
    cols = [("verified_tx", "Verified purchases", False), ("collected_cash", "Collected cash", True),
            ("refunds", "Known refunds", True), ("commission", "Commission", True),
            ("net_after_commission", "Net after commission", True),
            ("pending_not_collected", "Pending — not collected", True),
            ("paid_not_delivered", "Paid, not delivered", True)]
    head = "".join(f'<th scope="col" class="num">{esc(l)}</th>' for _, l, _ in cols)
    rows = []
    for ch in a["channels"] + [o]:
        mm = a["money"][ch]
        cells = "".join(f'<td class="num">{money(mm[k]) if is_m else mm[k]}</td>' for k, _, is_m in cols)
        cls = ' class="total"' if ch == o else ""
        rows.append(f'<tr{cls}><th scope="row">{esc(ch)}</th>{cells}</tr>')

    tx_rows = []
    for t in a["transactions"]:
        yes = lambda b: "✓" if b else "—"
        ver = ", ".join(e["event_id"] for e in t["verification"]) or "—"
        tx_rows.append(
            f'<tr id="tx-{esc(t["id"])}"><th scope="row" class="mono">{esc(t["id"])}</th>'
            f'<td class="mono">{esc(t["user_id"])}</td><td>{esc(t["channel"])}</td>'
            f'<td>{badge(t["status"], STATUS_KIND.get(t["status"], "neutral"))}</td>'
            f'<td class="c">{yes(t["purchase"])}</td><td class="mono">{esc(ver)}</td>'
            f'<td class="c">{yes(t["delivered"])}</td><td class="c">{yes(t["refunded"])}</td>'
            f'<td class="mono dim">{esc(", ".join(t["event_ids"]))}</td>'
            f'<td>{esc("; ".join(t["notes"]))}</td></tr>')
    p = r["params"]
    return f"""
<section id="money">
  <h2>3 · Payments and cash</h2>
  <p class="lead">Money is counted per verified transaction at {money(p['price'])} (example price).
  A second verification event for the same transaction adds nothing. Commission is
  {p['commission_rate'] * 100:.0f}% of kept sales and is reversed on a full refund. Pending purchases are shown
  but are not collected cash.</p>
  <div class="scroll"><table>
    <caption>Cash by channel</caption>
    <thead><tr><th scope="col">Channel</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  <details open><summary>All {len(a['transactions'])} transactions (audit trail)</summary>
  <div class="scroll"><table class="tx">
    <thead><tr><th scope="col">Transaction</th><th scope="col">User</th><th scope="col">Channel</th>
    <th scope="col">Status at cutoff</th><th scope="col">Purchase</th><th scope="col">Verification event(s)</th>
    <th scope="col">Delivered</th><th scope="col">Refunded</th><th scope="col">Source events</th>
    <th scope="col">Notes</th></tr></thead>
    <tbody>{''.join(tx_rows)}</tbody>
  </table></div></details>
</section>"""


def section_costs(r):
    a, o, p = r["analysis"], r["overall"], r["params"]
    rows = []
    for ch in a["channels"] + [o]:
        c, f, m = a["costs"][ch], a["funnel"][ch], a["money"][ch]
        hours = "—" if c["hours"] is None else f"{c['hours']:g} h"
        shared = money(c["shared"]) if ch == o else "—"
        na = lambda v, d: money(v) if v is not None else f'<span class="na" title="{esc(d)}">N/A</span>'
        cash_na = "cost missing" if c["cash"] is None else "0 payers"
        cls = ' class="total"' if ch == o else ""
        rows.append(
            f'<tr{cls}><th scope="row">{esc(ch)}</th>'
            f'<td class="num">{money(c["cash"])}</td><td class="num">{shared}</td>'
            f'<td class="num">{money(c["labor"])}<span class="sub">{hours}</span></td>'
            f'<td class="num">{f["first_time_payer"]}</td>'
            f'<td class="num">{na(c["first_pay_cac_cash"], cash_na)}</td>'
            f'<td class="num">{f["unrefunded_delivered"]}</td>'
            f'<td class="num">{na(c["delivered_cac_cash"], cash_na)}</td>'
            f'<td class="num">{na(c["delivered_cac_loaded"], cash_na)}</td>'
            f'<td class="num">{money(m["net_after_commission"])}</td>'
            f'<td class="num">{money(c["cash_contribution"])}</td>'
            f'<td class="num">{money(c["contribution_after_labor"])}</td></tr>')
    s = a["shared"]
    return f"""
<section id="costs">
  <h2>4 · Cost, CAC and contribution</h2>
  <p class="lead">Three cost types are kept apart and each is counted once: <b>channel cash</b> (from
  channel_data.csv), <b>converted production labor</b> (hours × {money(p['labor_rate'])}/h) and <b>shared
  processing</b> — {p['inference_calls']:g} inference calls × {money(p['inference_unit'])} =
  {money(s['inference'])} plus shared tools {money(s['tools'])} — which appears only in the Overall row.
  CAC is N/A, never $0, when its payer denominator is zero.</p>
  <p class="assume">{badge("assumption", "warn")} Labor hours come from <span class="mono">config/params.json</span>,
  not from the input data — {esc(p['hours_source'] or 'no source given')}</p>
  <div class="scroll"><table>
    <caption>Cash CAC uses cash only (Overall adds shared processing); “+ labor” adds converted production labor</caption>
    <thead><tr><th scope="col">Channel</th><th scope="col" class="num">Channel cash</th>
    <th scope="col" class="num">Shared, once</th><th scope="col" class="num">Labor (converted)</th>
    <th scope="col" class="num">First-time payers</th><th scope="col" class="num">First-pay CAC, cash</th>
    <th scope="col" class="num">Unrefunded delivered</th><th scope="col" class="num">Delivered CAC, cash</th>
    <th scope="col" class="num">Delivered CAC, + labor</th><th scope="col" class="num">Net after commission</th>
    <th scope="col" class="num">Cash contribution</th><th scope="col" class="num">Contribution after labor</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  <p class="note">Contribution is an exercise metric (net cash after commission and refunds, minus the listed
  costs). It is not company profit. Tax and FX are ignored.</p>
</section>"""


def _quote_table(cites):
    rows = []
    for c in cites:
        hits = c["matched"]
        cell = lambda fld: (f'<td class="{"hit" if fld in hits else ""}">{esc(c[fld])}'
                            + (f'<span class="sub">matched: {esc(", ".join(hits[fld]))}</span>' if fld in hits else "")
                            + "</td>")
        rows.append(f'<tr><th scope="row">{cite_link(c["session_id"])}<span class="sub">{esc(c["participant_id"])} · '
                    f'{esc(c["kind"])}</span></th>{cell("observed_behavior")}{cell("user_statements")}'
                    f'<td class="dim">{esc(c["researcher_inferences"])}</td></tr>')
    return (f'<div class="scroll"><table class="quotes"><thead><tr><th scope="col">Session</th>'
            f'<th scope="col">Observed (evidence)</th><th scope="col">Said (evidence)</th>'
            f'<th scope="col">Researcher inference (not counted)</th></tr></thead><tbody>{"".join(rows)}</tbody>'
            f'</table></div>')


def section_priorities(r):
    out = []
    for p in r["priorities"]:
        ev = p["event_evidence"]
        ev_rows = "".join(
            f'<li>{esc(row["label"])}: <b>{row["count"]}</b>'
            + (f' of {row["of"]}' if "of" in row else "")
            + (" — " + ", ".join(tx_link(i) for i in row["ids"]) if row["ids"] else "") + "</li>"
            for row in ev["rows"])
        chips = " ".join(cite_link(c["session_id"], f' · {c["participant_id"]} · '
                                   f'{"first" if c["kind"] == "first observation" else "re-test"}')
                         for c in p["citations"])
        status_kind = {"PASS": "good", "FAIL": "bad"}.get(p["current_status"], "neutral")
        unc = "".join(f"<li>{esc(u)}</li>" for u in p["uncertainty"])
        out.append(f"""
  <article class="prio" data-id="{esc(p['id'])}">
    <header><span class="rank">{p['rank']}</span>
      <h3 data-field="title">{esc(p['title'])}</h3>{badge(p['id'], 'neutral')}</header>
    <dl class="kv">
      <dt>User problem</dt><dd data-field="user_problem">{esc(p['user_problem'])}</dd>
      <dt>Independent participants</dt><dd><b>{len(p['participants'])} of {r['total_participants']}</b> ·
        <span class="mono">{esc(' '.join(p['participants']))}</span></dd>
      <dt>Feedback IDs</dt><dd class="chips">{chips}</dd>
      <dt>Event evidence</dt><dd>{esc(ev['headline'])}{f'<ul class="tight">{ev_rows}</ul>' if ev_rows else ''}</dd>
      <dt>Proposed change</dt><dd data-field="proposed_change">{esc(p['proposed_change'])}</dd>
      <dt>Pass if</dt><dd data-field="acceptance_pass">{esc(p['acceptance_pass'])}</dd>
      <dt>Fail if</dt><dd data-field="acceptance_fail">{esc(p['acceptance_fail'])}</dd>
      <dt>Now</dt><dd>{badge(p['current_status'], status_kind)} <span class="dim">baseline: {esc(ev['baseline'])}</span></dd>
      <dt>Uncertainty</dt><dd><ul class="tight">{unc}</ul></dd>
      <dt>Analyst note</dt><dd data-field="analyst_note">{esc(p['analyst_note'] or '—')}</dd>
      <dt>Match terms</dt><dd data-field="match_terms" class="mono">{esc(', '.join(p['match_terms']))}</dd>
    </dl>
    <details><summary>Quotes behind this priority — observed, said, inferred</summary>{_quote_table(p['citations'])}</details>
  </article>""")

    rej = "".join(
        f'<tr><th scope="row">{esc(x["id"])}</th><td>{esc(x["title"])}</td>'
        f'<td class="mono">{esc(" ".join(x["participants"]) or "—")}</td>'
        f'<td>{" ".join(cite_link(s) for s in x["sessions"]) or "—"}</td><td>{esc(x["reason"])}</td></tr>'
        for x in r["rejected_priorities"])
    cfg_json = json.dumps(r["priorities_cfg"], ensure_ascii=False).replace("</", "<\\/")
    rule = r["priorities_cfg"]
    return f"""
<section id="priorities">
  <h2>5 · Product priorities</h2>
  <p class="lead">Up to {rule.get('max_priorities', 3)} changes, ranked by independent participants (re-tests never
  add a participant), then by the size of the related event evidence; at least
  {rule.get('min_participants', 2)} participants are required. Only observed behavior and user statements count as
  evidence; researcher inferences are shown beside them but not counted.</p>
  <div class="toolbar no-print">
    <button type="button" id="edit-toggle" aria-pressed="false">Edit priorities</button>
    <button type="button" id="download-priorities">Export priorities.json</button>
    <span class="dim">Edits stay in this page. Export, save the JSON as <span class="mono">config/priorities.json</span>
    and re-run to recompute evidence.</span>
  </div>
  <div id="export-box" class="no-print" hidden>
    <textarea id="export-json" readonly rows="10" aria-label="priorities.json"></textarea>
    <span class="dim small" id="export-status"></span>
  </div>
  {''.join(out)}
  <h3 class="h-sm">Considered, not selected</h3>
  <div class="scroll"><table><thead><tr><th scope="col">ID</th><th scope="col">Candidate</th>
  <th scope="col">Participants</th><th scope="col">Sessions</th><th scope="col">Why not</th></tr></thead>
  <tbody>{rej or '<tr><td colspan="5">None</td></tr>'}</tbody></table></div>
  <script type="application/json" id="priorities-config">{cfg_json}</script>
</section>"""


def _cite_list(cites):
    return "".join(
        f'<li>{cite_link(c["session_id"])} <span class="dim">{esc(FIELD_LABEL.get(c["field"], c["field"]))}'
        + (f' · {esc(c.get("participant_id", ""))} · {esc(c.get("kind", ""))}' if not c["broken"] else "")
        + f'</span> <q>{esc(c["text"])}</q></li>' for c in cites)


def _inline_cites(cites):
    return " ".join(cite_link(c["session_id"]) for c in cites)


def _card(cd):
    st_kind = {"BLOCKED": "stop", "DRAFT": "warn", "READY FOR REVIEW": "ok"}[cd["status"]]
    prereq = "".join(
        f'<li class="pr-{"ok" if p["met"] is True else "no" if p["met"] is False else "q"}">'
        f'<span class="pr-icon" aria-hidden="true">{"✓" if p["met"] is True else "✗" if p["met"] is False else "?"}</span>'
        f'{esc(p["text"])} <span class="dim">— {esc(p["detail"])}</span></li>' for p in cd["prerequisites"])
    linked = " ".join(badge(f'{lp["id"]}: {lp["status"]}', {"PASS": "good", "FAIL": "bad"}.get(lp["status"], "neutral"))
                      for lp in cd["linked_priorities"])
    if cd["type"] == "aso":
        sc, cp = cd["screenshot_concept"], cd["copy"]
        creative = f"""
      <div class="store">
        <div class="store-head"><div class="store-icon" aria-hidden="true"></div>
          <div><div class="store-title">{esc(cp.get('title_concept', ''))}</div>
          <div class="store-sub">{esc(cp.get('subtitle', ''))}</div></div></div>
        <figure class="shot"><div class="shot-art" aria-hidden="true"><span class="before">before</span><span class="after">after</span></div>
          <figcaption><b>{esc(sc.get('caption', ''))}</b><span class="shot-badge">{esc(sc.get('badge', ''))}</span>
          <span class="dim">{esc(sc.get('footnote', ''))}</span></figcaption></figure>
        <p class="dim small">{esc(sc.get('frame', ''))}: {esc(sc.get('visual', ''))}</p>
      </div>"""
        kw = "".join(
            f'<tr><th scope="row">{esc(g["group"])}</th><td>{esc(g["intent"])}</td>'
            f'<td class="mono">{esc(", ".join(g.get("example_terms", [])))}</td><td>{_inline_cites(g["evidence"])}</td>'
            f'<td class="dim">{esc(g["search_volume"])}</td></tr>' for g in cd["keyword_intent_groups"])
        creative += (f'<h4>Keyword intent groups</h4><div class="scroll"><table><thead><tr><th scope="col">Group</th>'
                     f'<th scope="col">Intent</th><th scope="col">Example terms</th><th scope="col">Evidence</th>'
                     f'<th scope="col">Search volume</th></tr></thead><tbody>{kw}</tbody></table></div>')
    else:
        cp = cd["copy"]
        frames = "".join(
            f'<li class="frame"><div class="frame-n">Shot {esc(s["shot"])} · {esc(s["seconds"])} s</div>'
            f'<div class="frame-screen"><span>{esc(s["on_screen_text"])}</span></div>'
            f'<p><b>Visual.</b> {esc(s["visual"])}</p><p><b>Voice.</b> “{esc(s["voiceover"])}”</p>'
            f'<p class="dim small">Evidence: {_inline_cites(s["evidence"])}</p></li>' for s in cd["script"])
        creative = (f'<ol class="storyboard">{frames}</ol>'
                    f'<dl class="kv"><dt>Hook</dt><dd>{esc(cp.get("hook", ""))}</dd>'
                    f'<dt>Caption</dt><dd>{esc(cp.get("caption", ""))}</dd>'
                    f'<dt>Call to action</dt><dd>{esc(cp.get("call_to_action", ""))}</dd></dl>')
    facts = "".join(f'<li>{esc(x["text"])} {_inline_cites(x["evidence"])}</li>' for x in cd["product_facts"])
    unsup = "".join(f'<li>{esc(x["text"])} {_inline_cites(x["evidence"])}</li>' for x in cd["unsupported_capabilities"])
    hyps = "".join(f"<li>{esc(x)}</li>" for x in cd["marketing_hypotheses"])
    pm = cd["primary_metric"]
    guards = "".join(f'<tr><th scope="row">{esc(g["name"])}</th><td>{esc(g["denominator"])}</td><td>{esc(g["rule"])}</td></tr>'
                     for g in cd["guardrails"])
    bases = "".join(f'<tr><th scope="row">{esc(b["label"])}</th><td class="num">{esc(b["value"])}</td></tr>'
                    for k, b in cd["baselines"].items() if k != "budget_cap")
    cc = cd["copy_check"]
    copy_check = (badge("copy check passed", "good") if cc["passed"]
                  else badge("copy check failed: " + ", ".join(cc["violations"]), "bad"))
    return f"""
  <article class="xcard" id="{esc(cd['id'])}">
    <div class="status s-{st_kind}"><b>{esc(cd['status'])}</b> {esc(cd['status_reason'])}</div>
    <header class="xhead"><div><span class="dim small">{esc(cd['type_label'])} · {esc(cd['id'])}</span>
      <h3>{esc(cd['title'])}</h3></div>
      <dl class="meta-grid"><div><dt>Channel</dt><dd>{esc(cd['channel'])}</dd></div>
      <div><dt>Budget cap</dt><dd>{money(cd['budget_cap_usd'])}</dd></div>
      <div><dt>Owner</dt><dd>{esc(cd['owner'])}</dd></div></dl></header>
    <dl class="kv">
      <dt>Target problem</dt><dd>{esc(cd['target_problem'])}</dd>
      <dt>Hypothesis</dt><dd>{esc(cd['hypothesis'])}</dd>
      <dt>Linked priorities</dt><dd>{linked}</dd>
    </dl>
    <h4>Product prerequisites</h4><ul class="prereq">{prereq}</ul>
    <h4>Copy and creative</h4>{creative}
    <div class="three">
      <div><h4>Product facts</h4><ul class="tight">{facts}</ul></div>
      <div><h4>Not supported — do not claim</h4><ul class="tight">{unsup}</ul></div>
      <div><h4>Marketing hypotheses (unproven)</h4><ul class="tight">{hyps}</ul></div>
    </div>
    <h4>Measurement</h4>
    <dl class="kv"><dt>Primary metric</dt><dd><b>{esc(pm.get('name', ''))}</b> = {esc(pm.get('numerator', ''))}
      <br><span class="dim">÷</span> {esc(pm.get('denominator', ''))}<br><span class="dim">Baseline:</span> {esc(pm.get('baseline', ''))}</dd></dl>
    <div class="scroll"><table><thead><tr><th scope="col">Guardrail</th><th scope="col">Denominator</th>
      <th scope="col">Rule</th></tr></thead><tbody>{guards}</tbody></table></div>
    <div class="scroll"><table class="narrow"><caption>Baselines from current data ({esc(cd['baseline_channel'])})</caption>
      <tbody>{bases}</tbody></table></div>
    <dl class="kv"><dt>Stop</dt><dd>{esc(cd['stop_rule'])}</dd><dt>Continue</dt><dd>{esc(cd['continue_rule'])}</dd></dl>
    <details><summary>Evidence citations ({len(cd['evidence'])})</summary><ul class="cites">{_cite_list(cd['evidence'])}</ul></details>
    <p class="small">{copy_check} <span class="dim">Terms checked: {esc(', '.join(cc['terms_checked']))}. No keyword
    volumes, no reach or virality promises.</span></p>
  </article>"""


def section_experiments(r):
    b = r["budget"]
    within = badge("within cap", "good") if b["within_cap"] else badge("over cap", "bad")
    return f"""
<section id="experiments">
  <h2>6 · Experiment cards</h2>
  <p class="lead">Exactly two cards. Status comes from the given readiness flag and the data: while commercial
  delivery is not ready a card can only be BLOCKED or DRAFT — never approved. Combined caps
  <b>{money(b['total'])}</b> of the {money(b['cap'])} limit for the next {b['days']} days {within}
  (a ceiling, not a spend target).</p>
  {''.join(_card(cd) for cd in r['cards'])}
</section>"""


def section_evidence(r):
    rows = []
    for s in r["sessions"]:
        rep = badge("repaired", "warn", "unquoted commas repaired") if s.get("repaired") else ""
        rows.append(
            f'<tr id="{esc(s["session_id"])}"><th scope="row">{esc(s["session_id"])}</th>'
            f'<td class="mono">{esc(s["participant_id"])}</td><td>{esc(s["kind"])}</td>'
            f'<td>{esc(s["observed_behavior"])}</td><td>“{esc(s["user_statements"])}”</td>'
            f'<td class="dim">{esc(s["researcher_inferences"])}</td>'
            f'<td class="mono dim">line {s["line"]} {rep}</td></tr>')
    a = r["analysis"]
    stage_keys = [k for k, _ in r["stages"]]
    user_rows = []
    for uid in sorted(a["user_channel"]):
        ch = a["user_channel"][uid]
        marks = "".join(f'<td class="c">{"●" if uid in a["users"][ch][k] else "·"}</td>' for k in stage_keys)
        user_rows.append(f'<tr><th scope="row" class="mono">{esc(uid)}</th><td>{esc(ch)}</td>{marks}</tr>')
    uhead = "".join(f'<th scope="col" class="c">{esc(l)}</th>' for _, l in r["stages"])
    res = r["research"]
    return f"""
<section id="evidence">
  <h2>7 · Source records</h2>
  <p class="lead">{res['sessions']} feedback sessions from {res['participants']} independent participants;
  {res['retests']} are re-tests ({esc(', '.join(res['multi_session_participants']) or 'none')}). Every citation
  above links here.</p>
  <div class="scroll"><table class="sessions">
    <thead><tr><th scope="col">Session</th><th scope="col">Participant</th><th scope="col">Visit</th>
    <th scope="col">Observed</th><th scope="col">Said</th><th scope="col">Researcher inference</th>
    <th scope="col">Source</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>
  <details><summary>Stage reached by each of the {len(user_rows)} users</summary>
  <div class="scroll"><table class="users"><thead><tr><th scope="col">User</th><th scope="col">Channel</th>{uhead}</tr></thead>
  <tbody>{''.join(user_rows)}</tbody></table></div></details>
</section>"""


def section_method(r):
    p = r["params"]
    return f"""
<section id="method">
  <h2>8 · Definitions</h2>
  <dl class="kv">
    <dt>Users</dt><dd>Counted by user_id; channel = channel of the user's first first_open (first touch). Channel
    attribution is not a measure of incrementality.</dd>
    <dt>Qualified scan</dt><dd>A scan event by a user who also has first_open and qualified.</dd>
    <dt>Verified first-time payer</dt><dd>A user with at least one transaction that has a verification event at or
    before the cutoff. Several verification events for one transaction are one sale.</dd>
    <dt>Delivered guide</dt><dd>A verified transaction with a delivery event. A delivery without verified payment
    is not counted.</dd>
    <dt>Unrefunded delivered payer</dt><dd>Verified, delivered, and no full refund known at the cutoff
    ({esc(r['analysis']['cutoff'])}).</dd>
    <dt>Collected cash</dt><dd>Verified transactions × example price. Pending purchases are excluded.</dd>
    <dt>Net after commission</dt><dd>Collected − full refunds − {p['commission_rate'] * 100:.0f}% commission on kept
    sales (commission reversed on refund).</dd>
    <dt>Research vs events</dt><dd>Research participants are a separate cohort from the event-log users; feedback
    and events are linked by theme, never by person.</dd>
  </dl>
</section>"""


CSS = """
:root{--bg:#f7f7f5;--panel:#fff;--ink:#1d1d1f;--dim:#6b6b70;--line:#e3e3e0;--soft:#f1f1ee;
--accent:#2f5bea;--good:#1f7a4d;--good-bg:#e5f4ec;--warn:#9a6200;--warn-bg:#fdf1db;--bad:#b42318;--bad-bg:#fde8e6;
--muted:#5b5b8a;--muted-bg:#ececf6;--bar:#2f5bea;--hit:#fff5c2}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121214;--panel:#1b1b1f;--ink:#ececf0;--dim:#9a9aa3;
--line:#2c2c33;--soft:#232329;--accent:#7c9cff;--good:#5cd69a;--good-bg:#13301f;--warn:#f1b54a;--warn-bg:#33270f;
--bad:#ff8a7a;--bad-bg:#3a1714;--muted:#b4b4e6;--muted-bg:#25253a;--bar:#7c9cff;--hit:#3a3410}}
:root[data-theme="dark"]{--bg:#121214;--panel:#1b1b1f;--ink:#ececf0;--dim:#9a9aa3;--line:#2c2c33;--soft:#232329;
--accent:#7c9cff;--good:#5cd69a;--good-bg:#13301f;--warn:#f1b54a;--warn-bg:#33270f;--bad:#ff8a7a;--bad-bg:#3a1714;
--muted:#b4b4e6;--muted-bg:#25253a;--bar:#7c9cff;--hit:#3a3410}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:56px}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,
"Helvetica Neue",Arial,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
header.top{padding:28px 0 18px;border-bottom:1px solid var(--line);background:var(--panel)}
.eyebrow{margin:0;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}
h1{margin:6px 0 6px;font-size:26px;line-height:1.2;letter-spacing:-.01em}
.meta{margin:0;color:var(--dim);font-size:13px}
nav.toc{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);
backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
nav.toc .wrap{display:flex;gap:4px;overflow-x:auto;padding-top:8px;padding-bottom:8px;scrollbar-width:none}
nav.toc a{flex:none;color:var(--dim);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:999px}
nav.toc a:hover,nav.toc a:focus-visible{background:var(--soft);color:var(--ink)}
section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0}
h2{margin:0 0 6px;font-size:19px}
h2.h-sm,h3.h-sm{font-size:15px;margin:18px 0 6px}
h3{margin:0;font-size:17px;line-height:1.3}
h4{margin:18px 0 6px;font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--dim)}
.lead{margin:0 0 14px;color:var(--dim);max-width:78ch}
a{color:var(--accent)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.92em}
.dim{color:var(--dim)} .small{font-size:13px} .c{text-align:center}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0 12px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;color:var(--dim);font-size:12.5px;padding:0 0 6px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
thead th{font-size:12px;font-weight:600;color:var(--dim);background:var(--soft);white-space:nowrap}
tbody th{font-weight:600;white-space:nowrap}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.sub{display:block;font-size:11.5px;color:var(--dim);font-weight:400}
tr.total th,tr.total td{background:var(--soft);font-weight:700;border-top:2px solid var(--line)}
tr:target,tr:target th,tr:target td{background:var(--hit)!important}
.badge{display:inline-block;font-size:11.5px;font-weight:600;padding:1px 8px;border-radius:999px;white-space:nowrap;
vertical-align:1px}
.b-good{background:var(--good-bg);color:var(--good)} .b-warn{background:var(--warn-bg);color:var(--warn)}
.b-bad{background:var(--bad-bg);color:var(--bad)} .b-muted{background:var(--muted-bg);color:var(--muted)}
.b-neutral{background:var(--soft);color:var(--dim)}
.verdict{border-radius:12px;padding:14px 16px;margin-bottom:16px;font-size:15px}
.verdict.stop{background:var(--bad-bg);color:var(--ink);border-left:4px solid var(--bad)}
.verdict.ok{background:var(--good-bg);border-left:4px solid var(--good)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.tile{border:1px solid var(--line);border-radius:12px;padding:12px}
.t-label{font-size:12px;color:var(--dim)} .t-value{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums;
letter-spacing:-.01em} .t-sub{font-size:12px;color:var(--dim)}
.findings{margin:0;padding-left:18px} .findings li{margin:4px 0}
.funnel{display:grid;gap:6px;margin:6px 0 14px}
.fbar{display:grid;grid-template-columns:minmax(120px,190px) 1fr 86px minmax(0,170px);gap:10px;align-items:center;font-size:13.5px}
.f-track{height:14px;background:var(--soft);border-radius:4px;overflow:hidden}
.f-fill{height:100%;background:var(--bar);border-radius:4px}
.f-num{text-align:right;font-variant-numeric:tabular-nums} .f-step{font-size:12px}
.issues{list-style:none;padding:0;margin:8px 0} .issues li{padding:6px 0;border-bottom:1px dashed var(--line);font-size:13.5px}
.src{color:var(--dim);margin-left:6px;font-size:12px}
.ok-line{color:var(--good)}
details{margin:10px 0} summary{cursor:pointer;color:var(--accent);font-size:14px}
.fp{font-size:12.5px;padding-left:18px}
.assume{font-size:13.5px;margin:0 0 6px}
.note{font-size:12.5px;color:var(--dim);margin:6px 0 0}
.na{color:var(--dim);border-bottom:1px dotted var(--dim);cursor:help}
#export-box{margin:0 0 12px;display:grid;gap:4px}
#export-box textarea{width:100%;font:12px/1.4 ui-monospace,Menlo,monospace;background:var(--soft);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px;font-size:13px}
button{font:inherit;font-size:13px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel);
color:var(--ink);cursor:pointer} button:hover{background:var(--soft)} button[aria-pressed="true"]{background:var(--accent);
color:#fff;border-color:var(--accent)}
.prio{border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:12px 0}
.prio header{display:flex;gap:10px;align-items:center;margin-bottom:8px;flex-wrap:wrap}
.rank{flex:none;width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;display:grid;place-items:center;
font-weight:700}
.prio h3{flex:1;min-width:200px}
dl.kv{display:grid;grid-template-columns:minmax(110px,170px) 1fr;gap:6px 14px;margin:6px 0}
dl.kv dt{color:var(--dim);font-size:13px} dl.kv dd{margin:0}
.chips{display:flex;flex-wrap:wrap;gap:6px}
a.cite{display:inline-block;font-size:12px;padding:1px 7px;border-radius:6px;background:var(--soft);text-decoration:none;
white-space:nowrap}
.tight{margin:2px 0;padding-left:18px} .tight li{margin:2px 0}
td.hit{background:var(--hit)}
body.editing [data-field]{outline:2px dashed var(--accent);outline-offset:2px;border-radius:4px;background:var(--soft)}
.xcard{border:1px solid var(--line);border-radius:14px;padding:0 16px 14px;margin:16px 0;overflow:hidden}
.status{margin:0 -16px 12px;padding:10px 16px;font-size:14px}
.status b{margin-right:6px;letter-spacing:.04em}
.s-stop{background:var(--bad-bg);color:var(--bad)} .s-warn{background:var(--warn-bg);color:var(--warn)}
.s-ok{background:var(--good-bg);color:var(--good)}
.xhead{display:grid;gap:10px}
.meta-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:0}
.meta-grid div{background:var(--soft);border-radius:8px;padding:8px 10px}
.meta-grid dt{font-size:11.5px;color:var(--dim)} .meta-grid dd{margin:0;font-size:13.5px}
.prereq{list-style:none;padding:0;margin:0} .prereq li{padding:4px 0;font-size:13.5px}
.pr-icon{display:inline-block;width:20px;font-weight:700}
.pr-ok .pr-icon{color:var(--good)} .pr-no .pr-icon{color:var(--bad)} .pr-q .pr-icon{color:var(--warn)}
.three{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.three>div{background:var(--soft);border-radius:10px;padding:2px 12px 10px}
.three h4{margin-top:10px}
.store{border:1px solid var(--line);border-radius:14px;padding:12px;max-width:380px;background:var(--soft)}
.store-head{display:flex;gap:10px;align-items:center}
.store-icon{width:44px;height:44px;border-radius:11px;background:linear-gradient(135deg,var(--accent),var(--good))}
.store-title{font-weight:700} .store-sub{font-size:13px;color:var(--dim)}
.shot{margin:10px 0 6px;border-radius:12px;overflow:hidden;border:1px solid var(--line);background:var(--panel)}
.shot-art{height:120px;display:grid;grid-template-columns:1fr 1fr;font-size:11px;color:var(--dim)}
.shot-art span{display:flex;align-items:flex-end;padding:6px}
.before{background:repeating-linear-gradient(45deg,var(--soft) 0 8px,var(--panel) 8px 16px)}
.after{background:linear-gradient(0deg,color-mix(in srgb,var(--good) 25%,transparent),transparent);color:var(--good)}
.shot figcaption{padding:8px 10px;display:grid;gap:3px;font-size:13px}
.shot-badge{justify-self:start;font-size:11px;font-weight:700;padding:1px 6px;border-radius:5px;background:var(--warn-bg);
color:var(--warn)}
.storyboard{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.frame{border:1px solid var(--line);border-radius:12px;padding:10px;font-size:13.5px}
.frame p{margin:6px 0}
.frame-n{font-size:12px;font-weight:700;color:var(--dim)}
.frame-screen{margin-top:6px;aspect-ratio:9/12;max-height:170px;border-radius:10px;background:linear-gradient(160deg,var(--soft),
var(--muted-bg));display:flex;align-items:flex-end;padding:8px}
.frame-screen span{background:rgba(0,0,0,.65);color:#fff;font-weight:600;font-size:12.5px;padding:3px 7px;border-radius:5px}
table.narrow{max-width:560px}
.cites{padding-left:18px;font-size:13.5px} .cites li{margin:4px 0} q{font-style:italic}
footer{color:var(--dim);font-size:12px;padding:10px 0 40px}
@media (max-width:640px){
 h1{font-size:21px} section{padding:16px;border-radius:12px}
 .fbar{grid-template-columns:1fr 70px;row-gap:2px} .fbar .f-track{grid-column:1/-1;order:3} .f-step{grid-column:1/-1;order:4}
 dl.kv{grid-template-columns:1fr} dl.kv dt{margin-top:6px}
 .t-value{font-size:20px}
}
@media print{nav.toc,.no-print{display:none} section{break-inside:avoid-page;border:0;padding:0} body{background:#fff}}
"""

JS = """
(function(){
  var btn=document.getElementById('edit-toggle'), dl=document.getElementById('download-priorities');
  if(!btn||!dl) return;
  btn.addEventListener('click',function(){
    var on=document.body.classList.toggle('editing');
    btn.setAttribute('aria-pressed',on?'true':'false');
    btn.textContent=on?'Done editing':'Edit priorities';
    document.querySelectorAll('.prio [data-field]').forEach(function(el){el.contentEditable=on?'true':'false';});
  });
  dl.addEventListener('click',function(){
    var cfg=JSON.parse(document.getElementById('priorities-config').textContent);
    document.querySelectorAll('.prio').forEach(function(card){
      var c=(cfg.candidates||[]).find(function(x){return x.id===card.dataset.id;});
      if(!c) return;
      card.querySelectorAll('[data-field]').forEach(function(el){
        var v=el.innerText.trim(); if(v==='\\u2014') v='';
        c[el.dataset.field]=el.dataset.field==='match_terms'?v.split(',').map(function(s){return s.trim();}).filter(Boolean):v;
      });
    });
    // Show + copy instead of a file download: downloads are blocked in sandboxed hosting.
    var text=JSON.stringify(cfg,null,2)+'\\n', box=document.getElementById('export-box'),
        ta=document.getElementById('export-json'), st=document.getElementById('export-status');
    ta.value=text; box.hidden=false; ta.focus(); ta.select();
    var ok=function(){st.textContent='Copied to the clipboard.';}, no=function(){st.textContent='Selected — press Ctrl/\u2318+C to copy.';};
    try{navigator.clipboard.writeText(text).then(ok,no);}catch(e){no();}
  });
})();
"""


def render_html(r):
    a = r["analysis"]
    nav = [("summary", "Summary"), ("quality", "Input checks"), ("funnel", "Funnel"), ("money", "Payments"),
           ("costs", "Cost & CAC"), ("priorities", "Priorities"), ("experiments", "Experiments"),
           ("evidence", "Source records"), ("method", "Definitions")]
    nav_html = "".join(f'<a href="#{k}">{esc(v)}</a>' for k, v in nav)
    fp = " · ".join(f"{esc(k)} {esc(v[:12])}" for k, v in r["fingerprints"].items())
    body = "".join([section_summary(r), section_quality(r), section_funnel(r), section_money(r), section_costs(r),
                    section_priorities(r), section_experiments(r), section_evidence(r), section_method(r)])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ChiSensor Trial Readout</title>
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <p class="eyebrow">ChiSensor · evidence → experiments</p>
  <h1>Trial readout: what to fix, what to say, what it costs</h1>
  <p class="meta">Synthetic exercise data · cutoff {esc(a['cutoff'])} · first-touch attribution (not causal) ·
  {money(r['params']['price'])} is an example price, not an approved one</p>
</div></header>
<nav class="toc" aria-label="Sections"><div class="wrap">{nav_html}</div></nav>
<main class="wrap">{body}</main>
<footer class="wrap">Generated by evidence_tool {esc(r['version'])} · inputs (SHA-256): {fp} ·
deterministic: the same inputs produce an identical file.</footer>
<script>{JS}</script>
</body>
</html>
"""


def render_markdown(r):
    lines = ["# ChiSensor experiment cards", "",
             f"Combined budget caps: {money(r['budget']['total'])} of {money(r['budget']['cap'])} for the next "
             f"{r['budget']['days']} days ({'within' if r['budget']['within_cap'] else 'OVER'} cap).", ""]
    for cd in r["cards"]:
        cite = lambda cs: ", ".join(c["session_id"] for c in cs)
        lines += [f"## {cd['id']} — {cd['title']}", "",
                  f"**Status: {cd['status']}.** {cd['status_reason']}", "",
                  f"- **Type:** {cd['type_label']}",
                  f"- **Channel:** {cd['channel']}",
                  f"- **Owner:** {cd['owner']}",
                  f"- **Budget cap:** {money(cd['budget_cap_usd'])}",
                  f"- **Linked priorities:** " + ", ".join(f"{p['id']} ({p['status']})" for p in cd["linked_priorities"]),
                  "", "### Target problem", "", cd["target_problem"], "",
                  "### Hypothesis", "", cd["hypothesis"], "", "### Product prerequisites", ""]
        for p in cd["prerequisites"]:
            mark = "x" if p["met"] is True else " "
            lines.append(f"- [{mark}] {p['text']} — {p['detail']}")
        lines += ["", "### Copy", ""]
        for k, v in cd["copy"].items():
            lines.append(f"- **{k.replace('_', ' ').capitalize()}:** {v}")
        if cd["type"] == "aso":
            sc = cd["screenshot_concept"]
            lines += ["", "### Screenshot concept", "", f"{sc.get('frame', '')}: {sc.get('visual', '')}", "",
                      "### Keyword intent groups (no search volumes — not provided, not estimated)", "",
                      "| Group | Intent | Example terms | Evidence |", "| --- | --- | --- | --- |"]
            for g in cd["keyword_intent_groups"]:
                lines.append(f"| {g['group']} | {g['intent']} | {', '.join(g.get('example_terms', []))} | "
                             f"{cite(g['evidence'])} |")
        else:
            lines += ["", "### Three-shot script", "", "| Shot | Seconds | Visual | On screen | Voice | Evidence |",
                      "| --- | --- | --- | --- | --- | --- |"]
            for s in cd["script"]:
                lines.append(f"| {s['shot']} | {s['seconds']} | {s['visual']} | {s['on_screen_text']} | "
                             f"{s['voiceover']} | {cite(s['evidence'])} |")
        lines += ["", "### Product facts", ""] + [f"- {x['text']} ({cite(x['evidence'])})" for x in cd["product_facts"]]
        lines += ["", "### Not supported — do not claim", ""] + \
                 [f"- {x['text']} ({cite(x['evidence'])})" for x in cd["unsupported_capabilities"]]
        lines += ["", "### Marketing hypotheses (unproven)", ""] + [f"- {x}" for x in cd["marketing_hypotheses"]]
        pm = cd["primary_metric"]
        lines += ["", "### Measurement", "",
                  f"- **Primary metric:** {pm.get('name', '')} = {pm.get('numerator', '')} ÷ {pm.get('denominator', '')}",
                  f"- **Primary baseline:** {pm.get('baseline', '')}"]
        lines += [f"- **Guardrail — {g['name']}** (÷ {g['denominator']}): {g['rule']}" for g in cd["guardrails"]]
        lines += [f"- Baseline — {b['label']}: {b['value']}" for k, b in cd["baselines"].items() if k != "budget_cap"]
        lines += ["", f"**Stop:** {cd['stop_rule']}", "", f"**Continue:** {cd['continue_rule']}", "",
                  "### Evidence citations", ""]
        for c in cd["evidence"]:
            lines.append(f"- {c['session_id']} ({FIELD_LABEL.get(c['field'], c['field'])}"
                         + (f", {c.get('participant_id')}, {c.get('kind')}" if not c["broken"] else "")
                         + f"): “{c['text']}”")
        cc = cd["copy_check"]
        lines += ["", f"Copy check: {'passed' if cc['passed'] else 'FAILED — ' + ', '.join(cc['violations'])}.", "",
                  "---", ""]
    return "\n".join(lines)

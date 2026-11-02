"""Self-contained HTML report + Markdown experiment cards, in English or Chinese.

Every string that comes from input or config passes through esc(). Interface text
comes from i18n.t(). The output is deterministic (no clock, no random IDs):
same inputs and language → identical bytes.
"""
from __future__ import annotations

import json
from decimal import Decimal
from html import escape

from .i18n import get_lang, join, t, tn

OTHER_FILE = {"en": ("report.zh-CN.html", "中文"), "zh": ("report.html", "EN")}


def esc(x):
    return escape("" if x is None else str(x), quote=True)


def money(v, na="N/A"):
    if v is None:
        return na
    v = Decimal(v).quantize(Decimal("0.01"))
    return f"−${-v:,.2f}" if v < 0 else f"${v:,.2f}"


def pct(num, den):
    return "—" if not den else f"{num / den:.0%}"


def badge(text, kind="neutral", title=""):
    ttl = f' title="{esc(title)}"' if title else ""
    return f'<span class="badge b-{kind}"{ttl}>{esc(text)}</span>'


def cite_link(sid, extra=""):
    return f'<a class="cite" href="#{esc(sid)}">{esc(sid)}{esc(extra)}</a>'


def tx_link(tid):
    return f'<a class="cite mono" href="#tx-{esc(tid)}">{esc(tid)}</a>'


def stage(key):
    return t(f"stage.{key}")


def ch_name(ch, overall):
    return t("overall") if ch == overall else ch


def tx_status(code):
    return t("txs." + code.replace(", ", "_").replace(" ", "_"))


STATUS_KIND = {"delivered": "good", "refunded": "muted", "paid, not delivered": "bad", "pending": "warn",
               "unknown": "neutral"}
PSTATUS_KIND = {"PASS": "good", "FAIL": "bad"}


# ─── sections ───────────────────────────────────────────────────────

def section_summary(r):
    a, o = r["analysis"], r["overall"]
    f, m, c = a["funnel"][o], a["money"][o], a["costs"][o]
    keys = [k for k, _ in r["stages"]]

    # biggest adjacent drop in the overall funnel
    drops = [(f[keys[i]] - f[keys[i + 1]], keys[i], keys[i + 1], f[keys[i]]) for i in range(len(keys) - 1)]
    lost, s_from, s_to, base = max(drops, key=lambda d: d[0])

    with_cac = [(a["costs"][ch]["delivered_cac_cash"], ch) for ch in a["channels"]
                if a["costs"][ch]["delivered_cac_cash"] is not None]
    no_payer = [ch for ch in a["channels"] if a["funnel"][ch]["unrefunded_delivered"] == 0]
    largest = max((a["funnel"][ch]["first_open"] for ch in a["channels"]), default=0)

    if r["delivery_ready"]:
        verdict = f'<div class="verdict ok">{t("verdict.ready")}</div>'
    else:
        reasons = []
        if m["undelivered_tx"]:
            reasons.append(tn("verdict.undelivered", m["undelivered_tx"]))
        if m["pending_tx"]:
            reasons.append(tn("verdict.pending", m["pending_tx"]))
        if not r["params"]["commercial_delivery_ready"]:
            reasons.append(t("verdict.flag"))
        text = t("sep.semi").join(reasons)
        verdict = f'<div class="verdict stop">{t("verdict.stop", reasons=esc(text[:1].upper() + text[1:]))}</div>'

    tiles = [
        (t("tile.first_open"), f["first_open"], t("tile.first_open.sub")),
        (t("tile.scans"), f["qualified_scan"], t("tile.scans.sub", pct=pct(f["qualified_scan"], f["first_open"]))),
        (t("tile.payers"), f["first_time_payer"],
         t("tile.payers.sub", pct=pct(f["first_time_payer"], f["free_suggestion_viewed"]))),
        (t("tile.unrefunded"), f["unrefunded_delivered"],
         t("tile.unrefunded.sub", pct=pct(f["unrefunded_delivered"], f["first_open"]))),
        (t("tile.net"), money(m["net_after_commission"]), t("tile.net.sub", v=money(m["collected_cash"]))),
        (t("tile.contrib"), money(c["cash_contribution"]), t("tile.contrib.sub", v=money(c["contribution_after_labor"]))),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="t-label">{esc(l)}</div><div class="t-value">{esc(v)}</div>'
        f'<div class="t-sub">{esc(s)}</div></div>' for l, v, s in tiles)

    findings = [
        t("find.drop", a=esc(stage(s_from)), b=esc(stage(s_to)), lost=lost, base=base, pct=pct(lost, base)),
        t("find.pay", v=m["verified_tx"], r=m["refunded_tx"], u=m["undelivered_tx"], p=m["pending_tx"]),
    ]
    if with_cac:
        lo, hi = min(with_cac), max(with_cac)
        na = t("find.cac.na", ch=esc(join(no_payer))) if no_payer else ""
        findings.append(t("find.cac", lo=money(lo[0]), lo_ch=esc(lo[1]), hi=money(hi[0]), hi_ch=esc(hi[1]),
                          na=na, largest=largest))
    if r["priorities"]:
        p0 = r["priorities"][0]
        findings.append(t("find.prio", title=esc(p0["title"]), n=len(p0["participants"]), total=r["total_participants"]))
    reach = [f"{esc(cd['id'])} {esc(cd['baselines']['reach']['value'])}"
             for cd in r["cards"] if "reach" in cd["baselines"]]
    if reach:
        findings.append(t("find.reach", list=t("sep.semi").join(reach)))
    items = "".join(f"<li>{x}</li>" for x in findings)
    return f"""
<section id="summary">
  {verdict}
  <div class="tiles">{tiles_html}</div>
  <h2 class="h-sm">{t("find.title")}</h2>
  <ul class="findings">{items}</ul>
</section>"""


def section_quality(r):
    labels = ["rows", "valid", "exact_duplicates", "conflicting_duplicates", "duplicates", "repaired", "invalid"]
    rows = []
    for fname, c in r["counts"].items():
        cells = "".join(f'<td class="num">{c.get(k, "—")}</td>' for k in labels)
        rows.append(f'<tr><th scope="row" class="mono">{esc(fname)}</th>{cells}</tr>')
    head = "".join(f'<th scope="col" class="num">{esc(t("q." + k))}</th>' for k in labels)

    by_sev = {"error": [], "warning": [], "info": []}
    for i in r["issues"]:
        by_sev[i["severity"]].append(i)

    def issue_list(items):
        return "".join(
            f'<li>{badge(t("sev." + i["severity"]), {"error": "bad", "warning": "warn", "info": "neutral"}[i["severity"]])} '
            f'<span class="mono dim">{esc(i["code"])}</span> {esc(i["message"])} '
            f'<span class="src mono">{esc(i["source"])}</span></li>' for i in items)

    main = by_sev["error"] + by_sev["warning"]
    main_html = (f'<ul class="issues">{issue_list(main)}</ul>' if main
                 else f'<p class="ok-line">{t("q.clean")}</p>')
    info_html = (f'<details><summary>{tn("q.notes", len(by_sev["info"]))}</summary><ul class="issues">'
                 f'{issue_list(by_sev["info"])}</ul></details>' if by_sev["info"] else "")
    fp = "".join(f'<li><span class="mono">{esc(k)}</span> <span class="mono dim">{esc(v[:16])}…</span></li>'
                 for k, v in r["fingerprints"].items())
    counts = " · ".join([tn("q.errors", len(by_sev["error"])), tn("q.warnings", len(by_sev["warning"])),
                         tn("q.notes", len(by_sev["info"]))])
    return f"""
<section id="quality">
  <h2>{t("q.title")}</h2>
  <p class="lead">{counts}{t("end")} {t("q.lead")}</p>
  <div class="scroll"><table>
    <caption>{t("q.caption")}</caption>
    <thead><tr><th scope="col">{t("q.file")}</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  {main_html}
  {info_html}
  <details><summary>{t("q.fingerprints")}</summary><ul class="fp">{fp}</ul></details>
</section>"""


def section_funnel(r):
    a, o = r["analysis"], r["overall"]
    keys = [k for k, _ in r["stages"]]
    f = a["funnel"][o]
    top = f[keys[0]] or 1
    bars = []
    for i, key in enumerate(keys):
        n = f[key]
        prev = f[keys[i - 1]] if i else None
        step = "" if i == 0 else t("f.step", pct=pct(n, prev), lost=prev - n)
        bars.append(
            f'<div class="fbar"><div class="f-label">{esc(stage(key))}</div>'
            f'<div class="f-track"><div class="f-fill" style="width:{n / top * 100:.1f}%"></div></div>'
            f'<div class="f-num"><b>{n}</b> <span class="dim">{pct(n, top)}</span></div>'
            f'<div class="f-step dim">{esc(step)}</div></div>')

    low_n = r["params"]["low_n"]
    head = "".join(f'<th scope="col" class="num">{esc(stage(k))}</th>' for k in keys)
    rows = []
    for ch in a["channels"] + [o]:
        fc = a["funnel"][ch]
        cells = []
        for i, key in enumerate(keys):
            n = fc[key]
            if i == 0:
                cells.append(f'<td class="num"><b>{n}</b></td>')
            else:
                den = fc[keys[i - 1]]
                sub = t("f.of", pct=pct(n, den), den=den) if den else t("f.noden")
                cells.append(f'<td class="num"><b>{n}</b><span class="sub">{esc(sub)}</span></td>')
        flag = badge(t("f.lown"), "warn", t("f.lown.title", n=low_n)) if fc["first_open"] < low_n else ""
        cls = ' class="total"' if ch == o else ""
        rows.append(f'<tr{cls}><th scope="row">{esc(ch_name(ch, o))} {flag}</th>{"".join(cells)}</tr>')
    return f"""
<section id="funnel">
  <h2>{t("f.title")}</h2>
  <p class="lead">{t("f.lead")}</p>
  <div class="funnel" role="img" aria-label="{esc(t("f.aria"))}">{''.join(bars)}</div>
  <div class="scroll"><table class="funnel-table">
    <caption>{t("f.caption")}</caption>
    <thead><tr><th scope="col">{t("f.channel")}</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
</section>"""


def section_money(r):
    a, o, p = r["analysis"], r["overall"], r["params"]
    cols = [("verified_tx", False), ("collected_cash", True), ("refunds", True), ("commission", True),
            ("net_after_commission", True), ("pending_not_collected", True), ("paid_not_delivered", True)]
    head = "".join(f'<th scope="col" class="num">{esc(t("m." + k))}</th>' for k, _ in cols)
    rows = []
    for ch in a["channels"] + [o]:
        mm = a["money"][ch]
        cells = "".join(f'<td class="num">{money(mm[k]) if is_m else mm[k]}</td>' for k, is_m in cols)
        cls = ' class="total"' if ch == o else ""
        rows.append(f'<tr{cls}><th scope="row">{esc(ch_name(ch, o))}</th>{cells}</tr>')

    tx_rows = []
    yes = lambda b: "✓" if b else "—"
    for x in a["transactions"]:
        ver = ", ".join(e["event_id"] for e in x["verification"]) or "—"
        tx_rows.append(
            f'<tr id="tx-{esc(x["id"])}"><th scope="row" class="mono">{esc(x["id"])}</th>'
            f'<td class="mono">{esc(x["user_id"])}</td><td>{esc(x["channel"])}</td>'
            f'<td>{badge(tx_status(x["status"]), STATUS_KIND.get(x["status"], "neutral"))}</td>'
            f'<td class="c">{yes(x["purchase"])}</td><td class="mono">{esc(ver)}</td>'
            f'<td class="c">{yes(x["delivered"])}</td><td class="c">{yes(x["refunded"])}</td>'
            f'<td class="mono dim">{esc(", ".join(x["event_ids"]))}</td>'
            f'<td>{esc(t("sep.semi").join(x["notes"]))}</td></tr>')
    th = "".join(f'<th scope="col">{t(k)}</th>' for k in
                 ("m.tx", "m.user", "f.channel", "m.status", "m.purchase", "m.verifications", "m.delivered",
                  "m.refunded", "m.source", "m.notes"))
    return f"""
<section id="money">
  <h2>{t("m.title")}</h2>
  <p class="lead">{t("m.lead", price=money(p['price']), rate=f"{p['commission_rate'] * 100:.0f}")}</p>
  <div class="scroll"><table>
    <caption>{t("m.caption")}</caption>
    <thead><tr><th scope="col">{t("f.channel")}</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  <details open><summary>{t("m.audit", n=len(a['transactions']))}</summary>
  <div class="scroll"><table class="tx">
    <thead><tr>{th}</tr></thead>
    <tbody>{''.join(tx_rows)}</tbody>
  </table></div></details>
</section>"""


def section_costs(r):
    a, o, p = r["analysis"], r["overall"], r["params"]
    rows = []
    for ch in a["channels"] + [o]:
        c, f, m = a["costs"][ch], a["funnel"][ch], a["money"][ch]
        hours = "—" if c["hours"] is None else t("c.hours", h=f"{c['hours']:g}")
        shared = money(c["shared"]) if ch == o else "—"
        na_reason = t("c.na.cost") if c["cash"] is None else t("c.na.payers")
        na = lambda v: money(v) if v is not None else f'<span class="na" title="{esc(na_reason)}">N/A</span>'
        cls = ' class="total"' if ch == o else ""
        rows.append(
            f'<tr{cls}><th scope="row">{esc(ch_name(ch, o))}</th>'
            f'<td class="num">{money(c["cash"])}</td><td class="num">{shared}</td>'
            f'<td class="num">{money(c["labor"])}<span class="sub">{esc(hours)}</span></td>'
            f'<td class="num">{f["first_time_payer"]}</td>'
            f'<td class="num">{na(c["first_pay_cac_cash"])}</td>'
            f'<td class="num">{f["unrefunded_delivered"]}</td>'
            f'<td class="num">{na(c["delivered_cac_cash"])}</td>'
            f'<td class="num">{na(c["delivered_cac_loaded"])}</td>'
            f'<td class="num">{money(m["net_after_commission"])}</td>'
            f'<td class="num">{money(c["cash_contribution"])}</td>'
            f'<td class="num">{money(c["contribution_after_labor"])}</td></tr>')
    s = a["shared"]
    head = "".join(f'<th scope="col" class="num">{t("c." + k)}</th>' for k in
                   ("cash", "shared", "labor", "payers", "fpcac", "unrefunded", "dcac", "dcacl", "net", "contrib", "contribl"))
    return f"""
<section id="costs">
  <h2>{t("c.title")}</h2>
  <p class="lead">{t("c.lead", rate=money(p['labor_rate']), calls=f"{p['inference_calls']:g}", unit=money(p['inference_unit']),
                      inference=money(s['inference']), tools=money(s['tools']))}</p>
  <p class="assume">{badge(t("c.assumption"), "warn")} {t("c.assume")}</p>
  <div class="scroll"><table>
    <caption>{t("c.caption")}</caption>
    <thead><tr><th scope="col">{t("f.channel")}</th>{head}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  <p class="note">{t("c.note")}</p>
</section>"""


def _quote_table(cites):
    rows = []
    for c in cites:
        hits = c["matched"]
        cell = lambda fld: (f'<td class="{"hit" if fld in hits else ""}">{esc(c[fld])}'
                            + (f'<span class="sub">{esc(t("qt.matched", terms=", ".join(hits[fld])))}</span>'
                               if fld in hits else "") + "</td>")
        rows.append(f'<tr><th scope="row">{cite_link(c["session_id"])}<span class="sub">{esc(c["participant_id"])} · '
                    f'{esc(c["kind"])}</span></th>{cell("observed_behavior")}{cell("user_statements")}'
                    f'<td class="dim">{esc(c["researcher_inferences"])}</td></tr>')
    return (f'<div class="scroll"><table class="quotes"><thead><tr><th scope="col">{t("qt.session")}</th>'
            f'<th scope="col">{t("qt.observed")}</th><th scope="col">{t("qt.said")}</th>'
            f'<th scope="col">{t("qt.inferred")}</th></tr></thead><tbody>{"".join(rows)}</tbody>'
            f'</table></div>')


def section_priorities(r):
    out = []
    for p in r["priorities"]:
        ev = p["event_evidence"]
        ev_rows = "".join(
            f'<li>{esc(row["label"])}{t("sep.colon")}<b>{row["count"]}</b>'
            + (esc(t("p.row.of", n=row["of"])) if "of" in row else "")
            + (" — " + ", ".join(tx_link(i) for i in row["ids"]) if row["ids"] else "") + "</li>"
            for row in ev["rows"])
        chips = " ".join(cite_link(c["session_id"], f' · {c["participant_id"]} · '
                                   f'{t("chip.first") if c["visit"] == 1 else t("chip.retest")}')
                         for c in p["citations"])
        st = p["current_status"]
        unc = "".join(f"<li>{esc(u)}</li>" for u in p["uncertainty"])
        out.append(f"""
  <article class="prio" data-id="{esc(p['id'])}">
    <header><span class="rank">{p['rank']}</span>
      <h3 data-field="title">{esc(p['title'])}</h3>{badge(p['id'], 'neutral')}</header>
    <dl class="kv">
      <dt>{t("p.problem")}</dt><dd data-field="user_problem">{esc(p['user_problem'])}</dd>
      <dt>{t("p.participants")}</dt><dd><b>{t("p.of", n=len(p['participants']), total=r['total_participants'])}</b> ·
        <span class="mono">{esc(' '.join(p['participants']))}</span></dd>
      <dt>{t("p.feedback")}</dt><dd class="chips">{chips}</dd>
      <dt>{t("p.events")}</dt><dd>{esc(ev['headline'])}{f'<ul class="tight">{ev_rows}</ul>' if ev_rows else ''}</dd>
      <dt>{t("p.change")}</dt><dd data-field="proposed_change">{esc(p['proposed_change'])}</dd>
      <dt>{t("p.pass")}</dt><dd data-field="acceptance_pass">{esc(p['acceptance_pass'])}</dd>
      <dt>{t("p.fail")}</dt><dd data-field="acceptance_fail">{esc(p['acceptance_fail'])}</dd>
      <dt>{t("p.now")}</dt><dd>{badge(t("pstatus." + st), PSTATUS_KIND.get(st, "neutral"))} <span class="dim">{esc(t("p.baseline", v=ev['baseline']))}</span></dd>
      <dt>{t("p.uncertainty")}</dt><dd><ul class="tight">{unc}</ul></dd>
      <dt>{t("p.note")}</dt><dd data-field="analyst_note">{esc(p['analyst_note'] or '—')}</dd>
      <dt>{t("p.terms")}</dt><dd data-field="match_terms" class="mono">{esc(', '.join(p['match_terms']))}</dd>
    </dl>
    <details><summary>{t("p.quotes")}</summary>{_quote_table(p['citations'])}</details>
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
  <h2>{t("p.title")}</h2>
  <p class="lead">{t("p.lead", max=rule.get('max_priorities', 3), min=rule.get('min_participants', 2))}</p>
  <div class="toolbar no-print">
    <button type="button" id="edit-toggle" aria-pressed="false">{t("p.edit")}</button>
    <button type="button" id="download-priorities">{t("p.export")}</button>
    <span class="dim">{t("p.hint")}</span>
  </div>
  <div id="export-box" class="no-print" hidden>
    <textarea id="export-json" readonly rows="10" aria-label="priorities.json"></textarea>
    <span class="dim small" id="export-status"></span>
  </div>
  {''.join(out)}
  <h3 class="h-sm">{t("p.rejected")}</h3>
  <div class="scroll"><table><thead><tr><th scope="col">{t("p.id")}</th><th scope="col">{t("p.candidate")}</th>
  <th scope="col">{t("p.participants")}</th><th scope="col">{t("p.sessions")}</th><th scope="col">{t("p.whynot")}</th></tr></thead>
  <tbody>{rej or f'<tr><td colspan="5">{t("p.none")}</td></tr>'}</tbody></table></div>
  <script type="application/json" id="priorities-config">{cfg_json}</script>
</section>"""


def _cite_list(cites):
    return "".join(
        f'<li>{cite_link(c["session_id"])} <span class="dim">{esc(t("field." + c["field"]))}'
        + (f' · {esc(c.get("participant_id", ""))} · {esc(c.get("kind", ""))}' if not c["broken"] else "")
        + f'</span> <q>{esc(c["text"])}</q></li>' for c in cites)


def _inline_cites(cites):
    return " ".join(cite_link(c["session_id"]) for c in cites)


def _terms_for_lang(terms):
    """The check scans copy in every language; each report lists the terms in its own script."""
    cjk = lambda w: any("\u4e00" <= ch <= "\u9fff" for ch in w)
    return [w for w in terms if cjk(w) == (get_lang() == "zh")] or terms


def _card(cd):
    st_kind = {"BLOCKED": "stop", "DRAFT": "warn", "READY FOR REVIEW": "ok"}[cd["status"]]
    prereq = "".join(
        f'<li class="pr-{"ok" if p["met"] is True else "no" if p["met"] is False else "q"}">'
        f'<span class="pr-icon" aria-hidden="true">{"✓" if p["met"] is True else "✗" if p["met"] is False else "?"}</span>'
        f'{esc(p["text"])} <span class="dim">— {esc(p["detail"])}</span></li>' for p in cd["prerequisites"])
    linked = " ".join(badge(f'{lp["id"]}: {t("pstatus." + lp["status"])}', PSTATUS_KIND.get(lp["status"], "neutral"))
                      for lp in cd["linked_priorities"])
    if cd["type"] == "aso":
        sc, cp = cd["screenshot_concept"], cd["copy"]
        creative = f"""
      <div class="store">
        <div class="store-head"><div class="store-icon" aria-hidden="true"></div>
          <div><div class="store-title">{esc(cp.get('title_concept', ''))}</div>
          <div class="store-sub">{esc(cp.get('subtitle', ''))}</div></div></div>
        <figure class="shot"><div class="shot-art" aria-hidden="true"><span class="before">{t("x.before")}</span><span class="after">{t("x.after")}</span></div>
          <figcaption><b>{esc(sc.get('caption', ''))}</b><span class="shot-badge">{esc(sc.get('badge', ''))}</span>
          <span class="dim">{esc(sc.get('footnote', ''))}</span></figcaption></figure>
        <p class="dim small">{esc(sc.get('frame', ''))}{t("sep.colon")}{esc(sc.get('visual', ''))}</p>
      </div>"""
        kw = "".join(
            f'<tr><th scope="row">{esc(g["group"])}</th><td>{esc(g["intent"])}</td>'
            f'<td class="mono">{esc(", ".join(g.get("example_terms", [])))}</td><td>{_inline_cites(g["evidence"])}</td>'
            f'<td class="dim">{esc(g["search_volume"])}</td></tr>' for g in cd["keyword_intent_groups"])
        creative += (f'<h4>{t("x.kw")}</h4><div class="scroll"><table><thead><tr><th scope="col">{t("x.kw.group")}</th>'
                     f'<th scope="col">{t("x.kw.intent")}</th><th scope="col">{t("x.kw.terms")}</th>'
                     f'<th scope="col">{t("x.kw.evidence")}</th><th scope="col">{t("x.kw.volume")}</th></tr></thead>'
                     f'<tbody>{kw}</tbody></table></div>')
    else:
        cp = cd["copy"]
        frames = "".join(
            f'<li class="frame"><div class="frame-n">{esc(t("x.shot", n=s["shot"], s=s["seconds"]))}</div>'
            f'<div class="frame-screen"><span>{esc(s["on_screen_text"])}</span></div>'
            f'<p><b>{t("x.visual")}</b> {esc(s["visual"])}</p><p><b>{t("x.voice")}</b> “{esc(s["voiceover"])}”</p>'
            f'<p class="dim small">{t("x.evidence")} {_inline_cites(s["evidence"])}</p></li>' for s in cd["script"])
        creative = (f'<ol class="storyboard">{frames}</ol>'
                    f'<dl class="kv"><dt>{t("x.hook")}</dt><dd>{esc(cp.get("hook", ""))}</dd>'
                    f'<dt>{t("x.caption")}</dt><dd>{esc(cp.get("caption", ""))}</dd>'
                    f'<dt>{t("x.cta")}</dt><dd>{esc(cp.get("call_to_action", ""))}</dd></dl>')
    facts = "".join(f'<li>{esc(x["text"])} {_inline_cites(x["evidence"])}</li>' for x in cd["product_facts"])
    unsup = "".join(f'<li>{esc(x["text"])} {_inline_cites(x["evidence"])}</li>' for x in cd["unsupported_capabilities"])
    hyps = "".join(f"<li>{esc(x)}</li>" for x in cd["marketing_hypotheses"])
    pm = cd["primary_metric"]
    guards = "".join(f'<tr><th scope="row">{esc(g["name"])}</th><td>{esc(g["denominator"])}</td><td>{esc(g["rule"])}</td></tr>'
                     for g in cd["guardrails"])
    bases = "".join(f'<tr><th scope="row">{esc(b["label"])}</th><td class="num">{esc(b["value"])}</td></tr>'
                    for k, b in cd["baselines"].items() if k != "budget_cap")
    cc = cd["copy_check"]
    copy_check = (badge(t("x.copyok"), "good") if cc["passed"]
                  else badge(t("x.copybad", v=", ".join(cc["violations"])), "bad"))
    return f"""
  <article class="xcard" id="{esc(cd['id'])}">
    <div class="status s-{st_kind}"><b>{esc(cd['status_label'])}</b> {esc(cd['status_reason'])}</div>
    <header class="xhead"><div><span class="dim small">{esc(cd['type_label'])} · {esc(cd['id'])}</span>
      <h3>{esc(cd['title'])}</h3></div>
      <dl class="meta-grid"><div><dt>{t("x.channel")}</dt><dd>{esc(cd['channel'])}</dd></div>
      <div><dt>{t("x.budget")}</dt><dd>{money(cd['budget_cap_usd'])}</dd></div>
      <div><dt>{t("x.owner")}</dt><dd>{esc(cd['owner'])}</dd></div></dl></header>
    <dl class="kv">
      <dt>{t("x.problem")}</dt><dd>{esc(cd['target_problem'])}</dd>
      <dt>{t("x.hypothesis")}</dt><dd>{esc(cd['hypothesis'])}</dd>
      <dt>{t("x.linked")}</dt><dd>{linked}</dd>
    </dl>
    <h4>{t("x.prereq")}</h4><ul class="prereq">{prereq}</ul>
    <h4>{t("x.copy")}</h4>{creative}
    <div class="three">
      <div><h4>{t("x.facts")}</h4><ul class="tight">{facts}</ul></div>
      <div><h4>{t("x.unsupported")}</h4><ul class="tight">{unsup}</ul></div>
      <div><h4>{t("x.hyps")}</h4><ul class="tight">{hyps}</ul></div>
    </div>
    <h4>{t("x.measure")}</h4>
    <dl class="kv"><dt>{t("x.primary")}</dt><dd><b>{esc(pm.get('name', ''))}</b> = {esc(pm.get('numerator', ''))}
      <br><span class="dim">÷</span> {esc(pm.get('denominator', ''))}<br><span class="dim">{t("x.base")}</span> {esc(pm.get('baseline', ''))}</dd></dl>
    <div class="scroll"><table><thead><tr><th scope="col">{t("x.guard")}</th><th scope="col">{t("x.den")}</th>
      <th scope="col">{t("x.rule")}</th></tr></thead><tbody>{guards}</tbody></table></div>
    <div class="scroll"><table class="narrow"><caption>{esc(t("x.bases", ch=cd['baseline_channel']))}</caption>
      <tbody>{bases}</tbody></table></div>
    <dl class="kv"><dt>{t("x.stop")}</dt><dd>{esc(cd['stop_rule'])}</dd><dt>{t("x.continue")}</dt><dd>{esc(cd['continue_rule'])}</dd></dl>
    <details><summary>{t("x.cites", n=len(cd['evidence']))}</summary><ul class="cites">{_cite_list(cd['evidence'])}</ul></details>
    <p class="small">{copy_check} <span class="dim">{esc(t("x.terms", terms=", ".join(_terms_for_lang(cc['terms_checked']))))}</span></p>
  </article>"""


def section_experiments(r):
    b = r["budget"]
    within = badge(t("x.within"), "good") if b["within_cap"] else badge(t("x.over"), "bad")
    return f"""
<section id="experiments">
  <h2>{t("x.title")}</h2>
  <p class="lead">{t("x.lead", total=money(b['total']), cap=money(b['cap']), days=b['days'], badge=within)}</p>
  {''.join(_card(cd) for cd in r['cards'])}
</section>"""


def section_evidence(r):
    rows = []
    for s in r["sessions"]:
        rep = badge(t("e.repaired"), "warn", t("e.repaired.title")) if s.get("repaired") else ""
        rows.append(
            f'<tr id="{esc(s["session_id"])}"><th scope="row">{esc(s["session_id"])}</th>'
            f'<td class="mono">{esc(s["participant_id"])}</td><td>{esc(s["kind"])}</td>'
            f'<td lang="en">{esc(s["observed_behavior"])}</td><td lang="en">“{esc(s["user_statements"])}”</td>'
            f'<td class="dim" lang="en">{esc(s["researcher_inferences"])}</td>'
            f'<td class="mono dim">{esc(t("e.line", n=s["line"]))} {rep}</td></tr>')
    a = r["analysis"]
    keys = [k for k, _ in r["stages"]]
    user_rows = []
    for uid in sorted(a["user_channel"]):
        ch = a["user_channel"][uid]
        marks = "".join(f'<td class="c">{"●" if uid in a["users"][ch][k] else "·"}</td>' for k in keys)
        user_rows.append(f'<tr><th scope="row" class="mono">{esc(uid)}</th><td>{esc(ch)}</td>{marks}</tr>')
    uhead = "".join(f'<th scope="col" class="c">{esc(stage(k))}</th>' for k in keys)
    res = r["research"]
    original = f' {t("e.original")}' if get_lang() != "en" else ""
    return f"""
<section id="evidence">
  <h2>{t("e.title")}</h2>
  <p class="lead">{t("e.lead", sessions=res['sessions'], participants=res['participants'], retests=res['retests'],
                      who=esc(join(res['multi_session_participants']) or t("e.none")))}{original}</p>
  <div class="scroll"><table class="sessions">
    <thead><tr><th scope="col">{t("e.session")}</th><th scope="col">{t("e.participant")}</th><th scope="col">{t("e.visit")}</th>
    <th scope="col">{t("e.observed")}</th><th scope="col">{t("e.said")}</th><th scope="col">{t("e.inferred")}</th>
    <th scope="col">{t("e.source")}</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>
  <details><summary>{t("e.users", n=len(user_rows))}</summary>
  <div class="scroll"><table class="users"><thead><tr><th scope="col">{t("e.user")}</th><th scope="col">{t("f.channel")}</th>{uhead}</tr></thead>
  <tbody>{''.join(user_rows)}</tbody></table></div></details>
</section>"""


def section_method(r):
    p = r["params"]
    items = [("users", {}), ("scan", {}), ("payer", {}), ("delivered", {}),
             ("unrefunded", {"cutoff": esc(r['analysis']['cutoff'])}), ("cash", {}),
             ("net", {"rate": f"{p['commission_rate'] * 100:.0f}"}), ("cohort", {})]
    dl = "".join(f'<dt>{t("d." + k)}</dt><dd>{t("d." + k + ".v", **kw)}</dd>' for k, kw in items)
    return f"""
<section id="method">
  <h2>{t("d.title")}</h2>
  <dl class="kv">{dl}</dl>
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
"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;-webkit-text-size-adjust:100%}
.lang-switch{float:right;font-size:13px;font-weight:600;text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:3px 10px;color:var(--ink)}
.lang-switch:hover{background:var(--soft)}
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
  var L=JSON.parse(document.getElementById('i18n').textContent);
  var btn=document.getElementById('edit-toggle'), dl=document.getElementById('download-priorities');
  if(!btn||!dl) return;
  btn.addEventListener('click',function(){
    var on=document.body.classList.toggle('editing');
    btn.setAttribute('aria-pressed',on?'true':'false');
    btn.textContent=on?L.done:L.edit;
    document.querySelectorAll('.prio [data-field]').forEach(function(el){el.contentEditable=on?'true':'false';});
  });
  dl.addEventListener('click',function(){
    var cfg=JSON.parse(document.getElementById('priorities-config').textContent);
    document.querySelectorAll('.prio').forEach(function(card){
      var c=(cfg.candidates||[]).find(function(x){return x.id===card.dataset.id;});
      if(!c) return;
      card.querySelectorAll('[data-field]').forEach(function(el){
        var f=el.dataset.field, v=el.innerText.trim(); if(v==='\\u2014') v='';
        if(f==='match_terms'){c[f]=v.split(',').map(function(s){return s.trim();}).filter(Boolean);return;}
        // bilingual fields keep both languages; only the one shown on this page is replaced
        if(c[f]&&typeof c[f]==='object'){c[f][L.lang]=v;}
        else if(L.lang!=='en'){c[f]={en:c[f]||'',zh:v};}
        else{c[f]=v;}
      });
    });
    // Show + copy instead of a file download: downloads are blocked in sandboxed hosting.
    var text=JSON.stringify(cfg,null,2)+'\\n', box=document.getElementById('export-box'),
        ta=document.getElementById('export-json'), st=document.getElementById('export-status');
    ta.value=text; box.hidden=false; ta.focus(); ta.select();
    var ok=function(){st.textContent=L.copied;}, no=function(){st.textContent=L.selected;};
    try{navigator.clipboard.writeText(text).then(ok,no);}catch(e){no();}
  });
})();
"""


def render_html(r):
    a = r["analysis"]
    lang = r["lang"]
    nav = ["summary", "quality", "funnel", "money", "costs", "priorities", "experiments", "evidence", "method"]
    nav_html = "".join(f'<a href="#{k}">{esc(t("nav." + k))}</a>' for k in nav)
    fp = " · ".join(f"{esc(k)} {esc(v[:12])}" for k, v in r["fingerprints"].items())
    body = "".join([section_summary(r), section_quality(r), section_funnel(r), section_money(r), section_costs(r),
                    section_priorities(r), section_experiments(r), section_evidence(r), section_method(r)])
    other, other_label = OTHER_FILE[lang]
    i18n = json.dumps({"lang": lang, "edit": t("p.edit"), "done": t("p.done"), "copied": t("p.copied"),
                       "selected": t("p.selected")}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="{t('html.lang')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(t('r.title'))}</title>
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="lang-switch" href="{other}" hreflang="{'zh-CN' if lang == 'en' else 'en'}">{other_label}</a>
  <p class="eyebrow">{esc(t('r.eyebrow'))}</p>
  <h1>{esc(t('r.h1'))}</h1>
  <p class="meta">{esc(t('r.meta', cutoff=a['cutoff'], price=money(r['params']['price'])))}</p>
</div></header>
<nav class="toc" aria-label="{esc(t('nav.sections'))}"><div class="wrap">{nav_html}</div></nav>
<main class="wrap">{body}</main>
<footer class="wrap">{esc(t('r.footer', version=r['version'], fp=fp))}</footer>
<script type="application/json" id="i18n">{i18n}</script>
<script>{JS}</script>
</body>
</html>
"""


def render_markdown(r):
    b = r["budget"]
    lines = [f"# {t('md.title')}", "",
             t("md.budget", total=money(b["total"]), cap=money(b["cap"]), days=b["days"],
               state=t("md.within") if b["within_cap"] else t("md.over")), ""]
    cite = lambda cs: ", ".join(c["session_id"] for c in cs)
    for cd in r["cards"]:
        lines += [f"## {cd['id']} — {cd['title']}", "",
                  f"**{t('md.status', s=cd['status_label'])}** {cd['status_reason']}", "",
                  f"- **{t('md.type')}:** {cd['type_label']}",
                  f"- **{t('md.channel')}:** {cd['channel']}",
                  f"- **{t('md.owner')}:** {cd['owner']}",
                  f"- **{t('md.budgetcap')}:** {money(cd['budget_cap_usd'])}",
                  f"- **{t('md.linked')}:** " + ", ".join(f"{p['id']} ({t('pstatus.' + p['status'])})"
                                                         for p in cd["linked_priorities"]),
                  "", f"### {t('md.problem')}", "", cd["target_problem"], "",
                  f"### {t('md.hypothesis')}", "", cd["hypothesis"], "", f"### {t('md.prereq')}", ""]
        for p in cd["prerequisites"]:
            lines.append(f"- [{'x' if p['met'] is True else ' '}] {p['text']} — {p['detail']}")
        lines += ["", f"### {t('md.copy')}", ""]
        for k, v in cd["copy"].items():
            lines.append(f"- **{t('copy.' + k)}:** {v}")
        if cd["type"] == "aso":
            sc = cd["screenshot_concept"]
            lines += ["", f"### {t('md.screenshot')}", "", f"{sc.get('frame', '')}: {sc.get('visual', '')}", "",
                      f"### {t('md.kw')}", "", t("md.kwhead"), "| --- | --- | --- | --- |"]
            for g in cd["keyword_intent_groups"]:
                lines.append(f"| {g['group']} | {g['intent']} | {', '.join(g.get('example_terms', []))} | "
                             f"{cite(g['evidence'])} |")
        else:
            lines += ["", f"### {t('md.script')}", "", t("md.scripthead"), "| --- | --- | --- | --- | --- | --- |"]
            for s in cd["script"]:
                lines.append(f"| {s['shot']} | {s['seconds']} | {s['visual']} | {s['on_screen_text']} | "
                             f"{s['voiceover']} | {cite(s['evidence'])} |")
        lines += ["", f"### {t('md.facts')}", ""] + [f"- {x['text']} ({cite(x['evidence'])})" for x in cd["product_facts"]]
        lines += ["", f"### {t('md.unsupported')}", ""] + \
                 [f"- {x['text']} ({cite(x['evidence'])})" for x in cd["unsupported_capabilities"]]
        lines += ["", f"### {t('md.hyps')}", ""] + [f"- {x}" for x in cd["marketing_hypotheses"]]
        pm = cd["primary_metric"]
        lines += ["", f"### {t('md.measure')}", "",
                  f"- **{t('md.primary')}:** {pm.get('name', '')} = {pm.get('numerator', '')} ÷ {pm.get('denominator', '')}",
                  f"- **{t('md.primarybase')}:** {pm.get('baseline', '')}"]
        lines += [f"- **{t('md.guard')} — {g['name']}** (÷ {g['denominator']}): {g['rule']}" for g in cd["guardrails"]]
        lines += [f"- {t('md.base')} — {bb['label']}: {bb['value']}" for k, bb in cd["baselines"].items() if k != "budget_cap"]
        lines += ["", f"**{t('md.stop')}:** {cd['stop_rule']}", "", f"**{t('md.continue')}:** {cd['continue_rule']}", "",
                  f"### {t('md.cites')}", ""]
        for c in cd["evidence"]:
            lines.append(f"- {c['session_id']} ({t('field.' + c['field'])}"
                         + (f", {c.get('participant_id')}, {c.get('kind')}" if not c["broken"] else "")
                         + f"): “{c['text']}”")
        cc = cd["copy_check"]
        lines += ["", t("md.copyok") if cc["passed"] else t("md.copybad", v=", ".join(cc["violations"])), "", "---", ""]
    return "\n".join(lines)

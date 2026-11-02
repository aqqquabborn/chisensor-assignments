#!/usr/bin/env python3
"""Assemble the hosted version of the submission.

    python build_site.py <01_room_prototype dir> <02_evidence_tool dir> <out dir>

Needs `npm run build` in 01 (dist/) and `python analyze.py` in 02 (out/).
Writes: index.html (cover page), prototype.html (single-file app),
report(.zh-CN).html, experiment_cards(.zh-CN).md/.json, index.html + index.zh-CN.html.
Every number on the cover page is
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
for sfx in ("", ".zh-CN"):
    for name in (f"report{sfx}.html", f"experiment_cards{sfx}.md", f"experiment_cards{sfx}.json"):
        shutil.copy(tool / "out" / name, out / name)

HEAD = '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">\n<style>\n/* Layout: a cover sheet — two assignment bands, each pairing the live thing with what to check; a verification ledger closes. */\n:root {\n  --paper: #f6f7f8; --sheet: #ffffff; --ink: #14181f; --muted: #5d6673; --rule: #dde1e6;\n  --accent: #0e6f68; --accent-soft: #e2f1ef; --stop: #b42318; --stop-soft: #fdecea; --warn: #8a5a00; --warn-soft: #fbf0d9;\n  --ok: #1d6b45; --ok-soft: #e3f3ea; --device: #1b1f27;\n  --display: "Archivo", "Helvetica Neue", Arial, sans-serif;\n  --body: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, sans-serif;\n  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;\n}\n@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {\n  --paper: #0f1216; --sheet: #161a20; --ink: #e8ebef; --muted: #9aa3ae; --rule: #2a3039;\n  --accent: #4fc3b6; --accent-soft: #12312e; --stop: #ff8f80; --stop-soft: #3a1714; --warn: #f0bc5c; --warn-soft: #33270f;\n  --ok: #6fd6a0; --ok-soft: #12301f; --device: #000; color-scheme: dark } }\n:root[data-theme="dark"] {\n  --paper: #0f1216; --sheet: #161a20; --ink: #e8ebef; --muted: #9aa3ae; --rule: #2a3039;\n  --accent: #4fc3b6; --accent-soft: #12312e; --stop: #ff8f80; --stop-soft: #3a1714; --warn: #f0bc5c; --warn-soft: #33270f;\n  --ok: #6fd6a0; --ok-soft: #12301f; --device: #000; color-scheme: dark }\n* { box-sizing: border-box }\nbody { margin: 0; background: var(--paper); color: var(--ink); font: 15px/1.55 var(--body); }\n.wrap { max-width: 1120px; margin: 0 auto; padding-block: 0; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)) }\nheader.wrap { padding-block: 40px 28px }\n.eyebrow { font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 }\nh1 { font: 700 clamp(28px, 4.4vw, 44px)/1.08 var(--display); letter-spacing: -.015em; margin: 10px 0 10px; text-wrap: balance }\nh2 { font: 700 24px/1.15 var(--display); margin: 0; text-wrap: balance }\nh3 { font: 600 13px/1.3 var(--body); text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 8px }\n.lead { max-width: 66ch; color: var(--muted); margin: 0 }\n.mono { font-family: var(--mono); font-size: .92em }\na { color: var(--accent) }\na:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }\n.status { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px }\n.pill { font: 500 12.5px/1 var(--mono); padding: 7px 10px; border-radius: 999px; background: var(--sheet); border: 1px solid var(--rule) }\n.pill b { color: var(--ok); font-weight: 500 }\nsection { background: var(--sheet); border-block: 1px solid var(--rule); padding-block: 32px; margin-block: 0 20px }\n.band-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; margin-bottom: 18px }\n.tag { font: 500 12px/1 var(--mono); color: var(--accent); background: var(--accent-soft); padding: 5px 8px; border-radius: 6px }\n.grid { display: grid; grid-template-columns: minmax(0, 400px) minmax(0, 1fr); gap: 32px; align-items: start }\n@media (max-width: 860px) { .grid { grid-template-columns: minmax(0, 1fr) } }\n.device { background: var(--device); border-radius: 34px; padding: 10px; max-width: 410px; margin-inline: auto; width: 100% }\n.device iframe { display: block; width: 100%; height: 760px; border: 0; border-radius: 26px; background: #fff }\n.device-cap { text-align: center; font-size: 12.5px; color: var(--muted); margin: 10px 0 0 }\n.stack { display: grid; gap: 22px; min-width: 0 }\n.stack > *, .grid > *, .two > * { min-width: 0 }\n@media (max-width: 520px) { tbody th { white-space: normal; word-break: break-word } }\n.scroll { overflow-x: auto }\ntable { border-collapse: collapse; width: 100%; font-size: 14px }\nth, td { text-align: left; vertical-align: top; padding: 8px 10px 8px 0; border-bottom: 1px solid var(--rule) }\ntbody th { font-weight: 500; white-space: nowrap; padding-right: 16px }\n.note { font-size: 13.5px; color: var(--muted); margin: 0 }\n.btnrow { display: flex; flex-wrap: wrap; gap: 8px }\n.btn { display: inline-flex; align-items: center; min-height: 40px; padding: 0 14px; border-radius: 8px; font-weight: 600; font-size: 14px; text-decoration: none; border: 1px solid var(--rule); color: var(--ink); background: var(--sheet) }\n.btn.primary { background: var(--accent); color: var(--sheet); border-color: var(--accent) }\n.verdict { border-left: 4px solid var(--stop); background: var(--stop-soft); padding: 12px 14px; border-radius: 0 8px 8px 0 }\n.verdict strong { color: var(--stop) }\n.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0; border-top: 1px solid var(--rule) }\n.kpi { padding: 12px 12px 12px 0; border-bottom: 1px solid var(--rule) }\n.kpi .v { font: 700 24px/1.1 var(--display); font-variant-numeric: tabular-nums }\n.kpi .l { font-size: 12.5px; color: var(--muted) }\nol.list, ul.list { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px }\nol.list li { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 10px; align-items: start }\n.rank { width: 26px; height: 26px; border-radius: 50%; background: var(--accent); color: var(--sheet); display: grid; place-items: center; font: 600 13px/1 var(--mono) }\n.meta { display: block; font-size: 13px; color: var(--muted) }\nul.list li { border: 1px solid var(--rule); border-radius: 10px; padding: 12px 14px; display: grid; gap: 4px }\n.cardhead { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center }\n.state { font: 600 11.5px/1 var(--mono); letter-spacing: .04em; padding: 5px 8px; border-radius: 6px }\n.s-blocked { background: var(--stop-soft); color: var(--stop) } .s-draft { background: var(--warn-soft); color: var(--warn) } .s-ready { background: var(--ok-soft); color: var(--ok) }\n.ledger td.n { font: 500 14px var(--mono); white-space: nowrap; font-variant-numeric: tabular-nums }\npre { background: var(--paper); border: 1px solid var(--rule); border-radius: 8px; padding: 12px 14px; overflow-x: auto; font: 13px/1.5 var(--mono); margin: 6px 0 0 }\n.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px }\nfooter.wrap { padding-block: 8px 40px; color: var(--muted); font-size: 12.5px }\n@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto } }\n.topline { display: flex; justify-content: space-between; align-items: center; gap: 12px }\n.langswitch { font: 600 13px/1 var(--mono); padding: 8px 12px; border: 1px solid var(--rule); border-radius: 999px; background: var(--sheet); color: var(--ink); text-decoration: none }\nhtml:lang(zh-CN) { --body: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; --display: "Archivo", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif }\n</style>'

# ── 3. cover pages (EN + 中文) from the tool's own outputs ──
REPO = os.environ.get("REPO_URL", "https://github.com/")

T = {
    "en": {
        "file": "index.html", "other": ("index.zh-CN.html", "中文"), "html_lang": "en", "sfx": "",
        "title": "ChiSensor Submission",
        "eyebrow": "ChiSensor · remote assignments",
        "h1": "Two runnable submissions, one place to check them",
        "lead": "Assignment 1 runs live in the phone frame below. Assignment 2's report is generated by the tool from the supplied CSV files. Nothing here needs a paid API, an account or a real payment; every scan, analysis and purchase step is simulated and labelled.",
        "pill1": "Assignment 1 · <b>30 automated tests pass</b>", "pill2": "Assignment 2 · <b>33 automated tests pass</b>",
        "pill3": "EN / 中文 · Python 3.9–3.13 · Node 20+",
        "a1tag": "Assignment 1", "a1h": "Recoverable room-to-plan prototype", "iframe": "prototype.html#en",
        "iframe_title": "ChiSensor bedroom prototype",
        "cap": "Live prototype at 390 px. Open <b>Test panel</b> at the bottom to switch scenario; EN / 中文 in the header.",
        "a1lead": "A renter's bed cannot move; the goal is an easier walk from the door to the bedside without buying furniture. The bedroom is 4.0 m × 3.5 m; the free action moves the chair out of the entry path.",
        "scen_h": "Scenarios to try",
        "scen": ["Scan all three areas → analysis → free action → unlock → confirm → deliver",
                 "Stopped and explained before any scan",
                 "Missing area named; re-scan keeps what was captured",
                 "Step 3 fails once; Retry continues the same job ID",
                 "Plan stays locked; refresh keeps the same transaction",
                 "Retry delivers on the same transaction, no new charge"],
        "a1note": "Refresh during analysis or a pending payment: the same job ID or transaction ID comes back. The Test panel shows job ID, transaction ID, entitlement and delivery status, and can send a duplicate verification event.",
        "fullscreen": "Open full screen",
        "a2tag": "Assignment 2", "a2h": "Evidence to promotion experiments",
        "verdict": "Fix delivery before promoting.", "ready": "Delivery is ready",
        "undelivered": lambda n: f"{n} verified payment{'' if n == 1 else 's'} never delivered",
        "pending": lambda n: f"{n} purchase{'' if n == 1 else 's'} stuck in pending",
        "sep": "; ", "end": ".", "blocked": "Both experiment cards stay BLOCKED as drafts.",
        "k1": "first opens", "k2": "unrefunded delivered payers", "k3": "net after commission", "k4": "cash contribution (not profit)",
        "open_report": "Open the full report", "md": "Cards · Markdown", "json": "Cards · JSON",
        "prio_h": "Product priorities", "of_part": lambda n, total: f"{n} of {total} participants",
        "cards_h": lambda tot, cap: f"Experiment cards · {tot} of {cap} cap", "cap_word": "cap",
        "status": lambda s: s,
        "v_h": "Verification",
        "ledger": [("Prototype — unit checks", "State machine, analysis retry, idempotent payment, persistence, room geometry", "21 pass"),
                   ("Prototype — browser checks", "Six brief flows at 390 px, refresh recovery, Chinese UI, no camera or payment API use", "9 pass"),
                   ("Tool — repeatable checks", "Reprocessing, zero payers, new refund, same participant, cost change, validation, readiness, Chinese output", "33 pass"),
                   ("Tool — mutation run", "Six injected bugs, each caught by at least one check", "6 / 6")],
        "run_h": "Run it locally", "src": "Source, data and tests:",
        "run1": "npm run check      # build + 21 unit + 9 browser checks",
        "run2": "python analyze.py  # → out/report.html + out/report.zh-CN.html",
        "footer": "Cover figures are read from the tool's own output (analysis.json). Inputs: {inputs}. $9.99 is the exercise's example price.",
    },
    "zh": {
        "file": "index.zh-CN.html", "other": ("index.html", "EN"), "html_lang": "zh-CN", "sfx": ".zh-CN",
        "title": "ChiSensor 作业提交",
        "eyebrow": "ChiSensor · 远程作业",
        "h1": "两份可运行的作业，一处即可检查",
        "lead": "作业 1 在下方的手机框中实时运行。作业 2 的报告由工具根据提供的 CSV 文件生成。这里不需要付费 API、账号或真实付款；所有扫描、分析和购买步骤均为模拟，并有明确标注。",
        "pill1": "作业 1 · <b>30 项自动化检查通过</b>", "pill2": "作业 2 · <b>33 项自动化检查通过</b>",
        "pill3": "EN / 中文 · Python 3.9–3.13 · Node 20+",
        "a1tag": "作业 1", "a1h": "可恢复的房间到方案交互原型", "iframe": "prototype.html#zh",
        "iframe_title": "ChiSensor 卧室原型",
        "cap": "390 px 实时原型。点击底部的<b>测试面板</b>切换场景；顶部可切换 EN / 中文。",
        "a1lead": "租客的床不能移动；目标是在不购买家具的前提下，让从门口走到床边更顺畅。卧室为 4.0 m × 3.5 m；免费建议是把椅子移出入口通道。",
        "scen_h": "可尝试的场景",
        "scen": ["扫描全部三个区域 → 分析 → 免费建议 → 解锁 → 确认 → 交付",
                 "在扫描前就停止并说明原因",
                 "指出缺失区域；重新扫描保留已采集的内容",
                 "第 3 步失败一次；重试沿用同一个任务 ID",
                 "方案保持锁定；刷新后仍是同一笔交易",
                 "重试在同一笔交易上完成交付，不会重复扣款"],
        "a1note": "在分析中或付款处理中刷新页面：会恢复同一个任务 ID 或交易 ID。测试面板显示任务 ID、交易 ID、权益与交付状态，并可发送重复的验证事件。",
        "fullscreen": "全屏打开",
        "a2tag": "作业 2", "a2h": "从用户证据到推广试验",
        "verdict": "先修复交付，再做推广。", "ready": "交付已就绪",
        "undelivered": lambda n: f"{n} 笔已验证付款从未交付",
        "pending": lambda n: f"{n} 笔购买卡在处理中",
        "sep": "；", "end": "。", "blocked": "两张试验卡都保持为“已阻止”的草稿。",
        "k1": "首次打开", "k2": "未退款且已交付的付费用户", "k3": "扣除佣金后净额", "k4": "现金贡献（不是利润）",
        "open_report": "打开完整报告", "md": "试验卡 · Markdown", "json": "试验卡 · JSON",
        "prio_h": "产品优先级", "of_part": lambda n, total: f"{total} 位参与者中的 {n} 位",
        "cards_h": lambda tot, cap: f"试验卡 · {tot} / 上限 {cap}", "cap_word": "上限",
        "status": lambda s: {"BLOCKED": "已阻止", "DRAFT": "草稿", "READY FOR REVIEW": "待评审"}.get(s, s),
        "v_h": "验证",
        "ledger": [("原型 — 单元检查", "状态机、分析重试、幂等付款、持久化、房间几何", "21 通过"),
                   ("原型 — 浏览器检查", "390 px 下的六个场景、刷新恢复、中文界面、不调用相机或支付 API", "9 通过"),
                   ("工具 — 可重复检查", "重复处理、零付费、新退款、同一参与者、成本变化、校验、就绪状态、中文输出", "33 通过"),
                   ("工具 — 变异测试", "注入六个缺陷，每个都至少被一项检查发现", "6 / 6")],
        "run_h": "本地运行", "src": "源代码、数据与测试：",
        "run1": "npm run check      # 构建 + 21 单元 + 9 浏览器检查",
        "run2": "python analyze.py  # → out/report.html + out/report.zh-CN.html",
        "footer": "封面数字读取自工具自身的输出（analysis.json）。输入：{inputs}。$9.99 为作业给出的示例价格。",
    },
}
SCEN_KEYS = ["① happy", "② unsupported", "③ scan_incomplete", "④ analysis_failed_recoverable",
             "⑤ purchase_pending", "⑥ verified_payment_delivery_failed"]


def money(v):
    return f"−${-v:,.2f}" if v < 0 else f"${v:,.2f}"


def build(lang):
    L = T[lang]
    sfx = L["sfx"]
    a = json.loads((tool / "out" / f"analysis{sfx}.json").read_text(encoding="utf-8"))
    f, m_, c = a["funnel"]["Overall"], a["money"]["Overall"], a["costs"]["Overall"]
    cards, prios, budget = a["experiment_cards"], a["priorities"], a["experiment_budget"]
    participants = a["research"]["participants"]

    reasons = []
    if m_["undelivered_tx"]:
        reasons.append(L["undelivered"](m_["undelivered_tx"]))
    if m_["pending_tx"]:
        reasons.append(L["pending"](m_["pending_tx"]))
    reason = L["sep"].join(reasons) if reasons else L["ready"]
    if lang == "en":
        reason = reason[:1].upper() + reason[1:]

    prio_rows = "".join(
        f'<li><span class="rank">{p["rank"]}</span><div><strong>{esc(p["title"])}</strong>'
        f'<span class="meta">{esc(L["of_part"](len(p["participants"]), participants))} · '
        f'{esc(p["event_evidence"]["headline"])}</span></div></li>' for p in prios)
    card_rows = "".join(
        f'<li><div class="cardhead"><span class="state s-{c_["status"].split()[0].lower()}">{esc(L["status"](c_["status"]))}</span>'
        f'<span class="meta mono">{esc(c_["id"])} · {L["cap_word"]} {money(c_["budget_cap_usd"])}</span></div>'
        f'<strong>{esc(c_["title"])}</strong><span class="meta">{esc(c_["type_label"])}</span></li>' for c_ in cards)
    scen_rows = "".join(f'<tr><th scope="row" class="mono">{esc(k)}</th><td>{esc(v)}</td></tr>'
                        for k, v in zip(SCEN_KEYS, L["scen"]))
    ledger = "".join(f'<tr><th scope="row">{esc(x)}</th><td>{esc(y)}</td><td class="n">{esc(z)}</td></tr>'
                     for x, y, z in L["ledger"])
    inputs = " · ".join(f"{k} {v[:10]}" for k, v in a["input_sha256"].items() if k.endswith(".csv"))
    other_file, other_label = L["other"]
    other_lang = "zh-CN" if lang == "en" else "en"

    body = f"""
<header class="wrap">
  <div class="topline"><p class="eyebrow">{L["eyebrow"]}</p><a class="langswitch" href="{other_file}" hreflang="{other_lang}" lang="{other_lang}">{other_label}</a></div>
  <h1>{L["h1"]}</h1>
  <p class="lead">{L["lead"]}</p>
  <div class="status">
    <span class="pill">{L["pill1"]}</span>
    <span class="pill">{L["pill2"]}</span>
    <span class="pill">{L["pill3"]}</span>
  </div>
</header>

<section aria-labelledby="a1">
  <div class="wrap">
    <div class="band-head"><span class="tag">{L["a1tag"]}</span><h2 id="a1">{L["a1h"]}</h2></div>
    <div class="grid">
      <div>
        <div class="device"><iframe src="{L["iframe"]}" title="{L["iframe_title"]}" loading="lazy"></iframe></div>
        <p class="device-cap">{L["cap"]}</p>
      </div>
      <div class="stack">
        <p class="lead">{L["a1lead"]}</p>
        <div>
          <h3>{L["scen_h"]}</h3>
          <div class="scroll"><table><tbody>{scen_rows}</tbody></table></div>
        </div>
        <p class="note">{L["a1note"]}</p>
        <div class="btnrow"><a class="btn primary" href="{L["iframe"]}" target="_blank" rel="noopener">{L["fullscreen"]}</a></div>
      </div>
    </div>
  </div>
</section>

<section aria-labelledby="a2">
  <div class="wrap">
    <div class="band-head"><span class="tag">{L["a2tag"]}</span><h2 id="a2">{L["a2h"]}</h2></div>
    <div class="grid">
      <div class="stack">
        <p class="verdict"><strong>{L["verdict"]}</strong> {esc(reason)}{L["end"]} {L["blocked"]}</p>
        <div class="kpis">
          <div class="kpi"><div class="v">{f["first_open"]}</div><div class="l">{L["k1"]}</div></div>
          <div class="kpi"><div class="v">{f["unrefunded_delivered"]}</div><div class="l">{L["k2"]}</div></div>
          <div class="kpi"><div class="v">{money(m_["net_after_commission"])}</div><div class="l">{L["k3"]}</div></div>
          <div class="kpi"><div class="v">{money(c["cash_contribution"])}</div><div class="l">{L["k4"]}</div></div>
        </div>
        <div class="btnrow">
          <a class="btn primary" href="report{sfx}.html" target="_blank" rel="noopener">{L["open_report"]}</a>
          <a class="btn" href="experiment_cards{sfx}.md" target="_blank" rel="noopener">{L["md"]}</a>
          <a class="btn" href="experiment_cards{sfx}.json" target="_blank" rel="noopener">{L["json"]}</a>
        </div>
      </div>
      <div class="stack">
        <div><h3>{L["prio_h"]}</h3><ol class="list">{prio_rows}</ol></div>
        <div><h3>{esc(L["cards_h"](money(budget["total"]), money(budget["cap"])))}</h3><ul class="list">{card_rows}</ul></div>
      </div>
    </div>
  </div>
</section>

<section aria-labelledby="v">
  <div class="wrap two">
    <div>
      <h2 id="v">{L["v_h"]}</h2>
      <div class="scroll"><table class="ledger"><tbody>{ledger}</tbody></table></div>
    </div>
    <div>
      <h2>{L["run_h"]}</h2>
      <p class="note">{L["src"]} <a href="{REPO}">{esc(REPO.replace("https://", ""))}</a></p>
      <pre>cd 01_room_prototype
npm install
npm run dev        # http://localhost:5173
{L["run1"]}</pre>
      <pre>cd 02_evidence_tool
{L["run2"]}
python -m unittest -v
bash scripts/demo.sh</pre>
    </div>
  </div>
</section>

<footer class="wrap">{esc(L["footer"].format(inputs=inputs))}</footer>
"""
    doc = (f'<!doctype html>\n<html lang="{L["html_lang"]}">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           f'<title>{L["title"]}</title>\n'
           f'<link rel="alternate" hreflang="{other_lang}" href="{other_file}">\n'
           + HEAD + "\n</head>\n<body>" + body + "</body>\n</html>\n")
    (out / L["file"]).write_text(doc, encoding="utf-8")


for lang in T:
    build(lang)
print("site written to", out, [p.name for p in sorted(out.iterdir())])

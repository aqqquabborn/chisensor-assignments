**English** · [中文](README.zh-CN.md)

# ChiSensor — remote assignments

[![Tests](https://github.com/aqqquabborn/chisensor-assignments/actions/workflows/pages.yml/badge.svg)](https://github.com/aqqquabborn/chisensor-assignments/actions)

**▶ Live demo: https://aqqquabborn.github.io/chisensor-assignments/**
Both assignments in one page — nothing to install.

## What I built

**1. Room-to-plan prototype** — `01_room_prototype`
A mobile web app (390 px) for the bedroom flow: scan check → analysis → one free action →
optional paid plan. All six scenarios from the brief can be switched in the built-in Test
panel, including scan errors, analysis failure with recovery, pending payment and failed
delivery. Payments are idempotent: a repeated verification or a delivery retry never creates
a second charge.

**2. Evidence-to-experiments tool** — `02_evidence_tool`
A command-line tool that turns the supplied feedback, event and channel data into an
auditable HTML report. The report covers the funnel by channel, cost and CAC, three product
priorities linked to evidence, and two experiment cards (ASO and short content). Change any
input file and every figure is recalculated.

Automated tests run on every update: 29 for the prototype, 27 for the tool, all passing.

## Run locally

```bash
# Prototype (Node 20+)
cd 01_room_prototype && npm install && npm run dev    # open http://localhost:5173

# Tool (Python 3.9+, no dependencies)
cd 02_evidence_tool && python analyze.py              # open out/report.html
```

Details, design decisions and the AI usage log are in each folder's `README.md` and
`AI_USAGE_LOG.md`.

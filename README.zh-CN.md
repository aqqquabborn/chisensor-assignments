[English](README.md) · **中文**

# ChiSensor — 远程作业

[![Tests](https://github.com/aqqquabborn/chisensor-assignments/actions/workflows/pages.yml/badge.svg)](https://github.com/aqqquabborn/chisensor-assignments/actions)

**▶ 在线演示：https://aqqquabborn.github.io/chisensor-assignments/**
两份作业集中在一个页面，无需安装。

## 完成内容

**远程作业一：可恢复的房间到方案交互原型** — `01_room_prototype`
移动端网页原型（390 px），覆盖卧室主线：扫描质量检查 → 分析 → 一项完整免费行动 → 可选付费方案。
内置测试面板可切换题目给定的全部 6 个场景，包括扫描不完整、分析失败后恢复、付款 pending、
已验证付款后交付失败。同一交易的重复验证或重试交付，都不会产生第二次收费。

**远程作业二：从用户证据到推广试验的轻量工具** — `02_evidence_tool`
命令行工具，读取给定的 feedback、event 和 channel 数据，生成可审计的 HTML 报告：
按渠道及整体计算的漏斗、成本与 CAC、3 个与证据关联的产品优先项，以及 2 张试验卡
（ASO/商店价值表达卡和短内容卡）。替换任一输入文件，所有数字都会重新计算。

每次更新都会自动运行测试：原型 29 项，工具 27 项，全部通过。

## 本地运行

```bash
# 原型（Node 20+）
cd 01_room_prototype && npm install && npm run dev    # 打开 http://localhost:5173

# 工具（Python 3.9+，无需额外依赖）
cd 02_evidence_tool && python analyze.py              # 打开 out/report.html
```

各目录下的 `README.md` 和 `AI_USAGE_LOG.md` 说明了实现细节、设计决策和 AI 使用记录（英文）。

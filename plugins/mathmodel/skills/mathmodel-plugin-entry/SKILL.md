---
name: mathmodel-plugin-entry
description: Route natural-language MathModel requests to the existing S0-S8 workflow and keep a local progress record for the optional dashboard. Use when a user asks to start, continue, inspect progress, verify results, or open the MathModel workspace.
---

# MathModel Plugin Entry

Use this skill as the friendly entry point for the MathModel Codex plugin.

## Routing

- “开始建模”, “分析这道题”, or “start modeling”: invoke `$paper-workflow-orchestrator`.
- “继续”, “继续第二问”, or “resume”: read the current workflow guard report and `.mathmodel/status.json` when present, then resume from the first incomplete or invalid stage.
- “查看进度” or “status”: summarize S0-S8 from `paper_output/qa/workflow_guard_report.json` and `.mathmodel/status.json` when present.
- “检查结果”, “验证”, or “verify”: invoke the evidence gate and report the actual PASS/FAIL artifacts.
- “打开看板” or “dashboard”: follow the plugin README command for the local dashboard. Do not claim that a persistent Codex sidebar is available unless the host visibly provides it.

## Progress records

When the project has the plugin status helper available, record meaningful stage
changes with `update_model_status.py`. Keep status claims grounded in files and
command results. A running status is not evidence of a successful model run.

The existing MathModel workflow remains authoritative for model decisions,
calculations, evidence, and paper QA. This entry skill only improves routing and
visibility; it must not invent results or bypass workflow guards.

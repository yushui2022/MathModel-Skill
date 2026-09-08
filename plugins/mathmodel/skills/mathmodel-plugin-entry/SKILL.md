---
name: mathmodel-plugin-entry
description: Route natural-language MathModel requests to the existing S0-S8 workflow so a stateless Codex can resume a reproducible, evidence-backed paper. Use when a user asks to start, continue, inspect progress, verify results, or open the optional evidence workspace.
---

# MathModel Plugin Entry

Use this skill as the friendly entry point for the MathModel Codex plugin. The conversation remains the place for problem interpretation, model selection, reasoning, and formal writing. The optional right-side workspace is an evidence and runtime companion; it is not a replacement IDE and it never writes a paper by itself.

## Stateless recovery protocol

At the beginning of every new or resumed conversation, do not rely on chat history. Run the read-only context packet:

```powershell
python <plugin-root>/scripts/build_context_packet.py --project-root <contest-project> --format markdown
```

Treat `paper_output/qa/workflow_guard_report.json` as the authoritative gate and
`paper_output/context/workflow_memory.json` as a durable handoff summary. If the
memory summary disagrees with Guard, report the mismatch and follow Guard. Put a
compact context packet into the conversation containing the project, verified
count, current/next stage, blockers, recommended Skill, next action, active job,
and the relevant artifact paths. This is the coaching contract that lets a fresh
Codex follow the same rhythm as the previous session.

After each meaningful Skill handoff, run Guard again and refresh workflow memory.
Never infer PASS from a user message, a manually written event, or a stage number.
Only actual files, hashes, calculations, evidence gates, and format checks can
advance the workflow. When all S0-S8 gates pass, ask the formal writer to perform
the final consistency review before delivery.

## Routing

- “开始建模”, “分析这道题”, or “start modeling”: build the context packet, run the plugin preflight, and invoke `$paper-workflow-orchestrator`. Start/reuse `scripts/serve_dashboard.py --project-root <contest-project> --port 0` only when a visual companion helps; use the Codex host's right-side browser panel when available. Do not wait for the user to manually write a status file.
- “继续”, “继续第二问”, or “resume”: build a fresh context packet, follow Guard's first incomplete or invalid stage, and invoke only its recommended Skill. Do not replay stages that already have valid evidence.
- “查看进度” or “status”: summarize the context packet and S0-S8 from `paper_output/qa/workflow_guard_report.json` and `.mathmodel/status.json` when present, using “已验证 X/9 个阶段” rather than a fake percentage.
- “检查结果”, “验证”, or “verify”: invoke the evidence gate and report the actual PASS/FAIL artifacts.
- “打开看板” or “dashboard”: start/reuse the local service and open its printed URL in the host's right panel when the host exposes that capability. The panel should show context, evidence, experiments, logs, and delivery previews. If the host cannot open a panel, return the local URL and a copyable next action. Do not claim fullscreen, picture-in-picture, or a persistent sidebar unless the host visibly provides it.

## Progress records

When the project has the plugin status helper available, record meaningful stage
activity with `update_model_status.py`. Keep status claims grounded in files and
command results. A running or manually passed event is not evidence of a
successful model run; the workflow guard remains the completion authority.

The existing MathModel workflow remains authoritative for model decisions,
calculations, evidence, and paper QA. This entry skill supplies recovery,
sequencing, and visibility so a stateless Codex can produce a coherent paper; it
must not invent results, run hidden agents, or bypass workflow guards.

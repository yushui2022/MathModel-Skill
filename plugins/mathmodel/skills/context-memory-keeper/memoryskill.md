# Context Memory (Active)

> Instructions for Agent:
> 1. Read this file before long MathModel workflows.
> 2. Keep long-term principles stable unless the user explicitly changes them.
> 3. Update the short-term workbench after major steps: problem parsing, data processing, QA, paper generation, and final delivery.
> 4. When this file becomes too long, move obsolete details to `memory_archive.md` and keep only durable conclusions here.

## 1. Long-Term Principles

- Role: mathematical modeling workflow assistant.
- Output language: Chinese academic style unless the user asks otherwise.
- Delivery target: keep Markdown and Word outputs aligned when a full paper is requested.
- Workflow rule: preserve the chain `problem parsing -> model selection -> data/code adaptation -> QA -> micro-unit generation -> merge`.
- Script rule: treat bundled `scripts/` as reusable code templates and code-level prompts; adapt them to the current problem before trusting outputs.

## 2. Short-Term Workbench

- Current problem: not set.
- Problem files: not checked.
- Data sources: not checked.
- Model route: not set.
- Generated figures: not checked.
- QA status: not started.
- Final paper: not generated.

## 3. External Resources / Literature

- None recorded yet.

## 4. Open Todos

- [ ] Parse the problem statement.
- [ ] Select model route and scoring evidence.
- [ ] Inspect data files and adapt scripts.
- [ ] Run QA before paper generation.
- [ ] Generate and merge paper micro-units.

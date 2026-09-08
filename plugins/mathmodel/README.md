# MathModel Codex Plugin

This plugin packages the existing MathModel Standard workflow for Codex. The
workflow remains the source of truth: S0 input admission, S1 problem analysis,
S2 model route, S3 data and visualization planning, S4 code generation, S5 real
execution, S6 evidence gate, S7 formal writing, and S8 Word/PDF QA.

## Start a project

Place the contest statement and attachments in `problem_files/`, then ask Codex:

> Start a mathematical modeling project. Run preflight first, follow S0-S8,
> keep all project code and artifacts under `paper_output/`, and record progress
> with the MathModel status script.

The plugin does not silently install Python or LibreOffice. Use the existing
preflight check to identify missing dependencies before a long run.

## Local progress dashboard

From the contest project root, run:

```bash
python <path-to-mathmodel-plugin>/scripts/update_model_status.py \\
  --stage S0 --status running --message "Admitting contest inputs"
python <path-to-mathmodel-plugin>/scripts/serve_dashboard.py
```

Then open the printed local URL. The dashboard reads `.mathmodel/status.json`
and `.mathmodel/events.jsonl` from the current project, and can preview images
and other artifacts below the project root. It is deliberately local-only.

The dashboard is a first integration slice. A future MCP server can expose the
same state as structured tools and return an in-Codex UI resource where the host
supports it.

## Development note

The skills under `skills/` are copied from `packages/codex/.agents/skills/` for
plugin packaging. Keep the canonical workflow changes in the package source and
refresh this copy before publishing a release.

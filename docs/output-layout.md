# Standard 2.2 Output Layout

All current-contest generated artifacts stay under `paper_output/`. Installed skills remain reusable and must not contain contest-specific code or results.

```text
paper_output/
├── OUTPUT_LAYOUT.md
├── preflight_report.json
├── input_manifest.json
├── step1/
│   └── problem_analysis.json
├── plan/
│   ├── model_route.json
│   ├── rubric_alignment.json
│   ├── scoring_strategy.md
│   ├── data_plan.json
│   ├── visualization_plan.json
│   ├── paper_outline.json
│   └── writing_plan.json
├── code/
│   ├── data_processing/
│   ├── visualization/
│   ├── modeling/
│   └── qa/
├── data_cleaned/
├── figures/
├── figure_index.json
├── tables/
│   └── table_index.json
├── results/
│   ├── run_manifest.json
│   ├── model_results.json
│   ├── metrics.json
│   └── conclusions.json
├── qa/
│   ├── workflow_guard_report.json
│   ├── evidence_gate_report.json
│   ├── draft_audit.json
│   ├── repair_queue.json
│   └── rendered/
├── context/
│   ├── authoring_state.json
│   └── workflow_memory.json
├── drafts/
│   ├── sections/
│   ├── repairs/
│   ├── legacy/
│   │   ├── micro_units/
│   │   ├── legacy_scaffold.md
│   │   ├── legacy_scaffold.docx
│   │   └── legacy_ref_check.md
│   └── assembled_draft.md
├── quickstart/
├── final_paper_source.md
├── final_paper.docx
├── format_check_report.md
└── format_check_report.json
```

## Ownership

| Path | Owner |
|---|---|
| `step1/` | problem analysis |
| `plan/model_route.json` | model/rubric selector |
| `code/`, `results/`, `tables/` | current-contest computation |
| `qa/evidence_gate_report.json` | quality-assurance-auditor |
| `plan/writing_plan.json`, `context/authoring_state.json` | paper-formal-writer |
| `drafts/sections/`, `drafts/assembled_draft.md` | formal S7 |
| `drafts/repairs/` | queued micro repair |
| `drafts/legacy/`, `quickstart/` | non-formal scaffolds |
| `final_paper_source.md`, `final_paper.docx` | sole formal manuscript path |

`tasks.json` may appear for legacy/quickstart compatibility. It is not required by S6 or formal S7.

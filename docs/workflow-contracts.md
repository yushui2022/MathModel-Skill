# Standard 2.2 Workflow Contracts

Contracts are machine-readable handoff records, not substitutes for reasoning. Current hashes decide whether a stage remains valid.

## S0-S6

| Contract | Producer | Purpose |
|---|---|---|
| `preflight_report.json` | orchestrator | input/runtime/edition admission |
| `input_manifest.json` | orchestrator | attachment role, size, SHA-256 |
| `step1/problem_analysis.json` | problem selector | questions, constraints, attachment use |
| `plan/model_route.json` | model selector | model and validation route |
| `plan/rubric_alignment.json` | model selector | scoring evidence |
| `plan/data_plan.json` | data skill | dataset and field use |
| `plan/visualization_plan.json` | data skill | planned figures/tables |
| `results/run_manifest.json` | model runner | commands, scripts, inputs, outputs, exit codes, hashes |
| `results/model_results.json` | model runner | computed question results |
| `results/metrics.json` | model runner | finite evaluation values |
| `results/conclusions.json` | model runner | evidence-backed conclusions |
| `qa/evidence_gate_report.json` | QA | S6 status and input hashes |

## S7 Adaptive Authoring

Every new S7 contract includes `schema_version`, UTC creation time, producer role, status, and upstream `input_hashes`.

### `plan/writing_plan.json`

Records requested and selected mode, selection reason, outline/evidence hashes, section order, target length, required evidence, figures, tables, formulas, and global constraints.

### `context/authoring_state.json`

Overall states:

```text
PLANNED -> DRAFTING -> REPAIR_REQUIRED -> ASSEMBLED -> PASS
                                      \-> BLOCKED
```

Each unit records path, attempts, repeated issue count, last draft hash, approved hash, status, and issues. Assembly and final source have independent paths, hashes, and statuses.

### `qa/draft_audit.json`

Stores rolling audits for sections, assembly, and final source: effective length, required/declared evidence, numerical coverage, formula errors, placeholders, duplicate prose, internal language, and broken figure/table references.

### `qa/repair_queue.json`

Each issue contains ID, section, category, expected evidence, attempt count, and strategy:

```text
section-rewrite | micro-repair
```

The queue cannot be used to bypass the two-failure threshold.

## S8

`format_check_report.json` records content, citation, formula, DOCX, visual, and render status plus hashes of the formal source, DOCX, outline, indexes, evidence report, writing plan, and authoring state.

## Invalidation

- Changed evidence input invalidates S6, writing plan, S7, DOCX, and S8.
- Changed writing plan invalidates all section approvals and downstream files.
- Changed approved section invalidates assembly, final source approval, DOCX, and S8.
- Changed assembly invalidates final source approval.
- Changed final source invalidates formal DOCX and S8.
- Changed DOCX invalidates S8.

Re-run the owning command; never edit status or hash fields by hand.

`paper_output/tasks.json` is an optional legacy/quickstart contract and is intentionally excluded from official S6 and formal S7 hashes.

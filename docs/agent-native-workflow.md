# Agent-Native Standard Workflow

The Agent reasons and writes; scripts make admission, evidence, state transitions, assembly, and delivery checks deterministic.

## Formal Sequence

```text
S0 preflight
-> S1 problem analysis
-> S2 model/rubric route
-> S3 data/visualization plan
-> S4 contest-specific code
-> S5 real execution and result contracts
-> S6 evidence gate
-> S7 adaptive authoring and global revision
-> S8 native Word and required PDF render QA
```

Start with `$paper-workflow-orchestrator`. On resume, run `workflow_guard.py --status` and trust current artifacts and hashes over remembered conversation state.

## Input And Code Boundary

Put official files in `problem_files/`. Preflight classifies each file as statement, raw data, result template, unreadable input, or unsupported attachment and records size plus SHA-256.

Current-contest code belongs only in:

```text
paper_output/code/data_processing/
paper_output/code/visualization/
paper_output/code/modeling/
paper_output/code/qa/
```

Do not modify installed skill scripts to fit one contest.

## Evidence Boundary

S5 must actually execute model code and write `run_manifest.json`, model results, finite metrics, conclusions, tables, and usable figures. S6 recomputes hashes and rejects stale scripts, changed inputs/outputs, placeholders, empty values, failed artifacts, and untraceable conclusions.

Codex command:

```bash
python .agents/skills/quality-assurance-auditor/scripts/evidence_gate.py --mode official
```

Claude Code uses `.claude/skills`; Trae uses `.trae/skills`.

## Authoring Boundary

After S6 PASS, use `paper-formal-writer`:

```bash
python .agents/skills/paper-formal-writer/scripts/build_paper_outline.py
python .agents/skills/paper-formal-writer/scripts/prepare_authoring.py --mode auto
```

Normal papers use complete sections. Validate each section, use queued micro repair only after two repeated categories, assemble passed sections deterministically, then globally revise the whole manuscript. The formal source is `paper_output/final_paper_source.md`; legacy and quickstart scaffolds never become formal inputs.

```bash
python .agents/skills/paper-formal-writer/scripts/assemble_sections.py
python .agents/skills/paper-formal-writer/scripts/validate_authoring.py --assembled
python .agents/skills/paper-formal-writer/scripts/validate_authoring.py --final
```

## Delivery Boundary

```bash
python .agents/skills/paper-formal-writer/scripts/format_formal_docx.py
python .agents/skills/paper-formal-writer/scripts/check_paper_format.py --render required
```

Formal Word requires fresh S6 and S7 state. Equations must be editable OMML. Final delivery requires LibreOffice PDF rendering, pages, extractable text, complete citations, valid figures/tables, and current hashes.

## Quickstart

`quickstart_run.py` is only an installation smoke test. It writes under `paper_output/quickstart/`; it cannot create or validate formal output.

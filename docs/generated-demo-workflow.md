# CUMCM 2024 B Demo Status

`examples/cumcm2024-b-demo/` is retained as a historical generated artifact set. Standard 2.2 does not modify or regenerate its paper, code, figures, tables, evidence reports, or Word file.

The demo remains useful for inspecting:

- contest-specific code under `paper_output/code/`
- model results, metrics, conclusions, and run provenance
- figure/table indexing
- a completed Markdown and Word paper from the earlier Standard workflow

It does **not** contain the new Standard 2.2 S7 contracts:

```text
paper_output/plan/writing_plan.json
paper_output/context/authoring_state.json
paper_output/qa/draft_audit.json
paper_output/qa/repair_queue.json
paper_output/drafts/assembled_draft.md
```

Therefore the preserved demo must not be presented as having passed the new adaptive authoring and hash invalidation gates.

## Applying 2.2 To A Fresh Problem

Run the current `paper-workflow-orchestrator` from S0. After official S6 evidence PASS:

```bash
python .agents/skills/paper-formal-writer/scripts/build_paper_outline.py
python .agents/skills/paper-formal-writer/scripts/prepare_authoring.py --mode auto
```

Use `.claude/skills` or `.trae/skills` on those platforms. Draft and audit complete sections, deterministically assemble them, globally revise the paper, validate the final Markdown, then generate DOCX and run required render QA.

Official CUMCM problem files are not distributed in this repository. Users must obtain and place authorized contest materials in their own `problem_files/` directory.

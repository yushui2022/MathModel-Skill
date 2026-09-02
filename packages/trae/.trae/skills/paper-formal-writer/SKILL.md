---
name: paper-formal-writer
description: Plan, draft, audit, globally revise, format, and verify a formal mathematical-modeling paper after the Standard evidence gate passes. Use for the sole S7/S8 formal manuscript path, not for legacy micro-unit scaffolds.
---

# Paper Formal Writer

This skill is the sole formal author and final manuscript producer in Standard. It turns a fresh S6 evidence chain into an audited Markdown source and native-equation Word document.

## Entry

Run before formal work:

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill paper-formal-writer
```

S0-S6 must pass. If workflow state is uncertain, run `workflow_guard.py --status` and follow its current artifact report rather than memory.

## Single Formal Path

```text
S6 evidence PASS
-> writing plan
-> chapter drafts
-> chapter audits
-> queued local repair when required
-> deterministic assembly
-> Agent global revision
-> final Markdown audit
-> formal DOCX
-> S8 format/render gate
```

Do not promote quickstart, legacy, or mechanically merged micro-unit output into a formal filename.

## Prepare

1. Build the evidence-aware outline:

```bash
python .trae/skills/paper-formal-writer/scripts/build_paper_outline.py
```

2. Prepare adaptive authoring:

```bash
python .trae/skills/paper-formal-writer/scripts/prepare_authoring.py --mode auto
```

`auto` selects `global` only when the ideal body target is at most 6000 effective characters. Normal competition papers use `section`. Use explicit `global` only for a user-requested short report.

The authoritative S7 contracts are:

- `paper_output/plan/writing_plan.json`
- `paper_output/context/authoring_state.json`
- `paper_output/qa/draft_audit.json`
- `paper_output/qa/repair_queue.json`

## Draft And Audit

Write only to the path recorded for the current unit in `authoring_state.json`. Each chapter must be a complete, coherent section and must include its required removable marker:

```html
<!-- mathmodel-evidence: evidence-id-1, evidence-id-2 -->
```

Audit every changed draft:

```bash
python .trae/skills/paper-formal-writer/scripts/validate_authoring.py --section <section-id>
```

Routing is deterministic:

- `global` repeats the same blocking category twice: switch to `section`.
- A section fails once: rewrite that section.
- A section repeats the same category twice: `$paper-micro-unit-generator` may repair only queued locations.
- The third changed attempt with the same category: S7 becomes `BLOCKED`; report the cause and suggest Lite as a user choice without switching automatically.

Audits block short drafts, missing chapters/evidence/numbers, broken formulas, placeholders, duplicate prose, broken figure/table references, and internal workflow language.

## Assemble And Revise

After all active units pass:

```bash
python .trae/skills/paper-formal-writer/scripts/assemble_sections.py
python .trae/skills/paper-formal-writer/scripts/validate_authoring.py --assembled
```

The assembler follows outline order, strips evidence comments, and preserves existing numbering. It writes `paper_output/drafts/assembled_draft.md`.

Then read the entire assembled draft and evidence chain, and rewrite the paper globally into:

```text
paper_output/final_paper_source.md
```

This pass must unify terminology, notation, transitions, argument order, citations, captions, and conclusions. Copying the assembled draft unchanged is rejected.

Run the final source audit:

```bash
python .trae/skills/paper-formal-writer/scripts/validate_authoring.py --final
```

Any change to evidence, writing plan, approved section draft, assembly, or final source invalidates downstream PASS state.

## Word And S8

Only after `authoring_state.status = PASS`:

```bash
python .trae/skills/paper-formal-writer/scripts/format_formal_docx.py
python .trae/skills/paper-formal-writer/scripts/check_paper_format.py --render required
```

Formal mode requires fresh S6 and S7 hashes. `--allow-draft` may create `final_paper_draft.docx` for layout diagnosis, but never satisfies S7/S8 or overwrites the formal DOCX.

`format_formal_docx.py` converts LaTeX to editable Word OMML and blocks failed conversion. `check_paper_format.py` checks dynamic length, required hierarchy, citations, evidence-linked figures/tables, formulas, duplicate prose, DOCX structure, LibreOffice PDF rendering, page count, and extractable text.

## Writing Standard

- Use `1 / 1.1 / 1.1.1` headings and complete CUMCM sections.
- For each question, connect assumptions, variables, derivation, algorithm, computed values, validation, uncertainty, and conclusion.
- Define symbols before formulas and explain every displayed result.
- Cite and interpret every included figure/table.
- Use only current evidence; never invent runs, values, sources, or validation.
- Avoid copied or number-swapped paragraphs used only to meet length.
- Keep implementation language out of body prose; reproducibility paths belong in the appendix.

## References

- Format standard: [references/cumcm-paper-standard.md](references/cumcm-paper-standard.md)
- Full-paper structure: [references/formal-paper-template.md](references/formal-paper-template.md)
- Section expansion: [references/section-expansion-rules.md](references/section-expansion-rules.md)
- Figures, tables, formulas, and results: [references/figure-table-writing-rules.md](references/figure-table-writing-rules.md)

Read only the reference needed for the current writing or repair decision.

## Handoff

After each meaningful transition, run workflow status and update `paper_output/context/workflow_memory.json`:

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
python .trae/skills/context-memory-keeper/scripts/update_workflow_memory.py
```

S8 is complete only when the machine-readable format report is PASS and fresh.

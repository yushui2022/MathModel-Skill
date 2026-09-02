# Standard 2.2 Formal Paper Authoring

`paper-formal-writer` is the sole formal author. `paper-micro-unit-generator` is limited to queued local repair and explicit legacy/quickstart scaffolds.

## Preconditions

- S0-S5 artifacts are complete.
- `paper_output/qa/evidence_gate_report.json` is a fresh S6 PASS.
- Computed values, tables, figures, conclusions, and run hashes are current.

## Prepare

```bash
python .claude/skills/paper-formal-writer/scripts/build_paper_outline.py
python .claude/skills/paper-formal-writer/scripts/prepare_authoring.py --mode auto
```

Replace `.claude/skills` with `.agents/skills` for Codex or `.trae/skills` for Trae.

`auto` selects global drafting only for a target of at most 6000 effective characters. Normal competition papers use section mode.

## Draft Sections

Read `writing_plan.json` and write every unit to its recorded path. Preserve removable evidence markers:

```html
<!-- mathmodel-evidence: metric:Q1:rmse, table:Q1-results -->
```

Audit each changed unit:

```bash
python .claude/skills/paper-formal-writer/scripts/validate_authoring.py --section <section-id>
```

The first repeated issue stays with a section rewrite. The second repeated category creates a micro-repair queue. The third blocks S7. Global mode falls back to section mode after two repeated categories.

## Assemble And Globally Revise

```bash
python .claude/skills/paper-formal-writer/scripts/assemble_sections.py
python .claude/skills/paper-formal-writer/scripts/validate_authoring.py --assembled
```

The assembler removes evidence comments and preserves reference numbering. The Agent must read the whole assembly and rewrite it into `paper_output/final_paper_source.md`, unifying argument flow, notation, terminology, citations, captions, and conclusions.

```bash
python .claude/skills/paper-formal-writer/scripts/validate_authoring.py --final
```

An unchanged copy of `assembled_draft.md` is rejected.

## Generate Word And Render

```bash
python .claude/skills/paper-formal-writer/scripts/format_formal_docx.py
python .claude/skills/paper-formal-writer/scripts/check_paper_format.py --render required
```

Formal generation rechecks S6, writing-plan, approved-section, assembly, and final-source hashes. LaTeX must convert to native Word OMML. The final gate requires successful LibreOffice PDF rendering, a nonzero page count, extractable text, valid citations, and source/DOCX consistency.

`--allow-draft` writes `final_paper_draft.docx` only and never satisfies formal gates.

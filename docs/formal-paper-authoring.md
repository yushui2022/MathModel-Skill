# Standard Formal Paper Authoring

`paper-formal-writer` is the sole formal author. `paper-micro-unit-generator` is limited to queued local repair and explicit legacy/quickstart scaffolds.

## Preconditions

- S0-S5 artifacts are complete.
- `paper_output/qa/evidence_gate_report.json` is a fresh S6 PASS.
- Computed values, tables, figures, conclusions, and run hashes are current.

## Prepare

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/build_paper_outline.py"
python "<SKILL_ROOT>/paper-formal-writer/scripts/prepare_authoring.py" --mode auto
```

Replace `<SKILL_ROOT>` with the actual parent directory of the loaded Skill folder. Keep the working directory at the contest project root; this placeholder is not a shell variable.

Default `competition` delivery sets a planning target of at least 14000 effective characters and routes `auto` to section mode. The final checks require 8000 main-paper characters and 18 rendered pages before appendices. These are project defaults, not universal contest rules; verify the actual competition's cap and page-count scope. Comments, fenced code and appendices cannot fill the main-paper floor. Each question needs its own substantive `5.1`, `5.2`, ... section.

A user-requested short report can use:

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/prepare_authoring.py" --mode auto --delivery short-report --scope-reason "User requested a short technical report"
```

Custom `--min-pages` and `--min-body-chars` also require `--scope-reason`. Do not lower them just to bypass a failure. `smoke-test` is only for installation fixtures. All scope changes invalidate downstream hashes and require renewed authoring/format audits. Read the installed formal writer's `references/competition-scope.md` for expansion and boundary handling; old plans without scope must be prepared again.

## Draft Sections

Read `writing_plan.json` and write every unit to its recorded path. Preserve removable evidence markers:

```html
<!-- mathmodel-evidence: metric:Q1:rmse, table:Q1-results -->
```

Audit each changed unit:

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/validate_authoring.py" --section <section-id>
```

The first repeated issue stays with a section rewrite. The second repeated category creates a micro-repair queue. The third blocks S7. Global mode falls back to section mode after two repeated categories.

### Numerical Claim Semantics

Formal preparation now resolves required metrics from computed `metrics.json`,
checks their CSV cells and successful run records, and freezes their IDs, units,
sample scopes, splits and permitted conversions in the writing plan. Read the
installed writer's `references/metric-claims.md` for the complete producer schema.
Missing metadata is a modeling repair, not permission to infer it during writing.

Each draft and final source has a sibling `.claims.json` binding exact visible
result sentences to those metrics. Section, assembly and final audits reject
wrong train/test populations, units, values, undeclared percentage conversions
and unsupported feasibility/optimality claims. Use `claims: []` when a draft has
no metrics. The sidecar records the exact Markdown SHA-256; update it after edits.
Assembly merges the records automatically. Global revision needs updated final
quotes, and changing approved bindings blocks DOCX export. Sidecars never appear
in the paper. Rules cover registered metrics and recognized wording, not arbitrary
semantic inference; reviewers still assess experiment design and mathematical claims.

Old formal writing plans need to be rebuilt. The explicit installation-only
`smoke-test` mode is not a numerical-claim certification.

## Assemble And Globally Revise

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/assemble_sections.py"
python "<SKILL_ROOT>/paper-formal-writer/scripts/validate_authoring.py" --assembled
```

The assembler removes evidence comments and preserves reference numbering. The Agent must read the whole assembly and rewrite it into `paper_output/final_paper_source.md`, unifying argument flow, notation, terminology, citations, captions, and conclusions.

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/validate_authoring.py" --final
```

An unchanged copy of `assembled_draft.md` is rejected.

## Generate Word And Render

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/format_formal_docx.py"
python "<SKILL_ROOT>/paper-formal-writer/scripts/check_paper_format.py" --render required
```

Formal generation rechecks S6, writing-plan, approved-section, assembly, and final-source hashes. LaTeX must convert to native Word OMML. The final gate requires successful LibreOffice PDF rendering, a nonzero page count, extractable text, valid citations, and source/DOCX consistency.

`--allow-draft` writes `final_paper_draft.docx` only and never satisfies formal gates.

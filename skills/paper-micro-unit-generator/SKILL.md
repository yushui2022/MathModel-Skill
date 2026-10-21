---
name: paper-micro-unit-generator
description: "按修复队列重写反复不通过的论文章节，或按明确要求生成旧版与演练草稿脚手架。当章节连续审计失败需要局部重写、或用户明确要求快速草稿而非正式论文时使用。"
compatibility: "Requires Python 3.11-3.12; draft modes additionally need python-docx; LibreOffice not required."
---

# Paper Micro-Unit Generator
Resolve <SKILL_ROOT> to the parent directory of this loaded skill folder, using its actual absolute path. Run commands from the contest project root, never from the installed skill directory. The placeholder is not a shell environment variable.


Use this skill only for local repair or an explicitly requested legacy scaffold. `paper-formal-writer` remains the sole formal author and the only producer of `paper_output/final_paper_source.md` and `paper_output/final_paper.docx`.

## Entry Check

For formal repair, run:

```bash
python "<SKILL_ROOT>/paper-workflow-orchestrator/scripts/workflow_guard.py" --skill paper-micro-unit-generator
```

Continue only when S0-S6 pass and `paper_output/qa/repair_queue.json` contains at least one item whose strategy is `micro-repair`. Do not create a repair queue manually to bypass the two-failure threshold.

Legacy and quickstart modes are installation or old-model scaffolds. They do not satisfy S7 and do not require the formal repair queue.

## Formal Repair Mode

1. Read `paper_output/plan/writing_plan.json`, `paper_output/context/authoring_state.json`, `paper_output/qa/draft_audit.json`, and `paper_output/qa/repair_queue.json`.
2. Select only queued `micro-repair` items. Keep the issue ID, section, failure category, expected evidence, and attempt count intact.
3. Read the affected section draft and only the evidence needed by that issue. Do not rewrite unrelated sections.
4. Write repair material to `paper_output/drafts/repairs/<issue-id>.md`. The material must contain concrete replacement text, its target location, and any required evidence marker.
5. Apply the replacement to the queued section draft. Preserve valid headings, equations, figure/table identifiers, citations, and evidence markers.
6. Re-run the section audit:

```bash
python "<SKILL_ROOT>/paper-formal-writer/scripts/validate_authoring.py" --section <section-id>
```

7. Return to `paper-formal-writer` or `paper-workflow-orchestrator`. This skill must not assemble the formal manuscript or generate Word.

If the same blocking category reaches the third changed attempt, respect `authoring_state.status = BLOCKED`. Report the evidence or requirement causing the failure and suggest Lite as a user decision; never switch editions automatically.

## Repair Rules

- Repair the failed claim or paragraph, not the whole paper.
- Use only computed values and paths present in the current evidence chain.
- Preserve `<!-- mathmodel-evidence: ... -->` markers until deterministic assembly removes them.
- Do not invent data, citations, completed experiments, or successful validation.
- Do not expose workflow language in paper prose.
- Do not renumber existing figure, table, equation, or bibliography references.
- A repair is complete only after `validate_authoring.py --section` returns PASS.

## Legacy Mode

The old command names remain available. With no arguments they write only to `paper_output/drafts/legacy/`:

```bash
python "<SKILL_ROOT>/paper-micro-unit-generator/scripts/generate_all_offline.py"
python "<SKILL_ROOT>/paper-micro-unit-generator/scripts/merge.py"
```

Expected outputs:

```text
paper_output/drafts/legacy/micro_units/*.txt
paper_output/drafts/legacy/generate_log.json
paper_output/drafts/legacy/legacy_scaffold.md
paper_output/drafts/legacy/legacy_scaffold.docx
paper_output/drafts/legacy/legacy_ref_check.md
```

`tasks.json` is required only for this legacy batch path. The merge is deterministic and preserves existing reference numbers.

For the built-in smoke test, the orchestrator passes `--output-root paper_output/quickstart --stem quickstart_scaffold`; all smoke-test files stay under `paper_output/quickstart/`.

Never write `final_paper.md`, `final_paper_source.md`, `final_paper.docx`, or similarly formal names from legacy/quickstart mode.

## Template Library

Read [references/micro-unit-library.md](references/micro-unit-library.md) only when a queued repair needs a fine-grained paragraph/sentence pattern or when the user explicitly requests legacy scaffolding. Do not load the full 200+ template library for ordinary section writing.

## Handoff

After a formal repair, run workflow status and update persistent context:

```bash
python "<SKILL_ROOT>/paper-workflow-orchestrator/scripts/workflow_guard.py" --status
python "<SKILL_ROOT>/context-memory-keeper/scripts/update_workflow_memory.py"
```

The guard report is authoritative if memory and current artifacts disagree.
Read the persistent snapshot at `paper_output/context/workflow_memory.json` before resuming a repair.

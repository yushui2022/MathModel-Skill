# MathModel Skill Standard 2.2 for Claude Code

This package installs the Standard edition only. It is recommended for strong models with long context and reliable tool use. Ordinary or older models should use the independent `lite` branch.

## Install

Extract the archive at the contest project root. It creates:

```text
.claude/skills/
requirements.txt
docs/
VERSION
MATHMODEL_BUILD.json
```

It does not create or overwrite root `CLAUDE.md`. Install only one MathModel edition in a project.

```bash
python -m pip install -r requirements.txt
python -m pip check
```

Put the contest statement and official attachments in `problem_files/`.

## Start

```text
Use $paper-workflow-orchestrator to complete this mathematical-modeling project. Run preflight and workflow status first, keep all contest code and artifacts under paper_output/, and follow S0-S8. After S6 passes, use the Standard 2.2 section-authoring path; only use micro repair when repair_queue.json requests it. Globally revise the assembled paper before producing formal Word and required PDF render QA.
```

Manual status check:

```bash
python .claude/skills/paper-workflow-orchestrator/scripts/preflight_check.py
python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
```

Quickstart is only an installation smoke test. Its drafts stay under `paper_output/quickstart/` and cannot satisfy formal S7/S8.

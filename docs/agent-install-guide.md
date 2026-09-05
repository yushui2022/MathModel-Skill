# Agent Installation Guide

## Choose One Edition

| Need | Branch |
|---|---|
| Strong model and formal competition delivery | `standard` (Standard) |
| Ordinary/older model and simpler workflow | `lite` |
| Top-tier model, high cost allowed, maximum verification | `pro` |

Never combine editions in one project. Preflight scans `skills/`, `.agents/skills/`, `.codex/skills/`, `.claude/skills/`, and `.trae/skills/`, including legacy installs without markers.

## Standard Platform Layout

| Platform | Archive | Project path | Entry |
|---|---|---|---|
| Codex | `MathModel-Skill-Codex.zip` | `.agents/skills/` | `.agents/skills/paper-workflow-orchestrator/SKILL.md` |
| Claude Code | `MathModel-Skill-Claude-Code.zip` | `.claude/skills/` | `.claude/skills/paper-workflow-orchestrator/SKILL.md` |
| Trae | `MathModel-Skill-Trae.zip` | `.trae/skills/` | `.trae/skills/paper-workflow-orchestrator/SKILL.md` |

Archives contain no root `AGENTS.md` or `CLAUDE.md`; existing project instructions remain untouched.

## Install

1. Create or open the contest project.
2. Extract one platform ZIP at its root.
3. Create `problem_files/` and add the statement and official attachments.
4. Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

5. Install LibreOffice for the required final render gate.
6. Invoke `$paper-workflow-orchestrator`.

## Verify The Package

Each archive contains:

- `VERSION`
- `MATHMODEL_BUILD.json` with per-file SHA-256 values
- `LICENSE`
- `requirements.txt`
- platform README and workflow docs

Release-level hashes are in `SHA256SUMS.txt`.

## Manual Commands

Claude Code:

```bash
python .claude/skills/paper-workflow-orchestrator/scripts/preflight_check.py
python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
```

Codex:

```bash
python .agents/skills/paper-workflow-orchestrator/scripts/preflight_check.py
python .agents/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
```

Trae:

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/preflight_check.py
python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
```

Use `quickstart_run.py` only to test installation. It writes exclusively under `paper_output/quickstart/` and cannot pass formal S7/S8.

## Upgrade

Remove the previous MathModel skill directories before extracting a newer edition. Do not keep old Standard under `skills/` while adding Standard under `.agents/skills/`; duplicate same-edition installs are warned because model routing can become ambiguous.

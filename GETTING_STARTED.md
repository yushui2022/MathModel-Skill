# MathModel Skill Standard 2.2 Quick Start

Standard is intended for strong models with long context and stable tool use. Use the `lite` branch for ordinary or older models, and `pro` only for top-tier models when high computation cost is acceptable.

Install exactly one edition in each contest project.

## 1. Extract One Package

| Platform | Package | Installed skill root |
|---|---|---|
| Codex | `MathModel-Skill-Codex.zip` | `.agents/skills/` |
| Claude Code | `MathModel-Skill-Claude-Code.zip` | `.claude/skills/` |
| Trae | `MathModel-Skill-Trae.zip` | `.trae/skills/` |

The archives do not overwrite root `AGENTS.md` or `CLAUDE.md`.

## 2. Install Dependencies

```bash
python -m pip install -r requirements.txt
python -m pip check
```

Install LibreOffice before final delivery. S8 uses it to render DOCX to PDF and verify pages and extractable text.

## 3. Add Contest Files

Create `problem_files/` at the project root and place the statement plus all official attachments there.

## 4. Start The Orchestrator

```text
Use $paper-workflow-orchestrator to complete this mathematical-modeling project. Run preflight and workflow status first, then follow S0-S8. Use the Standard 2.2 section-authoring path after S6, globally revise the assembled manuscript, and do not call any output final until the evidence, authoring, Word, and required render gates pass.
```

## 5. Inspect Final Status

The main outputs are:

```text
paper_output/qa/evidence_gate_report.json
paper_output/context/authoring_state.json
paper_output/final_paper_source.md
paper_output/final_paper.docx
paper_output/format_check_report.json
```

Quickstart output is only a smoke-test scaffold under `paper_output/quickstart/`.

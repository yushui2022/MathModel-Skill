# Quickstart Smoke Test

This minimal input checks that the Standard package is installed and can run basic parsing, contracts, scaffold generation, and Word export. It is not a real contest workflow.

## Run

Copy `problem_files/` into a temporary project containing one platform package.

```bash
# Codex
python .agents/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Claude Code
python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Trae
python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

## Expected Output

Quickstart may create input, plan, result-contract, and legacy task artifacts for smoke testing. All generated paper-like drafts must stay under:

```text
paper_output/quickstart/
```

It must not create formal `paper_output/final_paper_source.md` or `paper_output/final_paper.docx`.

For a real problem, invoke `$paper-workflow-orchestrator`, run official S6 evidence validation, execute Standard 2.2 adaptive S7 writing, and finish with required S8 render QA.

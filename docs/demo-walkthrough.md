# Quickstart Smoke-Test Walkthrough

Quickstart checks installation, basic input parsing, legacy scaffold generation, and Word availability. It is not a competition-paper workflow.

## Prepare

Create a temporary project and extract one platform archive. Copy the sample inputs:

```text
examples/quickstart/problem_files/
```

Install dependencies, then run the platform command:

```bash
# Codex
python .agents/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Claude Code
python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Trae
python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

## Expected Boundary

Smoke-test drafts appear only under:

```text
paper_output/quickstart/
```

The run must not create:

```text
paper_output/final_paper_source.md
paper_output/final_paper.docx
```

For a real contest, invoke `$paper-workflow-orchestrator` and execute S0-S8 instead of promoting quickstart output.

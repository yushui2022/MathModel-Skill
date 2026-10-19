# Quickstart Smoke-Test Walkthrough

Quickstart checks installation, basic input parsing, legacy scaffold generation, and Word availability. It is not a competition-paper workflow.

## Prepare

Create a temporary contest project and install the universal archive into one host directory. Copy the sample inputs from the repository:

```text
examples/quickstart/problem_files/
```

Install dependencies. Replace <SKILL_ROOT> with the actual installed skills directory, then run:

```bash
python "<SKILL_ROOT>/paper-workflow-orchestrator/scripts/quickstart_run.py" --project-root "<contest-project>"
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

For a real contest, invoke `paper-workflow-orchestrator` and execute S0-S8 instead of promoting quickstart output.

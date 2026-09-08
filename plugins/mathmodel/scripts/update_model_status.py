#!/usr/bin/env python3
"""Write a small, append-only progress record for the MathModel dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workbench import WorkbenchState


STAGES = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--status", choices=["pending", "running", "passed", "failed", "stale"], required=True)
    parser.add_argument("--message", default="")
    parser.add_argument("--current-task", default="")
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args()

    project = Path(args.project_root).resolve()
    state = WorkbenchState(project)
    state.record_event(args.stage, args.status, args.message, args.current_task, args.artifact)
    print(f"MathModel activity recorded: {project / '.mathmodel' / 'status.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

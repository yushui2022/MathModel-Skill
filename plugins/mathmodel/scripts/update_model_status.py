#!/usr/bin/env python3
"""Write a small, append-only progress record for the MathModel dashboard."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


STAGES = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    state_dir = project / ".mathmodel"
    state_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now()
    event = {
        "timestamp": timestamp,
        "stage": args.stage,
        "status": args.status,
        "message": args.message,
        "current_task": args.current_task,
        "artifacts": args.artifact,
    }

    status_path = state_dir / "status.json"
    previous = {}
    if status_path.exists():
        try:
            previous = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    history = previous.get("history", [])
    history = (history + [event])[-100:]
    payload = {
        "project": project.name,
        "stage": args.stage,
        "stage_index": STAGES.index(args.stage),
        "stage_count": len(STAGES),
        "status": args.status,
        "message": args.message,
        "current_task": args.current_task,
        "artifacts": args.artifact,
        "updated_at": timestamp,
        "history": history,
    }
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (state_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"MathModel status updated: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

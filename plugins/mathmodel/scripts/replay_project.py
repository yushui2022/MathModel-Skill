"""Explicit export/run entry points; no Pro checkpoint approval is created."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from runtime.replay import export_replay, run_replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--project-root", type=Path, required=True)
    export.add_argument("--destination", type=Path, required=True)
    export.add_argument("--allow-input", action="append", default=[])
    run = commands.add_parser("run")
    run.add_argument("--bundle-root", type=Path, required=True)
    run.add_argument("--output-root", type=Path, required=True)
    run.add_argument("--python-executable", type=Path)
    args = parser.parse_args()
    result = (export_replay(args.project_root, args.destination, args.allow_input) if args.command == "export"
              else run_replay(args.bundle_root, args.output_root, args.python_executable))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] in {"PASS", "EXPORTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pro-workflow-orchestrator" / "scripts"))
from pro_contracts import read_json, validate_envelope


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the shared Pro consensus contract.")
    parser.add_argument("--output-root", type=Path, default=Path("paper_output_pro"))
    args = parser.parse_args()
    try:
        from pro_checkpoint import validate_checkpoint_artifacts
        root = args.output_root.resolve()
        errors = validate_checkpoint_artifacts(root.parent, root, "1")
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"[BLOCKED] {error}")
    print("[BLOCKED]" if errors else "[PASS] Shared Pro validation")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

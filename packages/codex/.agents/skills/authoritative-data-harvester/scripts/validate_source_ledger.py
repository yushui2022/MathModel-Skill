from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pro-workflow-orchestrator" / "scripts"))
from pro_contracts import read_json, validate_envelope
from pro_validation import check_sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the shared Pro source contract.")
    parser.add_argument("--ledger", type=Path, default=Path("paper_output_pro/source_ledger.json"))
    args = parser.parse_args()
    try:
        errors = validate_envelope(args.ledger, {"PASS"}) + check_sources(args.ledger.resolve().parent, read_json(args.ledger))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"[BLOCKED] {error}")
    print("[BLOCKED]" if errors else "[PASS] Shared Pro validation")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

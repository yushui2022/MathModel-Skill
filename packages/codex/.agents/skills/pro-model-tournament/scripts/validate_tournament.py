from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pro-workflow-orchestrator" / "scripts"))
from pro_contracts import read_json, validate_envelope
from pro_validation import check_tournament

DIMENSIONS = {"task_fit", "data_feasibility", "validation_strength", "robustness", "interpretability", "innovation_value", "implementation_risk"}
validate = check_tournament


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the shared Pro tournament contract.")
    parser.add_argument("--candidates", type=Path, default=Path("paper_output_pro/candidate_routes.json"))
    parser.add_argument("--report", type=Path, default=Path("paper_output_pro/tournament_report.json"))
    args = parser.parse_args()
    try:
        errors = validate_envelope(args.candidates, {"PASS"}) + validate_envelope(args.report, {"PASS"}) + check_tournament(read_json(args.candidates), read_json(args.report))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"[BLOCKED] {error}")
    print("[BLOCKED]" if errors else "[PASS] Shared Pro validation")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

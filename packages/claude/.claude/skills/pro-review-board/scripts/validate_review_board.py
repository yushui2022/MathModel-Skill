from __future__ import annotations

import argparse
import json
from pathlib import Path


ROLES = {
    "mathematical_correctness",
    "code_reproducibility",
    "source_provenance",
    "paper_expression",
    "adversarial_challenge",
}
BLOCKING = {"CRITICAL", "MAJOR"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Pro five-role review board contract.")
    parser.add_argument("--report", type=Path, default=Path("paper_output_pro/review_board_report.json"))
    args = parser.parse_args()
    errors: list[str] = []
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report = {}
        errors.append(str(exc))
    rounds = report.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        errors.append("review_board_report.json requires at least one complete round")
    else:
        for index, round_data in enumerate(rounds, 1):
            reviews = round_data.get("reviews") if isinstance(round_data, dict) else None
            found_roles = {review.get("role") for review in reviews or [] if isinstance(review, dict)}
            if found_roles != ROLES:
                errors.append(f"round {index}: expected exactly five independent roles, found {sorted(found_roles)}")
            for review in reviews or []:
                if not review.get("isolated_context"):
                    errors.append(f"round {index}/{review.get('role')}: isolated_context must be true")
                for finding in review.get("findings") or []:
                    if finding.get("severity") not in {"CRITICAL", "MAJOR", "MINOR", "NOTE"}:
                        errors.append(f"round {index}/{review.get('role')}: invalid finding severity")
                    if not finding.get("finding_id") or not finding.get("evidence") or not finding.get("disposition"):
                        errors.append(f"round {index}/{review.get('role')}: incomplete finding record")
        final_reviews = rounds[-1].get("reviews", []) if isinstance(rounds[-1], dict) else []
        blocking = [
            finding
            for review in final_reviews
            for finding in review.get("findings", [])
            if finding.get("severity") in BLOCKING and finding.get("disposition") != "RESOLVED"
        ]
        if blocking:
            errors.append(f"final review round has {len(blocking)} unresolved Critical/Major findings")
    if report.get("status") != "PASS":
        errors.append("review board status must be PASS")
    for error in errors:
        print(f"[FAIL] {error}")
    if errors:
        return 1
    print("[PASS] Five-role Pro review board has no unresolved Critical/Major findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

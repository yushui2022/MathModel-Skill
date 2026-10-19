"""Prepare isolated review requests or collect their current, hash-bound reports."""
from __future__ import annotations

import argparse
from pathlib import Path

from pro_contracts import contract, output_root, read_json, sha256_file, write_json
from pro_validation import REVIEW_ROLES, check_review, review_inputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    if args.round < 1:
        parser.error("round must be positive")
    root = output_root(args.project_root)
    try:
        from pro_authoring_policy import read_policy
        inputs = review_inputs(root)
        questions = read_json(root / "problem_consensus.json")["subproblems"] if read_policy(root)["mode"] == "competition" else []
        directory = root / "reviews" / f"round-{args.round}"
        directory.mkdir(parents=True, exist_ok=True)
        reports = []
        for role in sorted(REVIEW_ROLES):
            path = directory / f"{role}.json"
            if args.prepare:
                if not path.exists():
                    write_json(path, contract(producer_role=role, status="PENDING", input_hashes=inputs,
                        role=role, isolated_context=False, execution={}, checks_performed=[], assessment="", findings=[],
                        subproblem_assessments=[{"subproblem_id": q["subproblem_id"], "verdict": "PENDING", "evidence": ""} for q in questions]))
            else:
                reports.append({"role": role, "report_path": path.relative_to(root).as_posix(),
                                "report_sha256": sha256_file(path)})
        if args.prepare:
            print(f"Prepared review requests: {directory}")
            return 0
        path = root / "review_board_report.json"
        previous = read_json(path).get("rounds", []) if path.exists() else []
        if any(r.get("round", 0) > args.round for r in previous):
            raise ValueError("cannot replace a round older than the latest collected round")
        rounds = [r for r in previous if r.get("round") != args.round]
        rounds.append({"round": args.round, "input_hashes": inputs, "reviews": reports})
        report = contract(producer_role="pro-review-chair", status="PASS", input_hashes=inputs, rounds=rounds)
        errors = check_review(root, report)
        if errors:
            report["status"] = "BLOCKED"
            report["errors"] = errors
        write_json(path, report)
        print("\n".join(errors) if errors else "Review board PASS")
        return int(bool(errors))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

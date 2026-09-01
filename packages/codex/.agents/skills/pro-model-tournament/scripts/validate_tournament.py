from __future__ import annotations

import argparse
import json
from pathlib import Path


DIMENSIONS = {
    "task_fit",
    "data_feasibility",
    "validation_strength",
    "robustness",
    "interpretability",
    "innovation_value",
    "implementation_risk",
}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def validate(candidates: dict, report: dict) -> list[str]:
    errors: list[str] = []
    subproblems = candidates.get("subproblems")
    decisions = report.get("decisions")
    if not isinstance(subproblems, list) or not subproblems:
        return ["candidate_routes.json requires non-empty subproblems[]"]
    if not isinstance(decisions, list):
        decisions = []
        errors.append("tournament_report.json requires decisions[]")
    decision_by_id = {item.get("subproblem_id"): item for item in decisions if isinstance(item, dict)}

    for subproblem in subproblems:
        subproblem_id = subproblem.get("subproblem_id")
        routes = subproblem.get("routes")
        if not subproblem_id or not isinstance(routes, list):
            errors.append("each subproblem needs subproblem_id and routes[]")
            continue
        if not 3 <= len(routes) <= 5:
            errors.append(f"{subproblem_id}: requires 3-5 routes, found {len(routes)}")
        route_ids = [route.get("route_id") for route in routes if isinstance(route, dict)]
        if len(set(route_ids)) != len(routes) or None in route_ids:
            errors.append(f"{subproblem_id}: route_id values must be unique and non-empty")
        if not any(route.get("is_interpretable_baseline") is True for route in routes if isinstance(route, dict)):
            errors.append(f"{subproblem_id}: missing interpretable baseline")
        for route in routes:
            if not isinstance(route, dict):
                errors.append(f"{subproblem_id}: route must be an object")
                continue
            if not route.get("model_family") or not route.get("experiment_plan") or not route.get("expected_evidence"):
                errors.append(f"{subproblem_id}/{route.get('route_id')}: incomplete route rationale")
            scores = route.get("scores")
            if not isinstance(scores, dict) or set(scores) != DIMENSIONS:
                errors.append(f"{subproblem_id}/{route.get('route_id')}: scores must contain exactly {sorted(DIMENSIONS)}")
            elif any(not isinstance(value, (int, float)) or not 0 <= value <= 10 for value in scores.values()):
                errors.append(f"{subproblem_id}/{route.get('route_id')}: scores must be numbers in [0, 10]")

        decision = decision_by_id.get(subproblem_id)
        if not decision:
            errors.append(f"{subproblem_id}: missing tournament decision")
            continue
        selected = decision.get("selected_route_id")
        backup = decision.get("backup_route_id")
        if selected not in route_ids or backup not in route_ids or selected == backup:
            errors.append(f"{subproblem_id}: selected and backup routes must be distinct valid route IDs")
        rejected = decision.get("rejected_routes")
        rejected_ids = {item.get("route_id") for item in rejected or [] if isinstance(item, dict) and item.get("reason")}
        expected_rejected = set(route_ids) - {selected, backup}
        if rejected_ids != expected_rejected:
            errors.append(f"{subproblem_id}: every non-selected/non-backup route needs a rejection reason")
        if not decision.get("recommended_experiment_plan") or not decision.get("implementation_risks"):
            errors.append(f"{subproblem_id}: missing experiment plan or implementation risks")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Pro route tournament contracts.")
    parser.add_argument("--candidates", type=Path, default=Path("paper_output_pro/candidate_routes.json"))
    parser.add_argument("--report", type=Path, default=Path("paper_output_pro/tournament_report.json"))
    args = parser.parse_args()
    try:
        errors = validate(load(args.candidates), load(args.report))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f"[FAIL] {error}")
    if errors:
        return 1
    print("[PASS] Pro model tournament contracts are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

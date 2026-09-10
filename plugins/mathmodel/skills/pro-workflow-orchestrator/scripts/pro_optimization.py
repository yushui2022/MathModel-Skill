"""Explicit M3 companion contract; legacy Pro 3.3 is not silently upgraded."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from pro_contracts import (approval_is_fresh, check_hashes, read_json, safe_path,
                           sha256_file)

_path = Path(__file__).resolve().parents[2] / "quality-assurance-auditor" / "scripts" / "check_optimization_spec.py"
_loader = importlib.util.spec_from_file_location("mathmodel_independent_optimization", _path)
assert _loader and _loader.loader
checker = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(checker)

PROFILE = "linear-v1"
DECLARATION = "optimization_applicability.json"
SOURCES = ("problem_consensus.json", "candidate_routes.json", "tournament_report.json")


def enabled(root: Path) -> bool:
    return read_json(root / "pro_config.json").get("optimization_check_profile") is not None


def _declaration(root: Path) -> tuple[dict, dict, dict]:
    config = read_json(root / "pro_config.json")
    if config.get("optimization_check_profile") != PROFILE:
        raise ValueError("MIGRATION_REQUIRED: enable optimization_check_profile='linear-v1' before fresh checkpoint 1/2 decisions; legacy Pro approval is not M3 approval")
    declaration = checker.load_json(root / DECLARATION)
    checker.fields(declaration, {"schema_version", "profile", "input_hashes", "routes"}, DECLARATION)
    if declaration["schema_version"] != checker.SCHEMA_VERSION or declaration["profile"] != PROFILE:
        raise ValueError("unsupported M3 applicability schema/profile")
    expected = {name: sha256_file(root / name) for name in SOURCES}
    if declaration["input_hashes"] != expected:
        raise ValueError("M3 applicability is stale for consensus, candidates or tournament")
    consensus = read_json(root / SOURCES[0])
    questions = {row["subproblem_id"] for row in consensus["subproblems"]}
    candidates = read_json(root / SOURCES[1])
    candidate_questions = {row["subproblem_id"] for row in candidates["subproblems"]}
    if candidate_questions != questions:
        raise ValueError("M3 candidates must cover all confirmed subproblems")
    roster = {}
    for question in candidates["subproblems"]:
        for route in question["routes"]:
            if route["route_id"] in roster:
                raise ValueError("M3 requires globally unique route_id values")
            roster[route["route_id"]] = (question["subproblem_id"], route)
    decisions = read_json(root / SOURCES[2])["decisions"]
    if {row["subproblem_id"] for row in decisions} != questions:
        raise ValueError("M3 tournament does not cover every confirmed question")
    for decision in decisions:
        for key in ("selected_route_id", "backup_route_id"):
            if decision[key] not in roster or roster[decision[key]][0] != decision["subproblem_id"]:
                raise ValueError("M3 tournament references an unknown or cross-question route")
    bindings, specs, hashes = {}, {}, {DECLARATION: sha256_file(root / DECLARATION)}
    for entry in checker.rows(declaration["routes"], "applicability/routes"):
        checker.fields(entry, {"subproblem_id", "route_id", "scope", "spec_path", "rationale"}, "applicability route")
        route_id = entry["route_id"]
        if route_id not in roster or route_id in bindings or entry["subproblem_id"] != roster[route_id][0]:
            raise ValueError("M3 has duplicate, unknown or cross-question applicability route")
        if type(entry["rationale"]) is not str or len(entry["rationale"].strip()) < 40:
            raise ValueError(f"{route_id}: applicability requires a substantive rationale (40+ characters)")
        if entry["scope"] not in ("LP", "MILP", "outside_scope"):
            raise ValueError(f"{route_id}: unknown applicability scope")
        bindings[route_id] = entry
        if entry["scope"] == "outside_scope":
            if entry["spec_path"] is not None:
                raise ValueError(f"{route_id}: outside_scope cannot hide a specification")
            # This detects an explicit contradiction; it does not claim to classify arbitrary prose.
            family = str(roster[route_id][1].get("model_family", "")).strip().casefold().replace("-", " ")
            if family in {"lp", "milp", "linear programming", "mixed integer linear programming", "线性规划", "混合整数线性规划", "整数线性规划"}:
                raise ValueError(f"{route_id}: outside_scope contradicts the approved linear model family")
            continue
        path = safe_path(root, entry["spec_path"])
        if not path.is_relative_to((root / "optimization_specs").resolve()) or path.suffix != ".json":
            raise ValueError("M3 specifications must be JSON files under optimization_specs/")
        spec = checker.load_json(path)
        checker.validate_spec(spec)
        if (spec["route_id"] != route_id or spec["subproblem_id"] != entry["subproblem_id"]
                or spec["model_class"] != entry["scope"]):
            raise ValueError(f"{route_id}: specification identity/scope differs from applicability")
        input_errors = check_hashes(root, spec["input_hashes"])
        if input_errors:
            raise ValueError("; ".join(input_errors))
        for name, digest in spec["input_hashes"].items():
            if not any(safe_path(root, name).is_relative_to((root / directory).resolve()) for directory in ("data_cleaned", "research")):
                raise ValueError("M3 spec inputs must be frozen files under data_cleaned/ or research/")
            hashes[name] = digest
        hashes[entry["spec_path"]] = sha256_file(path)
        specs[route_id] = (spec, entry["spec_path"])
    if set(bindings) != set(roster):
        raise ValueError("M3 applicability must cover every candidate route, including rejected routes")
    actual_specs = {p.relative_to(root).as_posix() for p in (root / "optimization_specs").rglob("*") if p.is_file()}
    declared_specs = {entry["spec_path"] for entry in bindings.values() if entry["spec_path"] is not None}
    if actual_specs != declared_specs:
        raise ValueError("unregistered or missing optimization specification; relabeling a route cannot suppress a spec")
    return bindings, specs, hashes


def approval_hashes(root: Path) -> dict[str, str]:
    """P2 dependencies, computed before approval and on every freshness check."""
    return _declaration(root)[2]


def validate_preapproval(root: Path) -> list[str]:
    try:
        _declaration(root)
        return []
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [f"M3: {exc}"]


def inspect_delivery(root: Path) -> dict:
    report = {"schema_version": checker.SCHEMA_VERSION, "profile": PROFILE,
              "status": "BLOCKED", "errors": [], "runs": [], "outside_scope_routes": [],
              "coverage": "declared LP/MILP only; applicability and natural-language fit require checkpoint review"}
    try:
        bindings, specs, dependencies = _declaration(root)
        ledger = read_json(root / "checkpoint_ledger.json")
        approval = ledger.get("checkpoints", {}).get("2", {})
        if approval.get("status") != "APPROVED" or not approval_is_fresh(root, approval):
            raise ValueError("M3 requires fresh checkpoint 2 approval")
        if any(approval.get("artifact_hashes", {}).get(name) != digest for name, digest in dependencies.items()):
            raise ValueError("MIGRATION_REQUIRED: checkpoint 2 did not approve the M3 applicability/specification/data hashes")
        # Enforce the entire current P2 object set, not only the companion hashes.
        from pro_contracts import checkpoint_hashes
        if approval.get("artifact_hashes") != checkpoint_hashes(root, "2"):
            raise ValueError("M3 checkpoint 2 approval is stale or has a different dependency set")
        from pro_validation import receipts
        runs, run_errors = receipts(root, read_json(root / "experiment_manifest.json"))
        report["errors"].extend(run_errors)
        visited = set()
        for run_id, run in runs.items():
            route_id = run.get("route_id")
            if route_id not in bindings:
                report["errors"].append(f"{run_id}: experiment route has no approved M3 applicability")
                continue
            result_name = f"experiments/{run_id}/optimization_result.json"
            result_path = safe_path(root, result_name)
            if route_id not in specs:
                if result_path.exists():
                    report["errors"].append(f"{run_id}: outside_scope route produced an optimization result; review applicability")
                continue
            if run.get("status") != "PASS":
                continue
            spec, spec_name = specs[route_id]
            spec_hash = dependencies[spec_name]
            if run.get("input_hashes", {}).get(spec_name) != spec_hash:
                report["errors"].append(f"{run_id}: approved specification was not a hashed experiment input")
            if any(run.get("input_hashes", {}).get(name) != digest for name, digest in spec["input_hashes"].items()):
                report["errors"].append(f"{run_id}: frozen specification data were not hashed experiment inputs")
            if not result_path.is_file() or run.get("output_hashes", {}).get(result_name) != sha256_file(result_path):
                report["errors"].append(f"{run_id}: missing or unrecorded optimization_result.json")
                continue
            result = checker.load_json(result_path)
            if result.get("run_id") != run_id:
                report["errors"].append(f"{run_id}: solution has a different run identity")
            checked = checker.check_solution(spec, result, spec_sha256=spec_hash)
            metrics = read_json(safe_path(root, run.get("metrics_file", ""))).get("metrics", {})
            metric_name = spec["objective"]["metric"]
            measured = checker.number(metrics.get(metric_name), f"{run_id}/metrics/{metric_name}")
            reported = checker.number(result.get("reported_objective"), f"{run_id}/reported_objective")
            if abs(measured-reported) > checker.objective_tolerance(measured, reported):
                report["errors"].append(f"{run_id}: recorded objective metric {metric_name} differs from independently checked solution")
            report["runs"].append({"run_id": run_id, "route_id": route_id, "report": checked})
            visited.add(route_id)
            if checked["status"] != "PASS":
                report["errors"].append(f"{run_id}: independent optimization check {checked['status']}: " + "; ".join(e["code"]+" at "+e.get("location", "") for e in checked["errors"]))
        selected = {row["selected_route_id"] for row in read_json(root / "tournament_report.json")["decisions"]}
        for route_id in selected & set(specs) - visited:
            report["errors"].append(f"{route_id}: selected linear route has no checked successful execution")
        report["outside_scope_routes"] = sorted(set(bindings)-set(specs))
        report["input_hashes"] = dependencies
        if not report["errors"]:
            report["status"] = "PASS" if specs else "NOT_APPLICABLE"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        report["errors"].append(f"M3: {exc}")
    return report


def validate_delivery(root: Path) -> list[str]:
    return inspect_delivery(root)["errors"]


def main() -> int:
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Read-only M3 companion gate; never grants checkpoint approval")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--preapproval", action="store_true")
    args = parser.parse_args()
    from pro_contracts import output_root
    root = output_root(args.project_root)
    report = ({"errors": validate_preapproval(root), "scope": "preapproval_only"}
              if args.preapproval else inspect_delivery(root))
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())

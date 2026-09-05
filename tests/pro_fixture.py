"""Executable integration fixtures. Synthetic role/approval records are NOT model evaluations."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "packages/claude/.claude/skills"
SCRIPTS = SKILLS / "pro-workflow-orchestrator/scripts"
sys.path.insert(0, str(SCRIPTS))
from pro_contracts import contract, read_json, sha256_file, write_json
from pro_validation import DIMENSIONS, REVIEW_ROLES, review_inputs


def run(script, *args, cwd=REPO, check=True):
    result = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=cwd, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if check and result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


def envelope(producer, **kwargs):
    return contract(producer_role=producer, status="PASS", **kwargs)


def prepare(project: Path, model="gpt-6-astra") -> Path:
    problem = project / "problem_files"
    problem.mkdir(parents=True, exist_ok=True)
    (problem / "task.md").write_text("# Capacitated distribution design\nChoose depots and assign each demand point to one depot. Compare all-open operation and a 20 percent demand stress. Minimize opening plus delivery cost.\n", encoding="utf-8")
    shutil.copyfile(REPO / "tests/fixtures/forward/optimization/facility_data.json", problem / "data.json")
    run(SCRIPTS / "pro_preflight.py", "--project-root", project, "--platform", "codex", "--model", model, "--reasoning", "ultra")
    root = project / "paper_output_pro"
    complete_consensus(root)
    return root


def complete_consensus(root: Path):
    inventory = read_json(root / "instruction_manifest.json")
    write_json(root / "instruction_audit.json", envelope("fixture-instruction-audit",
        instruction_manifest_sha256=sha256_file(root / "instruction_manifest.json"),
        reviewed_files=[{"locator": f["locator"], "sha256": f["sha256"]} for f in inventory["files"]],
        conflicts=[], unresolved_conflicts=[], active_execution_contract=inventory["required_execution_contract"]))
    analyses = []
    for index in range(3):
        path = root / "analysis/independent" / f"reader-{index}.json"
        write_json(path, envelope(f"fixture-reader-{index}", isolated_context=True,
            summary=["binary assignment and capacity", "known demand and costs", "baseline and demand stress"][index]))
        analyses.append({"role_id": f"reader-{index}", "path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    write_json(root / "problem_consensus.json", envelope("fixture-consensus", independent_analyses=analyses,
        consensus=["minimize fixed and variable distribution cost"], disagreements=[], assumptions=["single depot per demand point"],
        subproblems=[{"subproblem_id": "q1"}], attachment_roles=[{"path": f["path"], "role": f["role"]} for f in read_json(root / "input_manifest.json")["files"]]))


def approve(project: Path, number: int):
    return run(SCRIPTS / "pro_checkpoint.py", "approve", "--checkpoint", number, "--decision", "AUTOMATED TEST FIXTURE decision; not a real user approval", "--project-root", project)


def candidates():
    return envelope("fixture-routes", weights={d: 1 / 7 for d in sorted(DIMENSIONS)}, subproblems=[{
        "subproblem_id": "q1", "routes": [{"route_id": f"r{i}", "model_family": family,
            "is_interpretable_baseline": i == 1, "scores": {d: 7 for d in DIMENSIONS},
            "experiment_plan": "Solve and test objective and capacity feasibility", "expected_evidence": "objective and assignment"}
            for i, family in enumerate(["all-open assignment", "mixed integer programming", "complete enumeration", "greedy assignment"], 1)]}])


def tournament():
    return envelope("fixture-tournament", decisions=[{"subproblem_id": "q1", "selected_route_id": "r2", "backup_route_id": "r3",
        "rejected_routes": [{"route_id": "r1", "reason": "retained as operating baseline"}, {"route_id": "r4", "reason": "no global optimality certificate"}],
        "recommended_experiment_plan": "independent exhaustive validation", "implementation_risks": ["integer formulation error"]}],
        comparison_rules={key: {"kind": "numeric", "atol": 1e-7, "rtol": 1e-9} for key in ("Ecost", "Ebaseline", "Estress")})


def prepare_evidence(project: Path) -> Path:
    from pro_run_experiment import execute, refresh_manifest
    root = prepare(project)
    approve(project, 1)
    write_json(root / "source_ledger.json", envelope("fixture-sources", sources=[], critical_claims=[]))
    write_json(root / "candidate_routes.json", candidates())
    write_json(root / "tournament_report.json", tournament())
    approve(project, 2)
    for name in ("solve_milp.py", "solve_enumeration.py"):
        shutil.copyfile(REPO / "tests/fixtures/forward/optimization" / name, root / "code" / name)
    shutil.copyfile(project / "problem_files/data.json", root / "data_cleaned/data.json")
    values = {}
    for scenario, extra in (("base", []), ("baseline", ["--all-open"]), ("stress", ["--scale", "1.2"])):
        for implementation, name in (("milp", "solve_milp.py"), ("enum", "solve_enumeration.py")):
            run_id = f"{scenario}-{implementation}"
            spec_path = root / "code" / f"spec-{run_id}.json"
            write_json(spec_path, {"run_id": run_id, "route_id": "r2" if implementation == "milp" else "r3",
                "implementation_id": implementation, "script": f"code/{name}", "inputs": ["data_cleaned/data.json"],
                "args": ["--input", "data_cleaned/data.json", "--out", "{run_dir}", *extra]})
            _, success = execute(project, spec_path)
            assert success, run_id
            values[run_id] = read_json(root / "experiments" / run_id / "metrics.json")["metrics"]
    refresh_manifest(root)
    results = []
    for result_id, scenario in (("Ecost", "base"), ("Ebaseline", "baseline"), ("Estress", "stress")):
        results.append({"result_id": result_id, "replication_paths": [{"run_id": f"{scenario}-{impl}", "metric": "cost"} for impl in ("milp", "enum")],
            "comparison_rule": tournament()["comparison_rules"][result_id], "agreement_status": "PASS",
            "independence_rationale": "HiGHS MILP versus full assignment enumeration without shared computation code"})
    write_json(root / "replication_report.json", envelope("fixture-replication", critical_results=results))
    def measurement(run_id):
        return {"run_id": run_id, "metric": "cost", "value": values[run_id]["cost"]}
    write_json(root / "robustness_report.json", envelope("fixture-robustness",
        baseline_comparisons=[{"test_id": "all-open", "interpretation": "cost of keeping every depot open", "measurements": [measurement("base-milp"), measurement("baseline-milp")]}],
        sensitivity_tests=[{"test_id": "demand", "interpretation": "20 percent higher demand", "measurements": [measurement("base-milp"), measurement("stress-milp")]}],
        constraint_stress_tests=[{"test_id": "capacity", "interpretation": "demand stress", "feasibility_assessment": "all assignments satisfy depot capacities", "measurements": [measurement("stress-milp")]}], stochastic_methods=[]))
    write_json(root / "ablation_report.json", envelope("fixture-ablation", ablations=[], not_applicable_reason="No separable learned components; all-open intervention is the baseline experiment."))
    claims = []
    for claim_id, evidence, run_id in (("Ccost", "Ecost", "base-milp"), ("Cbaseline", "Ebaseline", "baseline-milp"), ("Cstress", "Estress", "stress-milp")):
        claims.append({"claim_id": claim_id, "statement": f"Verified objective for {run_id}", "section_id": "results",
            "evidence_ids": [evidence], "external": False, "source_ids": [],
            "numeric_evidence": [{"run_id": run_id, "metric": "cost", "decimals": 2, "display": f"{values[run_id]['cost']:.2f}"}]})
    write_json(root / "claim_evidence_map.json", envelope("fixture-claims", claims=claims))
    approve(project, 3)
    run(SCRIPTS / "pro_freeze_evidence.py", "--project-root", project)
    return root


def write_test_paper(root: Path):
    sections = [
        ("abstract", "Abstract", "We investigate a small capacitated distribution system with discrete opening decisions and indivisible customer assignments. The objective combines fixed operating charges and demand-weighted delivery costs. Exact optimization and independent exhaustive enumeration provide two computational paths with different failure modes. The study compares the selected layout against all-open operation and reoptimizes under increased demand. This constructed instance tests reproducibility and is not an empirical claim about a real logistics company."),
        ("model", "Model", "Each customer is served by one open depot. Assignment variables and opening variables are binary. A depot cannot serve more than its declared capacity, and demand is treated as known within each scenario. We minimize the sum of opening charges and delivery expenditures. The model excludes time windows, vehicle routing and disruptions, so the conclusions apply to aggregate allocation rather than detailed dispatch schedules.\n\n$$z=\\sum_j f_j y_j+\\sum_j\\sum_i c_{ji} d_i x_{ji}$$"),
        ("methods", "Methods", "The primary implementation builds a mixed integer program and obtains both an incumbent objective and a dual bound. The verification implementation enumerates all depot assignments, computes loads directly and rejects infeasible combinations. It does not import the primary solver or share its constraint construction. Agreement therefore checks both the objective calculation and the formulation on a tractable instance, although it does not prove the model captures every practical condition."),
        ("results", "Results", "The independent implementations agree within the preregistered absolute and relative tolerances. Every feasible candidate remains available to the exhaustive search, including alternatives that do not improve the incumbent. The comparison below separates the optimized base scenario, the operating baseline with all depots open, and the demand stress scenario. These costs have the same accounting scope and may therefore be compared directly."),
        ("limits", "Limitations", "The exactness claim is restricted to the constructed finite instance and stated single-depot assignment assumption. Real deployments require calibrated demand, comparable cost units, service-level constraints and observation of disruption risk. Demand stress here represents a scenario intervention, not a probabilistic confidence interval. Reoptimization allows the depot decisions to change; it must not be interpreted as robustness of a fixed installed network. Scaling the demand continuously may also change which capacity constraints bind."),
        ("conclusion", "Conclusion", "The experiment demonstrates that explicit fixed costs and capacity limits affect facility selection. Independent exhaustive enumeration provides a useful verification method for small systems, while integer optimization supports larger instances. A defensible recommendation must report feasibility and its assumptions alongside the objective. The next empirical step is to obtain actual demand and operating records and test whether the same formulation retains predictive and operational value."),
    ]
    text = "# Capacitated Distribution Design\n\n"
    for identifier, title, paragraph in sections:
        text += f"## {title}\n\n{paragraph}\n\n"
        if identifier == "results":
            for claim in read_json(root / "claim_evidence_map.json")["claims"]:
                text += f"The objective for {claim['numeric_evidence'][0]['run_id']} is {claim['numeric_evidence'][0]['display']}. <!-- claim:{claim['claim_id']} -->\n\n"
    (root / "final_paper_source.md").write_text(text, encoding="utf-8")
    write_json(root / "paper_plan.json", envelope("fixture-paper-plan", title="Capacitated Distribution Design", language="en",
        target_characters=2500, sections=[{"section_id": i, "title": t, "minimum_characters": 100} for i, t, _ in sections], figures=[]))


def write_test_reviews(root: Path):
    inputs = review_inputs(root)
    reports = []
    for role in sorted(REVIEW_ROLES):
        record = root / "reviews" / f"fixture-{role}.txt"
        record.write_text("SYNTHETIC TEST RECORD: validates schema plumbing only; no independent model review occurred.\n", encoding="utf-8")
        path = root / "reviews" / f"{role}.json"
        write_json(path, envelope("fixture-reviewer", role=role, input_hashes=inputs, isolated_context=True,
            execution={"mode": "fresh-session", "context_id": f"fixture-{role}", "model": "synthetic-test-fixture",
                "record_path": record.relative_to(root).as_posix(), "record_sha256": sha256_file(record)},
            checks_performed=["synthetic schema validation"], assessment="Synthetic passing reviewer for integration tests", findings=[]))
        reports.append({"role": role, "report_path": path.relative_to(root).as_posix(), "report_sha256": sha256_file(path)})
    write_json(root / "review_board_report.json", envelope("fixture-chair", input_hashes=inputs, rounds=[{"round": 1, "input_hashes": inputs, "reviews": reports}]))


def write_test_visual(root: Path):
    render = read_json(root / "render_manifest.json")
    write_json(root / "visual_review.json", envelope("fixture-visual-review", render_manifest_sha256=sha256_file(root / "render_manifest.json"),
        pages=[{"page": p["page"], "image_sha256": p["sha256"], "status": "PASS", "issues": [], "observations": "Synthetic visual-review fixture; not a human or model inspection"} for p in render["pages"]]))


def complete(project: Path) -> Path:
    root = prepare_evidence(project)
    write_test_paper(root)
    write_test_reviews(root)
    run(SKILLS / "paper-formal-writer/scripts/format_formal_docx.py", cwd=project)
    run(SCRIPTS / "pro_render_pdf.py", cwd=project)
    write_test_visual(root)
    run(SCRIPTS / "pro_format_check.py", "--project-root", project)
    run(SCRIPTS / "pro_gate.py", "--project-root", project)
    return root

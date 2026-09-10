from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "packages/claude/.claude/skills/pro-workflow-orchestrator/scripts"
sys.path.insert(0, str(SCRIPTS))
import pro_optimization as gate
from pro_contracts import canonical_json_hash, checkpoint_hashes, contract, sha256_file, write_json

check = gate.checker


def specification():
    return {"schema_version": "1.0", "profile": "linear-v1", "problem_id": "contest",
            "subproblem_id": "q1", "route_id": "r1", "model_class": "LP",
            "input_hashes": {"data_cleaned/input.csv": "a" * 64},
            "variables": [{"id": "x", "unit": "units", "domain": "continuous", "lower": 0, "upper": 10}],
            "objective": {"sense": "max", "unit": "revenue", "metric": "objective", "constant": 1, "coefficients": {"x": 2}},
            "constraints": [{"id": "capacity", "unit": "units", "coefficients": {"x": 1}, "sense": "le", "rhs": 4}],
            "tolerances": dict(check.TOLERANCES)}


def solution():
    return {"schema_version": "1.0", "spec_sha256": "b" * 64, "run_id": "run1", "values": {"x": 4},
            "reported_objective": 9, "claim": "feasible", "certificate": None}


class ArithmeticTests(unittest.TestCase):
    def codes(self, result):
        return {error["code"] for error in result["errors"]}

    def test_valid_solution_and_independent_objective(self):
        report = check.check_solution(specification(), solution())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["objective"], 9)
        self.assertEqual(report["optimality"], "NOT_CLAIMED")

    def test_capacity_error_has_constraint_id(self):
        result = solution()
        result["values"]["x"] = 5
        result["reported_objective"] = 11
        report = check.check_solution(specification(), result)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["max_constraint_violation"], 1)
        self.assertIn("constraints/capacity", [error["location"] for error in report["errors"]])

    def test_fractional_integer_and_binary_are_detected(self):
        for domain in ("integer", "binary"):
            spec, result = specification(), solution()
            spec["model_class"] = "MILP"
            spec["variables"][0]["domain"] = domain
            if domain == "binary":
                spec["variables"][0]["upper"] = 1
            result["values"]["x"] = 0.5
            result["reported_objective"] = 2
            self.assertIn("INTEGRALITY_VIOLATION", self.codes(check.check_solution(spec, result)))

    def test_bounds_and_equalities_and_ge_are_recomputed(self):
        for sense in ("eq", "ge"):
            spec, result = specification(), solution()
            spec["constraints"][0]["sense"] = sense
            result["values"]["x"] = -1
            result["reported_objective"] = -1
            codes = self.codes(check.check_solution(spec, result))
            self.assertIn("BOUND_VIOLATION", codes)
            self.assertIn("CONSTRAINT_VIOLATION", codes)

    def test_objective_error_detected_even_if_feasible(self):
        result = solution()
        result["reported_objective"] = 10
        report = check.check_solution(specification(), result)
        self.assertEqual(report["feasibility"], "PASS")
        self.assertIn("OBJECTIVE_MISMATCH", self.codes(report))

    def test_optimal_without_certificate_is_unknown(self):
        result = solution()
        result["claim"] = "optimal"
        report = check.check_solution(specification(), result)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["optimality"], "UNSUPPORTED")

    def test_verified_dual_certificate_for_lp_and_milp(self):
        for kind in ("LP", "MILP"):
            spec, result = specification(), solution()
            spec["model_class"] = kind
            if kind == "MILP":
                spec["variables"][0]["domain"] = "integer"
            result.update(claim="optimal", certificate={"kind": "lagrangian_bound", "multipliers": {"capacity": 2}})
            report = check.check_solution(spec, result)
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["optimality"], "CERTIFIED_WITHIN_TOLERANCE")
            self.assertEqual(report["verified_absolute_gap"], 0)

    def test_loose_bound_does_not_prove_optimality(self):
        result = solution()
        result.update(claim="optimal", certificate={"kind": "lagrangian_bound", "multipliers": {"capacity": 0}})
        self.assertEqual(check.check_solution(specification(), result)["status"], "UNKNOWN")

    def test_negative_multiplier_cannot_forge_bound(self):
        result = solution()
        result.update(claim="optimal", certificate={"kind": "lagrangian_bound", "multipliers": {"capacity": -2}})
        self.assertEqual(check.check_solution(specification(), result)["status"], "UNKNOWN")

    def test_unbounded_reduced_cost_must_be_exactly_zero(self):
        spec, result = specification(), solution()
        spec["variables"][0]["upper"] = None
        result.update(claim="optimal", certificate={"kind": "lagrangian_bound", "multipliers": {"capacity": 1.99999999999}})
        self.assertEqual(check.check_solution(spec, result)["optimality"], "UNSUPPORTED")

    def test_solver_status_is_not_an_optimality_certificate(self):
        result = solution()
        result.update(claim="optimal", certificate={"kind": "solver_status", "status": "optimal", "gap": 0})
        self.assertEqual(check.check_solution(specification(), result)["status"], "UNKNOWN")

    def test_fixed_tolerances_cannot_be_relaxed(self):
        spec = specification()
        spec["tolerances"]["feasibility_absolute"] = 100
        self.assertEqual(check.check_solution(spec, solution())["status"], "INVALID")

    def test_strict_schema_rejects_unknown_field_boolean_nan_and_missing_variable(self):
        for mutate in (lambda value: value.update(feasibility=True),
                       lambda value: value["values"].update(x=True),
                       lambda value: value["values"].update(x=float("nan")),
                       lambda value: value["values"].clear()):
            result = solution()
            mutate(result)
            self.assertEqual(check.check_solution(specification(), result)["status"], "INVALID")

    def test_duplicate_ids_and_nonfinite_coefficients_rejected(self):
        for mutate in (lambda spec: spec["variables"].append(dict(spec["variables"][0])),
                       lambda spec: spec["objective"]["coefficients"].update(x=float("inf")),
                       lambda spec: spec["constraints"][0]["coefficients"].update(unknown=1)):
            spec = specification()
            mutate(spec)
            self.assertEqual(check.check_solution(spec, solution())["status"], "INVALID")

    def test_wrong_spec_hash_rejected(self):
        self.assertEqual(check.check_solution(specification(), solution(), spec_sha256="c"*64)["status"], "INVALID")

    def test_minimization_ge_and_equality_certificates(self):
        for sense, multiplier in (("ge", 2), ("eq", -2)):
            spec, result = specification(), solution()
            spec["objective"]["sense"] = "min"
            spec["constraints"][0]["sense"] = sense
            result.update(claim="optimal", certificate={"kind": "lagrangian_bound", "multipliers": {"capacity": multiplier}})
            report = check.check_solution(spec, result)
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["verified_objective_bound"], 9)

    def test_verified_bounds_respect_exhaustively_enumerated_integer_optimum(self):
        spec = specification()
        spec["model_class"] = "MILP"
        spec["variables"] = [{"id": key, "unit": "units", "domain": "integer", "lower": 0, "upper": bound}
                             for key, bound in (("x", 3), ("y", 4))]
        spec["objective"].update(sense="min", constant=0, coefficients={"x": 2, "y": -3})
        spec["constraints"][0]["coefficients"] = {"x": 1, "y": 1}
        actual_minimum = min(2*x-3*y for x in range(4) for y in range(5) if x+y <= 4)
        parsed = check.validate_spec(spec)
        for multiplier in (0, 0.5, 1, 2, 3, 10):
            bound = check.dual_bound(parsed, {"kind": "lagrangian_bound", "multipliers": {"capacity": multiplier}})
            self.assertLessEqual(bound, actual_minimum)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        cache = Path(os.environ.get("MATHMODEL_TEST_TMP", "G:/DevCache/Temp/mathmodel-insert/optimization-tests"))
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.root = self.project / "paper_output_pro"
        self.root.mkdir()
        self.write("pro_config.json", {"optimization_check_profile": "linear-v1"})
        self.write("problem_consensus.json", {"subproblems": [{"subproblem_id": "q1"}]})
        self.write("candidate_routes.json", {"subproblems": [{"subproblem_id": "q1", "routes": [
            {"route_id": "r1", "model_family": "LP"}, {"route_id": "r2", "model_family": "simulation"}]}]})
        self.write("tournament_report.json", {"decisions": [{"subproblem_id": "q1", "selected_route_id": "r1", "backup_route_id": "r2"}]})
        self.write("source_ledger.json", {"sources": []})
        data = self.root / "data_cleaned/input.csv"
        data.parent.mkdir()
        data.write_text("capacity\n4\n", encoding="utf-8")
        self.spec = specification()
        self.spec["input_hashes"] = {"data_cleaned/input.csv": sha256_file(data)}
        self.write("optimization_specs/q1.json", self.spec)
        self.declaration = {"schema_version": "1.0", "profile": "linear-v1", "input_hashes": {
            name: sha256_file(self.root/name) for name in gate.SOURCES}, "routes": [
            {"subproblem_id": "q1", "route_id": "r1", "scope": "LP", "spec_path": "optimization_specs/q1.json", "rationale": "The approved route is a linear capacity allocation problem with explicit bounds."},
            {"subproblem_id": "q1", "route_id": "r2", "scope": "outside_scope", "spec_path": None, "rationale": "The backup performs a discrete-event simulation, without a declared LP/MILP solution."}]}
        self.write(gate.DECLARATION, self.declaration)
        self.approve()
        self.record_run()

    def write(self, name, data):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, sort_keys=True, allow_nan=False), encoding="utf-8")

    def approve(self):
        hashes = checkpoint_hashes(self.root, "2")
        self.write("checkpoint_ledger.json", {"checkpoints": {"2": {"status": "APPROVED", "artifact_hashes": hashes,
                    "approval_hash": canonical_json_hash(hashes)}}})

    def record_run(self, result=None):
        spec_hash = sha256_file(self.root/"optimization_specs/q1.json")
        result = solution() if result is None else result
        result["spec_sha256"] = spec_hash
        self.write("experiments/run1/optimization_result.json", result)
        self.write("experiments/run1/metrics.json", {"metrics": {"objective": result["reported_objective"]}})
        self.write("code/run.json", {"run_id": "run1"})
        script = self.root/"code/run.py"
        script.write_text("# test execution receipt fixture; not an actual experiment\n", encoding="utf-8")
        outputs = {name: sha256_file(self.root/name) for name in ("experiments/run1/optimization_result.json", "experiments/run1/metrics.json")}
        receipt = contract(producer_role="pro-experiment-runner", status="PASS", run_id="run1", route_id="r1", implementation_id="test-fixture",
            input_hashes={"optimization_specs/q1.json": spec_hash, **self.spec["input_hashes"]},
            script_hashes={"code/run.py": sha256_file(script)}, output_hashes=outputs, argv=["python", "run.py"], environment={"test_fixture": True},
            exit_code=0, started_at_utc="2026-09-10T00:00:00Z", finished_at_utc="2026-09-10T00:00:01Z",
            metrics_file="experiments/run1/metrics.json", spec_path="code/run.json", spec_sha256=sha256_file(self.root/"code/run.json"))
        self.write("experiments/run1/receipt.json", receipt)
        self.write("experiment_manifest.json", {"runs": [{"run_id": "run1", "receipt_path": "experiments/run1/receipt.json", "receipt_sha256": sha256_file(self.root/"experiments/run1/receipt.json")}]})

    def test_p2_hashes_cover_applicability_spec_and_frozen_data(self):
        hashes = checkpoint_hashes(self.root, "2")
        for name in (gate.DECLARATION, "optimization_specs/q1.json", "data_cleaned/input.csv"):
            self.assertEqual(hashes[name], sha256_file(self.root/name))
        self.assertEqual(gate.inspect_delivery(self.root)["status"], "PASS")

    def test_changed_constraint_invalidates_approval(self):
        self.spec["constraints"][0]["rhs"] = 100
        self.write("optimization_specs/q1.json", self.spec)
        self.assertTrue(gate.validate_delivery(self.root))

    def test_changed_data_invalidates_approval(self):
        (self.root/"data_cleaned/input.csv").write_text("capacity\n100\n", encoding="utf-8")
        self.assertTrue(gate.validate_delivery(self.root))

    def test_missing_profile_is_migration_required(self):
        self.write("pro_config.json", {})
        self.assertIn("MIGRATION_REQUIRED", " ".join(gate.validate_delivery(self.root)))

    def test_legacy_approval_does_not_gain_companion_meaning(self):
        ledger = check.load_json(self.root/"checkpoint_ledger.json")
        approval = ledger["checkpoints"]["2"]
        for name in gate.approval_hashes(self.root):
            approval["artifact_hashes"].pop(name)
        approval["approval_hash"] = canonical_json_hash(approval["artifact_hashes"])
        self.write("checkpoint_ledger.json", ledger)
        self.assertIn("MIGRATION_REQUIRED", " ".join(gate.validate_delivery(self.root)))

    def test_relabeling_scope_cannot_bypass_existing_spec(self):
        self.declaration["routes"][0].update(scope="outside_scope", spec_path=None)
        self.write(gate.DECLARATION, self.declaration)
        self.assertTrue(gate.validate_preapproval(self.root))
        self.assertTrue(gate.validate_delivery(self.root))

    def test_missing_result_is_not_not_applicable(self):
        (self.root/"experiments/run1/optimization_result.json").unlink()
        report = gate.inspect_delivery(self.root)
        self.assertEqual(report["status"], "BLOCKED")

    def test_recorded_bad_solution_blocks_delivery(self):
        result = solution()
        result["values"]["x"] = 5
        result["reported_objective"] = 11
        self.record_run(result)
        self.assertIn("CONSTRAINT_VIOLATION", " ".join(gate.validate_delivery(self.root)))

    def test_enabled_profile_is_actually_enforced_by_formal_gate(self):
        import pro_gate
        result = solution()
        result["values"]["x"] = 5
        result["reported_objective"] = 11
        self.record_run(result)
        for name in ("evidence_freeze.json", "review_board_report.json", "final_format_report.json"):
            self.write(name, {})
        # Isolate the new formal gate integration: other Pro invariants are covered
        # by the unchanged Pro suite; the actual M3 checker runs against hashed files.
        with mock.patch.object(sys, "argv", ["pro_gate.py", "--project-root", str(self.project)]), \
             mock.patch.object(pro_gate, "validate_envelope", return_value=[]), \
             mock.patch.object(pro_gate, "require_checkpoints", return_value=[]), \
             mock.patch.object(pro_gate, "check_freeze", return_value=[]), \
             mock.patch.object(pro_gate, "check_review", return_value=[]), \
             mock.patch.object(pro_gate, "check_documents", return_value=[]):
            self.assertEqual(pro_gate.main(), 1)
        report = check.load_json(self.root/"pro_gate_report.json")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["checks"]["optimization_specifications"], "BLOCKED")

    def test_validated_numeric_result_does_not_certify_unsupported_optimality(self):
        result = solution()
        result["claim"] = "optimal"
        self.record_run(result)
        self.assertIn("UNSUPPORTED_OPTIMALITY", " ".join(gate.validate_delivery(self.root)))

    def test_explicit_nonapplicability_is_distinct_from_pass(self):
        candidate = check.load_json(self.root/"candidate_routes.json")
        candidate["subproblems"][0]["routes"][0]["model_family"] = "simulation"
        self.write("candidate_routes.json", candidate)
        self.declaration["input_hashes"]["candidate_routes.json"] = sha256_file(self.root/"candidate_routes.json")
        self.declaration["routes"][0].update(scope="outside_scope", spec_path=None,
            rationale="The selected method is now a discrete-event simulation rather than a linear mathematical program.")
        self.write(gate.DECLARATION, self.declaration)
        (self.root/"optimization_specs/q1.json").unlink()
        self.approve()
        result_name = "experiments/run1/optimization_result.json"
        (self.root/result_name).unlink()
        receipt = check.load_json(self.root/"experiments/run1/receipt.json")
        receipt["input_hashes"].pop("optimization_specs/q1.json")
        receipt["output_hashes"].pop(result_name)
        self.write("experiments/run1/receipt.json", receipt)
        self.write("experiment_manifest.json", {"runs": [{"run_id": "run1", "receipt_path": "experiments/run1/receipt.json", "receipt_sha256": sha256_file(self.root/"experiments/run1/receipt.json")}]})
        self.assertEqual(gate.inspect_delivery(self.root)["status"], "NOT_APPLICABLE")

    def test_metrics_cannot_disagree_with_checked_solution(self):
        self.write("experiments/run1/metrics.json", {"metrics": {"objective": 999}})
        receipt = check.load_json(self.root/"experiments/run1/receipt.json")
        receipt["output_hashes"]["experiments/run1/metrics.json"] = sha256_file(self.root/"experiments/run1/metrics.json")
        self.write("experiments/run1/receipt.json", receipt)
        self.write("experiment_manifest.json", {"runs": [{"run_id": "run1", "receipt_path": "experiments/run1/receipt.json", "receipt_sha256": sha256_file(self.root/"experiments/run1/receipt.json")}]})
        self.assertIn("objective metric", " ".join(gate.validate_delivery(self.root)))

    def test_cli_and_duplicate_json_rejection(self):
        spec_path = self.root/"optimization_specs/q1.json"
        result_path = self.root/"experiments/run1/optimization_result.json"
        completed = subprocess.run([sys.executable, str(check.__file__), "--spec", str(spec_path), "--result", str(result_path)],
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")
        duplicate = self.root/"duplicate.json"
        duplicate.write_text('{"x":1,"x":2}', encoding="utf-8")
        with self.assertRaises(ValueError):
            check.load_json(duplicate)

    def test_preflight_enables_profile_and_preserves_it_on_rerun(self):
        problem = self.project/"problem_files/problem.txt"
        problem.parent.mkdir()
        problem.write_text("Allocate a bounded resource.", encoding="utf-8")
        self.write("pro_config.json", {})
        command = [sys.executable, str(SCRIPTS/"pro_preflight.py"), "--project-root", str(self.project),
                   "--platform", "claude-code", "--model", "test-unverified-model"]
        first = subprocess.run(command+["--optimization-check-profile", "linear-v1"], capture_output=True, text=True, encoding="utf-8")
        self.assertIn(first.returncode, (0, 1), first.stderr)
        self.assertEqual(check.load_json(self.root/"pro_config.json")["optimization_check_profile"], "linear-v1")
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertIn(second.returncode, (0, 1), second.stderr)
        self.assertEqual(check.load_json(self.root/"pro_config.json")["optimization_check_profile"], "linear-v1")


if __name__ == "__main__":
    unittest.main()

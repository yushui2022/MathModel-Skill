"""Impact follows real file hashes and declared cross-run/claim dependencies."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plugins/mathmodel/scripts"))
from runtime.dependencies import get_change_impact


class ImpactTests(unittest.TestCase):
    def setUp(self):
        temp = Path(os.environ.get("MATHMODEL_TEST_TEMP", "G:/DevCache/Temp/mathmodel-plugin" if os.name == "nt" else tempfile.gettempdir()))
        temp.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="impact-", dir=temp)
        self.project = Path(self.temp.name) / "中文 比赛"
        self.root = self.project / "paper_output_pro"
        self.root.mkdir(parents=True)
        self.write("problem_files/task.md", "Question one and question two", project=True)
        for q in (1, 2):
            self.write(f"problem_files/q{q}.csv", f"x\n{q}\n", project=True)
            self.write(f"data_cleaned/q{q}.csv", f"x\n{q}\n")
            self.write(f"code/q{q}.py", f"print({q})\n")
        self.write("code/shared.py", "value = 1\n")
        self.write("pro_config.json", {"project_root": str(self.project)})
        self.write("problem_consensus.json", {"subproblems": [{"subproblem_id": "q1"}, {"subproblem_id": "q2"}]})
        self.write("candidate_routes.json", {"subproblems": [{"subproblem_id": f"q{q}", "routes": [{"route_id": f"r{q}"}]} for q in (1, 2)]})
        self.write("tournament_report.json", {"decisions": []})
        self.write("source_ledger.json", {"sources": []})
        self.write("input_manifest.json", {"files": [{"path": p.relative_to(self.project).as_posix(), "sha256": self.hash(p)} for p in sorted((self.project / "problem_files").iterdir())]})
        for q in (1, 2):
            self.make_run(q)
        self.write("replication_report.json", {"critical_results": [{"result_id": f"e{q}", "replication_paths": [{"run_id": f"run{q}", "metric": "cost"}]} for q in (1, 2)]})
        self.write("claim_evidence_map.json", {"claims": [{"claim_id": f"c{q}", "section_id": f"s{q}", "evidence_ids": [f"e{q}"], "numeric_evidence": [{"run_id": f"run{q}", "metric": "cost"}]} for q in (1, 2)]})
        self.write("final_paper_source.md", "A supported result.")
        self.refresh()

    def tearDown(self):
        self.temp.cleanup()

    def hash(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write(self, name, value, project=False):
        path = (self.project if project else self.root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, dict) else value, encoding="utf-8")
        return path

    def read(self, name):
        return json.loads((self.root / name).read_text(encoding="utf-8"))

    def make_run(self, q):
        spec = self.write(f"code/spec{q}.json", {"run_id": f"run{q}", "script": f"code/q{q}.py", "inputs": [f"data_cleaned/q{q}.csv"], "dependencies": ["code/shared.py"]})
        output = self.write(f"experiments/run{q}/metrics.json", {"metrics": {"cost": q}})
        self.write(f"experiments/run{q}/receipt.json", {"run_id": f"run{q}", "route_id": f"r{q}", "status": "PASS",
            "input_hashes": {f"data_cleaned/q{q}.csv": self.hash(self.root / f"data_cleaned/q{q}.csv")},
            "script_hashes": {name: self.hash(self.root / name) for name in (f"code/q{q}.py", "code/shared.py")},
            "output_hashes": {output.relative_to(self.root).as_posix(): self.hash(output)},
            "spec_path": spec.relative_to(self.root).as_posix(), "spec_sha256": self.hash(spec),
            "metrics_file": output.relative_to(self.root).as_posix()})

    def refresh(self):
        self.write("experiment_manifest.json", {"runs": [{"run_id": f"run{q}", "receipt_path": f"experiments/run{q}/receipt.json", "receipt_sha256": self.hash(self.root / f"experiments/run{q}/receipt.json")} for q in (1, 2)]})
        self.write("evidence_freeze.json", {"file_hashes": {p.relative_to(self.root).as_posix(): self.hash(p) for p in sorted(self.root.rglob("*")) if p.is_file() and p.name != "evidence_freeze.json"}})

    def fingerprint(self):
        return {str(p): (self.hash(p), p.stat().st_mtime_ns) for p in self.project.rglob("*") if p.is_file()}

    def query(self, paths=None):
        before = self.fingerprint()
        result = get_change_impact(self.project, paths)
        self.assertEqual(before, self.fingerprint())
        return result

    def test_unchanged_has_no_recompute_and_does_not_grant_approval(self):
        result = self.query()
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["recompute_queue"], [])
        self.assertEqual(result["preserved_runs"], ["run1", "run2"])
        self.assertIn("Advisory only", result["approval_policy"])

    def test_q2_data_changes_only_its_run_claim_section(self):
        self.write("data_cleaned/q2.csv", "x\n99\n")
        result = self.query()
        self.assertEqual(result["affected_runs"], ["run2"])
        self.assertEqual(result["affected_claims"], ["c2"])
        self.assertEqual(result["affected_sections"], ["s2"])
        self.assertEqual(result["preserved_runs"], ["run1"])
        self.assertFalse(result["conservative"])
        self.assertEqual(result["recompute_queue"][0]["dependency_path"][0], "file:paper_output_pro/data_cleaned/q2.csv")

    def test_shared_code_changes_both_runs(self):
        self.write("code/shared.py", "value = 2\n")
        self.assertEqual(self.query()["affected_runs"], ["run1", "run2"])

    def test_wording_edit_requires_review_without_model_recompute(self):
        frozen = self.read("evidence_freeze.json")
        frozen["file_hashes"].pop("final_paper_source.md")
        self.write("evidence_freeze.json", frozen)
        self.write("review_board_report.json", {"input_hashes": {"final_paper_source.md": self.hash(self.root/"final_paper_source.md")}})
        self.write("final_paper_source.md", "A clearer supported result.")
        result = self.query()
        self.assertEqual(result["affected_runs"], [])
        self.assertIn("gate:review", [n["id"] for n in result["affected_nodes"]])

    def test_unmapped_raw_data_expands_conservatively(self):
        self.write("problem_files/q2.csv", "x\n99\n", project=True)
        result = self.query()
        self.assertTrue(result["conservative"])
        self.assertEqual(result["affected_runs"], ["run1", "run2"])

    def test_raw_to_clean_provenance_preserves_other_question(self):
        self.write("data_cleaned/provenance.json", {"transforms": [{
            "input_hashes": {"problem_files/q2.csv": self.hash(self.project / "problem_files/q2.csv")},
            "output_hashes": {"paper_output_pro/data_cleaned/q2.csv": self.hash(self.root / "data_cleaned/q2.csv")}}]})
        self.refresh()
        self.write("problem_files/q2.csv", "x\n99\n", project=True)
        result = self.query()
        self.assertFalse(result["conservative"])
        self.assertEqual(result["affected_runs"], ["run2"])

    def test_new_hidden_dependency_or_missing_hashes_cannot_be_preserved(self):
        self.write("code/new_helper.py", "value = 3\n")
        result = self.query()
        self.assertTrue(result["conservative"])
        self.assertEqual(result["preserved_runs"], [])
        (self.root / "code/new_helper.py").unlink()
        receipt = self.read("experiments/run1/receipt.json")
        receipt.pop("input_hashes")
        self.write("experiments/run1/receipt.json", receipt)
        self.refresh()
        self.write("data_cleaned/q2.csv", "x\n100\n")
        result = self.query()
        self.assertTrue(result["conservative"])
        self.assertEqual(result["preserved_runs"], [])

    def test_frozen_but_undeclared_helper_and_new_data_are_conservative(self):
        self.write("code/undeclared.py", "value = 1\n")
        self.refresh()
        self.assertEqual(self.query()["changed"], [])
        self.write("code/undeclared.py", "value = 2\n")
        self.assertEqual(self.query()["preserved_runs"], [])
        self.refresh()
        self.write("data_cleaned/new.csv", "x\n4\n")
        result = self.query()
        self.assertIn("paper_output_pro/data_cleaned/new.csv", result["changed"])
        self.assertTrue(result["conservative"])

    def test_cross_run_dependency_has_topological_recompute_order(self):
        receipt = self.read("experiments/run2/receipt.json")
        receipt["input_hashes"]["experiments/run1/metrics.json"] = self.hash(self.root / "experiments/run1/metrics.json")
        self.write("experiments/run2/receipt.json", receipt)
        self.refresh()
        self.write("data_cleaned/q1.csv", "x\n123\n")
        result = self.query()
        self.assertEqual([r["run_id"] for r in result["recompute_queue"]], ["run1", "run2"])
        self.assertTrue(all(r["requires_fresh_approval"] for r in result["recompute_queue"]))

    def test_mathematical_spec_change_targets_its_route(self):
        self.write("optimization_specs/q2.json", {"input_hashes": {"data_cleaned/q2.csv": self.hash(self.root / "data_cleaned/q2.csv")}, "constraint": 2})
        self.write("optimization_applicability.json", {"routes": [{"route_id": "r2", "spec_path": "optimization_specs/q2.json"}]})
        self.refresh()
        self.write("optimization_specs/q2.json", {"input_hashes": {}, "constraint": 4})
        self.assertEqual(self.query()["affected_runs"], ["run2"])

    def test_explicit_paths_are_bounded_and_cli_supports_unicode(self):
        for paths in (["../outside"], ["C:/secrets"], ["/etc/passwd"], ["a"] * 257):
            with self.assertRaises(ValueError):
                self.query(paths)
        result = subprocess.run([sys.executable, "-B", str(REPO / "plugins/mathmodel/scripts/change_impact.py"), "--project-root", str(self.project), "--changed", "paper_output_pro/data_cleaned/q2.csv"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["affected_runs"], ["run2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

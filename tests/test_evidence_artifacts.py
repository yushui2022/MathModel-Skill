"""Artifact regressions; synthetic receipts are unit fixtures, not model assessments."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

from pro_fixture import SCRIPTS, prepare_evidence, run
from pro_contracts import sha256_file, write_json
from pro_validation import check_artifacts


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mathmodel-pro-artifacts-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "experiments/test/result.csv"
        self.path.parent.mkdir(parents=True)
        self.path.write_text("metric,value\ncost,2\n", encoding="utf-8")

    def receipt(self):
        return {"test": {"status": "PASS", "exit_code": 0,
                        "output_hashes": {"experiments/test/result.csv": sha256_file(self.path)}}}

    def test_valid_table_and_conflicting_status(self):
        self.assertEqual(check_artifacts(self.root, self.receipt()), [])
        write_json(self.root / "table_index.json", {"tables": [{
            "path": "experiments/test/result.csv", "status": "computed", "evidence_status": "FAIL"
        }]})
        self.assertTrue(any("unacceptable" in x for x in check_artifacts(self.root, self.receipt())))

    def test_changed_or_failed_origin_cannot_back_a_copy(self):
        target = self.root / "tables/copy.csv"
        target.parent.mkdir()
        target.write_bytes(self.path.read_bytes())
        write_json(self.root / "table_index.json", {"tables": [{
            "path": "tables/copy.csv", "status": "computed", "run_id": "test",
            "output_path": "experiments/test/result.csv"
        }]})
        receipt = self.receipt()
        self.assertEqual(check_artifacts(self.root, receipt), [])
        receipt["test"]["status"] = "FAILED"
        self.assertTrue(any("successful experiment" in x for x in check_artifacts(self.root, receipt)))
        self.assertTrue(any("paper artifact" in x for x in check_artifacts(
            self.root, receipt, required_paths=["experiments/test/result.csv"])))
        target.write_text("metric,value\ncost,999\n", encoding="utf-8")
        self.assertTrue(any("successful experiment" in x for x in check_artifacts(self.root, self.receipt())))

    def test_unregistered_and_exploratory_assets_rejected(self):
        target = self.root / "tables/preview.csv"
        target.parent.mkdir()
        target.write_bytes(self.path.read_bytes())
        self.assertTrue(any("unregistered" in x for x in check_artifacts(self.root, self.receipt())))
        write_json(self.root / "table_index.json", {"tables": [{
            "path": "tables/preview.csv", "status": "computed", "evidence_role": "exploratory",
            "run_id": "test", "output_path": "experiments/test/result.csv"
        }]})
        self.assertTrue(any("exploratory" in x for x in check_artifacts(self.root, self.receipt())))

    def test_corrupt_table_and_image_with_fresh_hashes_rejected(self):
        self.path.write_text("a,b\n1,2,3\n", encoding="utf-8")
        self.assertTrue(any("row width" in x for x in check_artifacts(self.root, self.receipt())))
        image = self.path.with_suffix(".png")
        image.write_bytes(b"corrupt PNG")
        receipt = {"test": {"status": "PASS", "exit_code": 0,
                           "output_hashes": {"experiments/test/result.png": sha256_file(image)}}}
        self.assertTrue(any("invalid artifact" in x for x in check_artifacts(self.root, receipt)))

    def test_checkpoint_three_rejects_actual_corrupt_experiment(self):
        from pro_run_experiment import execute, refresh_manifest
        project = self.root / "contest"
        root = prepare_evidence(project)
        script = root / "code/corrupt.py"
        script.write_text(
            "import sys, json\nfrom pathlib import Path\n"
            "out = Path(sys.argv[1])\n"
            "(out / 'metrics.json').write_text(json.dumps({'metrics': {'cost': 2}}))\n"
            "(out / 'broken.png').write_bytes(b'not a PNG')\n", encoding="utf-8"
        )
        spec = root / "code/corrupt-spec.json"
        write_json(spec, {"run_id": "corrupt", "route_id": "r2", "implementation_id": "chart",
                         "script": "code/corrupt.py", "inputs": ["data_cleaned/data.json"], "args": ["{run_dir}"]})
        _, success = execute(project, spec)
        self.assertFalse(success)  # A zero process exit does not imply usable outputs.
        refresh_manifest(root)
        receipt = json.loads((root / "experiments/corrupt/receipt.json").read_text())
        self.assertIn("invalid artifact broken.png", receipt["failure_reason"])
        self.assertEqual(check_artifacts(root, {"corrupt": receipt}), [])
        write_json(root / "figure_index.json", {"figures": [{
            "path": "experiments/corrupt/broken.png", "status": "computed"
        }]})
        result = run(SCRIPTS / "pro_checkpoint.py", "approve", "--checkpoint", "3",
                     "--decision", "synthetic regression approval", "--project-root", project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid artifact broken.png", result.stdout)
        script = root / "code/failed-metrics.py"
        script.write_text(
            "import sys, json\nfrom pathlib import Path\n"
            "(Path(sys.argv[1]) / 'metrics.json').write_text(json.dumps("
            "{'status': 'computed', 'evidence_status': 'FAIL', 'metrics': {'cost': 2}}))\n",
            encoding="utf-8"
        )
        spec = root / "code/failed-metrics-spec.json"
        write_json(spec, {"run_id": "failed-metrics", "route_id": "r2", "implementation_id": "chart",
                         "script": "code/failed-metrics.py", "inputs": ["data_cleaned/data.json"], "args": ["{run_dir}"]})
        receipt_path, success = execute(project, spec)
        self.assertFalse(success)
        self.assertIn("unacceptable", json.loads(receipt_path.read_text())["failure_reason"])


if __name__ == "__main__":
    unittest.main()

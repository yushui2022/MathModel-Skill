"""Fresh-output regressions without model/API calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import run_flash_tests as fixtures


class FreshOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mathmodel-flash-fresh-")
        self.addCleanup(self.temp.cleanup)
        self.previous_sandbox = fixtures.SANDBOX
        fixtures.SANDBOX = Path(self.temp.name)
        self.addCleanup(setattr, fixtures, "SANDBOX", self.previous_sandbox)
        self.root = fixtures.prepare("project")
        self.output = self.root / "paper_output_flash"

    def run_model(self):
        result = fixtures.run(fixtures.RUNNER, self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        return json.loads((self.output / "run_manifest.json").read_text(encoding="utf-8"))

    def omit_table_generation(self):
        model = self.output / "code/model.py"
        lines = model.read_text(encoding="utf-8").splitlines()
        model.write_text("\n".join(line for line in lines if not line.startswith("table.write_text")) + "\n", encoding="utf-8")

    def test_old_table_not_enrolled_and_old_word_archived(self):
        first = self.run_model()
        result = fixtures.run(fixtures.FINALIZER, self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        old_table = (self.output / "tables/q1.csv").read_bytes()
        self.omit_table_generation()
        second = self.run_model()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(second["output_policy"], "fresh-directories-v1")
        self.assertFalse((self.output / "tables/q1.csv").exists())
        self.assertFalse((self.output / "paper.docx").exists())
        self.assertFalse((self.output / "flash_report.json").exists())
        self.assertFalse(any(item["path"].endswith("q1.csv") for item in second["outputs"]))
        archive = self.output / "runs" / second["run_id"] / "previous"
        self.assertEqual((archive / "tables/q1.csv").read_bytes(), old_table)
        self.assertTrue((archive / "paper.docx").exists())
        self.assertEqual(json.loads((archive / "run_manifest.json").read_text())["run_id"], first["run_id"])
        self.assertNotEqual(fixtures.run(fixtures.FINALIZER, self.root).returncode, 0)

    def test_old_nested_figure_not_enrolled(self):
        figure = self.output / "figures/old/nested.png"
        figure.parent.mkdir()
        figure.write_bytes(b"old artifact")
        result = self.run_model()
        self.assertFalse(figure.exists())
        self.assertFalse(any(item["path"].endswith("nested.png") for item in result["outputs"]))
        self.assertTrue((self.output / "runs" / result["run_id"] / "previous/figures/old/nested.png").is_file())

    def test_identical_regenerated_output_is_accepted(self):
        self.run_model()
        first_hash = hashlib.sha256((self.output / "tables/q1.csv").read_bytes()).hexdigest()
        second = self.run_model()
        record = next(item for item in second["outputs"] if item["path"].endswith("q1.csv"))
        self.assertEqual(record["sha256"], first_hash)
        result = fixtures.run(fixtures.FINALIZER, self.root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_unrecorded_evidence_is_rejected(self):
        path = self.root / "unrecorded.csv"
        path.write_text("metric,value\nslope,2\n", encoding="utf-8")
        model = self.output / "code/model.py"
        model.write_text(model.read_text().replace("paper_output_flash/tables/q1.csv", "unrecorded.csv"), encoding="utf-8")
        self.run_model()
        result = fixtures.run(fixtures.FINALIZER, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not bound to this run", result.stdout)

    def test_recorded_input_can_be_cited(self):
        model = self.output / "code/model.py"
        model.write_text(model.read_text().replace("paper_output_flash/tables/q1.csv", "problem_files/data.csv"), encoding="utf-8")
        self.run_model()
        result = fixtures.run(fixtures.FINALIZER, self.root)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_legacy_receipt_requires_rerun(self):
        report = self.run_model()
        report.pop("output_policy")
        (self.output / "run_manifest.json").write_text(json.dumps(report), encoding="utf-8")
        result = fixtures.run(fixtures.FINALIZER, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy run receipt", result.stdout)

    def test_failed_run_does_not_retain_previous_success(self):
        self.run_model()
        (self.output / "code/model.py").write_text("raise RuntimeError('failed experiment')\n", encoding="utf-8")
        self.assertNotEqual(fixtures.run(fixtures.RUNNER, self.root).returncode, 0)
        report = json.loads((self.output / "run_manifest.json").read_text())
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["outputs"], [])
        self.assertFalse((self.output / "tables/q1.csv").exists())

    def test_linked_output_is_rejected_without_moving_input(self):
        original = self.root / "problem_files/data.csv"
        before = original.read_bytes()
        link = self.output / "tables/linked.csv"
        try:
            link.symlink_to(original)
        except OSError as exc:
            self.skipTest(f"host cannot create symlinks: {exc}")
        result = fixtures.run(fixtures.RUNNER, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(original.read_bytes(), before)

    def test_linked_archive_is_rejected_before_moving_outputs(self):
        self.run_model()
        # A dedicated input-side folder must not become an archive destination.
        import shutil
        runs = self.output / "runs"
        self.assertTrue(runs.resolve().is_relative_to(Path(self.temp.name).resolve()))
        shutil.rmtree(runs)
        target = self.root / "problem_files"
        try:
            runs.symlink_to(target, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"host cannot create symlinks: {exc}")
        before = (self.output / "tables/q1.csv").read_bytes()
        result = fixtures.run(fixtures.RUNNER, self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.output / "tables/q1.csv").read_bytes(), before)
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["data.csv", "problem.txt"])


if __name__ == "__main__":
    unittest.main()

"""Verify that Pro status uses real contracts without mutating any project file."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pro_fixture import prepare, approve, candidates, tournament, envelope, SCRIPTS, complete
from pro_contracts import read_json, write_json


def fingerprint(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob("*") if p.is_file()}


class ProStatusTests(unittest.TestCase):
    def setUp(self):
        temp = Path(os.environ.get("MATHMODEL_TEST_TEMP", "G:/DevCache/Temp/mathmodel-plugin" if os.name == "nt" else tempfile.gettempdir())).resolve()
        temp.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="pro-status-", dir=temp)
        self.project = Path(self.temporary.name) / "中文 比赛"
        self.project.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def query(self):
        before = fingerprint(self.project)
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "pro_status.py"), "--project-root", str(self.project), "--format", "json"], capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, fingerprint(self.project), "read-only query changed files or mtimes")
        return json.loads(result.stdout)

    def test_empty_project_is_pending_without_new_files(self):
        status = self.query()
        self.assertEqual(status["status"], "PENDING")
        self.assertEqual(status["next_step"], "P0")
        self.assertEqual(status["verified_count"], 0)

    def test_approval_is_not_inferred_from_complete_analysis(self):
        prepare(self.project)
        status = self.query()
        self.assertEqual(status["next_step"], "P1")
        self.assertEqual(status["awaiting_checkpoint"], "1")
        self.assertEqual(status["steps"][1]["status"], "PENDING")

    def test_route_ready_but_not_approved_stays_at_p2(self):
        root = prepare(self.project)
        approve(self.project, 1)
        write_json(root / "source_ledger.json", envelope("fixture", sources=[], critical_claims=[]))
        write_json(root / "candidate_routes.json", candidates())
        write_json(root / "tournament_report.json", tournament())
        status = self.query()
        self.assertEqual(status["next_step"], "P2")
        self.assertEqual(status["awaiting_checkpoint"], "2")
        approve(self.project, 2)
        status = self.query()
        self.assertEqual(status["next_step"], "P3")
        self.assertEqual(status["steps"][3]["status"], "PENDING")

    def test_stale_approval_detected_without_changing_ledger(self):
        root = prepare(self.project)
        approve(self.project, 1)
        consensus = read_json(root / "problem_consensus.json")
        consensus["assumptions"].append("new unapproved assumption")
        write_json(root / "problem_consensus.json", consensus)
        status = self.query()
        self.assertEqual(status["next_step"], "P1")
        self.assertEqual(status["steps"][1]["status"], "INVALID")
        self.assertTrue(status["checkpoints"]["1"]["stale"])
        self.assertEqual(read_json(root / "checkpoint_ledger.json")["checkpoints"]["1"]["status"], "APPROVED")

    def test_changed_original_input_blocks_p0(self):
        prepare(self.project)
        approve(self.project, 1)
        (self.project / "problem_files/task.md").write_text("changed question", encoding="utf-8")
        status = self.query()
        self.assertEqual(status["next_step"], "P0")
        self.assertNotEqual(status["status"], "COMPLETE")

    def test_forged_final_pass_cannot_advance(self):
        root = prepare(self.project)
        write_json(root / "pro_gate_report.json", envelope("forged", acceptance_scope="COMPETITION_REPORT_CHECKED"))
        status = self.query()
        self.assertEqual(status["next_step"], "P1")
        self.assertEqual(status["acceptance_scope"], "NOT_ACCEPTED")

    def test_required_phase_exit_code_keeps_query_read_only(self):
        prepare(self.project)
        before = fingerprint(self.project)
        command = [sys.executable, "-B", str(SCRIPTS / "pro_status.py"), "--project-root", str(self.project), "--fail-if-blocked"]
        full = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(full.returncode, 2)
        self.assertEqual(json.loads(full.stdout)["next_step"], "P1")
        initial = subprocess.run(command + ["--require-through", "P0"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(initial.returncode, 0, initial.stderr)
        evidence = subprocess.run(command + ["--require-through", "P5"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(evidence.returncode, 2)
        self.assertEqual(before, fingerprint(self.project))

    @unittest.skipUnless(shutil.which("soffice") or Path("C:/Program Files/LibreOffice/program/soffice.exe").is_file(), "LibreOffice required for real full-pipeline status")
    def test_real_synthetic_pipeline_is_complete_and_late_tamper_is_rejected(self):
        root = complete(self.project)
        status = self.query()
        self.assertEqual(status["status"], "COMPLETE", status["failures"])
        self.assertEqual(status["verified_count"], 10)
        self.assertEqual(status["acceptance_scope"], "ENGINEERING_SMOKE_ONLY")
        manuscript = root / "final_paper_source.md"
        manuscript.write_text(manuscript.read_text(encoding="utf-8") + "\nAn unreviewed edit.\n", encoding="utf-8")
        changed = self.query()
        self.assertNotEqual(changed["status"], "COMPLETE")
        self.assertIn(changed["next_step"], ("P7", "P8"))
        self.assertEqual(changed["acceptance_scope"], "NOT_ACCEPTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

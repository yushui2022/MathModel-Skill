"""Recovery tests use synthetic records, never claim contest-paper quality."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plugins/mathmodel/scripts"))
from build_context_packet import build_packet
from runtime.context import collect_facts, digest_file, read_contract, write_snapshot


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="恢复 比赛-", dir=os.environ.get("MATHMODEL_TEST_TEMP"))
        self.project = Path(self.temp.name).resolve()
        self.root = self.project / "paper_output_pro"
        write(self.project / "problem_files/data.json", {"capacity": 12})
        write(self.root / "pro_config.json", {"project_root": self.project.as_posix()})
        write(self.root / "input_manifest.json", {"files": [{"path": "problem_files/data.json", "sha256": digest_file(self.project / "problem_files/data.json")}]})
        write(self.root / "problem_consensus.json", {"subproblems": [
            {"subproblem_id": "q1", "task": "确定供给"},
            {"subproblem_id": "q2", "task": "运输分配", "depends_on": ["q1"], "assumptions": ["需求固定"]}], "assumptions": ["成本同一币值"]})
        write(self.root / "candidate_routes.json", {"subproblems": [
            {"subproblem_id": "q1", "routes": [{"route_id": "q1-base"}]},
            {"subproblem_id": "q2", "routes": [{"route_id": "q2-milp"}, {"route_id": "q2-greedy"}]}]})
        write(self.root / "tournament_report.json", {"decisions": [{"subproblem_id": "q2", "selected_route_id": "q2-milp", "backup_route_id": "q2-enum", "rejected_routes": [{"route_id": "q2-greedy", "reason": "无法给出满足容量的全局解"}]}]})

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_process_recovers_question_reasons_without_writing(self):
        before = {p.relative_to(self.project).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.project.rglob("*") if p.is_file()}
        result = subprocess.run([sys.executable, "-B", str(REPO / "plugins/mathmodel/scripts/build_context_packet.py"), "--project-root", str(self.project), "--question", "q2"], capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.assertEqual(packet["focus"]["question_id"], "q2")
        route = next(f for f in packet["facts"] if f["category"] == "route")
        self.assertEqual(route["value"]["selected_route_id"], "q2-milp")
        self.assertIn("容量", route["value"]["rejected_routes"][0]["reason"])
        self.assertEqual(route["source"]["pointer"], "/decisions/0")
        self.assertNotEqual(packet["workflow"]["status"], "COMPLETE")
        after = {p.relative_to(self.project).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse((self.project / ".mathmodel").exists())

    def test_original_change_marks_recovered_facts_stale(self):
        write(self.project / "problem_files/data.json", {"capacity": 5})
        facts, diagnostics, _ = collect_facts(self.project, "paper_output_pro", "q2")
        self.assertTrue(diagnostics)
        self.assertTrue(all(f["state"] == "stale" for f in facts))

    def test_activity_does_not_invalidate_source_pagination(self):
        from workbench import WorkbenchState
        first = build_packet(self.project, "q2")
        WorkbenchState(self.project).record_event("P3", "running", "真实活动与来源版本分开")
        second = build_packet(self.project, "q2")
        self.assertEqual(first["handoff"]["input_revision"], second["handoff"]["input_revision"])

    def test_malformed_contract_shape_and_identity_are_diagnostic(self):
        write(self.root / "candidate_routes.json", {"subproblems": None})
        write(self.root / "context/workflow_memory.json", {"project_root": ["invalid"]})
        packet = build_packet(self.project, "q2")
        self.assertTrue(any("expected list" in item for item in packet["diagnostics"]))
        self.assertFalse(packet["memory_consistency"]["matches_guard"])

    def test_malformed_manifest_paths_do_not_crash_recovery(self):
        write(self.root / "input_manifest.json", {"files": [{"path": ["bad"], "sha256": "x"}]})
        write(self.root / "experiment_manifest.json", {"runs": [{"receipt_path": ["bad"]}]})
        write(self.root / "experiments/bad/receipt.json", {"spec_path": ["bad"], "metrics_file": {"bad": True}})
        packet = build_packet(self.project)
        self.assertTrue(any("invalid or duplicate" in item for item in packet["diagnostics"]))
        self.assertFalse(any(f["state"] == "current" for f in packet["facts"]))

    def test_receipt_needs_manifest_and_current_code(self):
        write(self.root / "code/input.json", {"x": 2})
        script = self.root / "code/solve.py"
        script.write_text("print(2)\n", encoding="utf-8")
        write(self.root / "code/run.json", {"run_id": "q2-one"})
        write(self.root / "experiments/q2-one/metrics.json", {"metrics": {"cost": 2}})
        receipt = {"status": "PASS", "exit_code": 0, "run_id": "q2-one", "route_id": "q2-milp", "metrics_file": "experiments/q2-one/metrics.json", "spec_path": "code/run.json", "spec_sha256": digest_file(self.root / "code/run.json"), "input_hashes": {"code/input.json": digest_file(self.root / "code/input.json")}, "script_hashes": {"code/solve.py": digest_file(script)}, "output_hashes": {"experiments/q2-one/metrics.json": digest_file(self.root / "experiments/q2-one/metrics.json")}}
        write(self.root / "experiments/q2-one/receipt.json", receipt)
        write(self.root / "experiment_manifest.json", {"runs": [{"receipt_path": "experiments/q2-one/receipt.json", "receipt_sha256": digest_file(self.root / "experiments/q2-one/receipt.json")}]})
        facts = collect_facts(self.project, "paper_output_pro", "q2")[0]
        # Hash-matched, hand-written data cannot claim authoritative execution validation.
        self.assertEqual(next(f for f in facts if f["category"] == "experiment")["state"], "recorded")
        script.write_text("print(3)\n", encoding="utf-8")
        facts = collect_facts(self.project, "paper_output_pro", "q2")[0]
        self.assertEqual(next(f for f in facts if f["category"] == "experiment")["state"], "stale")
        self.assertFalse(any(f["category"] == "metrics" and f["state"] == "current" for f in facts))

    def test_unknown_question_and_corrupt_memory_are_explicit(self):
        with self.assertRaisesRegex(ValueError, "Unknown question"):
            build_packet(self.project, "q9")
        memory = self.root / "context/workflow_memory.json"
        memory.parent.mkdir(parents=True)
        memory.write_text('{"phase": "P9", "phase": "P9"}', encoding="utf-8")
        packet = build_packet(self.project, "q2")
        self.assertFalse(packet["memory_consistency"]["matches_guard"])
        self.assertNotEqual(packet["workflow"]["status"], "COMPLETE")

    def test_paging_keeps_handoff_identity_and_makes_progress(self):
        write(self.root / "paper_plan.json", {"subproblem_coverage": [{"subproblem_id": "q2", "section_ids": [f"s{i}" for i in range(20)]}], "sections": [{"section_id": f"s{i}", "title": "运算与解释" * 100} for i in range(20)]})
        first = build_packet(self.project, "q2", max_chars=6000)
        self.assertLessEqual(len(json.dumps(first, ensure_ascii=False)), 6000)
        seen, cursor = [], 0
        while cursor is not None:
            packet = build_packet(self.project, "q2", max_chars=6000, cursor=cursor, source_revision=first["pagination"]["source_revision"])
            self.assertEqual(packet["handoff"]["task_id"], first["handoff"]["task_id"])
            self.assertLessEqual(len(json.dumps(packet, ensure_ascii=False)), 6000)
            seen.extend(f["source"]["path"] + f["source"]["pointer"] for f in packet["facts"])
            following = packet["pagination"]["next_cursor"]
            self.assertTrue(following is None or following > cursor)
            cursor = following
        self.assertEqual(len(seen), first["pagination"]["total_facts"])
        self.assertEqual(len(set(seen)), len(seen))
        write(self.root / "tournament_report.json", {"decisions": []})
        with self.assertRaisesRegex(ValueError, "Context sources changed"):
            build_packet(self.project, "q2", cursor=1, source_revision=first["pagination"]["source_revision"])

    def test_explicit_snapshot_is_separate_from_approval_memory(self):
        packet = build_packet(self.project, "q2")
        target = write_snapshot(self.project, packet)
        self.assertEqual(target, self.project / ".mathmodel/context/resume.json")
        self.assertFalse((self.root / "context/workflow_memory.json").exists())
        self.assertFalse((self.root / "checkpoint_ledger.json").exists())

    def test_project_identity_mismatch_and_path_escape(self):
        write(self.root / "pro_config.json", {"project_root": str(self.project.parent)})
        facts, diagnostics, _ = collect_facts(self.project, "paper_output_pro", "q2")
        self.assertTrue(all(f["state"] == "stale" for f in facts))
        self.assertTrue(diagnostics)
        value, source = read_contract(self.project, "../secret.json")
        self.assertIsNone(value)
        self.assertEqual(source["state"], "unknown")


if __name__ == "__main__":
    unittest.main()

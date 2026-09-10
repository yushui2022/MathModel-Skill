from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.mathmodel.scripts.workbench import WorkbenchState
from plugins.mathmodel.scripts.build_context_packet import build_packet


class WorkbenchStateTests(unittest.TestCase):
    def test_manual_pass_is_not_authoritative_without_guard_evidence(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            (root / "paper_output").mkdir()
            state = WorkbenchState(root)
            state.record_event("S8", "passed", "manual event")
            snapshot = state.status()
            self.assertNotEqual(snapshot["status"], "passed")
            self.assertEqual(snapshot["activity_status"], "awaiting_validation")
            state.close()

    def test_artifact_registry_rejects_escape_and_supports_unicode_paths(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            target = root / "paper_output" / "图表 数据.csv"
            target.parent.mkdir(parents=True)
            target.write_text("x,y\n1,2\n", encoding="utf-8")
            state = WorkbenchState(root)
            artifacts = state.artifacts()
            self.assertEqual(len(artifacts), 1)
            path, _ = state.read_artifact(artifacts[0]["id"])
            self.assertEqual(path, target.resolve())
            with self.assertRaises(FileNotFoundError):
                state.read_artifact("../../etc/passwd")
            state.close()

    def test_context_packet_recovers_without_chat_memory(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            (root / "paper_output_pro" / "context").mkdir(parents=True)
            problem = root / "problem_files" / "赛题 2026.pdf"
            problem.parent.mkdir(parents=True)
            problem.write_bytes(b"problem")
            packet = build_packet(root)
            self.assertEqual(packet["workflow"]["next_step"], "P0")
            self.assertEqual(packet["workflow"]["recommended_skill"], "pro-workflow-orchestrator")
            self.assertEqual(packet["inputs"]["problem_files"][0]["path"], "problem_files/赛题 2026.pdf")
            memory = root / "paper_output_pro" / "context" / "workflow_memory.json"
            memory.write_text('{"current_phase":"P9","next_action":"deliver"}', encoding="utf-8")
            packet = build_packet(root)
            self.assertFalse(packet["memory_consistency"]["matches_guard"])
            self.assertEqual(packet["workflow"]["next_step"], "P0")
            self.assertFalse((root / "paper_output_pro" / "pro_gate_report.json").exists())
            self.assertFalse((root / "paper_output" / "qa" / "workflow_guard_report.json").exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.mathmodel.scripts.workbench import WorkbenchState


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


if __name__ == "__main__":
    unittest.main()

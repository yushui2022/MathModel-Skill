"""Real subprocess tests of execution/logging only; checkpoint approval is mocked.

These engineering fixtures make no claim to be a user-approved Pro project.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "packages/claude/.claude/skills/pro-workflow-orchestrator/scripts"
sys.path.insert(0, str(SCRIPTS))
import pro_run_experiment as runner
from pro_contracts import sha256_file


def process_running(pid):
    if os.name == "nt":
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.CloseHandle.argtypes = [w.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258
        finally:
            kernel.CloseHandle(handle)
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists() and stat.read_text().split(") ", 1)[1].startswith("Z"):
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


class ExperimentLogTests(unittest.TestCase):
    def setUp(self):
        cache = Path("G:/DevCache/Temp/mathmodel-insert/experiment-log-tests") if os.name == "nt" else Path(tempfile.gettempdir()) / "mathmodel-experiment-logs"
        cache.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="engineering-", dir=cache)
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.root = self.project / "paper_output_pro"
        (self.root / "code").mkdir(parents=True)
        (self.root / "data_cleaned").mkdir()
        (self.root / "data_cleaned/input.json").write_text('[1,2,3]', encoding="utf-8")
        (self.root / "candidate_routes.json").write_text(json.dumps({"subproblems": [{"routes": [{"route_id": "engineering-route"}]}]}), encoding="utf-8")

    def run_script(self, body, *, run_id="engineering-run", timeout=10):
        script = self.root / "code/experiment.py"
        script.write_text(
            "import json, os, sys, time, subprocess, threading\nfrom pathlib import Path\n"
            "directory = Path(sys.argv[1])\n"
            "values = json.loads(Path('data_cleaned/input.json').read_text())\n"
            "(directory / 'metrics.json').write_text(json.dumps({'metrics': {'objective': sum(values)}}))\n" + body,
            encoding="utf-8")
        spec = self.root / "code/run.json"
        spec.write_text(json.dumps({"run_id": run_id, "route_id": "engineering-route", "implementation_id": "engineering-python",
                                    "script": "code/experiment.py", "inputs": ["data_cleaned/input.json"],
                                    "args": ["{run_dir}"], "timeout_seconds": timeout}), encoding="utf-8")
        with mock.patch.object(runner, "require_checkpoints", return_value=[]):
            receipt_path, passed = runner.execute(self.project, spec)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(passed, receipt["status"] == "PASS")
        for info in receipt["log_capture"].values():
            path = self.root / info["path"]
            self.assertLessEqual(path.stat().st_size, runner.LOG_LIMIT_BYTES)
            self.assertEqual(path.stat().st_size, info["retained_bytes"])
            self.assertEqual(receipt["output_hashes"][info["path"]], sha256_file(path))
        return receipt

    def test_normal_numerical_run_preserves_raw_utf8_logs_and_passes(self):
        receipt = self.run_script("os.write(1, '计算完成\\n'.encode('utf-8'))\nos.write(2, b'warning\\n')\n")
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["exit_code"], 0)
        self.assertIsNone(receipt["failure_reason"])
        self.assertEqual(json.loads((self.root / receipt["metrics_file"]).read_text())["metrics"]["objective"], 6)
        self.assertEqual(receipt["log_capture"]["stdout"]["observed_bytes"], len("计算完成\n".encode("utf-8")))
        for info in receipt["log_capture"].values():
            self.assertTrue(info["complete"])
            self.assertFalse(info["truncated"])

    def test_exact_limit_is_allowed_and_byte_preserving(self):
        receipt = self.run_script(f"os.write(1, b'\\xff' * {runner.LOG_LIMIT_BYTES})\n")
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["log_capture"]["stdout"]["observed_bytes"], runner.LOG_LIMIT_BYTES)
        self.assertEqual((self.root / receipt["log_capture"]["stdout"]["path"]).read_bytes(), b"\xff" * runner.LOG_LIMIT_BYTES)

    def test_excess_stdout_and_stderr_are_drained_counted_and_fail(self):
        count = runner.LOG_LIMIT_BYTES + 12345
        for stream, descriptor in (("stdout", 1), ("stderr", 2)):
            with self.subTest(stream=stream):
                receipt = self.run_script(f"os.write({descriptor}, b'x' * {count})\n", run_id=f"engineering-{stream}")
                self.assertEqual(receipt["status"], "FAILED")
                self.assertEqual(receipt["exit_code"], 0)
                info = receipt["log_capture"][stream]
                self.assertEqual(info["observed_bytes"], count)
                self.assertEqual(info["retained_bytes"], runner.LOG_LIMIT_BYTES)
                self.assertTrue(info["truncated"])
                self.assertTrue(info["complete"])
                self.assertIn(stream, receipt["failure_reason"])
                self.assertIn("new run_id", receipt["failure_reason"])

    def test_simultaneous_streams_cannot_deadlock_and_report_all_bytes(self):
        count = runner.LOG_LIMIT_BYTES * 2 + 99
        receipt = self.run_script(
            f"workers = [threading.Thread(target=os.write, args=(fd, b'x' * {count})) for fd in (1, 2)]\n"
            "for worker in workers: worker.start()\nfor worker in workers: worker.join()\n")
        self.assertEqual(receipt["status"], "FAILED")
        self.assertEqual(receipt["exit_code"], 0)
        for info in receipt["log_capture"].values():
            self.assertEqual(info["observed_bytes"], count)
            self.assertTrue(info["truncated"])
            self.assertTrue(info["complete"])

    def test_nonzero_exit_is_retained_with_truncation(self):
        receipt = self.run_script(f"os.write(2, b'error' * {runner.LOG_LIMIT_BYTES})\nsys.exit(7)\n")
        self.assertEqual(receipt["status"], "FAILED")
        self.assertEqual(receipt["exit_code"], 7)
        self.assertIn("exited with code 7", receipt["failure_reason"])
        self.assertIn("log limit exceeded", receipt["failure_reason"])

    def test_watchdog_is_bounded_and_failure_receipt_keeps_partial_output(self):
        started = time.monotonic()
        receipt = self.run_script("os.write(1, b'before timeout')\ntime.sleep(60)\n", timeout=1)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(receipt["status"], "FAILED")
        self.assertNotEqual(receipt["exit_code"], 0)
        self.assertIn("watchdog", receipt["failure_reason"])
        self.assertEqual(receipt["log_capture"]["stdout"]["observed_bytes"], len(b"before timeout"))

    def test_descendant_holding_pipes_is_terminated_after_parent_exit(self):
        started = time.monotonic()
        receipt = self.run_script(
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "(directory / 'child.pid').write_text(str(child.pid))\nos.write(1, b'parent done')\n")
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["status"], "FAILED")
        self.assertIn("remaining experiment descendants", receipt["failure_reason"])
        pid = int((self.root / "experiments/engineering-run/child.pid").read_text())
        self.assertFalse(process_running(pid), f"test descendant {pid} survived process-tree cleanup")
        self.assertTrue(all(info["complete"] for info in receipt["log_capture"].values()))

    def test_missing_metrics_and_immutable_run_id_remain_enforced(self):
        receipt = self.run_script("(directory / 'metrics.json').unlink()\n")
        self.assertEqual(receipt["status"], "FAILED")
        with mock.patch.object(runner, "require_checkpoints", return_value=[]):
            with self.assertRaisesRegex(ValueError, "new ID"):
                runner.execute(self.project, self.root / "code/run.json")


if __name__ == "__main__":
    unittest.main()

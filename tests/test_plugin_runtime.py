"""Integration tests for durable project jobs, pure reads and real invalidation."""
from __future__ import annotations
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plugins.mathmodel.scripts.workbench import WorkbenchState, JobRunner, evaluate_guard
from plugins.mathmodel.scripts.runtime import jobs
from plugins.mathmodel.scripts.runtime.safety import MAX_LOG_BYTES, process_identity, spawn_options

TEMP = Path(os.environ.get("MATHMODEL_TEST_TEMP", ROOT / "tests/.runtime-tmp"))
TEMP.mkdir(parents=True, exist_ok=True)


def wait_job(state, jid, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        item = state.job(jid)
        if predicate(item):
            return item
        time.sleep(0.05)
    raise AssertionError(f"job did not reach expected state: {state.job(jid)}")


def wait_workers_stopped(state, timeout=15):
    """A durable terminal result can precede the worker's actual process exit.

    Windows retains a process's current directory until that process exits. Wait
    for its recorded creation identity, including completed jobs, before removing
    the fixture. A PID reused by an unrelated process must not delay cleanup.
    """
    rows = state._rows("SELECT id,pid,process_identity,child_pid,child_identity FROM jobs")
    deadline = time.monotonic() + timeout
    while True:
        alive = []
        for item in rows:
            for pid_key, identity_key in (("pid", "process_identity"), ("child_pid", "child_identity")):
                pid, identity = item[pid_key], item[identity_key]
                if pid and identity and process_identity(pid) == identity:
                    alive.append((item["id"], pid_key, pid))
        if not alive:
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f"fixture processes did not exit after terminal status: {alive}")
        time.sleep(0.025)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="中文 比赛 ", dir=TEMP)
        self.root = Path(self.temp.name)
        self.state = WorkbenchState(self.root)

    def tearDown(self):
        if self.state.db_path.exists():
            runner = JobRunner(self.state)
            for item in self.state._rows("SELECT id FROM jobs WHERE status IN ('queued','running','cancelling')"):
                runner.cancel(item["id"])
                wait_job(self.state, item["id"], lambda j: j["status"] not in {"queued", "running", "cancelling"})
            wait_workers_stopped(self.state)
        self.temp.cleanup()

    def script(self, code):
        script = self.root / "fixture.py"
        script.write_text(code, encoding="utf-8")
        return script

    def command(self, script):
        return mock.patch.object(jobs, "job_command", side_effect=lambda root, kind, opts=None: ([sys.executable, "-B", "-u", str(script)], "P5", opts or {}))

    def test_guard_and_status_queries_are_pure(self):
        before = set(self.root.rglob("*"))
        guard = evaluate_guard(self.root)
        snapshot = self.state.status()
        self.assertNotEqual(guard["status"], "COMPLETE")
        self.assertEqual(snapshot["verified_count"], 0)
        self.assertEqual(before, set(self.root.rglob("*")))
        self.assertFalse((self.root / ".mathmodel").exists())

    def test_cleanup_waits_for_terminal_worker_process_exit(self):
        self.state.initialize()
        with subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(0.5)"],
                              cwd=self.root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, **spawn_options()) as worker:
            identity = process_identity(worker.pid)
            self.assertIsNotNone(identity)
            with self.state._db() as db:
                db.execute("INSERT INTO jobs(id,type,stage,status,command,created_at,pid,process_identity) VALUES(?,?,?,?,?,?,?,?)",
                           ("terminal-worker", "model_run", "P3", "succeeded", "[]", "2026-01-01", worker.pid, identity))
            # This represents the legitimate gap after a worker commits its
            # result and before interpreter shutdown releases the Windows cwd.
            self.assertEqual(self.state.job("terminal-worker")["status"], "succeeded")
            wait_workers_stopped(self.state)
            self.assertIsNone(process_identity(worker.pid))
            self.assertEqual(worker.wait(timeout=2), 0)

    def test_atomic_admission_two_clients_and_restart_keep_running(self):
        script = self.script("import time\nprint('started',flush=True)\ntime.sleep(30)\n")
        one, two = JobRunner(self.state), JobRunner(WorkbenchState(self.root))
        with self.command(script):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                ids = list(pool.map(lambda r: r.start("model_run", {}, "same-request"), [one, two]))
            self.assertEqual(ids[0], ids[1])
            started = wait_job(self.state, ids[0], lambda j: "started" in j["log"])
            self.assertEqual(started["status"], "running")
            self.assertEqual(two.start("model_run", {}, "second-client-key"), ids[0])
            reconnected = JobRunner(WorkbenchState(self.root))
            reconnected.recover()
            self.assertEqual(reconnected.get(ids[0])["status"], "running")
            queued = two.start("preflight", {"different": True})
            self.assertEqual(two.get(queued)["status"], "queued")
            two.cancel(queued)
            wait_job(self.state, queued, lambda j: j["status"] == "cancelled")
            with self.assertRaises(ValueError):
                two.start("model_run", {"different": True}, "same-request")
            self.assertTrue(two.cancel(ids[0]))
            done = wait_job(self.state, ids[0], lambda j: j["status"] == "cancelled")
            time.sleep(0.1)
            self.assertEqual(one.get(ids[0])["status"], "cancelled")
            self.assertIn("started", done["log"])
            self.assertEqual(two.start("model_run", {}, "second-client-key"), ids[0])
            script.write_text(script.read_text() + "\n# changed after submission\n")
            with self.assertRaises(ValueError):
                two.start("model_run", {}, "same-request")

    def test_real_logs_are_paged_and_capped_without_buffering_output(self):
        script = self.script("import sys\nsys.stdout.write('a'*(3*1024*1024))\nsys.stdout.flush()\n")
        with self.command(script):
            jid = JobRunner(self.state).start("model_run")
        done = wait_job(self.state, jid, lambda j: j["status"] in {"succeeded", "failed"})
        self.assertEqual(done["status"], "succeeded", done)
        self.assertTrue(done["log_truncated"])
        self.assertEqual(done["log_bytes"], MAX_LOG_BYTES)
        page = self.state.job(jid, cursor=5, limit=11)
        self.assertEqual(page["log"], "a" * 11)
        self.assertEqual(page["next_cursor"], 16)
        self.assertTrue(page["has_more"])

    def test_cancel_terminates_descendants_and_keeps_terminal_status(self):
        script = self.script("import subprocess,sys,time,pathlib\nchild=subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'])\npathlib.Path('child.pid').write_text(str(child.pid))\nprint('started',flush=True)\ntime.sleep(90)\n")
        runner = JobRunner(self.state)
        with self.command(script):
            jid = runner.start("model_run")
        wait_job(self.state, jid, lambda j: "started" in j["log"])
        pid = int((self.root / "child.pid").read_text())
        self.assertIsNotNone(process_identity(pid))
        runner.cancel(jid)
        wait_job(self.state, jid, lambda j: j["status"] == "cancelled")
        self.assertIsNone(process_identity(pid))

    def test_dead_worker_becomes_interrupted_without_discarding_log(self):
        self.state.initialize()
        with self.state._db() as db:
            db.execute("INSERT INTO jobs(id,type,stage,status,command,created_at,pid,process_identity,log) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("dead", "model_run", "P5", "running", "[]", "2000-01-01T00:00:00+00:00", 99999999, "old", "retained"))
        JobRunner(self.state).recover()
        self.assertEqual(self.state.job("dead")["status"], "interrupted")
        self.assertEqual(self.state.job("dead")["log"], "retained")

    def test_queue_runs_in_order_and_cancels_waiting_request(self):
        script = self.script("import sys,time,pathlib\np=pathlib.Path('sequence.log')\nwith p.open('a') as f:f.write('start'+sys.argv[1]+'\\n')\ntime.sleep(1)\nwith p.open('a') as f:f.write('end'+sys.argv[1]+'\\n')\n")
        runner = JobRunner(self.state)
        resolver = lambda root, kind, opts=None: ([sys.executable, "-B", "-u", str(script), str(opts["n"])], "P3", opts)
        with mock.patch.object(jobs, "job_command", side_effect=resolver):
            ids = [runner.start("model_run", {"n": n}) for n in range(3)]
        runner.cancel(ids[2])
        for jid in ids[:2]:
            self.assertEqual(wait_job(self.state, jid, lambda j: j["status"] in {"succeeded", "failed"})["status"], "succeeded")
        self.assertEqual(wait_job(self.state, ids[2], lambda j: j["status"] == "cancelled")["status"], "cancelled")
        self.assertEqual((self.root / "sequence.log").read_text().splitlines(), ["start0", "end0", "start1", "end1"])

    def test_fingerprint_changes_with_declared_inputs_and_runtime(self):
        code = self.root / "paper_output_pro/code"
        code.mkdir(parents=True)
        script = code / "model.py"; script.write_text("print(1)\n")
        data = code / "data.csv"; data.write_text("1\n")
        spec = code / "run.json"
        spec.write_text(json.dumps({"script": "code/model.py", "inputs": ["code/data.csv"], "dependencies": []}))
        command, stage, options = jobs.job_command(self.root, "model_run", {"spec": "code/run.json"})
        one = jobs.job_fingerprint(self.root, "model_run", options, command)
        data.write_text("2\n")
        two = jobs.job_fingerprint(self.root, "model_run", options, command)
        self.assertNotEqual(one, two)
        script.write_text("print(2)\n")
        self.assertNotEqual(two, jobs.job_fingerprint(self.root, "model_run", options, command))

    def test_retry_creates_new_run_spec_without_overwriting_previous(self):
        output = self.root / "paper_output_pro"
        code = output / "code"; code.mkdir(parents=True)
        (code / "model.py").write_text("print('model')\n")
        (code / "data.csv").write_text("1\n")
        spec = {"run_id": "original-run", "script": "code/model.py", "inputs": ["code/data.csv"], "dependencies": []}
        source = code / "run.json"; source.write_text(json.dumps(spec))
        self.state.initialize()
        with self.state._db() as db:
            db.execute("INSERT INTO jobs(id,type,stage,status,command,options,created_at) VALUES(?,?,?,?,?,?,?)",
                       ("failed-original", "model_run", "P3", "failed", "[]", json.dumps({"spec": "code/run.json"}), "2000-01-01T00:00:00+00:00"))
        runner = JobRunner(self.state)
        retry = runner.retry("failed-original", "retry-click")
        item = self.state.job(retry)
        attempt = output / item["options"]["spec"]
        self.assertEqual(json.loads(source.read_text()), spec)
        self.assertNotEqual(json.loads(attempt.read_text())["run_id"], spec["run_id"])
        self.assertEqual(json.loads(attempt.read_text())["retry_provenance"]["source_job_id"], "failed-original")
        self.assertEqual(item["retry_of"], "failed-original")
        self.assertEqual(runner.retry("failed-original", "retry-click"), retry)
        # Core approval remains mandatory: a fresh fixture must not execute its model.
        done = wait_job(self.state, retry, lambda j: j["status"] not in {"queued", "running", "cancelling"})
        self.assertEqual(done["status"], "failed")
        self.assertFalse((output / "experiments").exists())

    def test_revisions_track_files_and_remove_deleted_artifacts(self):
        output = self.root / "paper_output_pro/results"
        output.mkdir(parents=True)
        result = output / "中文 数据.csv"
        result.write_text("x,y\n1,2\n", encoding="utf-8")
        one = self.state.refresh()
        same = self.state.refresh()
        self.assertEqual(one["revision"], same["revision"])
        result.write_text("x,y\n1,3\n", encoding="utf-8")
        two = self.state.refresh()
        self.assertGreater(two["revision"], one["revision"])
        self.assertNotEqual(two["artifacts"][0]["sha256"], one["artifacts"][0]["sha256"])
        result.unlink()
        self.state.refresh()
        with self.assertRaises(FileNotFoundError):
            self.state.read_artifact(one["artifacts"][0]["id"])

    def test_manual_completed_activity_does_not_promote_guard(self):
        self.state.record_event("P9", "passed", "manual")
        snapshot = self.state.status()
        self.assertNotEqual(snapshot["status"], "passed")
        self.assertEqual(snapshot["verified_count"], 0)
        self.assertEqual(snapshot["activity_status"], "awaiting_validation")

    def test_project_isolation_and_event_pagination(self):
        self.state.initialize()
        with tempfile.TemporaryDirectory(dir=TEMP) as other:
            second = WorkbenchState(other)
            self.assertNotEqual(self.state.status()["project_id"], second.status()["project_id"])
            # Insert many durable events without rerunning unrelated Guard checks.
            with self.state._db() as db:
                for index in range(205):
                    db.execute("INSERT INTO events(revision,stage,status,message,artifacts,created_at) VALUES(?,?,?,?,?,?)",
                               (self.state._bump(db), "P0", "pending", str(index), "[]", "2026-01-01"))
            first = self.state.events(limit=200)
            last = self.state.events(cursor=first["next_cursor"], limit=200)
            self.assertEqual(len(first["items"]) + len(last["items"]), 205)
            self.assertEqual(second.events()["items"], [])


if __name__ == "__main__":
    unittest.main()

"""Exercise actual loopback HTTP, descriptor validation, and service reuse."""
from __future__ import annotations
import concurrent.futures
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
import importlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plugins.mathmodel.scripts.serve_dashboard import ProjectServer
from plugins.mathmodel.scripts.runtime.service import ServiceClient, ServiceError, ensure_service
from plugins.mathmodel.scripts.runtime.safety import process_identity

TEMP = ROOT / "tests/.runtime-tmp"
TEMP.mkdir(exist_ok=True)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="中文 HTTP ", dir=TEMP)
        self.root = Path(self.temp.name)
        self.server = ProjectServer(self.root, ROOT / "plugins/mathmodel/dashboard")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.descriptor = self.server.descriptor()
        self.client = ServiceClient(self.descriptor)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(5)
        self.temp.cleanup()

    def request(self, path, method="GET", body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        conn.request(method, path, body=body, headers=headers or {})
        result = conn.getresponse()
        response = result.status, result.read()
        conn.close()
        return response

    def test_host_origin_token_and_body_limits(self):
        self.assertEqual(self.request("/api/status")[0], 401)
        token = {"X-MathModel-Token": self.server.token}
        self.assertEqual(self.request("/api/status", headers={**token, "Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("/api/status", headers={**token, "Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("/api/status", headers={**token, "Origin": "null"})[0], 403)
        self.assertEqual(self.request("/api/jobs", "POST", "{}", {**token, "Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("/api/jobs", "POST", "{}", {**token, "Content-Type": "application/json", "Content-Length": "999999"})[0], 413)

    def test_second_owner_cannot_replace_the_project_service(self):
        with self.assertRaises(TimeoutError):
            ProjectServer(self.root, ROOT / "plugins/mathmodel/dashboard")
        self.assertEqual(self.client.request("GET", "/api/health")["instance_id"], self.server.instance_id)

    def test_static_traversal_and_registered_artifact(self):
        for path in ("/dashboard/../../.mcp.json", "/dashboard/%2e%2e/.mcp.json", "/dashboard/..%5c.mcp.json"):
            self.assertEqual(self.request(path)[0], 403, path)
        output = self.root / "paper_output_pro/figures"
        output.mkdir(parents=True)
        (output / "真实 图.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        items = self.client.request("GET", "/api/artifacts?cursor=0&limit=10")
        data = self.client.request("GET", "/api/artifacts/" + items["items"][0]["id"])
        self.assertEqual(data, (output / "真实 图.csv").read_bytes())
        status = self.client.request("GET", "/api/status")
        self.assertFalse((self.root / "paper_output_pro/qa/workflow_guard_report.json").exists())
        same = self.client.request("GET", f"/api/status?after_revision={status['revision']}")
        self.assertTrue(same["unchanged"])

    def test_input_and_markdown_mime_are_explicit_and_context_is_readable(self):
        inputs = self.root / "problem_files"; inputs.mkdir()
        (inputs / "赛题.md").write_text("# 题目\n请计算最优路径。\n", encoding="utf-8")
        data = self.client.request("GET", "/api/artifacts")
        self.assertEqual(len(data), 1)
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        conn.request("GET", "/api/artifacts/" + data[0]["id"], headers={"X-MathModel-Token": self.server.token})
        result = conn.getresponse()
        self.assertEqual(result.status, 200)
        self.assertTrue(result.headers["Content-Type"].startswith("text/markdown"))
        self.assertIn("最优路径", result.read().decode("utf-8")); conn.close()
        packet = self.client.request("GET", "/api/context")
        self.assertIn("workflow", packet)

    def test_parent_directory_links_are_not_registered(self):
        outside = self.root / "outside"
        outside.mkdir(); (outside / "private.txt").write_text("private")
        output = self.root / "paper_output_pro"
        output.mkdir()
        link = output / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("symlinks unavailable")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
            if result.returncode:
                self.skipTest("junction creation unavailable")
        try:
            self.assertEqual(self.client.request("GET", "/api/artifacts"), [])
        finally:
            if link.is_symlink():
                link.unlink()
            elif link.exists():
                link.rmdir()

    def test_descriptor_cannot_redirect_token_to_external_origin(self):
        for url in ("https://example.com", "http://example.com:1234", "http://127.0.0.1:1234@evil.example:1234", "http://127.0.0.1:80/path", "http://127.0.0.1:0", "http://127.0.0.1:1234?x=1"):
            with self.assertRaises(ServiceError):
                ServiceClient({**self.descriptor, "base_url": url})


class DetachedServiceTests(unittest.TestCase):
    def test_service_restart_preserves_worker_and_second_client_can_cancel(self):
        from plugins.mathmodel.scripts.workbench import WorkbenchState, JobRunner
        with tempfile.TemporaryDirectory(prefix="恢复 比赛 ", dir=TEMP) as name:
            root = Path(name)
            descriptor = ensure_service(root)
            client = ServiceClient(descriptor)
            state = WorkbenchState(root)
            script = root / "fixture.py"
            script.write_text("import time\nprint('running-real-worker',flush=True)\ntime.sleep(60)\n")
            module = importlib.import_module(JobRunner.__module__)
            with mock.patch.object(module, "job_command", return_value=([sys.executable, "-B", "-u", str(script)], "P3", {})):
                jid = JobRunner(state).start("model_run", idempotency_key="restart-proof")
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    job = client.request("GET", f"/api/jobs/{jid}")
                    if "running-real-worker" in job["log"]:
                        break
                    time.sleep(0.1)
                self.assertEqual(job["status"], "running", job)
                client.request("POST", "/api/shutdown", {})
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and process_identity(descriptor["pid"]) == descriptor["process_identity"]:
                    time.sleep(0.05)
                replacement = ensure_service(root)
                self.assertNotEqual(descriptor["instance_id"], replacement["instance_id"])
                client = ServiceClient(replacement)
                self.assertEqual(client.request("GET", f"/api/jobs/{jid}")["status"], "running")
                client.request("POST", f"/api/jobs/{jid}/cancel", {})
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    job = client.request("GET", f"/api/jobs/{jid}")
                    if job["status"] == "cancelled":
                        break
                    time.sleep(0.1)
                self.assertEqual(job["status"], "cancelled")
                descriptor = replacement
            finally:
                try:
                    client.request("POST", f"/api/jobs/{jid}/cancel", {})
                    client.request("POST", "/api/shutdown", {})
                finally:
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline and process_identity(descriptor["pid"]) == descriptor["process_identity"]:
                        time.sleep(0.05)

    def test_concurrent_clients_reuse_service_and_new_process_recovers(self):
        with tempfile.TemporaryDirectory(prefix="独立 比赛 ", dir=TEMP) as name:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                descriptors = list(pool.map(ensure_service, [name, name]))
            one, two = descriptors
            self.assertEqual(one["instance_id"], two["instance_id"])
            client = ServiceClient(one)
            self.assertEqual(client.request("GET", "/api/health")["instance_id"], one["instance_id"])
            try:
                code = "import sys,json;sys.path.insert(0,sys.argv[1]);from plugins.mathmodel.scripts.runtime.service import ensure_service;print(json.dumps(ensure_service(sys.argv[2])))"
                result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT), name], capture_output=True, text=True, encoding="utf-8", timeout=25)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["instance_id"], one["instance_id"])
            finally:
                client.request("POST", "/api/shutdown", {})
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline and process_identity(one["pid"]) == one["process_identity"]:
                    time.sleep(0.05)


if __name__ == "__main__":
    unittest.main()

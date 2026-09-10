"""Actual ZIP -> readonly installation -> official MCP SDK -> project service.

These are engineering fixtures, not contest results, reviews, or approvals.
Windows chmod marks files read-only (not a deny-write directory ACL); POSIX chmod
removes directory writes, though a root test process can override that restriction.
In both cases a full installed-file inventory/hash check detects any cache writes.
"""
from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
import importlib.util
import json
import os
from pathlib import Path
import stat
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request, build_opener, ProxyHandler
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.build_plugin_package import build, verify
from plugins.mathmodel.scripts.runtime.safety import file_hash, process_identity, terminate_tree


@unittest.skipUnless(importlib.util.find_spec("mcp"), "official MCP Python SDK is required")
class InstalledPluginTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cache = Path(os.environ.get("MATHMODEL_TEST_TMP", "G:/DevCache/Temp/mathmodel-insert/installation-tests"
                                  if os.name == "nt" else str(Path(tempfile.gettempdir())/"mathmodel-installation-tests")))
        cache.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="发行物 MCP ", dir=cache)
        cls.base = Path(cls.temp.name)
        cls.install = cls.base/"只读插件缓存"/"mathmodel"
        cls.install.mkdir(parents=True)
        cls.archive = build(cls.base/"MathModel.zip")
        failures = verify(cls.archive)
        if failures:
            raise AssertionError(f"built archive does not match source: {failures}")
        with zipfile.ZipFile(cls.archive) as archive:
            archive.extractall(cls.install)
        cls.installed_hashes = {p.relative_to(cls.install).as_posix(): file_hash(p)
                                for p in cls.install.rglob("*") if p.is_file()}
        for path in cls.install.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IREAD if os.name == "nt" else 0o444)
        if os.name != "nt":
            for path in sorted((p for p in cls.install.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                path.chmod(0o555)
            cls.install.chmod(0o555)

    @classmethod
    def tearDownClass(cls):
        if cls.install.exists():
            cls.install.chmod(0o755)
            for directory, folders, filenames in os.walk(cls.install):
                for name in folders:
                    (Path(directory)/name).chmod(0o755)
                for name in filenames:
                    (Path(directory)/name).chmod(stat.S_IWRITE | stat.S_IREAD if os.name == "nt" else 0o644)
        cls.temp.cleanup()

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 10
        self.project = self.base/"独立中文 比赛目录"
        self.project.mkdir()
        (self.project/"problem_files").mkdir()
        (self.project/"problem_files/工程测试说明.txt").write_text(
            "ENGINEERING TEST FIXTURE. This is not a contest submission or approved model.\n", encoding="utf-8")
        (self.project/"paper_output_pro").mkdir()
        (self.project/"paper_output_pro/工程测试记录.md").write_text("# 工程测试\n真实文字附件读取。\n", encoding="utf-8")
        (self.project/"paper_output_pro/像素测试.png").write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jSyoAAAAASUVORK5CYII="))
        self.runtime = self.base/"可写运行配置"
        self.job_ids = []
        self.session_number = 0
        self.environment = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                            "PYTHONDONTWRITEBYTECODE": "1", "TEMP": str(self.base), "TMP": str(self.base), "TMPDIR": str(self.base)}
        prepare = await asyncio.to_thread(subprocess.run, [sys.executable, "-B", str(self.install/"scripts/setup_runtime.py"),
            "--project-root", str(self.project), "--runtime-root", str(self.runtime), "--python", sys.executable],
            cwd=self.project, capture_output=True, text=True, encoding="utf-8", env=self.environment, timeout=60)
        self.assertEqual(prepare.returncode, 0, prepare.stdout+prepare.stderr)
        self.config = json.loads((self.runtime/"mcp.local.json").read_text(encoding="utf-8"))["mcpServers"]["mathmodel"]
        self.assertTrue(Path(self.config["command"]).is_absolute())
        self.assertTrue(Path(self.config["args"][-1]).is_absolute())
        self.assertTrue(Path(self.config["args"][-1]).is_relative_to(self.install))
        self.assertFalse((self.project/".agents/skills").exists())

    def descriptor(self):
        return json.loads((self.project/".mathmodel/service.json").read_text(encoding="utf-8"))

    def http(self, descriptor, path, body=None):
        encoded = None if body is None else json.dumps(body).encode()
        request = Request(descriptor["base_url"]+path, data=encoded,
                          headers={"X-MathModel-Token": descriptor["token"], "Content-Type": "application/json"},
                          method="GET" if body is None else "POST")
        with build_opener(ProxyHandler({})).open(request, timeout=15) as response:
            return json.load(response)

    def stored_job(self, job_id):
        database = self.project/".mathmodel/workbench.sqlite3"
        with sqlite3.connect(database.as_uri()+"?mode=ro", uri=True, timeout=15) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else {}

    async def asyncTearDown(self):
        descriptor_path = self.project/".mathmodel/service.json"
        if descriptor_path.exists():
            descriptor = self.descriptor()
            for job_id in self.job_ids:
                try:
                    await asyncio.to_thread(self.http, descriptor, f"/api/jobs/{job_id}/cancel", {})
                except (OSError, ValueError):
                    pass
            deadline = time.monotonic()+15
            while time.monotonic() < deadline:
                try:
                    status = await asyncio.to_thread(self.http, descriptor, "/api/status")
                    if not any(job["status"] in {"queued", "running", "cancelling"} for job in status.get("jobs", [])):
                        break
                except (OSError, ValueError):
                    break
                await asyncio.sleep(0.1)
            for job_id in self.job_ids:
                saved = self.stored_job(job_id)
                for pid_field, identity_field in (("child_pid", "child_identity"), ("pid", "process_identity")):
                    pid, identity = saved.get(pid_field), saved.get(identity_field)
                    if type(pid) is not int or not identity:
                        continue
                    worker_deadline = time.monotonic()+3
                    while time.monotonic() < worker_deadline and process_identity(pid) == identity:
                        await asyncio.sleep(0.05)
                    if process_identity(pid) == identity:
                        terminate_tree(pid, identity)
                    self.assertNotEqual(process_identity(pid), identity, "test worker or experiment was not stopped")
            try:
                await asyncio.to_thread(self.http, descriptor, "/api/shutdown", {})
            except (OSError, ValueError):
                pass
            deadline = time.monotonic()+8
            while time.monotonic() < deadline and process_identity(descriptor["pid"]) == descriptor["process_identity"]:
                await asyncio.sleep(0.1)
            if process_identity(descriptor["pid"]) == descriptor["process_identity"]:
                terminate_tree(descriptor["pid"], descriptor["process_identity"])
            self.assertNotEqual(process_identity(descriptor["pid"]), descriptor["process_identity"], "test service was not stopped")
        current = {p.relative_to(self.install).as_posix(): file_hash(p) for p in self.install.rglob("*") if p.is_file()}
        self.assertEqual(current, self.installed_hashes, "installed read-only payload was changed or gained generated files")

    @asynccontextmanager
    async def session(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        parameters = StdioServerParameters(command=self.config["command"], args=self.config["args"],
            cwd=str(self.project), env={**self.environment, **self.config.get("env", {})})
        self.session_number += 1
        with (self.base/f"mcp-session-{self.session_number}.log").open("w", encoding="utf-8") as error_log:
            async with stdio_client(parameters, errlog=error_log) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.serverInfo.name, "mathmodel")
                    yield session

    async def call(self, session, name, **arguments):
        result = await session.call_tool(name, arguments)
        text = "\n".join(item.text for item in result.content if getattr(item, "type", None) == "text")
        self.assertFalse(result.isError, f"{name} failed: {text}")
        if result.structuredContent is not None:
            return result.structuredContent
        return json.loads(text)

    async def test_release_zip_real_protocol_reuses_service_and_preserves_gate_truth(self):
        async with asyncio.timeout(150):
            async with self.session() as first:
                discovered = {tool.name for tool in (await first.list_tools()).tools}
                self.assertTrue({"open_workspace", "get_context_packet", "get_status", "list_artifacts", "read_artifact",
                                 "run_job", "get_job", "cancel_job"} <= discovered)
                opened = await self.call(first, "open_workspace", project_root=str(self.project))
                self.assertEqual(Path(opened["project_root"]), self.project)
                self.assertTrue(opened["dashboard_url"].startswith("http://127.0.0.1:"))
                descriptor = self.descriptor()
                self.assertEqual(Path(descriptor["plugin_root"]), self.install)
                initial = await self.call(first, "get_status", project_root=str(self.project))
                self.assertEqual(initial["core_edition"], "pro")
                self.assertNotEqual(initial["status"], "passed")
                packet = await self.call(first, "get_context_packet", project_root=str(self.project))
                self.assertEqual(packet["workflow"]["next_step"], "P0")
                self.assertEqual(packet["handoff"]["skill_id"], "pro-workflow-orchestrator")

                artifacts = await self.call(first, "list_artifacts", project_root=str(self.project), limit=50)
                text_item = next(item for item in artifacts["items"] if item["path"].endswith("工程测试记录.md"))
                image_item = next(item for item in artifacts["items"] if item["path"].endswith("像素测试.png"))
                text = await self.call(first, "read_artifact", project_root=str(self.project), artifact_id=text_item["id"], limit=6)
                self.assertEqual(len(text["content"]), 6)
                self.assertIsNotNone(text["next_offset"])
                picture = await self.call(first, "read_artifact", project_root=str(self.project), artifact_id=image_item["id"])
                self.assertEqual(picture["mime_type"], "image/png")
                self.assertIsNone(picture["content"])
                self.assertIn("preview_url", picture)

                await asyncio.to_thread(self.http, descriptor, "/api/events", {
                    "stage": "P9", "status": "passed", "message": "ENGINEERING FAULT INJECTION: manual PASS must not grant acceptance"})
                manual = await self.call(first, "get_status", project_root=str(self.project))
                self.assertNotEqual(manual["status"], "passed")
                self.assertEqual(manual["verified_count"], initial["verified_count"])

                async with self.session() as second:
                    second_status = await self.call(second, "get_status", project_root=str(self.project))
                    self.assertNotEqual(second_status["status"], "passed")
                    same = self.descriptor()
                    for key in ("pid", "process_identity", "instance_id", "base_url"):
                        self.assertEqual(same[key], descriptor[key])
                    request = {"project_root": str(self.project), "job_type": "evidence_check", "idempotency_key": "installed-engineering-check"}
                    started = await self.call(first, "run_job", **request)
                    self.job_ids.append(started["job_id"])
                    duplicate = await self.call(second, "run_job", **request)
                    self.assertEqual(started["job_id"], duplicate["job_id"])
                    deadline = time.monotonic()+45
                    while True:
                        job = await self.call(second, "get_job", project_root=str(self.project), job_id=started["job_id"], limit=40000)
                        if job["status"] in {"succeeded", "failed", "cancelled", "interrupted"}:
                            break
                        self.assertLess(time.monotonic(), deadline, "installed verification job timed out")
                        await asyncio.sleep(0.2)
                    self.assertEqual(job["status"], "failed", "incomplete engineering input must fail Pro evidence validation")
                    self.assertEqual(job["exit_code"], 2)  # pro_status: required stages have not passed
                    self.assertTrue(job["log"])
                    validation = json.loads(job["log"])
                    self.assertEqual(validation["next_step"], "P0")
                    self.assertNotEqual(validation["status"], "COMPLETE")
                    command = json.loads(self.stored_job(started["job_id"])["command"])
                    self.assertTrue(any(str(self.install) in part and part.endswith("pro_status.py") for part in command))
                final = await self.call(first, "get_status", project_root=str(self.project))
                self.assertNotEqual(final["status"], "passed")
                self.assertEqual(self.descriptor()["instance_id"], descriptor["instance_id"])


if __name__ == "__main__":
    unittest.main()

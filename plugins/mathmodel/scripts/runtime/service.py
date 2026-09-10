"""Connect clients to one persistent, loopback service for each project."""
from __future__ import annotations
import json
import hashlib
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path
from .locks import FileLock
from .safety import is_link, process_identity, spawn_options, reap_process

PROTOCOL_VERSION = 1


def runtime_fingerprint():
    plugin = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    digest.update(json.dumps([sys.executable, sys.version]).encode())
    paths = [plugin / ".codex-plugin/plugin.json", plugin / ".mcp.json", *sorted((plugin / "scripts").rglob("*.py")),
             *sorted(p for p in (plugin / "skills").rglob("*") if p.suffix in {".py", ".json", ".yaml", ".yml"})]
    for path in paths:
        if "__pycache__" in path.parts or not path.is_file():
            continue
        digest.update(path.relative_to(plugin).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_descriptor(descriptor):
    url = urllib.parse.urlsplit(str(descriptor.get("base_url", "")))
    try:
        port = url.port
    except ValueError as exc:
        raise ServiceError("invalid service port") from exc
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or url.username is not None or url.password is not None
            or url.path not in {"", "/"} or url.query or url.fragment or not port or not 1 <= port <= 65535):
        raise ServiceError("service descriptor must use a plain 127.0.0.1 origin")
    if not isinstance(descriptor.get("token"), str) or len(descriptor["token"]) < 16:
        raise ServiceError("invalid service token")


class ServiceError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ServiceError("local service redirects are rejected")


class ServiceClient:
    def __init__(self, descriptor, timeout=50):
        validate_descriptor(descriptor)
        self.descriptor = descriptor
        self.timeout = timeout

    def request(self, method, path, payload=None):
        validate_descriptor(self.descriptor)
        if not path.startswith("/api/") or path.startswith("//"):
            raise ValueError("only runtime API paths are supported")
        data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        headers = {"X-MathModel-Token": self.descriptor["token"]}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.descriptor["base_url"] + path, data=data, headers=headers, method=method.upper())
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            with opener.open(req, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                content = response.read(26 * 1024 * 1024)
                return json.loads(content) if "application/json" in content_type else content
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read(8192)).get("error", str(exc))
            except (ValueError, AttributeError):
                message = str(exc)
            raise ServiceError(message, exc.code) from exc
        except (OSError, urllib.error.URLError) as exc:
            raise ServiceError(f"MathModel 服务连接失败：{exc}") from exc


def _descriptor(root):
    path = root / ".mathmodel/service.json"
    if not path.is_file() or is_link(path) or is_link(path.parent):
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("protocol_version") != PROTOCOL_VERSION or value.get("project_root") != str(root):
            return None
        if not value.get("process_identity") or process_identity(int(value.get("pid", 0))) != value["process_identity"]:
            return None
        health = ServiceClient(value, timeout=1).request("GET", "/api/health")
        if health.get("instance_id") != value.get("instance_id") or health.get("project_id") != value.get("project_id"):
            return None
        expected_plugin = str(Path(__file__).resolve().parents[2])
        if value.get("plugin_root") != expected_plugin or health.get("runtime_fingerprint") != runtime_fingerprint():
            if health.get("active_job_count", 0):
                raise ServiceError("插件版本已更新，但旧服务仍有实验运行。请等待或取消该实验后重试；不会中断活任务。", 409)
            ServiceClient(value).request("POST", "/api/shutdown", {})
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and process_identity(value["pid"]) == value["process_identity"]:
                time.sleep(0.05)
            return None
        return value
    except ServiceError as exc:
        if exc.status == 409:
            raise
        return None
    except (OSError, ValueError, KeyError):
        return None


def ensure_service(project_root, *, timeout=20, dashboard_root=None):
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("比赛项目目录不存在")
    state_dir = root / ".mathmodel"
    if is_link(state_dir):
        raise PermissionError("linked runtime directory")
    existing = _descriptor(root)
    if existing:
        return existing
    with FileLock(state_dir / "startup.lock", timeout):
        existing = _descriptor(root)
        if existing:
            return existing
        script = Path(__file__).resolve().parents[1] / "serve_dashboard.py"
        command = [sys.executable, "-B", "-u", str(script), "--project-root", str(root), "--port", "0"]
        if dashboard_root is not None:
            command += ["--dashboard-root", str(Path(dashboard_root).resolve())]
        log_path = state_dir / "service-startup.log"
        if is_link(log_path):
            raise PermissionError("linked startup log")
        # Request logging is disabled, so the service log cannot grow per polling request.
        with log_path.open("wb") as log:
            process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                                       **spawn_options(detached=True))
        reap_process(process)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            existing = _descriptor(root)
            if existing:
                return existing
            if process.poll() is not None:
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise ServiceError(f"MathModel 服务启动失败：{detail}")
            time.sleep(0.1)
        raise ServiceError("MathModel 服务启动超时；请检查项目 .mathmodel/service-startup.log。")

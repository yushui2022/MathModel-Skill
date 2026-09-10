#!/usr/bin/env python3
"""Single-owner, authenticated loopback MathModel project service."""
from __future__ import annotations
import argparse
import http.server
import json
import mimetypes
import os
import secrets
import sys
import threading
import urllib.parse
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workbench import WorkbenchState, JobRunner, project_id
from runtime.locks import FileLock
from runtime.safety import MAX_ARTIFACT_BYTES, atomic_json, contained_file, process_identity, artifact_mime
from runtime.service import PROTOCOL_VERSION, runtime_fingerprint
from runtime.pdf_preview import preview_pdf, PDFPreviewError

MAX_BODY = 16 * 1024


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def _send(self, body, content_type="application/json; charset=utf-8", status=200, extra=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if content_type.startswith("application/json") and len(body) > 8 * 1024 * 1024:
            body = b'{"error":"response too large; use paginated artifact/log endpoints"}'
            status = 413
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _validate(self, *, mutation=False):
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host", "").lower()
        if host not in hosts:
            raise PermissionError("Host rejected")
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{value}" for value in hosts}:
            raise PermissionError("Origin rejected")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise PermissionError("cross-site request rejected")
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        if "\\" in path or "\x00" in path or any(x == ".." for x in path.split("/")):
            raise PermissionError("invalid path")
        query = urllib.parse.parse_qs(parsed.query)
        if path.startswith("/api/") or mutation:
            token = self.headers.get("X-MathModel-Token") or query.get("token", [""])[0]
            if not secrets.compare_digest(token, self.server.token):
                self._send({"error": "Unauthorized"}, status=401)
                return None
        return path, query

    def _error(self, exc):
        status = 403 if isinstance(exc, PermissionError) else 404 if isinstance(exc, (FileNotFoundError, KeyError)) else 409 if isinstance(exc, RuntimeError) else 400
        if isinstance(exc, PDFPreviewError):
            status = exc.status
        self._send({"error": str(exc)}, status=status)

    def do_GET(self):
        try:
            request = self._validate()
            if request is None:
                return
            path, query = request
            state, runner = self.server.state, self.server.runner
            if path == "/api/health":
                active = state._rows("SELECT id FROM jobs WHERE status IN ('queued','running','cancelling')")
                self._send({"instance_id": self.server.instance_id, "project_id": project_id(state.root), "protocol_version": PROTOCOL_VERSION,
                            "runtime_fingerprint": self.server.runtime_fingerprint, "active_job_count": len(active)})
            elif path == "/api/status":
                runner.recover()
                data = state.refresh()
                after = query.get("after_revision", [None])[0]
                if after is not None and int(after) == data["revision"]:
                    self._send({"unchanged": True, "revision": data["revision"]})
                else:
                    data["artifact_total"] = len(data["artifacts"])
                    data["artifacts_next_cursor"] = 500 if len(data["artifacts"]) > 500 else None
                    data["artifacts"] = data["artifacts"][:500]
                    self._send(data)
            elif path == "/api/context":
                from build_context_packet import build_packet
                self._send(build_packet(state.root, question_id=query.get("question_id", [None])[0],
                                        max_chars=int(query.get("max_chars", [8000])[0]), cursor=int(query.get("cursor", [0])[0]),
                                        source_revision=query.get("source_revision", [None])[0]))
            elif path == "/api/events":
                page = state.events(int(query.get("cursor", [0])[0]), int(query.get("limit", [100])[0]))
                if "cursor" in query or "limit" in query:
                    self._send(page)
                else:
                    recent = state._rows("SELECT * FROM events ORDER BY id DESC LIMIT 100")
                    recent.reverse()
                    for item in recent:
                        item["artifacts"] = json.loads(item["artifacts"] or "[]"); item["timestamp"] = item.pop("created_at")
                    self._send(("\n".join(json.dumps(x, ensure_ascii=False) for x in recent) + "\n").encode(), "application/x-ndjson; charset=utf-8")
            elif path == "/api/artifacts":
                items = state.artifacts(query.get("kind", [None])[0])
                if "cursor" in query or "limit" in query:
                    cursor = max(0, int(query.get("cursor", [0])[0])); limit = max(1, min(200, int(query.get("limit", [100])[0])))
                    self._send({"items": items[cursor:cursor + limit], "total": len(items),
                                "next_cursor": cursor + limit if cursor + limit < len(items) else None})
                else:
                    self._send(items[:2000])
            elif path.startswith("/api/jobs/"):
                self._send(runner.get(path.rsplit("/", 1)[-1], int(query.get("cursor", [0])[0]), int(query.get("limit", [65536])[0])))
            elif path.startswith("/api/artifacts/") and path.endswith(("/pdf-info", "/pdf-page")):
                parts = path.split("/")
                if len(parts) != 5:
                    raise FileNotFoundError("Not found")
                target, meta = state.read_artifact(parts[3])
                page = None if parts[4] == "pdf-info" else int(query.get("page", ["0"])[0])
                result = preview_pdf(state.root, target.relative_to(state.root).as_posix(), page=page)
                self._send({"artifact_id": parts[3], **result} if page is None else result,
                           "application/json; charset=utf-8" if page is None else "image/png")
            elif path.startswith(("/api/artifact/", "/api/artifacts/")):
                target, meta = state.read_artifact(path.rsplit("/", 1)[-1])
                mime = artifact_mime(target)
                # Untrusted active documents are always downloads, never same-origin HTML.
                extra = {}
                if target.suffix.lower() in {".html", ".htm", ".svg", ".xml", ".js"} or query.get("download") == ["1"]:
                    extra["Content-Disposition"] = "attachment; filename*=UTF-8''" + urllib.parse.quote(target.name)
                    mime = "application/octet-stream"
                self._send(target.read_bytes(), mime, extra=extra)
            else:
                relative = "index.html" if path in {"/", "/index.html"} else path.removeprefix("/dashboard/") if path.startswith("/dashboard/") else None
                if relative is None:
                    raise FileNotFoundError("Not found")
                target = contained_file(self.server.dashboard_root, relative, limit=MAX_ARTIFACT_BYTES)
                self._send(target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            self._error(exc)
        except Exception:
            self._send({"error": "无法读取项目状态；请检查运行时数据文件。"}, status=500)

    def do_POST(self):
        try:
            request = self._validate(mutation=True)
            if request is None:
                return
            path, query = request
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("chunked requests are unsupported")
            raw_length = self.headers.get("Content-Length", "0")
            if not raw_length.isdigit() or not 0 <= int(raw_length) <= MAX_BODY:
                self._send({"error": "request body exceeds limit"}, status=413)
                return
            if self.headers.get_content_type() != "application/json":
                self._send({"error": "application/json required"}, status=415)
                return
            data = json.loads(self.rfile.read(int(raw_length)) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("JSON body must be an object")
            if path not in {"/api/shutdown"} and not path.endswith("/cancel") and runtime_fingerprint() != self.server.runtime_fingerprint:
                raise RuntimeError("插件代码已更新，请重新连接项目服务后提交新任务。运行中任务仍可取消。")
            if path == "/api/jobs":
                if set(data) - {"type", "options", "idempotency_key"}:
                    raise ValueError("unsupported job parameter")
                self.server.runner.recover()
                jid = self.server.runner.start(data.get("type", ""), data.get("options"), data.get("idempotency_key"))
                self._send({"job_id": jid, "status": self.server.runner.get(jid)["status"]}, status=202)
            elif path.startswith("/api/jobs/") and path.endswith("/cancel"):
                self._send({"cancelled": self.server.runner.cancel(path.split("/")[3])})
            elif path.startswith("/api/jobs/") and path.endswith("/retry"):
                if set(data) - {"idempotency_key"}:
                    raise ValueError("unsupported retry parameter")
                original = path.split("/")[3]
                jid = self.server.runner.retry(original, data.get("idempotency_key"))
                self._send({"job_id": jid, "status": self.server.runner.get(jid)["status"], "retry_of": original}, status=202)
            elif path == "/api/events":
                if set(data) - {"stage", "status", "message", "current_task", "artifacts"}:
                    raise ValueError("unsupported activity field")
                self._send(self.server.state.record_event(**data), status=201)
            elif path == "/api/shutdown":
                # Controlled service stop leaves durable workers alive for reconnect.
                self._send({"stopping": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                raise FileNotFoundError("Not found")
        except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
            self._error(exc)
        except Exception:
            self._send({"error": "运行时操作失败；请检查项目状态。"}, status=500)

    def log_message(self, *args):
        pass  # Never log session tokens or unbounded browser polling.


class ProjectServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, root, dashboard_root, port=0, token=None):
        self.state = WorkbenchState(root)
        self.state.initialize()
        self.dashboard_root = Path(dashboard_root).resolve()
        self.token = token or secrets.token_urlsafe(32)
        self.instance_id = uuid.uuid4().hex
        self.runtime_fingerprint = runtime_fingerprint()
        self._owner_lock = FileLock(self.state.state_dir / "service.lock", timeout=0)
        self._owner_lock.acquire()
        try:
            super().__init__(("127.0.0.1", port), DashboardHandler)
            self.runner = JobRunner(self.state, owner=self.instance_id)
            self.runner.recover()
            self._stop_supervisor = threading.Event()
            self._supervisor = threading.Thread(target=self._supervise, daemon=True)
            self._supervisor.start()
        except Exception:
            self._owner_lock.release()
            if hasattr(self, "socket"):
                super().server_close()
            raise

    def _supervise(self):
        while not self._stop_supervisor.wait(1):
            try:
                self.runner.recover()
            except Exception:
                # Transient file/database locks must not destroy the owner loop.
                pass

    def server_close(self):
        if hasattr(self, "_stop_supervisor"):
            self._stop_supervisor.set()
            self._supervisor.join(timeout=3)
        super().server_close()
        if hasattr(self, "_owner_lock"):
            self._owner_lock.release()

    def descriptor(self):
        base = f"http://127.0.0.1:{self.server_address[1]}"
        return {"protocol_version": PROTOCOL_VERSION, "project_id": project_id(self.state.root), "project_root": str(self.state.root),
                "base_url": base, "dashboard_url": base + "/?token=" + self.token, "token": self.token,
                "pid": os.getpid(), "process_identity": process_identity(os.getpid()), "instance_id": self.instance_id,
                "plugin_root": str(Path(__file__).resolve().parents[1]), "runtime_fingerprint": self.runtime_fingerprint}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--dashboard-root", default=str(Path(__file__).resolve().parents[1] / "dashboard"))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("MathModel only supports loopback listening")
    state = WorkbenchState(args.project_root)
    state.initialize()
    with ProjectServer(state.root, args.dashboard_root, args.port) as server:
        descriptor = server.descriptor()
        atomic_json(state.state_dir / "service.json", descriptor)
        print("MathModel dashboard: " + descriptor["dashboard_url"], flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

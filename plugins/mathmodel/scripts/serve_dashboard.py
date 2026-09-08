#!/usr/bin/env python3
"""Serve the local MathModel progress dashboard without third-party packages."""

from __future__ import annotations

import argparse
import http.server
import json
import mimetypes
import os
import socketserver
import urllib.parse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workbench import WorkbenchState


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    project_root: Path
    dashboard_root: Path
    state: WorkbenchState

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            body = json.dumps(self.state.status(), ensure_ascii=False).encode("utf-8")
            self._send(body, "application/json; charset=utf-8")
            return
        if parsed.path == "/api/events":
            path = self.project_root / ".mathmodel" / "events.jsonl"
            body = path.read_bytes() if path.exists() else b""
            self._send(body, "application/x-ndjson; charset=utf-8")
            return
        if parsed.path == "/api/artifacts":
            kind = urllib.parse.parse_qs(parsed.query).get("kind", [None])[0]
            self._send(json.dumps(self.state.artifacts(kind), ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return
        if parsed.path.startswith("/api/artifact/"):
            try:
                path, meta = self.state.read_artifact(parsed.path.removeprefix("/api/artifact/"))
                if path.stat().st_size > 25 * 1024 * 1024: raise PermissionError("file too large")
                self._send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            except FileNotFoundError: self._send(b"Not found", "text/plain; charset=utf-8", 404)
            except PermissionError: self._send(b"Forbidden", "text/plain; charset=utf-8", 403)
            return
        if parsed.path == "/" or parsed.path == "/index.html":
            self._send((self.dashboard_root / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/dashboard/"):
            self._serve_file(self.dashboard_root / parsed.path.removeprefix("/dashboard/"))
            return
        self._send(b"Not found", "text/plain; charset=utf-8", 404)

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            self._send(b"Not found", "text/plain; charset=utf-8", 404)
            return
        self._send(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")

    def log_message(self, format: str, *args: object) -> None:
        print(format % args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--dashboard-root", default=str(Path(__file__).resolve().parents[1] / "dashboard"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    DashboardHandler.project_root = Path(args.project_root).resolve()
    DashboardHandler.dashboard_root = Path(args.dashboard_root).resolve()
    DashboardHandler.state = WorkbenchState(DashboardHandler.project_root)
    with socketserver.ThreadingTCPServer((args.host, args.port), DashboardHandler) as server:
        print(f"MathModel dashboard: http://{args.host}:{args.port}/")
        print(f"Project: {DashboardHandler.project_root}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

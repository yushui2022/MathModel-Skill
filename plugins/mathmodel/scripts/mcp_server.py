#!/usr/bin/env python3
"""Optional MCP adapter for the local MathModel workbench.

Install ``mcp`` (the official Python SDK) to expose these tools to a host.  The
state and job logic remains usable without the dependency through workbench.py.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
try:  # direct plugin execution
    from workbench import JobRunner, WorkbenchState, project_id
    from build_context_packet import build_packet
except ModuleNotFoundError:  # package imports in tests and host adapters
    from .workbench import JobRunner, WorkbenchState, project_id
    from .build_context_packet import build_packet

_states: dict[str, WorkbenchState] = {}
_runners: dict[str, JobRunner] = {}
_dashboard_processes: dict[str, subprocess.Popen[str]] = {}
_dashboard_urls: dict[str, str] = {}

def _state(root: str) -> WorkbenchState:
    p = str(Path(root).expanduser().resolve())
    if p not in _states:
        _states[p] = WorkbenchState(p); _runners[p] = JobRunner(_states[p])
    return _states[p]

def open_workspace(project_root: str) -> dict:
    s = _state(project_root)
    key = str(s.root)
    if key not in _dashboard_urls:
        try:
            script = Path(__file__).resolve().with_name("serve_dashboard.py")
            proc = subprocess.Popen([sys.executable, "-u", str(script), "--project-root", str(s.root), "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
            line = proc.stdout.readline().strip() if proc.stdout else ""
            url = line.split(": ", 1)[-1] if "MathModel dashboard:" in line else ""
            _dashboard_processes[key], _dashboard_urls[key] = proc, (url or os.environ.get("MATHMODEL_DASHBOARD_URL", "http://127.0.0.1:8765/"))
        except OSError:
            _dashboard_urls[key] = os.environ.get("MATHMODEL_DASHBOARD_URL", "http://127.0.0.1:8765/")
    return {"project_id": project_id(s.root), "project_root": str(s.root), "dashboard_url": _dashboard_urls[key], "status": s.status()}

def get_status(project_root: str) -> dict: return _state(project_root).status()
def list_artifacts(project_root: str, kind: str | None = None) -> list[dict]: return _state(project_root).artifacts(kind)
def read_artifact(project_root: str, artifact_id: str) -> dict:
    path, meta = _state(project_root).read_artifact(artifact_id)
    data = path.read_bytes()
    return {"artifact": meta, "content": data.decode("utf-8", errors="replace") if len(data) < 2_000_000 else "[文件过大，请在看板中预览]"}
def run_job(project_root: str, job_type: str) -> dict:
    s = _state(project_root); return {"job_id": _runners[str(s.root)].start(job_type), "status": "running"}
def get_job(project_root: str, job_id: str) -> dict: return _runners[str(_state(project_root).root)].get(job_id)
def cancel_job(project_root: str, job_id: str) -> dict: return {"cancelled": _runners[str(_state(project_root).root)].cancel(job_id)}
def get_next_action(project_root: str) -> dict:
    packet = build_packet(project_root)
    workflow = packet["workflow"]
    return {"recommended_skill": workflow["recommended_skill"], "next_action": workflow["next_action"], "next_step": workflow["next_step"], "blockers": workflow["blockers"]}

def get_context_packet(project_root: str) -> dict:
    """Return the stateless handoff context used by every resumed conversation."""
    return build_packet(project_root)

def main() -> int:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise SystemExit("MathModel MCP requires the optional dependency 'mcp'. Install it with: python -m pip install mcp")
    app = FastMCP("mathmodel")
    for fn in (open_workspace, get_status, list_artifacts, read_artifact, run_job, get_job, cancel_job, get_next_action, get_context_packet): app.tool()(fn)
    app.run()
    return 0

if __name__ == "__main__": raise SystemExit(main())

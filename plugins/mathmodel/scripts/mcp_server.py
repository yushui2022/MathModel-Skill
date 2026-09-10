#!/usr/bin/env python3
"""Official MCP SDK adapter. Only the project service owns experiment processes."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, ProxyHandler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
from runtime.service import ServiceClient, ensure_service, validate_descriptor, _NoRedirect


def _client(project_root: str) -> ServiceClient:
    return ServiceClient(ensure_service(project_root))


def open_workspace(project_root: str) -> dict:
    """Bind an existing contest directory; return its healthy right-panel URL."""
    descriptor = ensure_service(project_root)
    return {k: descriptor[k] for k in ("project_id", "project_root", "dashboard_url")} | {
        "status": ServiceClient(descriptor).request("GET", "/api/status"),
        "display": "Open dashboard_url with the Codex host open_in_codex browser capability when available."}


def get_status(project_root: str, after_revision: int | None = None) -> dict:
    """Read real stage validations, jobs, and blockers; never grant PASS from events."""
    suffix = "?" + urlencode({"after_revision": after_revision}) if after_revision is not None else ""
    return _client(project_root).request("GET", "/api/status" + suffix)


def list_artifacts(project_root: str, kind: str | None = None, cursor: int = 0, limit: int = 50) -> dict:
    """Page through registered contest inputs, code, scientific results and papers."""
    args = {"cursor": cursor, "limit": limit}
    if kind:
        args["kind"] = kind
    return _client(project_root).request("GET", "/api/artifacts?" + urlencode(args))


def read_artifact(project_root: str, artifact_id: str, offset: int = 0, limit: int = 40000) -> dict:
    """Read bounded text or return a typed local preview link for binary artifacts."""
    if offset < 0 or not 1 <= limit <= 100000:
        raise ValueError("offset must be nonnegative; limit must be 1..100000")
    if not artifact_id.isalnum() or len(artifact_id) > 64:
        raise ValueError("expected a registered artifact ID")
    descriptor = ensure_service(project_root)
    validate_descriptor(descriptor)
    url = descriptor["base_url"].rstrip("/") + "/api/artifacts/" + quote(artifact_id)
    request = Request(url, headers={"X-MathModel-Token": descriptor["token"]})
    with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "application/octet-stream").split(";")[0]
        size = int(response.headers.get("Content-Length", "0"))
        preview_url = url + "?" + urlencode({"token": descriptor["token"]})
        result = {"artifact_id": artifact_id, "mime_type": content_type, "size": size, "preview_url": preview_url}
        if content_type.startswith("text/") or content_type in {"application/json", "application/javascript"}:
            if size > 2 * 1024 * 1024:
                return result | {"content": None, "reason": "Text exceeds 2 MiB; use the local preview/download."}
            text = response.read(2 * 1024 * 1024 + 1).decode("utf-8", errors="replace")
            end = min(len(text), offset + limit)
            return result | {"content": text[offset:end], "offset": offset, "next_offset": end if end < len(text) else None}
        return result | {"content": None, "display": "Open the preview URL; binary data is not UTF-8 text."}


def run_job(project_root: str, job_type: str, options: dict | None = None, idempotency_key: str | None = None) -> dict:
    """Queue a defined check/experiment. Model runs require a Pro code/ run-spec."""
    return _client(project_root).request("POST", "/api/jobs", {"type": job_type, "options": options or {}, "idempotency_key": idempotency_key})


def get_job(project_root: str, job_id: str, cursor: int = 0, limit: int = 40000) -> dict:
    """Read current exit state and a bounded incremental log page."""
    return _client(project_root).request("GET", f"/api/jobs/{quote(job_id, safe='')}?" + urlencode({"cursor": cursor, "limit": limit}))


def cancel_job(project_root: str, job_id: str) -> dict:
    """Cancel one queued/running experiment and retain its logs and terminal state."""
    return _client(project_root).request("POST", f"/api/jobs/{quote(job_id, safe='')}/cancel", {})


def retry_job(project_root: str, job_id: str, idempotency_key: str | None = None) -> dict:
    """Create an independent retry of a known failed/cancelled/interrupted job."""
    return _client(project_root).request("POST", f"/api/jobs/{quote(job_id, safe='')}/retry", {"idempotency_key": idempotency_key})


def get_context_packet(project_root: str, question_id: str | None = None, cursor: int = 0, max_chars: int = 8000, source_revision: str | None = None) -> dict:
    """Recover a question's decisions, experiments and writing pointers without old chat."""
    args = {"cursor": cursor, "max_chars": max_chars}
    if question_id:
        args["question_id"] = question_id
    if source_revision:
        args["source_revision"] = source_revision
    return _client(project_root).request("GET", "/api/context?" + urlencode(args))


def get_next_action(project_root: str, question_id: str | None = None) -> dict:
    """Return the next Pro Skill and its handoff; this never launches another agent."""
    packet = get_context_packet(project_root, question_id)
    return {"workflow": packet["workflow"], "handoff": packet["handoff"], "pagination": packet["pagination"]}


def doctor(project_root: str | None = None) -> dict:
    """Inspect the active installation, dependencies and project Skill collisions."""
    from setup_runtime import doctor as inspect
    return inspect(project_root)


def get_change_impact(project_root: str, changed_paths: list[str] | None = None) -> dict:
    """Explain changed input/code → runs → claims → manuscript; never change approvals."""
    from runtime.dependencies import get_change_impact as inspect
    return inspect(project_root, changed_paths)


def export_replay(project_root: str, destination: str, allowed_inputs: list[str] | None = None) -> dict:
    """Export frozen Python experiments; only explicitly allowed inputs are bundled."""
    from runtime.replay import export_replay as export
    return export(project_root, destination, allowed_inputs)


def create_mcp():
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    app = FastMCP("mathmodel", instructions="Use an explicit contest project_root. Read get_context_packet on resume. Only Pro gates establish completion; scripts never generate a complete paper autonomously.")
    readers = (doctor, get_status, list_artifacts, read_artifact, get_job, get_next_action, get_context_packet, get_change_impact)
    for fn in readers:
        app.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))(fn)
    for fn in (open_workspace, run_job, cancel_job, retry_job, export_replay):
        app.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))(fn)
    return app


def main() -> int:
    try:
        app = create_mcp()
    except ImportError as exc:
        print("MathModel MCP dependency unavailable. Run scripts/setup_runtime.py with an explicit writable runtime directory. " + str(exc), file=sys.stderr)
        return 1
    app.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

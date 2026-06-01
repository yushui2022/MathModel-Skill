from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
QA_DIR = OUTPUT_DIR / "qa"
CONTEXT_DIR = OUTPUT_DIR / "context"
WORKFLOW_REPORT = QA_DIR / "workflow_guard_report.json"
MEMORY_JSON = CONTEXT_DIR / "workflow_memory.json"
MEMORY_MD = CONTEXT_DIR / "workflow_memory.md"


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": f"{type(exc).__name__}: {exc}"}


def artifact(path: Path) -> dict[str, Any]:
    data = load_json(path)
    item: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
    }
    if path.exists():
        item["bytes"] = path.stat().st_size
    if isinstance(data, dict):
        if data.get("__error__"):
            item["json_error"] = data["__error__"]
        if "status" in data:
            item["status"] = data.get("status")
    return item


def manifest_summary(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return {}
    entries = manifest.get("entries") if isinstance(manifest.get("entries"), list) else []
    by_role: dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "unknown")
        by_role[role] = by_role.get(role, 0) + 1
    return {
        "summary": manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {},
        "role_counts": by_role,
        "problem_statements": [entry.get("path") for entry in entries if isinstance(entry, dict) and entry.get("role") == "problem_statement"],
        "raw_data": [entry.get("path") for entry in entries if isinstance(entry, dict) and entry.get("role") == "raw_data"],
        "result_templates": [entry.get("path") for entry in entries if isinstance(entry, dict) and entry.get("role") == "result_template"],
    }


def run_summary(run_manifest: Any) -> dict[str, Any]:
    if not isinstance(run_manifest, dict):
        return {}
    runs = run_manifest.get("runs") if isinstance(run_manifest.get("runs"), list) else []
    return {
        "status": run_manifest.get("status"),
        "run_count": len(runs),
        "scripts": [run.get("script") for run in runs if isinstance(run, dict)],
        "returncodes": [run.get("returncode") for run in runs if isinstance(run, dict)],
    }


def compact_failures(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return []
    failures = report.get("failures")
    if isinstance(failures, list):
        return [str(item) for item in failures[:20]]
    return []


def build_snapshot() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    workflow = load_json(WORKFLOW_REPORT)
    if workflow is None:
        errors.append(f"Missing {rel(WORKFLOW_REPORT)}. Run workflow_guard.py --status before updating workflow memory.")
        workflow = {}
    elif isinstance(workflow, dict) and workflow.get("__error__"):
        errors.append(f"Cannot read {rel(WORKFLOW_REPORT)}: {workflow['__error__']}")

    preflight = load_json(OUTPUT_DIR / "preflight_report.json")
    manifest = load_json(OUTPUT_DIR / "input_manifest.json")
    load_report = load_json(OUTPUT_DIR / "data_cleaned" / "load_report.json")
    run_manifest = load_json(OUTPUT_DIR / "results" / "run_manifest.json")
    evidence_gate = load_json(QA_DIR / "evidence_gate_report.json")
    format_report = load_json(OUTPUT_DIR / "format_check_report.json")

    steps = workflow.get("steps") if isinstance(workflow, dict) and isinstance(workflow.get("steps"), list) else []
    completed_steps = [
        step.get("step")
        for step in steps
        if isinstance(step, dict) and str(step.get("status") or "").upper() == "PASS"
    ]

    snapshot = {
        "schema_version": "1.0",
        "generated_by": "context-memory-keeper/scripts/update_workflow_memory.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASS" if not errors else "FAIL",
        "root": str(BASE_DIR),
        "workflow": {
            "status": workflow.get("status") if isinstance(workflow, dict) else None,
            "mode": workflow.get("mode") if isinstance(workflow, dict) else None,
            "current_step": workflow.get("current_step") if isinstance(workflow, dict) else "",
            "next_step": workflow.get("next_step") if isinstance(workflow, dict) else "S0",
            "recommended_skill": workflow.get("recommended_skill") if isinstance(workflow, dict) else "paper-workflow-orchestrator",
            "next_action": workflow.get("next_action") if isinstance(workflow, dict) else "Run workflow_guard.py --status.",
            "completed_steps": completed_steps,
            "failures": compact_failures(workflow),
        },
        "inputs": manifest_summary(manifest),
        "runs": run_summary(run_manifest),
        "artifacts": {
            "workflow_guard_report": artifact(WORKFLOW_REPORT),
            "preflight_report": artifact(OUTPUT_DIR / "preflight_report.json"),
            "input_manifest": artifact(OUTPUT_DIR / "input_manifest.json"),
            "load_report": artifact(OUTPUT_DIR / "data_cleaned" / "load_report.json"),
            "run_manifest": artifact(OUTPUT_DIR / "results" / "run_manifest.json"),
            "evidence_gate_report": artifact(QA_DIR / "evidence_gate_report.json"),
            "format_check_report": artifact(OUTPUT_DIR / "format_check_report.json"),
        },
        "latest_statuses": {
            "preflight": preflight.get("status") if isinstance(preflight, dict) else None,
            "load_report": load_report.get("status") if isinstance(load_report, dict) else None,
            "run_manifest": run_manifest.get("status") if isinstance(run_manifest, dict) else None,
            "evidence_gate": evidence_gate.get("status") if isinstance(evidence_gate, dict) else None,
            "format_check": format_report.get("status") if isinstance(format_report, dict) else None,
        },
        "blockers": errors + compact_failures(workflow),
    }
    return snapshot, errors


def write_markdown(snapshot: dict[str, Any]) -> None:
    workflow = snapshot["workflow"]
    inputs = snapshot.get("inputs", {})
    runs = snapshot.get("runs", {})
    lines = [
        "# Workflow Memory Snapshot",
        "",
        f"- Status: `{snapshot['status']}`",
        f"- Generated at: `{snapshot['generated_at']}`",
        f"- Current step: `{workflow.get('current_step') or 'NONE'}`",
        f"- Next step: `{workflow.get('next_step') or 'DONE'}`",
        f"- Recommended skill: `{workflow.get('recommended_skill') or '-'}`",
        f"- Next action: {workflow.get('next_action') or '-'}",
        "",
        "## Completed Steps",
    ]
    completed = workflow.get("completed_steps") or []
    lines.extend(f"- `{step}`" for step in completed) if completed else lines.append("- None")
    lines.extend(["", "## Input Summary"])
    for key, value in (inputs.get("summary") or {}).items():
        lines.append(f"- {key}: `{value}`")
    role_counts = inputs.get("role_counts") or {}
    for role, count in sorted(role_counts.items()):
        lines.append(f"- role {role}: `{count}`")
    lines.extend(["", "## Run Summary"])
    lines.append(f"- Run count: `{runs.get('run_count', 0)}`")
    for script in runs.get("scripts") or []:
        lines.append(f"- Script: `{script}`")
    lines.extend(["", "## Blockers"])
    blockers = snapshot.get("blockers") or []
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- None")
    MEMORY_MD.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    snapshot, errors = build_snapshot()
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(snapshot)
    print(f"workflow memory json: {rel(MEMORY_JSON)}")
    print(f"workflow memory md: {rel(MEMORY_MD)}")
    if errors:
        print("[WORKFLOW MEMORY FAIL]")
        for error in errors:
            print(f" - {error}")
        return 1
    print("[WORKFLOW MEMORY PASS]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

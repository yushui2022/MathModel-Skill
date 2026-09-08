#!/usr/bin/env python3
"""Build a compact, deterministic handoff packet for a stateless Codex.

The packet is read-only by default.  It combines the authoritative workflow
Guard with the durable workflow-memory snapshot so a fresh conversation can
resume without trusting prior chat history.  ``--write`` refreshes only the
memory JSON through the existing memory skill; it never writes a QA report.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
from workbench import STAGES, WorkbenchState, project_id  # noqa: E402


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _memory_consistency(memory: dict[str, Any] | None, guard: dict[str, Any]) -> dict[str, Any]:
    workflow = memory.get("workflow", {}) if isinstance(memory, dict) else {}
    if not isinstance(workflow, dict):
        workflow = {}
    fields = ("current_step", "next_step", "recommended_skill")
    mismatches = []
    for field in fields:
        expected = str(guard.get(field) or "")
        recorded = str(workflow.get(field) or "")
        if recorded and expected != recorded:
            mismatches.append({"field": field, "memory": recorded, "guard": expected})
    return {
        "present": memory is not None,
        "matches_guard": not mismatches,
        "mismatches": mismatches,
        "source_of_truth": "workflow_guard",
    }


def build_packet(project_root: str | Path) -> dict[str, Any]:
    state = WorkbenchState(project_root)
    status = state.status()
    guard = status.get("guard") if isinstance(status.get("guard"), dict) else {}
    memory_path = state.root / "paper_output" / "context" / "workflow_memory.json"
    memory = _read_json(memory_path)
    steps = []
    raw_steps = guard.get("steps") if isinstance(guard.get("steps"), list) else []
    by_step = {str(item.get("step")): item for item in raw_steps if isinstance(item, dict)}
    for code in STAGES:
        item = by_step.get(code, {})
        steps.append({
            "step": code,
            "name": item.get("name", code),
            "status": str(item.get("status", "PENDING")).upper(),
            "failures": [str(x) for x in item.get("failures", [])][:8],
        })
    blockers = [str(x) for x in guard.get("failures", [])][:12]
    jobs = [j for j in status.get("jobs", []) if isinstance(j, dict)]
    active_jobs = [j for j in jobs if j.get("status") == "running"]
    next_step = str(guard.get("next_step") or ("S8" if guard.get("status") == "COMPLETE" else "S0"))
    packet = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": {
            "id": project_id(state.root),
            "name": state.root.name,
            "root": str(state.root),
        },
        "workflow": {
            "status": str(guard.get("status") or "UNKNOWN"),
            "current_step": str(guard.get("current_step") or ""),
            "next_step": next_step,
            "verified_count": int(status.get("verified_count") or 0),
            "steps": steps,
            "recommended_skill": str(guard.get("recommended_skill") or ""),
            "next_action": str(guard.get("next_action") or "先运行工作流预检。"),
            "blockers": blockers,
        },
        "activity": {
            "current_task": status.get("current_task", ""),
            "active_jobs": active_jobs,
            "recent_events": (status.get("history") or [])[-5:],
        },
        "evidence": {
            "artifact_count": len(status.get("artifacts") or []),
            "artifacts": (status.get("artifacts") or [])[:80],
            "guard_report": "paper_output/qa/workflow_guard_report.json",
            "memory": "paper_output/context/workflow_memory.json" if memory else None,
        },
        "memory_consistency": _memory_consistency(memory, guard),
        "resume_rule": "以 Guard 为准；先处理 blockers，再调用 recommended_skill。对话负责推理和写作，脚本只执行受控检查与计算。",
    }
    return packet


def _refresh_memory(root: Path) -> None:
    script = root / ".agents" / "skills" / "context-memory-keeper" / "scripts" / "update_workflow_memory.py"
    if not script.is_file():
        script = PLUGIN_ROOT / "skills" / "context-memory-keeper" / "scripts" / "update_workflow_memory.py"
    if script.is_file():
        subprocess.run([sys.executable, str(script)], cwd=root, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--write", action="store_true", help="刷新 workflow_memory.json 后再构建 packet")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if args.write:
        _refresh_memory(root)
    packet = build_packet(root)
    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        wf = packet["workflow"]
        print(f"# MathModel Context Packet — {packet['project']['name']}\n")
        print(f"- 状态：`{wf['status']}`；已验证 `{wf['verified_count']}/9` 个阶段")
        print(f"- 当前/下一阶段：`{wf['current_step'] or 'NONE'}` → `{wf['next_step'] or 'DONE'}`")
        print(f"- 推荐 Skill：`{wf['recommended_skill'] or '-'}`\n- 下一步：{wf['next_action']}")
        if wf["blockers"]:
            print("\n## 阻塞\n" + "\n".join(f"- {x}" for x in wf["blockers"]))
        print("\n## 恢复规则\n" + packet["resume_rule"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

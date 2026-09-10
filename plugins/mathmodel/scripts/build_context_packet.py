#!/usr/bin/env python3
"""Build a source-linked Pro handoff without writing project state or QA reports."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT_DIR))
from workbench import WorkbenchState, project_id
from runtime.context import collect_facts, digest_file, memory_consistency, safe_file, write_snapshot
from runtime.routing import make_handoff


def _input_index(root: Path) -> list[dict]:
    result = []
    for path in sorted(safe_file(root, "problem_files").rglob("*")):
        if len(result) >= 100:
            break
        try:
            relative = path.relative_to(root).as_posix()
            target = safe_file(root, relative)
            if target.is_file():
                result.append({"path": relative, "size": target.stat().st_size, "sha256": digest_file(target)})
        except (OSError, ValueError):
            continue
    return result


def build_packet(project_root: str | Path, question_id: str | None = None, *, max_chars: int = 8000, cursor: int = 0, source_revision: str | None = None) -> dict:
    if not 4000 <= max_chars <= 64000 or cursor < 0:
        raise ValueError("max_chars must be 4000..64000 and cursor must be nonnegative")
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("project_root must be an existing directory")
    status = WorkbenchState(root).status()
    guard = status.get("guard") or {}
    output_name = "paper_output_pro" if status.get("core_edition", "pro") == "pro" else "paper_output"
    verified_receipts = any(s.get("step") == "P3" and s.get("status") == "PASS" for s in guard.get("steps", []))
    facts, diagnostics, questions = collect_facts(root, output_name, question_id, verified_receipts=verified_receipts)
    steps = [{"step": s.get("step") or s.get("code"), "name": s.get("name", ""),
              "status": s.get("status", "unknown"), "failures": [str(x)[:180] for x in s.get("failures", [])[:2]]}
             for s in (guard.get("steps") or [])]
    workflow = {"status": guard.get("status", "UNKNOWN"), "current_step": guard.get("current_step", ""),
        "acceptance_scope": guard.get("acceptance_scope", "NOT_ACCEPTED"),
        "next_step": guard.get("next_step") or status.get("stage") or "P0", "verified_count": status.get("verified_count", 0),
        "stage_count": status.get("stage_count", 10), "steps": steps,
        "recommended_skill": guard.get("recommended_skill", "pro-workflow-orchestrator"),
        "next_action": str(guard.get("next_action") or status.get("next_action") or "运行 Pro 预检并读取当前契约。")[:500],
        "blockers": [str(x)[:220] for x in (guard.get("failures") or guard.get("blockers") or [])[:8]],
        "revision": hashlib.sha256(json.dumps({"contracts": guard.get("contract_hashes", {}), "steps": steps}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    packet = {"schema_version": "2.0", "project": {"id": project_id(root), "name": root.name, "root": str(root)},
        "core_edition": status.get("core_edition", "pro"),
        "focus": {"question_id": question_id, "available_questions": [q.get("subproblem_id") or q.get("question_id") for q in questions[:100]], "total_questions": len(questions)},
        "inputs": {"problem_files": _input_index(root)[:12], "manifest": f"{output_name}/input_manifest.json"},
        "workflow": workflow, "facts": [], "diagnostics": diagnostics[:8],
        "memory_consistency": memory_consistency(root, output_name, guard),
        "activity": {"active_jobs": [{k: j.get(k) for k in ("id", "type", "status", "stage")} for j in status.get("jobs", []) if j.get("status") in {"queued", "running"}][:8]},
        "evidence": {"artifact_count": len(status.get("artifacts", [])), "output_root": output_name},
        "pagination": {"cursor": cursor, "next_cursor": None, "total_facts": len(facts), "omitted": 0},
        "resume_rule": "先处理真实门禁与批准，再按所选问题恢复。current 仅表示记录哈希有效，不等于论文门禁通过；缺失理由保持未知。"}
    # Trim structural summaries before budgeting individually addressable facts.
    if len(json.dumps(packet, ensure_ascii=False)) > max_chars - 2200:
        workflow["steps"] = [{"step": x["step"], "status": x["status"]} for x in steps]
        packet["inputs"]["problem_files"] = packet["inputs"]["problem_files"][:3]
        packet["memory_consistency"]["mismatches"] = packet["memory_consistency"]["mismatches"][:2]
    handoff = make_handoff({**packet, "facts": facts}, PLUGIN_ROOT)
    version = handoff["input_revision"]
    if cursor and source_revision != version:
        raise ValueError("Context sources changed or source_revision is missing; restart pagination at cursor 0")
    packet["pagination"]["source_revision"] = version
    reserve = len(json.dumps(handoff, ensure_ascii=False)) + 80
    for fact in facts[cursor:]:
        packet["facts"].append(fact)
        if len(json.dumps(packet, ensure_ascii=False)) > max_chars - reserve:
            packet["facts"].pop()
            break
    end = cursor + len(packet["facts"])
    packet["pagination"].update(next_cursor=end if end < len(facts) else None, omitted=max(0, len(facts) - end))
    packet["handoff"] = handoff
    if facts[cursor:] and not packet["facts"]:
        # Never return a cursor that points to the same oversized page forever.
        workflow["steps"] = []
        workflow["blockers"] = workflow["blockers"][:2]
        packet["inputs"]["problem_files"] = []
        packet["diagnostics"] = diagnostics[:2]
        packet["facts"] = [facts[cursor]]
        packet["pagination"].update(next_cursor=cursor + 1 if cursor + 1 < len(facts) else None, omitted=max(0, len(facts) - cursor - 1))
    if len(json.dumps(packet, ensure_ascii=False)) > max_chars:
        raise ValueError("Context metadata exceeds max_chars; retry with a larger max_chars (maximum 64000)")
    return packet


def markdown(packet: dict) -> str:
    wf, focus = packet["workflow"], packet["focus"]
    lines = [f"# MathModel · {packet['project']['name']}", "",
        f"已验证 {wf['verified_count']}/{wf['stage_count']} 个阶段；下一阶段 {wf['next_step']}。",
        f"当前问题：{focus['question_id'] or '全项目'}；推荐 Skill：{packet['handoff']['skill_id']}",
        f"验收范围：{wf['acceptance_scope']}（ENGINEERING_SMOKE_ONLY 仅表示工程样例验收，不是比赛论文通过。）",
        f"下一步：{wf['next_action']}", "", "阻塞：" + ("；".join(wf["blockers"]) or "无已报告阻塞；以实时 Pro 状态为准。")]
    for fact in packet["facts"]:
        value = fact["value"] if isinstance(fact["value"], str) else json.dumps(fact["value"], ensure_ascii=False)
        lines += ["", f"- {fact['title']} [{fact['state']}]：{value}", f"  来源：{fact['source']['path']}#{fact['source']['pointer']}"]
    if packet["pagination"]["next_cursor"] is not None:
        lines += ["", f"还有 {packet['pagination']['omitted']} 条事实；用 --cursor {packet['pagination']['next_cursor']} --source-revision {packet['pagination']['source_revision']} 读取。"]
    return "\n".join([*lines, "", packet["resume_rule"]])


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--question", dest="question_id")
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--cursor", type=int, default=0)
    parser.add_argument("--source-revision")
    parser.add_argument("--write", action="store_true", help="保存 .mathmodel/context/resume.json，不修改 Pro 批准与 QA")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    try:
        packet = build_packet(args.project_root, args.question_id, max_chars=args.max_chars, cursor=args.cursor, source_revision=args.source_revision)
        if args.write:
            write_snapshot(Path(args.project_root).resolve(), packet)
        print(markdown(packet) if args.format == "markdown" else json.dumps(packet, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

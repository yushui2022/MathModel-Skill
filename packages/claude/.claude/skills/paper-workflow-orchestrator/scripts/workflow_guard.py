from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
REPORT_JSON = OUTPUT_DIR / "qa" / "workflow_guard_report.json"
REPORT_MD = OUTPUT_DIR / "qa" / "workflow_guard_report.md"

BAD_RESULT_STATUSES = {
    "",
    "missing",
    "needs_real_modeling",
    "draft_contract",
    "to_be_filled",
    "template",
    "draft",
    "scaffold_result_needs_review",
}

STEP_ORDER = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

STEP_RECOVERY = {
    "S0": {
        "recommended_skill": "paper-workflow-orchestrator",
        "action": "运行 preflight_check.py，生成 preflight_report.json 与 input_manifest.json。",
    },
    "S1": {
        "recommended_skill": "problem-doc-model-selector",
        "action": "解析题面并生成 paper_output/step1/problem_analysis.json。",
    },
    "S2": {
        "recommended_skill": "modeling-paper-rubric-and-model-selector",
        "action": "生成 model_route.json、rubric_alignment.json 与 scoring_strategy.md。",
    },
    "S3": {
        "recommended_skill": "data-cleaning-and-visualization",
        "action": "基于 input_manifest 与模型路线生成 data_plan、visualization_plan、figure_index 与 load_report。",
    },
    "S4": {
        "recommended_skill": "model-code-and-result-generator",
        "action": "生成 paper_output/code/modeling/ 下的 q*_model.py 与 run_modeling.py。",
    },
    "S5": {
        "recommended_skill": "model-code-and-result-generator",
        "action": "实际运行 run_modeling.py，生成 model_results、metrics、conclusions、table_index 与 run_manifest。",
    },
    "S6": {
        "recommended_skill": "quality-assurance-auditor",
        "action": "运行 evidence_gate.py --mode official，未通过则回补结果证据。",
    },
    "S7": {
        "recommended_skill": "paper-formal-writer",
        "action": "证据门禁通过后生成 paper_outline、final_paper_source.md 与 final_paper.docx。",
    },
    "S8": {
        "recommended_skill": "paper-formal-writer",
        "action": "运行 check_paper_format.py 并修复格式门禁失败项。",
    },
}

SKILL_REQUIREMENTS = {
    "paper-workflow-orchestrator": {
        "required_step": "S0",
        "handoff": "总入口只负责判定阶段和路由；预检未通过时不得进入任何子 skill。",
    },
    "problem-doc-model-selector": {
        "required_step": "S0",
        "handoff": "预检通过后才能审题，输出 problem_analysis.json 后回到 orchestrator。",
    },
    "modeling-paper-rubric-and-model-selector": {
        "required_step": "S1",
        "handoff": "题意结构化完成后才能生成 model_route/rubric_alignment。",
    },
    "authoritative-data-harvester": {
        "required_step": "S1",
        "handoff": "外部数据检索必须围绕已解析的题意和子问题进行，检索结果回填 crawled_data/ 或 data_plan。",
    },
    "data-cleaning-and-visualization": {
        "required_step": "S2",
        "handoff": "模型路线和评分点明确后才能清洗数据、规划图表和生成 load_report。",
    },
    "model-code-and-result-generator": {
        "required_step": "S3",
        "handoff": "数据/图表计划和 load_report 通过后才能生成或运行建模代码。",
    },
    "quality-assurance-auditor": {
        "required_step": "S5",
        "handoff": "结果证据具备后才能做 evidence gate；失败时回退补齐结果、表格、图表或结论。",
    },
    "paper-micro-unit-generator": {
        "required_step": "S5",
        "handoff": "微单元只能作为局部写作/兜底素材，不能替代正式 evidence gate 和 formal writer。",
    },
    "paper-formal-writer": {
        "required_step": "S6",
        "handoff": "证据门禁 PASS 后才能进入正式成稿；未 PASS 时只能生成草稿或待写清单。",
    },
    "context-memory-keeper": {
        "required_step": "S0",
        "handoff": "记忆更新必须记录当前 workflow 阶段、已完成产物、阻塞项和下一步，不得改变阶段顺序。",
    },
}


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


def status_of(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("status") or item.get("evidence_status") or "").strip()


def normalize_artifact(path_text: object) -> str:
    path = Path(str(path_text or "").strip())
    if not path.is_absolute():
        path = BASE_DIR / path
    return rel(path)


def check_json_file(path: Path, failures: list[str]) -> Any:
    data = load_json(path)
    if data is None:
        failures.append(f"缺少文件：{rel(path)}")
        return None
    if isinstance(data, dict) and data.get("__error__"):
        failures.append(f"JSON 无法读取：{rel(path)} ({data['__error__']})")
        return None
    return data


def check_text_file(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"缺少文件：{rel(path)}")
    elif path.is_file() and path.stat().st_size == 0:
        failures.append(f"文件为空：{rel(path)}")


def question_ids(model_route: Any) -> list[str]:
    questions = model_route.get("questions") if isinstance(model_route, dict) else []
    result: list[str] = []
    if isinstance(questions, list):
        for item in questions:
            if isinstance(item, dict):
                qid = str(item.get("question_id") or item.get("id") or "").strip()
                if qid:
                    result.append(qid)
    return sorted(set(result))


def check_s0() -> dict[str, Any]:
    failures: list[str] = []
    report = check_json_file(OUTPUT_DIR / "preflight_report.json", failures)
    manifest = check_json_file(OUTPUT_DIR / "input_manifest.json", failures)
    if isinstance(report, dict) and str(report.get("status") or "").upper() != "PASS":
        failures.append("preflight_report.json status 不是 PASS。")
    if isinstance(manifest, dict):
        entries = manifest.get("entries")
        if not isinstance(entries, list):
            failures.append("input_manifest.json 缺少 entries 列表。")
        summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
        if summary.get("problem_statement_count", 0) < 1:
            failures.append("input_manifest.json 中没有可解析题面文件。")
    return {"step": "S0", "name": "准入预检", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s1() -> dict[str, Any]:
    failures: list[str] = []
    check_json_file(OUTPUT_DIR / "step1" / "problem_analysis.json", failures)
    return {"step": "S1", "name": "审题分析", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s2() -> dict[str, Any]:
    failures: list[str] = []
    model_route = check_json_file(OUTPUT_DIR / "plan" / "model_route.json", failures)
    check_json_file(OUTPUT_DIR / "plan" / "rubric_alignment.json", failures)
    check_text_file(OUTPUT_DIR / "plan" / "scoring_strategy.md", failures)
    if isinstance(model_route, dict) and not question_ids(model_route):
        failures.append("model_route.json 中没有 question_id/id，无法追踪子问题。")
    return {"step": "S2", "name": "模型路线", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s3() -> dict[str, Any]:
    failures: list[str] = []
    check_json_file(OUTPUT_DIR / "plan" / "data_plan.json", failures)
    check_json_file(OUTPUT_DIR / "plan" / "visualization_plan.json", failures)
    check_json_file(OUTPUT_DIR / "figure_index.json", failures)
    load_report = check_json_file(OUTPUT_DIR / "data_cleaned" / "load_report.json", failures)
    if isinstance(load_report, dict) and str(load_report.get("status") or "").upper() == "FAIL":
        failures.append("data_cleaned/load_report.json status 为 FAIL。")
    if isinstance(load_report, dict) and not load_report.get("input_manifest_used"):
        failures.append("data_cleaned/load_report.json 未使用 input_manifest.json，附件角色可能未被统一约束。")
    return {"step": "S3", "name": "数据与图表计划", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s4() -> dict[str, Any]:
    failures: list[str] = []
    modeling_dir = OUTPUT_DIR / "code" / "modeling"
    if not modeling_dir.exists():
        failures.append(f"缺少建模代码目录：{rel(modeling_dir)}")
    else:
        scripts = sorted(modeling_dir.glob("q*_model.py"))
        if not scripts:
            failures.append("paper_output/code/modeling/ 中没有 q*_model.py。")
        if not (modeling_dir / "run_modeling.py").exists():
            failures.append("缺少 paper_output/code/modeling/run_modeling.py。")
    return {"step": "S4", "name": "建模代码", "status": "PASS" if not failures else "FAIL", "failures": failures}


def _items(data: Any, key: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        return []
    return [item for item in data[key] if isinstance(item, dict)]


def check_s5() -> dict[str, Any]:
    failures: list[str] = []
    model_results = check_json_file(OUTPUT_DIR / "results" / "model_results.json", failures)
    run_manifest = check_json_file(OUTPUT_DIR / "results" / "run_manifest.json", failures)
    metrics = check_json_file(OUTPUT_DIR / "results" / "metrics.json", failures)
    conclusions = check_json_file(OUTPUT_DIR / "results" / "conclusions.json", failures)
    table_index = check_json_file(OUTPUT_DIR / "tables" / "table_index.json", failures)
    runs = run_manifest.get("runs", []) if isinstance(run_manifest, dict) else []
    run_scripts = {
        normalize_artifact(run.get("script"))
        for run in runs
        if isinstance(run, dict)
    }

    for item in _items(model_results, "questions"):
        qid = str(item.get("question_id") or "UNKNOWN")
        state = status_of(item)
        if state in BAD_RESULT_STATUSES:
            failures.append(f"{qid}: model_results 状态仍不是正式结果：{state or 'missing'}")
        provenance = item.get("execution_provenance")
        if not isinstance(provenance, dict):
            failures.append(f"{qid}: 缺少 execution_provenance，无法证明结果来自实际代码运行。")
        elif provenance.get("run_exit_code") not in (0, "0"):
            failures.append(f"{qid}: execution_provenance.run_exit_code 不是 0。")
        elif normalize_artifact(provenance.get("source_code_path")) not in run_scripts:
            failures.append(f"{qid}: run_manifest.json 中没有对应 source_code_path 的运行记录。")

    for label, data, key in (
        ("metrics", metrics, "items"),
        ("conclusions", conclusions, "items"),
        ("table_index", table_index, "tables"),
    ):
        if data is not None and not _items(data, key):
            failures.append(f"{label} 中没有可追踪条目。")
        for item in _items(data, key):
            state = status_of(item)
            if state in BAD_RESULT_STATUSES:
                failures.append(f"{label}: 条目仍是草稿/待补状态：{state or 'missing'}")
    return {"step": "S5", "name": "结果证据", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s6() -> dict[str, Any]:
    failures: list[str] = []
    gate = check_json_file(OUTPUT_DIR / "qa" / "evidence_gate_report.json", failures)
    if isinstance(gate, dict) and str(gate.get("status") or "").upper() != "PASS":
        failures.append("evidence_gate_report.json status 不是 PASS。")
    return {"step": "S6", "name": "证据门禁", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s7() -> dict[str, Any]:
    failures: list[str] = []
    check_json_file(OUTPUT_DIR / "plan" / "paper_outline.json", failures)
    check_text_file(OUTPUT_DIR / "final_paper_source.md", failures)
    check_text_file(OUTPUT_DIR / "final_paper.docx", failures)
    return {"step": "S7", "name": "正式稿", "status": "PASS" if not failures else "FAIL", "failures": failures}


def check_s8() -> dict[str, Any]:
    failures: list[str] = []
    report = check_json_file(OUTPUT_DIR / "format_check_report.json", failures)
    if isinstance(report, dict) and str(report.get("status") or "").upper() != "PASS":
        failures.append("format_check_report.json status 不是 PASS。")
    return {"step": "S8", "name": "格式门禁", "status": "PASS" if not failures else "FAIL", "failures": failures}


CHECKERS = {
    "S0": check_s0,
    "S1": check_s1,
    "S2": check_s2,
    "S3": check_s3,
    "S4": check_s4,
    "S5": check_s5,
    "S6": check_s6,
    "S7": check_s7,
    "S8": check_s8,
}


def evaluate(target_step: str) -> dict[str, Any]:
    target_index = STEP_ORDER.index(target_step)
    checked_steps = STEP_ORDER[: target_index + 1]
    step_reports = [CHECKERS[step]() for step in checked_steps]
    failures = [f"{item['step']}: {failure}" for item in step_reports for failure in item["failures"]]
    return {
        "schema_version": "1.0",
        "generated_by": "paper-workflow-orchestrator/scripts/workflow_guard.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target_step": target_step,
        "status": "PASS" if not failures else "FAIL",
        "steps": step_reports,
        "failures": failures,
    }


def evaluate_skill(skill_name: str) -> dict[str, Any]:
    requirement = SKILL_REQUIREMENTS[skill_name]
    report = evaluate(requirement["required_step"])
    report.update(
        {
            "mode": "skill",
            "skill": skill_name,
            "required_step": requirement["required_step"],
            "handoff": requirement["handoff"],
        }
    )
    if report["status"] == "PASS":
        report["next_action"] = f"允许启动 {skill_name}；完成后必须回到 paper-workflow-orchestrator 判断下一步。"
    else:
        report["next_action"] = f"禁止启动 {skill_name}；先补齐 {requirement['required_step']} 及之前的失败项。"
    return report


def evaluate_status() -> dict[str, Any]:
    deepest_passed = ""
    first_blocked = ""
    first_report: dict[str, Any] | None = None
    for step in STEP_ORDER:
        report = evaluate(step)
        if report["status"] == "PASS":
            deepest_passed = step
            continue
        first_blocked = step
        first_report = report
        break

    if not first_blocked:
        return {
            "schema_version": "1.0",
            "generated_by": "paper-workflow-orchestrator/scripts/workflow_guard.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "status",
            "target_step": "S8",
            "status": "COMPLETE",
            "current_step": "S8",
            "next_step": "",
            "recommended_skill": "",
            "next_action": "S0-S8 全部通过；可以进行最终一致性复核或交付。",
            "steps": [CHECKERS[step]() for step in STEP_ORDER],
            "failures": [],
        }

    guidance = STEP_RECOVERY[first_blocked]
    return {
        "schema_version": "1.0",
        "generated_by": "paper-workflow-orchestrator/scripts/workflow_guard.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "status",
        "target_step": first_blocked,
        "status": "INCOMPLETE",
        "current_step": deepest_passed,
        "next_step": first_blocked,
        "recommended_skill": guidance["recommended_skill"],
        "next_action": guidance["action"],
        "steps": first_report["steps"] if first_report else [],
        "failures": first_report["failures"] if first_report else [],
    }


def write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Workflow Guard Report",
        "",
        f"- Target step: `{report['target_step']}`",
        f"- Status: `{report['status']}`",
        f"- Generated at: `{report['generated_at']}`",
    ]
    if report.get("skill"):
        lines.extend(
            [
                f"- Skill: `{report['skill']}`",
                f"- Required step: `{report['required_step']}`",
                f"- Handoff: {report['handoff']}",
                f"- Next action: {report['next_action']}",
            ]
        )
    if report.get("mode") == "status":
        lines.extend(
            [
                f"- Current step: `{report.get('current_step', '')}`",
                f"- Next step: `{report.get('next_step', '')}`",
                f"- Recommended skill: `{report.get('recommended_skill', '')}`",
                f"- Next action: {report.get('next_action', '')}",
            ]
        )
    lines.extend(["", "## Steps"])
    for item in report["steps"]:
        lines.append(f"- {item['step']} {item['name']}: `{item['status']}`")
        for failure in item["failures"]:
            lines.append(f"  - {failure}")
    REPORT_MD.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Check MathModel S0-S8 workflow state.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--step", choices=STEP_ORDER, help="Check all workflow requirements up to this step.")
    target.add_argument("--skill", choices=sorted(SKILL_REQUIREMENTS), help="Check whether this skill may start in the current workflow state.")
    target.add_argument("--status", action="store_true", help="Recover current workflow stage and recommend the next skill/action.")
    args = parser.parse_args()
    if args.status:
        report = evaluate_status()
    elif args.skill:
        report = evaluate_skill(args.skill)
    else:
        report = evaluate(args.step)
    write_reports(report)
    print(f"workflow guard report: {rel(REPORT_JSON)}")
    label = "status" if args.status else (args.skill or args.step)
    if args.status:
        print(f"[WORKFLOW STATUS] current={report.get('current_step') or 'NONE'} next={report.get('next_step') or 'DONE'} skill={report.get('recommended_skill') or '-'}")
        print(f" - {report.get('next_action', '')}")
        return 0
    if report["status"] == "PASS":
        print(f"[WORKFLOW PASS] {label}")
        return 0
    print(f"[WORKFLOW FAIL] {label}")
    if report.get("next_action"):
        print(f" - {report['next_action']}")
    for failure in report["failures"][:12]:
        print(f" - {failure}")
    if len(report["failures"]) > 12:
        print(f" - ...{len(report['failures']) - 12} more failures in report.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

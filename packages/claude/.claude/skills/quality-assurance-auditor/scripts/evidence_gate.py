import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "paper_output"
QA_DIR = OUTPUT_DIR / "qa"
MODEL_ROUTE_FILE = OUTPUT_DIR / "plan" / "model_route.json"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
MODEL_RESULTS_FILE = OUTPUT_DIR / "results" / "model_results.json"
RUN_MANIFEST_FILE = OUTPUT_DIR / "results" / "run_manifest.json"
METRICS_FILE = OUTPUT_DIR / "results" / "metrics.json"
CONCLUSIONS_FILE = OUTPUT_DIR / "results" / "conclusions.json"
TABLE_INDEX_FILE = OUTPUT_DIR / "tables" / "table_index.json"
TASKS_FILE = OUTPUT_DIR / "tasks.json"
REPORT_JSON = QA_DIR / "evidence_gate_report.json"
REPORT_MD = QA_DIR / "evidence_gate_report.md"

BAD_STATUSES = {
    "missing",
    "needs_real_modeling",
    "draft_contract",
    "to_be_filled",
    "template",
    "draft",
    "scaffold_result_needs_review",
}


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc)}


def question_ids(model_route: Any) -> list[str]:
    questions = model_route.get("questions") if isinstance(model_route, dict) else []
    if not isinstance(questions, list):
        return []
    result = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or item.get("id") or "").strip()
        if qid:
            result.append(qid)
    return sorted(set(result))


def grouped_items(data: Any, key: str) -> dict[str, list[dict[str, Any]]]:
    items = data.get(key) if isinstance(data, dict) else []
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(items, list):
        return grouped
    for item in items:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped.setdefault(qid, []).append(item)
    return grouped


def result_items(data: Any) -> dict[str, dict[str, Any]]:
    questions = data.get("questions") if isinstance(data, dict) else []
    grouped: dict[str, dict[str, Any]] = {}
    if not isinstance(questions, list):
        return grouped
    for item in questions:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped[qid] = item
    return grouped


def figure_items(data: Any) -> dict[str, list[dict[str, Any]]]:
    return grouped_items(data, "figures")


def table_items(data: Any) -> dict[str, list[dict[str, Any]]]:
    return grouped_items(data, "tables")


def status_of(item: dict[str, Any] | None) -> str:
    if not item:
        return "missing"
    return str(item.get("evidence_status") or item.get("status") or "").strip()


def resolve_artifact(path_text: object) -> Path:
    text = str(path_text or "").strip().strip("<>")
    path = Path(text)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def normalized_artifact(path_text: object) -> str:
    path = resolve_artifact(path_text)
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def provenance_failures(item: dict[str, Any]) -> list[str]:
    provenance = item.get("execution_provenance")
    if not isinstance(provenance, dict):
        return ["缺少 execution_provenance，无法证明结果来自实际代码运行"]

    failures: list[str] = []
    source_code = resolve_artifact(provenance.get("source_code_path"))
    if not provenance.get("source_code_path"):
        failures.append("execution_provenance.source_code_path 为空")
    elif not source_code.exists():
        failures.append(f"source_code_path 不存在：{source_code}")

    if provenance.get("run_exit_code") not in (0, "0"):
        failures.append(f"run_exit_code 不是 0：{provenance.get('run_exit_code')}")

    if not str(provenance.get("run_command") or "").strip():
        failures.append("execution_provenance.run_command 为空")

    for artifact in provenance.get("output_artifacts", []) or []:
        artifact_path = resolve_artifact(artifact)
        if not artifact_path.exists():
            failures.append(f"输出产物不存在：{artifact}")
    return failures


def run_manifest_failures(item: dict[str, Any], run_manifest: Any) -> list[str]:
    if not isinstance(run_manifest, dict):
        return ["缺少或无法读取 run_manifest.json，无法核验建模代码运行记录"]
    runs = run_manifest.get("runs")
    if not isinstance(runs, list):
        return ["run_manifest.json 缺少 runs 列表"]

    provenance = item.get("execution_provenance")
    if not isinstance(provenance, dict):
        return ["缺少 execution_provenance，无法匹配 run_manifest"]
    source_code = normalized_artifact(provenance.get("source_code_path"))
    qid = str(item.get("question_id") or "").strip()
    matches = [
        run for run in runs
        if isinstance(run, dict) and normalized_artifact(run.get("script")) == source_code
    ]
    if not matches:
        return [f"run_manifest.json 中没有 source_code_path 对应的运行记录：{source_code}"]

    run = matches[-1]
    failures: list[str] = []
    if run.get("returncode") not in (0, "0"):
        failures.append(f"run_manifest 记录 returncode 不是 0：{run.get('returncode')}")
    run_qids = {str(value) for value in run.get("question_ids", []) or []}
    if qid and run_qids and qid not in run_qids:
        failures.append(f"run_manifest 运行记录未包含当前 question_id：{qid}")
    run_outputs = {
        normalized_artifact(item.get("path"))
        for item in run.get("output_artifacts", []) or []
        if isinstance(item, dict)
    }
    for artifact in provenance.get("output_artifacts", []) or []:
        normalized = normalized_artifact(artifact)
        if normalized not in run_outputs:
            failures.append(f"execution_provenance 输出未进入 run_manifest：{normalized}")
    missing_outputs = [
        str(item.get("path"))
        for item in run.get("output_artifacts", []) or []
        if isinstance(item, dict) and not item.get("exists")
    ]
    for artifact in missing_outputs:
        failures.append(f"run_manifest 记录输出产物不存在：{artifact}")
    return failures


def has_bad_status(items: list[dict[str, Any]]) -> bool:
    for item in items:
        status = status_of(item)
        if status in BAD_STATUSES:
            return True
    return False


def conclusion_text_exists(items: list[dict[str, Any]]) -> bool:
    return any(str(item.get("conclusion_text") or "").strip() for item in items)


def task_items(data: Any) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(data, list):
        return grouped
    for item in data:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped.setdefault(qid, []).append(item)
    return grouped


def evaluate() -> dict[str, Any]:
    model_route = load_json(MODEL_ROUTE_FILE)
    figure_index = load_json(FIGURE_INDEX_FILE)
    model_results = load_json(MODEL_RESULTS_FILE)
    run_manifest = load_json(RUN_MANIFEST_FILE)
    metrics = load_json(METRICS_FILE)
    conclusions = load_json(CONCLUSIONS_FILE)
    table_index = load_json(TABLE_INDEX_FILE)
    tasks = load_json(TASKS_FILE)

    failures: list[str] = []
    warnings: list[str] = []

    for path, data in (
        (MODEL_ROUTE_FILE, model_route),
        (FIGURE_INDEX_FILE, figure_index),
        (MODEL_RESULTS_FILE, model_results),
        (RUN_MANIFEST_FILE, run_manifest),
        (METRICS_FILE, metrics),
        (CONCLUSIONS_FILE, conclusions),
        (TABLE_INDEX_FILE, table_index),
        (TASKS_FILE, tasks),
    ):
        if data is None:
            failures.append(f"缺少证据门禁输入文件：{path.relative_to(BASE_DIR) if path.is_relative_to(BASE_DIR) else path}")
        elif isinstance(data, dict) and data.get("__error__"):
            failures.append(f"无法读取证据门禁输入文件：{path} ({data['__error__']})")

    qids = question_ids(model_route)
    if not qids:
        failures.append("model_route.json 中没有可追溯的 question_id，无法执行正式证据门禁。")

    result_map = result_items(model_results)
    metric_map = grouped_items(metrics, "items")
    conclusion_map = grouped_items(conclusions, "items")
    figure_map = figure_items(figure_index)
    table_map = table_items(table_index)
    task_map = task_items(tasks)

    question_reports = []
    for qid in qids:
        q_failures: list[str] = []
        q_warnings: list[str] = []
        result = result_map.get(qid)
        q_metrics = metric_map.get(qid, [])
        q_conclusions = conclusion_map.get(qid, [])
        q_figures = figure_map.get(qid, [])
        q_tables = table_map.get(qid, []) + table_map.get("ALL", [])
        q_tasks = task_map.get(qid, [])

        if not result:
            q_failures.append("缺少 model_results.json 中的模型结果")
        elif status_of(result) in BAD_STATUSES:
            q_failures.append(f"模型结果状态仍不可作为正式证据：{status_of(result)}")
        else:
            for failure in provenance_failures(result):
                q_failures.append(f"模型结果缺少真实运行来源：{failure}")
            for failure in run_manifest_failures(result, run_manifest):
                q_failures.append(f"模型结果运行账本不完整：{failure}")

        if not q_metrics:
            q_failures.append("缺少 metrics.json 中的评价指标")
        elif has_bad_status(q_metrics):
            q_failures.append("评价指标仍包含草稿、模板或待补状态")

        if not q_conclusions or not conclusion_text_exists(q_conclusions):
            q_failures.append("缺少 conclusions.json 中可回扣原题的结论文本")
        elif has_bad_status(q_conclusions):
            q_failures.append("结论证据仍包含草稿、模板或待补状态")

        if not q_figures and not q_tables:
            q_failures.append("缺少图表或表格证据")
        if q_tables and has_bad_status(q_tables):
            q_failures.append("表格证据仍包含草稿、模板或待补状态")

        if not q_tasks:
            q_warnings.append("tasks.json 中没有对应问题任务，正式写作时需补齐任务追踪")

        for message in q_failures:
            failures.append(f"{qid}: {message}")
        for message in q_warnings:
            warnings.append(f"{qid}: {message}")

        question_reports.append(
            {
                "question_id": qid,
                "status": "FAIL" if q_failures else "PASS",
                "failures": q_failures,
                "warnings": q_warnings,
                "has_result": bool(result),
                "metric_count": len(q_metrics),
                "conclusion_count": len(q_conclusions),
                "figure_count": len(q_figures),
                "table_count": len(q_tables),
            }
        )

    return {
        "schema_version": "1.0",
        "generated_by": "quality-assurance-auditor/scripts/evidence_gate.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "questions": question_reports,
    }


def write_reports(report: dict[str, Any], mode: str) -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Evidence Gate Report",
        "",
        f"- Mode: `{mode}`",
        f"- Status: `{report['status']}`",
        f"- Generated at: `{report['generated_at']}`",
        "",
    ]
    if report["failures"]:
        lines.append("## Failures")
        lines.extend(f"- {item}" for item in report["failures"])
        lines.append("")
    if report["warnings"]:
        lines.append("## Warnings")
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")
    lines.append("## Questions")
    for item in report["questions"]:
        lines.append(
            f"- {item['question_id']}: {item['status']} "
            f"(results={item['has_result']}, metrics={item['metric_count']}, "
            f"conclusions={item['conclusion_count']}, figures={item['figure_count']}, tables={item['table_count']})"
        )
    REPORT_MD.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Check whether MathModel Skill evidence is ready for formal writing.")
    parser.add_argument(
        "--mode",
        choices=("official", "quickstart"),
        default=os.environ.get("MATHMODEL_EVIDENCE_GATE_MODE", "official"),
        help="official returns non-zero on missing evidence; quickstart only warns.",
    )
    args = parser.parse_args()

    report = evaluate()
    write_reports(report, args.mode)

    print(f"证据门禁报告：{REPORT_MD}")
    if report["status"] == "PASS":
        print("✅ 证据门禁通过，可以进入正式全局写作与最终 QA。")
        return 0

    print("⚠️ 证据门禁未通过。正式论文不得把当前 Word 称为最终稿。")
    for failure in report["failures"][:12]:
        print(f" - {failure}")
    if len(report["failures"]) > 12:
        print(f" - 其余 {len(report['failures']) - 12} 项见报告。")
    return 0 if args.mode == "quickstart" else 1


if __name__ == "__main__":
    raise SystemExit(main())

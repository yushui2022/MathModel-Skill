import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd()
PROBLEM_ANALYSIS_FILE = BASE_DIR / "paper_output" / "step1" / "problem_analysis.json"
MODEL_ROUTE_FILE = BASE_DIR / "paper_output" / "plan" / "model_route.json"
RUBRIC_ALIGNMENT_FILE = BASE_DIR / "paper_output" / "plan" / "rubric_alignment.json"
DATA_PLAN_FILE = BASE_DIR / "paper_output" / "plan" / "data_plan.json"
VISUALIZATION_PLAN_FILE = BASE_DIR / "paper_output" / "plan" / "visualization_plan.json"
FIGURE_INDEX_FILE = BASE_DIR / "paper_output" / "figure_index.json"
MODEL_RESULTS_FILE = BASE_DIR / "paper_output" / "results" / "model_results.json"
METRICS_FILE = BASE_DIR / "paper_output" / "results" / "metrics.json"
CONCLUSIONS_FILE = BASE_DIR / "paper_output" / "results" / "conclusions.json"
TABLE_INDEX_FILE = BASE_DIR / "paper_output" / "tables" / "table_index.json"
TASKS_FILE = BASE_DIR / "paper_output" / "tasks.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"无法读取 JSON: {path} ({exc})") from exc


def qids_from_problem_analysis(data: dict[str, Any]) -> set[str]:
    questions = data.get("questions") if isinstance(data, dict) else []
    if not isinstance(questions, list):
        return set()
    return {str(q.get("id")) for q in questions if isinstance(q, dict) and q.get("id")}


def qids_from_model_route(data: dict[str, Any]) -> set[str]:
    questions = data.get("questions") if isinstance(data, dict) else []
    if not isinstance(questions, list):
        return set()
    return {str(q.get("question_id")) for q in questions if isinstance(q, dict) and q.get("question_id")}


def qids_from_model_results(data: dict[str, Any]) -> set[str]:
    questions = data.get("questions") if isinstance(data, dict) else []
    if not isinstance(questions, list):
        return set()
    return {str(q.get("question_id")) for q in questions if isinstance(q, dict) and q.get("question_id")}


def qids_from_items_contract(data: dict[str, Any]) -> set[str]:
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        return set()
    return {str(item.get("question_id")) for item in items if isinstance(item, dict) and item.get("question_id")}


def is_relative_contract_path(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    return not Path(text).is_absolute()


def check_optional_evidence_contracts(failures: list[str]) -> None:
    if DATA_PLAN_FILE.exists():
        data_plan = load_json(DATA_PLAN_FILE)
        data_files = data_plan.get("data_files") if isinstance(data_plan, dict) else []
        if not isinstance(data_files, list):
            failures.append("data_plan.json 中没有 data_files[]")
        else:
            for item in data_files:
                if not isinstance(item, dict):
                    continue
                for key in ("path", "cleaned_output"):
                    if not is_relative_contract_path(item.get(key)):
                        failures.append(f"data_plan.json 的 {key} 必须是相对路径：{item.get(key)}")

    if VISUALIZATION_PLAN_FILE.exists():
        visualization_plan = load_json(VISUALIZATION_PLAN_FILE)
        figures = visualization_plan.get("figures") if isinstance(visualization_plan, dict) else []
        if not isinstance(figures, list):
            failures.append("visualization_plan.json 中没有 figures[]")
        else:
            for figure in figures:
                if not isinstance(figure, dict):
                    continue
                if not str(figure.get("figure_id") or "").strip():
                    failures.append("visualization_plan.json 中存在缺少 figure_id 的图表")
                if not str(figure.get("output_path") or "").strip():
                    failures.append(f"{figure.get('figure_id', '<unknown>')} 缺少 output_path")
                if not is_relative_contract_path(figure.get("output_path")):
                    failures.append(f"visualization_plan.json 的 output_path 必须是相对路径：{figure.get('output_path')}")
                if not is_relative_contract_path(figure.get("data_source")):
                    failures.append(f"visualization_plan.json 的 data_source 必须是相对路径：{figure.get('data_source')}")

    if FIGURE_INDEX_FILE.exists():
        figure_index = load_json(FIGURE_INDEX_FILE)
        figures = figure_index.get("figures") if isinstance(figure_index, dict) else []
        if not isinstance(figures, list):
            failures.append("figure_index.json 中没有 figures[]")
        else:
            for figure in figures:
                if isinstance(figure, dict) and not is_relative_contract_path(figure.get("path")):
                    failures.append(f"figure_index.json 的 path 必须是相对路径：{figure.get('path')}")


def check_optional_result_contracts(failures: list[str], route_qids: set[str], tasks: Any) -> None:
    if MODEL_RESULTS_FILE.exists():
        model_results = load_json(MODEL_RESULTS_FILE)
        for qid in qids_from_model_results(model_results):
            if route_qids and qid not in route_qids:
                failures.append(f"model_results.json 引用了不存在的 question_id：{qid}")

    if METRICS_FILE.exists():
        metrics = load_json(METRICS_FILE)
        for qid in qids_from_items_contract(metrics):
            if route_qids and qid not in route_qids:
                failures.append(f"metrics.json 引用了不存在的 question_id：{qid}")

    if CONCLUSIONS_FILE.exists():
        conclusions = load_json(CONCLUSIONS_FILE)
        conclusion_qids = qids_from_items_contract(conclusions)
        for qid in conclusion_qids:
            if route_qids and qid not in route_qids:
                failures.append(f"conclusions.json 引用了不存在的 question_id：{qid}")
        items = conclusions.get("items") if isinstance(conclusions, dict) else []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("question_id") and not str(item.get("conclusion_text") or "").strip():
                    failures.append(f"conclusions.json 中 {item.get('question_id')} 缺少 conclusion_text")

    if TABLE_INDEX_FILE.exists():
        table_index = load_json(TABLE_INDEX_FILE)
        tables = table_index.get("tables") if isinstance(table_index, dict) else []
        if not isinstance(tables, list):
            failures.append("table_index.json 中没有 tables[]")
        else:
            for table in tables:
                if not isinstance(table, dict):
                    continue
                if not is_relative_contract_path(table.get("path")):
                    failures.append(f"table_index.json 的 path 必须是相对路径：{table.get('path')}")
                qid = str(table.get("question_id") or "").strip()
                if route_qids and qid and qid != "ALL" and qid not in route_qids:
                    failures.append(f"table_index.json 引用了不存在的 question_id：{qid}")

    result_contracts_exist = any(path.exists() for path in (MODEL_RESULTS_FILE, METRICS_FILE, CONCLUSIONS_FILE, TABLE_INDEX_FILE))
    if result_contracts_exist and isinstance(tasks, list):
        required = {"result_summary", "key_metrics", "tables", "conclusions", "evidence_status"}
        for task in tasks:
            if not isinstance(task, dict) or not task.get("question_id"):
                continue
            missing = required - set(task)
            if missing:
                failures.append(f"tasks.json 中 {task.get('id', task.get('question_id'))} 缺少结果证据字段：{sorted(missing)}")


def main() -> int:
    failures: list[str] = []
    for path in (PROBLEM_ANALYSIS_FILE, MODEL_ROUTE_FILE, RUBRIC_ALIGNMENT_FILE, TASKS_FILE):
        if not path.exists():
            failures.append(f"缺少契约文件：{path}")

    if failures:
        for failure in failures:
            print(f"❌ {failure}")
        return 1

    analysis = load_json(PROBLEM_ANALYSIS_FILE)
    model_route = load_json(MODEL_ROUTE_FILE)
    rubric_alignment = load_json(RUBRIC_ALIGNMENT_FILE)
    tasks = load_json(TASKS_FILE)

    analysis_qids = qids_from_problem_analysis(analysis)
    route_qids = qids_from_model_route(model_route)
    if not analysis_qids:
        failures.append("problem_analysis.json 中没有 questions[].id")
    if not route_qids:
        failures.append("model_route.json 中没有 questions[].question_id")
    missing = analysis_qids - route_qids
    if missing:
        failures.append(f"model_route.json 未覆盖题意分析中的子问题：{sorted(missing)}")

    rubric_items = rubric_alignment.get("items") if isinstance(rubric_alignment, dict) else []
    if not isinstance(rubric_items, list) or not rubric_items:
        failures.append("rubric_alignment.json 中没有 items[]")
    else:
        for item in rubric_items:
            if not isinstance(item, dict):
                continue
            qid = str(item.get("question_id") or "")
            if qid and qid not in route_qids:
                failures.append(f"rubric_alignment.json 引用了不存在的 question_id：{qid}")

    if not isinstance(tasks, list) or not tasks:
        failures.append("tasks.json 不是非空数组")
    else:
        task_qids = {str(t.get("question_id")) for t in tasks if isinstance(t, dict) and t.get("question_id")}
        for qid in route_qids:
            if qid not in task_qids:
                failures.append(f"tasks.json 中没有追溯到 model_route.json 的问题任务：{qid}")

    questions = model_route.get("questions") if isinstance(model_route, dict) else []
    if isinstance(questions, list):
        for question in questions:
            if not isinstance(question, dict):
                continue
            for fig in question.get("figures", []):
                if not isinstance(fig, dict):
                    continue
                expected_path = str(fig.get("expected_path") or "")
                if expected_path and Path(expected_path).is_absolute():
                    failures.append(f"expected_path 必须是相对路径：{expected_path}")

    check_optional_evidence_contracts(failures)
    check_optional_result_contracts(failures, route_qids, tasks)

    if failures:
        for failure in failures:
            print(f"❌ {failure}")
        return 1

    print("✅ 工作流契约检查通过")
    print(f"   子问题：{sorted(route_qids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

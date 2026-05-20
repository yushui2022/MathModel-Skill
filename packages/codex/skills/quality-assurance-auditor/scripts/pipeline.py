import json
import os
import sys
from pathlib import Path


BASE_DIR = Path.cwd()
PROBLEM_DIR = BASE_DIR / "problem_files"
OUTPUT_DIR = BASE_DIR / "paper_output"
MICRO_UNITS_DIR = OUTPUT_DIR / "micro_units"
TASKS_FILE = OUTPUT_DIR / "tasks.json"
PROBLEM_ANALYSIS_FILE = OUTPUT_DIR / "step1" / "problem_analysis.json"
PLAN_DIR = OUTPUT_DIR / "plan"
MODEL_ROUTE_FILE = PLAN_DIR / "model_route.json"
RUBRIC_ALIGNMENT_FILE = PLAN_DIR / "rubric_alignment.json"
DATA_PLAN_FILE = PLAN_DIR / "data_plan.json"
VISUALIZATION_PLAN_FILE = PLAN_DIR / "visualization_plan.json"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
RESULTS_DIR = OUTPUT_DIR / "results"
MODEL_RESULTS_FILE = RESULTS_DIR / "model_results.json"
METRICS_FILE = RESULTS_DIR / "metrics.json"
CONCLUSIONS_FILE = RESULTS_DIR / "conclusions.json"
TABLE_INDEX_FILE = OUTPUT_DIR / "tables" / "table_index.json"


def init_project() -> None:
    for d in (PROBLEM_DIR, OUTPUT_DIR, MICRO_UNITS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def has_problem_files() -> bool:
    if not PROBLEM_DIR.exists():
        return False
    return any(PROBLEM_DIR.iterdir())


def load_existing_tasks() -> list[dict] | None:
    if not TASKS_FILE.exists():
        return None
    try:
        tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        return tasks if isinstance(tasks, list) else None
    except Exception:
        return None


def load_problem_analysis() -> dict | None:
    if not PROBLEM_ANALYSIS_FILE.exists():
        return None
    try:
        data = json.loads(PROBLEM_ANALYSIS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def load_model_route() -> dict | None:
    if not MODEL_ROUTE_FILE.exists():
        return None
    try:
        data = json.loads(MODEL_ROUTE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def load_rubric_alignment() -> dict | None:
    if not RUBRIC_ALIGNMENT_FILE.exists():
        return None
    try:
        data = json.loads(RUBRIC_ALIGNMENT_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def load_json_contract(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def is_relative_path(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    return not Path(text).is_absolute()


def figures_by_question(visualization_plan: dict | None) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    if not visualization_plan:
        return grouped
    figures = visualization_plan.get("figures")
    if not isinstance(figures, list):
        return grouped
    for figure in figures:
        if not isinstance(figure, dict):
            continue
        qid = str(figure.get("question_id") or "").strip()
        if qid:
            grouped.setdefault(qid, []).append(figure)
    return grouped


def question_ids_from_route(model_route: dict | None) -> set[str]:
    questions = model_route.get("questions") if isinstance(model_route, dict) else []
    if not isinstance(questions, list):
        return set()
    return {str(item.get("question_id") or item.get("id")).strip() for item in questions if isinstance(item, dict) and (item.get("question_id") or item.get("id"))}


def group_items_by_question(items: object) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    if not isinstance(items, list):
        return grouped
    for item in items:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped.setdefault(qid, []).append(item)
    return grouped


def model_results_by_question(model_results: dict | None) -> dict[str, dict]:
    questions = model_results.get("questions") if isinstance(model_results, dict) else []
    grouped: dict[str, dict] = {}
    if not isinstance(questions, list):
        return grouped
    for item in questions:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped[qid] = item
    return grouped


def metrics_by_question(metrics: dict | None) -> dict[str, list[dict]]:
    items = metrics.get("items") if isinstance(metrics, dict) else []
    return group_items_by_question(items)


def conclusions_by_question(conclusions: dict | None) -> dict[str, list[dict]]:
    items = conclusions.get("items") if isinstance(conclusions, dict) else []
    return group_items_by_question(items)


def tables_by_question(table_index: dict | None) -> dict[str, list[dict]]:
    tables = table_index.get("tables") if isinstance(table_index, dict) else []
    return group_items_by_question(tables)


def compact_metrics(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        result.append(
            {
                "metric_name": item.get("metric_name", ""),
                "metric_role": item.get("metric_role", ""),
                "value": item.get("value", None),
                "unit": item.get("unit", ""),
                "status": item.get("status", ""),
            }
        )
    return result


def compact_tables(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        result.append(
            {
                "table_id": item.get("table_id", ""),
                "title": item.get("title", ""),
                "purpose": item.get("purpose", ""),
                "path": item.get("path", ""),
                "status": item.get("status", ""),
            }
        )
    return result


def compact_conclusions(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        result.append(
            {
                "conclusion_text": item.get("conclusion_text", ""),
                "evidence_status": item.get("evidence_status", ""),
            }
        )
    return result


def evidence_status_for(result_item: dict | None, metric_items: list[dict], table_items: list[dict], conclusion_items: list[dict]) -> str:
    if not result_item and not metric_items and not table_items and not conclusion_items:
        return "missing"
    markers = [
        str((result_item or {}).get("evidence_status") or ""),
        str((result_item or {}).get("status") or ""),
        *[str(item.get("status") or item.get("evidence_status") or "") for item in metric_items],
        *[str(item.get("status") or item.get("evidence_status") or "") for item in table_items],
        *[str(item.get("status") or item.get("evidence_status") or "") for item in conclusion_items],
    ]
    if any(marker in {"needs_real_modeling", "draft_contract", "to_be_filled", "template", "draft"} for marker in markers):
        return "needs_real_modeling"
    return "ready"


def build_result_evidence(model_results: dict | None, metrics: dict | None, conclusions: dict | None, table_index: dict | None) -> dict[str, dict]:
    result_map = model_results_by_question(model_results)
    metric_map = metrics_by_question(metrics)
    conclusion_map = conclusions_by_question(conclusions)
    table_map = tables_by_question(table_index)
    all_tables = table_map.get("ALL", [])
    qids = set(result_map) | set(metric_map) | set(conclusion_map) | {qid for qid in table_map if qid != "ALL"}
    evidence: dict[str, dict] = {}
    for qid in qids:
        result_item = result_map.get(qid)
        metric_items = metric_map.get(qid, [])
        table_items = table_map.get(qid, []) + all_tables
        conclusion_items = conclusion_map.get(qid, [])
        evidence[qid] = {
            "result_summary": (result_item or {}).get("result_summary", ""),
            "key_metrics": compact_metrics(metric_items),
            "tables": compact_tables(table_items),
            "conclusions": compact_conclusions(conclusion_items),
            "evidence_status": evidence_status_for(result_item, metric_items, table_items, conclusion_items),
        }
    return evidence


def manifest_has_result_evidence(tasks: list[dict]) -> bool:
    question_tasks = [task for task in tasks if isinstance(task, dict) and task.get("question_id")]
    if not question_tasks:
        return False
    required = {"result_summary", "key_metrics", "tables", "conclusions", "evidence_status"}
    return all(required.issubset(set(task.keys())) for task in question_tasks)


def check_evidence_contracts() -> list[str]:
    warnings: list[str] = []
    model_route = load_model_route()
    route_qids = question_ids_from_route(model_route)
    data_plan = load_json_contract(DATA_PLAN_FILE)
    visualization_plan = load_json_contract(VISUALIZATION_PLAN_FILE)
    figure_index = load_json_contract(FIGURE_INDEX_FILE)
    model_results = load_json_contract(MODEL_RESULTS_FILE)
    metrics = load_json_contract(METRICS_FILE)
    conclusions = load_json_contract(CONCLUSIONS_FILE)
    table_index = load_json_contract(TABLE_INDEX_FILE)

    if data_plan is None:
        warnings.append(f"缺少数据处理计划：{DATA_PLAN_FILE}")
    else:
        data_files = data_plan.get("data_files")
        if not isinstance(data_files, list):
            warnings.append("data_plan.json 中没有 data_files[]")
        else:
            for item in data_files:
                if not isinstance(item, dict):
                    continue
                for key in ("path", "cleaned_output"):
                    if not is_relative_path(item.get(key)):
                        warnings.append(f"data_plan.json 的 {key} 必须是相对路径：{item.get(key)}")

    if visualization_plan is None:
        warnings.append(f"缺少图表规划：{VISUALIZATION_PLAN_FILE}")
    else:
        figures = visualization_plan.get("figures")
        if not isinstance(figures, list) or not figures:
            warnings.append("visualization_plan.json 中没有 figures[]")
        else:
            for figure in figures:
                if not isinstance(figure, dict):
                    continue
                if not str(figure.get("figure_id") or "").strip():
                    warnings.append("visualization_plan.json 中存在缺少 figure_id 的图表")
                if not str(figure.get("output_path") or "").strip():
                    warnings.append(f"{figure.get('figure_id', '<unknown>')} 缺少 output_path")
                if not is_relative_path(figure.get("output_path")):
                    warnings.append(f"visualization_plan.json 的 output_path 必须是相对路径：{figure.get('output_path')}")
                if not is_relative_path(figure.get("data_source")):
                    warnings.append(f"visualization_plan.json 的 data_source 必须是相对路径：{figure.get('data_source')}")

    if figure_index is None:
        warnings.append(f"缺少图表索引：{FIGURE_INDEX_FILE}")
    else:
        figures = figure_index.get("figures")
        if not isinstance(figures, list):
            warnings.append("figure_index.json 中没有 figures[]")
        else:
            for figure in figures:
                if isinstance(figure, dict) and not is_relative_path(figure.get("path")):
                    warnings.append(f"figure_index.json 的 path 必须是相对路径：{figure.get('path')}")

    result_map = model_results_by_question(model_results)
    metric_map = metrics_by_question(metrics)
    conclusion_map = conclusions_by_question(conclusions)
    table_map = tables_by_question(table_index)

    if model_results is None:
        warnings.append(f"缺少模型结果契约：{MODEL_RESULTS_FILE}")
    elif route_qids:
        for qid in result_map:
            if qid not in route_qids:
                warnings.append(f"model_results.json 引用了不存在的 question_id：{qid}")

    if metrics is None:
        warnings.append(f"缺少评价指标契约：{METRICS_FILE}")
    elif route_qids:
        for qid in metric_map:
            if qid not in route_qids:
                warnings.append(f"metrics.json 引用了不存在的 question_id：{qid}")

    if conclusions is None:
        warnings.append(f"缺少结论契约：{CONCLUSIONS_FILE}")
    elif route_qids:
        for qid in conclusion_map:
            if qid not in route_qids:
                warnings.append(f"conclusions.json 引用了不存在的 question_id：{qid}")

    if table_index is None:
        warnings.append(f"缺少表格索引契约：{TABLE_INDEX_FILE}")
    else:
        tables = table_index.get("tables")
        if not isinstance(tables, list):
            warnings.append("table_index.json 中没有 tables[]")
        else:
            for table in tables:
                if not isinstance(table, dict):
                    continue
                path = table.get("path")
                if not is_relative_path(path):
                    warnings.append(f"table_index.json 的 path 必须是相对路径：{path}")
                qid = str(table.get("question_id") or "").strip()
                if route_qids and qid and qid != "ALL" and qid not in route_qids:
                    warnings.append(f"table_index.json 引用了不存在的 question_id：{qid}")

    if route_qids:
        figure_map = figures_by_question(visualization_plan)
        result_evidence = build_result_evidence(model_results, metrics, conclusions, table_index)
        for qid in sorted(route_qids):
            evidence = result_evidence.get(qid, {})
            has_metric = bool(evidence.get("key_metrics"))
            has_table = bool(evidence.get("tables"))
            has_figure = bool(figure_map.get(qid))
            if not any((has_metric, has_table, has_figure)):
                warnings.append(f"{qid} 缺少图表、表格或指标证据之一，正文生成时只能写通用草稿")
            if evidence.get("evidence_status") == "missing":
                warnings.append(f"{qid} 缺少模型结果/指标/结论契约，真实建模结果待补")
            elif evidence.get("evidence_status") == "needs_real_modeling":
                warnings.append(f"{qid} 的结果证据仍是草稿骨架，需要结合真实建模代码补齐")
    return warnings


def rubric_points_for(question_id: str, rubric_alignment: dict | None) -> list[str]:
    if not rubric_alignment:
        return []
    items = rubric_alignment.get("items")
    if not isinstance(items, list):
        return []
    points = []
    for item in items:
        if isinstance(item, dict) and str(item.get("question_id")) == question_id:
            point = str(item.get("rubric_point") or "").strip()
            if point:
                points.append(point)
    return points


def figure_titles(figures: object) -> list[str]:
    if not isinstance(figures, list):
        return []
    titles = []
    for item in figures:
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
        else:
            title = str(item).strip()
        if title:
            titles.append(title)
    return titles


def question_section_name(index: int, question: dict) -> str:
    title = str(question.get("title") or "").strip()
    if title:
        return title
    numerals = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    suffix = numerals[index - 1] if 0 < index <= len(numerals) else str(index)
    return f"问题{suffix}"


def add_task(tasks: list[dict], task_id: str, section: str, target_words: int, **extra: object) -> None:
    payload = {
        "id": task_id,
        "section": section,
        "status": "pending",
        "target_words": int(target_words),
        "file_path": str(MICRO_UNITS_DIR / f"{task_id}.txt"),
    }
    payload.update(extra)
    tasks.append(payload)


def generate_dynamic_manifest(analysis: dict, target_words: int) -> list[dict]:
    questions = analysis.get("questions")
    if not isinstance(questions, list) or not questions:
        questions = []

    tasks: list[dict] = []
    add_task(tasks, "ABS-1", "摘要", target_words, role="background_and_problem")
    add_task(tasks, "ABS-2", "摘要", target_words, role="methods_overview")
    add_task(tasks, "ABS-3", "摘要", target_words, role="results_overview")
    add_task(tasks, "ABS-4", "摘要", target_words, role="validation_and_value")
    add_task(tasks, "ABS-5", "摘要", 120, role="keywords")

    add_task(tasks, "INTRO-1", "问题重述", target_words, role="background")
    add_task(tasks, "INTRO-2", "问题重述", target_words, role="question_breakdown")
    add_task(tasks, "INTRO-3", "问题重述", target_words, role="computable_tasks")

    add_task(tasks, "ASSUMP-1", "模型假设", target_words, role="assumptions")
    add_task(tasks, "ASSUMP-2", "模型假设", target_words, role="assumption_rationale")
    add_task(tasks, "SYMBOL-1", "符号说明", target_words, role="symbol_table")

    data_files = analysis.get("data_files") if isinstance(analysis.get("data_files"), list) else []
    data_units = max(3, min(5, len(data_files) + 2))
    for i in range(1, data_units + 1):
        add_task(tasks, f"DATA-{i}", "数据预处理", target_words, role="data_processing", data_file_count=len(data_files))

    if not questions:
        questions = [
            {
                "id": "Q1",
                "title": "问题一",
                "task_type": "综合建模/统计分析",
                "recommended_models": {"baseline": "可解释基线模型", "improved": "结合题目需求的改进模型"},
                "validation_plan": ["结果复核", "敏感性分析"],
                "figure_suggestions": ["数据概览图", "结果对比图"],
            }
        ]

    for index, question in enumerate(questions, start=1):
        section = question_section_name(index, question)
        qid = str(question.get("id") or f"Q{index}")
        model = question.get("recommended_models") if isinstance(question.get("recommended_models"), dict) else {}
        metadata = {
            "question_id": qid,
            "task_type": question.get("task_type", "综合建模/统计分析"),
            "baseline_model": model.get("baseline", "可解释基线模型"),
            "improved_model": model.get("improved", "结合题目需求的改进模型"),
            "validation_plan": question.get("validation_plan", []),
            "figure_suggestions": question.get("figure_suggestions", []),
            "result_summary": "",
            "key_metrics": [],
            "tables": [],
            "conclusions": [],
            "evidence_status": "missing",
        }
        roles = [
            "task_definition",
            "model_rationale",
            "model_formulation",
            "algorithm_design",
            "result_presentation",
            "validation",
            "sensitivity",
            "question_conclusion",
        ]
        for unit_index, role in enumerate(roles, start=1):
            add_task(tasks, f"{qid}-{unit_index}", section, target_words, role=role, **metadata)

    analysis_units = max(3, min(6, len(questions) + 2))
    for i in range(1, analysis_units + 1):
        add_task(tasks, f"ANALYSIS-{i}", "结果分析", target_words, role="result_analysis")

    add_task(tasks, "EVAL-1", "模型评价", target_words, role="advantages")
    add_task(tasks, "EVAL-2", "模型评价", target_words, role="limitations")
    add_task(tasks, "EVAL-3", "模型评价", target_words, role="extension")

    conclusion_units = max(2, min(4, len(questions) + 1))
    for i in range(1, conclusion_units + 1):
        add_task(tasks, f"CONCL-{i}", "结论", target_words, role="conclusion")

    add_task(tasks, "REF-1", "参考文献", 160, role="references")
    add_task(tasks, "APP-1", "附录", target_words, role="reproducibility")
    add_task(tasks, "APP-2", "附录", target_words, role="code_and_paths")
    return tasks


def generate_route_manifest(
    model_route: dict,
    rubric_alignment: dict | None,
    target_words: int,
    visualization_plan: dict | None = None,
    result_evidence: dict[str, dict] | None = None,
) -> list[dict]:
    questions = model_route.get("questions")
    if not isinstance(questions, list) or not questions:
        questions = []
    result_evidence = result_evidence or {}

    tasks: list[dict] = []
    add_task(tasks, "ABS-1", "摘要", target_words, role="background_and_problem")
    add_task(tasks, "ABS-2", "摘要", target_words, role="methods_overview")
    add_task(tasks, "ABS-3", "摘要", target_words, role="results_overview")
    add_task(tasks, "ABS-4", "摘要", target_words, role="validation_and_value")
    add_task(tasks, "ABS-5", "摘要", 120, role="keywords")

    add_task(tasks, "INTRO-1", "问题重述", target_words, role="background")
    add_task(tasks, "INTRO-2", "问题重述", target_words, role="question_breakdown")
    add_task(tasks, "INTRO-3", "问题重述", target_words, role="computable_tasks")

    add_task(tasks, "ASSUMP-1", "模型假设", target_words, role="assumptions")
    add_task(tasks, "ASSUMP-2", "模型假设", target_words, role="assumption_rationale")
    add_task(tasks, "SYMBOL-1", "符号说明", target_words, role="symbol_table")

    for i in range(1, 4):
        add_task(tasks, f"DATA-{i}", "数据预处理", target_words, role="data_processing")

    if not questions:
        questions = [
            {
                "question_id": "Q1",
                "title": "问题一",
                "task_type": "综合建模/统计分析",
                "baseline_model": "可解释基线模型",
                "main_model": "结合题目需求的主模型",
                "backup_models": ["可解释统计模型"],
                "model_reason": "根据题目目标选择可解释、可验证的主模型。",
                "formula_requirements": ["定义输入变量与输出目标", "说明核心模型函数或目标函数", "给出评价指标与检验方式"],
                "validation": ["结果复核", "敏感性分析"],
                "figures": [{"title": "数据概览图"}, {"title": "结果对比图"}],
            }
        ]

    planned_figures_by_qid = figures_by_question(visualization_plan)
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        section = question_section_name(index, {"title": question.get("title")})
        qid = str(question.get("question_id") or question.get("id") or f"Q{index}")
        planned_figures = planned_figures_by_qid.get(qid, [])
        route_figure_titles = figure_titles(question.get("figures"))
        planned_figure_titles = figure_titles(planned_figures)
        figure_suggestions = list(dict.fromkeys(route_figure_titles + planned_figure_titles))
        evidence = result_evidence.get(qid, {})
        metadata = {
            "question_id": qid,
            "task_type": question.get("task_type", "综合建模/统计分析"),
            "baseline_model": question.get("baseline_model", "可解释基线模型"),
            "main_model": question.get("main_model", question.get("baseline_model", "结合题目需求的主模型")),
            "backup_models": question.get("backup_models", []),
            "model_reason": question.get("model_reason", ""),
            "formula_requirements": question.get("formula_requirements", []),
            "validation_plan": question.get("validation", []),
            "figure_suggestions": figure_suggestions,
            "figures": question.get("figures", []),
            "planned_figures": planned_figures,
            "rubric_points": rubric_points_for(qid, rubric_alignment),
            "paper_sections": question.get("paper_sections", []),
            "result_summary": evidence.get("result_summary", ""),
            "key_metrics": evidence.get("key_metrics", []),
            "tables": evidence.get("tables", []),
            "conclusions": evidence.get("conclusions", []),
            "evidence_status": evidence.get("evidence_status", "missing"),
            "contract_source": "paper_output/plan/model_route.json",
        }
        roles = [
            "task_definition",
            "model_rationale",
            "model_formulation",
            "algorithm_design",
            "result_presentation",
            "validation",
            "sensitivity",
            "question_conclusion",
        ]
        for unit_index, role in enumerate(roles, start=1):
            add_task(tasks, f"{qid}-{unit_index}", section, target_words, role=role, **metadata)

    analysis_units = max(3, min(6, len(questions) + 2))
    for i in range(1, analysis_units + 1):
        add_task(tasks, f"ANALYSIS-{i}", "结果分析", target_words, role="result_analysis")

    add_task(tasks, "EVAL-1", "模型评价", target_words, role="advantages")
    add_task(tasks, "EVAL-2", "模型评价", target_words, role="limitations")
    add_task(tasks, "EVAL-3", "模型评价", target_words, role="extension")

    conclusion_units = max(2, min(4, len(questions) + 1))
    for i in range(1, conclusion_units + 1):
        add_task(tasks, f"CONCL-{i}", "结论", target_words, role="conclusion")

    add_task(tasks, "REF-1", "参考文献", 160, role="references")
    add_task(tasks, "APP-1", "附录", target_words, role="reproducibility")
    add_task(tasks, "APP-2", "附录", target_words, role="code_and_paths")
    return tasks


def generate_task_manifest(target_words: int = 300, force: bool = False) -> tuple[list[dict], bool]:
    existing = load_existing_tasks()
    if existing is not None and not force:
        if not MODEL_ROUTE_FILE.exists() or manifest_has_result_evidence(existing):
            return existing, False

    model_route = load_model_route()
    if model_route is not None:
        rubric_alignment = load_rubric_alignment()
        visualization_plan = load_json_contract(VISUALIZATION_PLAN_FILE)
        model_results = load_json_contract(MODEL_RESULTS_FILE)
        metrics = load_json_contract(METRICS_FILE)
        conclusions = load_json_contract(CONCLUSIONS_FILE)
        table_index = load_json_contract(TABLE_INDEX_FILE)
        result_evidence = build_result_evidence(model_results, metrics, conclusions, table_index)
        tasks = generate_route_manifest(model_route, rubric_alignment, target_words, visualization_plan, result_evidence)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return tasks, True

    analysis = load_problem_analysis()
    if analysis is not None:
        tasks = generate_dynamic_manifest(analysis, target_words)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return tasks, True

    sections = [
        ("ABS", "摘要", 5),
        ("INTRO", "问题重述", 3),
        ("ASSUMP", "模型假设", 2),
        ("SYMBOL", "符号说明", 1),
        ("DATA", "数据预处理", 4),
        ("MODEL1", "问题一", 8),
        ("MODEL2", "问题二", 8),
        ("MODEL3", "问题三", 8),
        ("ANALYSIS", "结果分析", 5),
        ("EVAL", "模型评价", 3),
        ("CONCL", "结论", 2),
        ("REF", "参考文献", 1),
        ("APP", "附录", 2),
    ]

    tasks: list[dict] = []
    for sec_code, sec_name, unit_count in sections:
        for i in range(1, unit_count + 1):
            task_id = f"{sec_code}-{i}"
            tasks.append(
                {
                    "id": task_id,
                    "section": sec_name,
                    "status": "pending",
                    "target_words": int(target_words),
                    "file_path": str(MICRO_UNITS_DIR / f"{task_id}.txt"),
                }
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    return tasks, True


def audit_gate(stage_name: str) -> bool:
    if stage_name == "赛题目录检查":
        if not has_problem_files():
            print(f"❌ 审计未通过：{PROBLEM_DIR} 为空")
            print("🔒 请先把赛题 PDF/Word 和附件数据放进 problem_files/ 再继续")
            return False

    return True


def verify_completeness() -> tuple[int, int, int]:
    if not TASKS_FILE.exists():
        return 0, 0, 0

    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    total = len(tasks)
    ok = 0
    total_chars = 0

    for t in tasks:
        p = Path(t["file_path"])
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")
        total_chars += len(content)
        if len(content) >= int(t.get("target_words", 0)):
            ok += 1

    return ok, total, total_chars


def scan_generated_text() -> list[str]:
    warnings: list[str] = []
    targets = []
    if (OUTPUT_DIR / "final_paper.md").exists():
        targets.append(OUTPUT_DIR / "final_paper.md")
    if MICRO_UNITS_DIR.exists():
        targets.extend(sorted(MICRO_UNITS_DIR.glob("*.txt")))

    bad_markers = ["内容生成中", "论文题目缺失", "关键词1；关键词2"]
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for marker in bad_markers:
            if marker in text:
                warnings.append(f"{path}: 检测到占位痕迹 `{marker}`")
    return warnings


def run_pipeline() -> int:
    print("=== QA 流水线（quality-assurance-auditor）===")
    init_project()

    if not audit_gate("赛题目录检查"):
        return 1

    force_regenerate = os.environ.get("MATHMODEL_REGENERATE_TASKS") == "1"
    tasks, generated = generate_task_manifest(target_words=270, force=force_regenerate)
    action = "已生成" if generated else "已读取已有"
    print(f"[+] {action}任务清单：{TASKS_FILE}（{len(tasks)} 个微单元）")
    if MODEL_ROUTE_FILE.exists():
        print(f"[+] 已连接模型路线契约：{MODEL_ROUTE_FILE}")
        if RUBRIC_ALIGNMENT_FILE.exists():
            print(f"[+] 已连接评分点契约：{RUBRIC_ALIGNMENT_FILE}")
        if MODEL_RESULTS_FILE.exists():
            print(f"[+] 已连接结果证据契约：{MODEL_RESULTS_FILE}")
        if TABLE_INDEX_FILE.exists():
            print(f"[+] 已连接表格证据索引：{TABLE_INDEX_FILE}")
    elif PROBLEM_ANALYSIS_FILE.exists():
        print(f"[+] 已连接结构化赛题分析：{PROBLEM_ANALYSIS_FILE}")
    else:
        print("[!] 未找到 problem_analysis.json，已使用通用任务清单模板")

    evidence_warnings = check_evidence_contracts()
    if evidence_warnings:
        print("[!] 数据/图表/结果证据链提示：")
        for item in evidence_warnings[:20]:
            print(f"    - {item}")
        if len(evidence_warnings) > 20:
            print(f"    - ... 共 {len(evidence_warnings)} 项")
    else:
        print("[+] 数据/图表/结果证据链契约检查通过")

    ok, total, total_chars = verify_completeness()
    print(f"[+] 进度：{ok}/{total}")
    print(f"[+] 当前总长度：{total_chars}")

    warnings = scan_generated_text()
    if warnings:
        print("[!] 发现需要人工复核的占位痕迹：")
        for item in warnings[:20]:
            print(f"    - {item}")
        if len(warnings) > 20:
            print(f"    - ... 共 {len(warnings)} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline())

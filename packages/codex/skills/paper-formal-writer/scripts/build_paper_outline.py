import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "paper_output"
PLAN_DIR = OUTPUT_DIR / "plan"

INPUT_FILES = {
    "problem_analysis": OUTPUT_DIR / "step1" / "problem_analysis.json",
    "model_route": PLAN_DIR / "model_route.json",
    "rubric_alignment": PLAN_DIR / "rubric_alignment.json",
    "figure_index": OUTPUT_DIR / "figure_index.json",
    "model_results": OUTPUT_DIR / "results" / "model_results.json",
    "metrics": OUTPUT_DIR / "results" / "metrics.json",
    "conclusions": OUTPUT_DIR / "results" / "conclusions.json",
    "table_index": OUTPUT_DIR / "tables" / "table_index.json",
}

OUTLINE_FILE = PLAN_DIR / "paper_outline.json"


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


def rel(path: Path) -> str:
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def natural_q_key(qid: str) -> tuple[int, str]:
    match = re.search(r"\d+", qid)
    if match:
        return (int(match.group()), qid)
    return (10_000, qid)


def normalize_qid(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"Q\s*(\d+)", text, flags=re.IGNORECASE)
    if match:
        return f"Q{int(match.group(1))}"
    match = re.search(r"问题\s*([一二三四五六七八九十\d]+)", text)
    if not match:
        return text
    raw = match.group(1)
    chinese = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    if raw.isdigit():
        return f"Q{int(raw)}"
    return f"Q{chinese.get(raw, raw)}"


def list_items(data: Any, key: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    items = data.get(key, [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def collect_questions(problem_analysis: Any, model_route: Any, model_results: Any) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}

    for source_name, source, key in (
        ("problem_analysis", problem_analysis, "questions"),
        ("model_route", model_route, "questions"),
        ("model_results", model_results, "questions"),
    ):
        for item in list_items(source, key):
            qid = normalize_qid(item.get("question_id") or item.get("id") or item.get("title"))
            if not qid:
                continue
            target = by_id.setdefault(qid, {"question_id": qid})
            q_number = re.sub(r"\D+", "", qid)
            title = item.get("title") or f"问题{q_number}"
            if title:
                target.setdefault("title", title)
            for field in (
                "summary",
                "raw_text",
                "task_type",
                "core_goal",
                "main_model",
                "baseline_model",
                "model_reason",
                "result_summary",
            ):
                if not item.get(field):
                    continue
                if source_name == "model_route" and field in {
                    "task_type",
                    "core_goal",
                    "main_model",
                    "baseline_model",
                    "model_reason",
                }:
                    target[field] = item[field]
                elif source_name == "model_results" and field == "result_summary":
                    target[field] = item[field]
                elif not target.get(field):
                    target[field] = item[field]
            if item.get("formula_requirements"):
                if source_name == "model_route" or not target.get("formula_requirements"):
                    target["formula_requirements"] = item["formula_requirements"]
            target.setdefault("sources", []).append(source_name)

    return [by_id[qid] for qid in sorted(by_id, key=natural_q_key)]


def group_by_question(data: Any, key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in list_items(data, key):
        qid = normalize_qid(item.get("question_id"))
        if not qid:
            continue
        grouped.setdefault(qid, []).append(item)
    return grouped


def result_by_question(data: Any) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in list_items(data, "questions"):
        qid = normalize_qid(item.get("question_id"))
        if qid:
            grouped[qid] = item
    return grouped


def evidence_for_question(
    qid: str,
    result_map: dict[str, dict[str, Any]],
    metric_map: dict[str, list[dict[str, Any]]],
    conclusion_map: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    result = result_map.get(qid)
    if result:
        evidence.append(
            {
                "type": "model_result",
                "summary": result.get("result_summary") or result.get("title") or qid,
                "status": result.get("evidence_status") or result.get("status"),
            }
        )
    for item in metric_map.get(qid, []):
        evidence.append(
            {
                "type": "metric",
                "name": item.get("metric_name") or item.get("metric_role"),
                "role": item.get("metric_role"),
                "value": item.get("value"),
                "unit": item.get("unit"),
                "status": item.get("status"),
            }
        )
    for item in conclusion_map.get(qid, []):
        evidence.append(
            {
                "type": "conclusion",
                "text": item.get("conclusion_text"),
                "status": item.get("evidence_status") or item.get("status"),
            }
        )
    return evidence


def brief_items(items: list[dict[str, Any]], id_key: str) -> list[dict[str, Any]]:
    result = []
    for item in items:
        brief = {
            id_key: item.get(id_key),
            "title": item.get("title"),
            "path": item.get("path") or item.get("expected_path"),
            "purpose": item.get("purpose"),
            "status": item.get("status") or item.get("evidence_status"),
        }
        result.append({k: v for k, v in brief.items() if v not in (None, "", [])})
    return result


def build_question_section(
    question: dict[str, Any],
    index: int,
    figures: dict[str, list[dict[str, Any]]],
    tables: dict[str, list[dict[str, Any]]],
    result_map: dict[str, dict[str, Any]],
    metric_map: dict[str, list[dict[str, Any]]],
    conclusion_map: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    qid = question["question_id"]
    section_id = f"5.{index}"
    formulas = question.get("formula_requirements") or []
    required_figures = brief_items(figures.get(qid, []), "figure_id")
    required_tables = brief_items(tables.get(qid, []), "table_id")
    required_evidence = evidence_for_question(qid, result_map, metric_map, conclusion_map)

    return {
        "section_id": section_id,
        "title": f"{question.get('title', qid)}模型的建立与求解",
        "question_id": qid,
        "target_words": 2200,
        "task_type": question.get("task_type"),
        "core_goal": question.get("core_goal") or question.get("summary"),
        "main_model": question.get("main_model"),
        "required_figures": required_figures,
        "required_tables": required_tables,
        "required_formulas": formulas,
        "required_evidence": required_evidence,
        "subsections": [
            {
                "section_id": f"{section_id}.1",
                "title": "建模思路",
                "question_id": qid,
                "target_words": 300,
            },
            {
                "section_id": f"{section_id}.2",
                "title": "变量定义与公式推导",
                "question_id": qid,
                "target_words": 600,
                "required_formulas": formulas,
            },
            {
                "section_id": f"{section_id}.3",
                "title": "求解算法",
                "question_id": qid,
                "target_words": 400,
            },
            {
                "section_id": f"{section_id}.4",
                "title": "结果分析",
                "question_id": qid,
                "target_words": 650,
                "required_figures": required_figures,
                "required_tables": required_tables,
                "required_evidence": required_evidence,
            },
            {
                "section_id": f"{section_id}.5",
                "title": "模型检验或灵敏度分析",
                "question_id": qid,
                "target_words": 250,
            },
        ],
    }


def infer_title(problem_analysis: Any) -> str:
    excerpt = str(problem_analysis.get("problem_text_excerpt") or "") if isinstance(problem_analysis, dict) else ""
    for line in excerpt.splitlines():
        line = line.strip()
        if not line or "文件" in line or ".pdf" in line.lower():
            continue
        if re.search(r"^[A-Z]\s*题\s+\S", line) and len(line) <= 60:
            title = re.sub(r"^\s*[A-Z]\s*题\s*", "", line)
            if title:
                return f"{title}的数学模型研究"
    return "数学建模问题的模型建立与求解"


def build_outline() -> dict[str, Any]:
    data = {name: load_json(path) for name, path in INPUT_FILES.items()}
    warnings: list[str] = []
    for name, path in INPUT_FILES.items():
        value = data[name]
        if value is None:
            warnings.append(f"缺少输入文件：{rel(path)}")
        elif isinstance(value, dict) and value.get("__error__"):
            warnings.append(f"无法读取输入文件：{rel(path)} ({value['__error__']})")

    questions = collect_questions(data["problem_analysis"], data["model_route"], data["model_results"])
    if not questions:
        warnings.append("未能从 problem_analysis/model_route/model_results 中识别 Q* 子问题，已生成基础论文模板。")

    figure_map = group_by_question(data["figure_index"], "figures")
    table_map = group_by_question(data["table_index"], "tables")
    result_map = result_by_question(data["model_results"])
    metric_map = group_by_question(data["metrics"], "items")
    conclusion_map = group_by_question(data["conclusions"], "items")

    question_analysis_sections = []
    for index, question in enumerate(questions, start=1):
        question_analysis_sections.append(
            {
                "section_id": f"2.{index}",
                "title": f"{question.get('title', question['question_id'])}分析",
                "question_id": question["question_id"],
                "target_words": 500,
                "required_evidence": evidence_for_question(question["question_id"], result_map, metric_map, conclusion_map),
            }
        )

    model_sections = [
        build_question_section(question, index, figure_map, table_map, result_map, metric_map, conclusion_map)
        for index, question in enumerate(questions, start=1)
    ]
    question_count = max(1, len(questions))
    target_min = 6500 + 1200 * question_count
    target_ideal = 7500 + 1500 * question_count
    target_max = 10000 + 2200 * question_count

    outline = {
        "schema_version": "1.0",
        "generated_by": "paper-formal-writer/scripts/build_paper_outline.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "numbering_style": "1 / 1.1 / 1.1.1",
        "target_words": {"min": target_min, "ideal": target_ideal, "max": target_max},
        "title": infer_title(data["problem_analysis"]),
        "front_matter": {
            "abstract_target_words": 700,
            "keyword_count": "4-6",
            "requirements": [
                "摘要按子问题展开，必须写明方法、模型、算法、关键结果和结论。",
                "关键词应覆盖核心模型、算法和问题领域。",
            ],
        },
        "inputs": {name: rel(path) for name, path in INPUT_FILES.items()},
        "warnings": warnings,
        "questions": questions,
        "sections": [
            {
                "section_id": "1",
                "title": "问题重述",
                "target_words": 900,
                "subsections": [
                    {"section_id": "1.1", "title": "背景说明", "target_words": 200},
                    {"section_id": "1.2", "title": "题目任务", "target_words": 450},
                    {"section_id": "1.3", "title": "本文解决思路概述", "target_words": 250},
                ],
            },
            {
                "section_id": "2",
                "title": "问题分析",
                "target_words": 1600,
                "subsections": question_analysis_sections,
            },
            {"section_id": "3", "title": "模型假设", "target_words": 600, "subsections": []},
            {"section_id": "4", "title": "符号说明", "target_words": 500, "subsections": []},
            {
                "section_id": "5",
                "title": "模型的建立与求解",
                "target_words": sum(item["target_words"] for item in model_sections),
                "subsections": model_sections,
            },
            {"section_id": "6", "title": "模型检验与灵敏度分析", "target_words": 1000, "subsections": []},
            {"section_id": "7", "title": "模型评价与推广", "target_words": 800, "subsections": []},
            {"section_id": "8", "title": "参考文献", "target_words": 350, "subsections": []},
            {"section_id": "appendix", "title": "附录", "target_words": 600, "subsections": []},
        ],
    }
    return outline


def main() -> int:
    configure_utf8_stdio()
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    outline = build_outline()
    OUTLINE_FILE.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"正式论文大纲契约已生成：{rel(OUTLINE_FILE)}")
    if outline["warnings"]:
        print("Warnings:")
        for item in outline["warnings"]:
            print(f" - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from result_contract_templates import metric_templates, result_type, suggested_table_titles


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
PLAN_DIR = OUTPUT_DIR / "plan"
RESULTS_DIR = OUTPUT_DIR / "results"
TABLES_DIR = OUTPUT_DIR / "tables"
MODELING_CODE_DIR = OUTPUT_DIR / "code" / "modeling"
MODEL_ROUTE_FILE = PLAN_DIR / "model_route.json"
DATA_PLAN_FILE = PLAN_DIR / "data_plan.json"
VISUALIZATION_PLAN_FILE = PLAN_DIR / "visualization_plan.json"
DATA_CLEANED_DIR = OUTPUT_DIR / "data_cleaned"
GENERATED_BY = "model-code-and-result-generator/scripts/build_result_contracts.py"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def safe_slug(text: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "item"


def load_questions(model_route: dict[str, Any] | None) -> list[dict[str, Any]]:
    questions = model_route.get("questions") if isinstance(model_route, dict) else None
    if isinstance(questions, list) and questions:
        return [q for q in questions if isinstance(q, dict)]
    return [
        {
            "question_id": "Q1",
            "title": "问题一",
            "task_type": "综合建模/统计分析",
            "baseline_model": "可解释基线模型",
            "main_model": "结合题目需求的主模型",
            "model_reason": "模型路线尚未生成，需结合题意补充。",
        }
    ]


def find_cleaned_csv_files() -> list[Path]:
    if not DATA_CLEANED_DIR.exists():
        return []
    return sorted(DATA_CLEANED_DIR.rglob("*.csv"), key=lambda p: str(p).lower())


def read_csv_rows(path: Path, limit: int = 500) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                rows = []
                for idx, row in enumerate(reader):
                    if idx >= limit:
                        break
                    rows.append({str(k): str(v) for k, v in row.items()})
                return rows
        except Exception:
            continue
    return []


def to_float(value: object) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def profile_csv(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows = read_csv_rows(path)
    if not rows:
        return [], 0
    columns = list(rows[0].keys())
    profiles: list[dict[str, Any]] = []
    for column in columns:
        values = [row.get(column, "") for row in rows]
        non_empty = [v for v in values if str(v).strip()]
        numeric = [v for v in (to_float(value) for value in non_empty) if v is not None]
        item: dict[str, Any] = {
            "field": column,
            "sample_rows": len(rows),
            "non_null_count": len(non_empty),
            "missing_count": len(values) - len(non_empty),
            "inferred_type": "numeric" if len(numeric) >= max(1, len(non_empty) // 2) else "text",
            "mean": "",
            "std": "",
            "min": "",
            "max": "",
        }
        if numeric:
            item.update(
                {
                    "mean": round(mean(numeric), 6),
                    "std": round(pstdev(numeric), 6) if len(numeric) > 1 else 0,
                    "min": round(min(numeric), 6),
                    "max": round(max(numeric), 6),
                }
            )
        profiles.append(item)
    return profiles, len(rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_data_profile_tables(cleaned_files: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    summary = {"cleaned_file_count": len(cleaned_files), "profiled_files": []}
    for path in cleaned_files:
        rows, sample_count = profile_csv(path)
        if not rows:
            continue
        table_id = f"table_data_profile_{safe_slug(path.stem)}"
        output = TABLES_DIR / f"{table_id}.csv"
        write_csv(output, rows)
        tables.append(
            {
                "table_id": table_id,
                "question_id": "ALL",
                "title": f"{path.stem} 数据字段画像表",
                "purpose": "说明清洗后数据字段、缺失情况和数值范围，供数据说明与建模输入选择使用。",
                "path": rel(output),
                "source": rel(path),
                "status": "generated_from_cleaned_data",
            }
        )
        summary["profiled_files"].append({"path": rel(path), "sample_rows": sample_count, "field_count": len(rows)})
    return tables, summary


def question_table_rows(question: dict[str, Any]) -> list[dict[str, Any]]:
    task_type = str(question.get("task_type") or "综合建模/统计分析")
    rows = []
    for title in suggested_table_titles(task_type):
        rows.append(
            {
                "table_title": title,
                "question_id": str(question.get("question_id") or question.get("id") or ""),
                "main_model": str(question.get("main_model") or question.get("baseline_model") or ""),
                "evidence_status": "needs_real_modeling",
                "note": "真实数值需由当前赛题专用建模代码补齐。",
            }
        )
    return rows


def write_modeling_code_readme(questions: list[dict[str, Any]], cleaned_files: list[Path]) -> None:
    MODELING_CODE_DIR.mkdir(parents=True, exist_ok=True)
    planned_files = []
    for index, question in enumerate(questions, start=1):
        qid = str(question.get("question_id") or question.get("id") or f"Q{index}").lower()
        planned_files.append(f"{qid}_model.py")

    lines = [
        "# Modeling Code Workspace",
        "",
        "This directory is for current-contest generated modeling code. Do not write generated contest code back into the skill package directory.",
        "",
        "## Planned Files",
        "",
        "```text",
        "paper_output/code/modeling/",
        "├── run_modeling.py          # optional unified entry for Q1/Q2/Q3 modeling scripts",
        "├── result_contract_io.py    # helper for writing results, metrics, conclusions and table_index contracts",
    ]
    for filename in planned_files:
        lines.append(f"├── {filename:<23} # current-contest modeling script")
    lines.extend(
        [
            "└── README.md",
            "```",
            "",
            "## Inputs",
            "",
            "- `paper_output/plan/model_route.json`",
            "- `paper_output/plan/data_plan.json`",
            "- `paper_output/plan/visualization_plan.json`",
            "- `paper_output/data_cleaned/`",
            "",
            "## Outputs To Write Back",
            "",
            "- `paper_output/results/model_results.json`",
            "- `paper_output/results/metrics.json`",
            "- `paper_output/results/conclusions.json`",
            "- `paper_output/tables/table_index.json`",
            "- `paper_output/tables/*.csv`",
            "",
            "## Cleaned Data Detected",
            "",
        ]
    )
    if cleaned_files:
        lines.extend(f"- `{rel(path)}`" for path in cleaned_files)
    else:
        lines.append("- No cleaned CSV files detected yet.")
    lines.extend(
        [
            "",
            "The generated result contracts may currently be draft skeletons. For a real contest, Agent should create or modify the planned scripts in this directory, run them, and then regenerate QA/tasks before final writing.",
            "",
        ]
    )
    (MODELING_CODE_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    MODELING_CODE_DIR.mkdir(parents=True, exist_ok=True)

    model_route = load_json(MODEL_ROUTE_FILE)
    data_plan = load_json(DATA_PLAN_FILE)
    visualization_plan = load_json(VISUALIZATION_PLAN_FILE)
    questions = load_questions(model_route)
    cleaned_files = find_cleaned_csv_files()

    table_entries, data_summary = build_data_profile_tables(cleaned_files)
    write_modeling_code_readme(questions, cleaned_files)
    result_items: list[dict[str, Any]] = []
    metric_items: list[dict[str, Any]] = []
    conclusion_items: list[dict[str, Any]] = []

    for index, question in enumerate(questions, start=1):
        qid = str(question.get("question_id") or question.get("id") or f"Q{index}")
        title = str(question.get("title") or f"问题{index}")
        task_type = str(question.get("task_type") or "综合建模/统计分析")
        main_model = str(question.get("main_model") or question.get("baseline_model") or "结合题目需求的主模型")
        result_summary = (
            f"{title} 已生成结果证据契约骨架。当前建议主模型为“{main_model}”，"
            "真实数值、参数和方案需结合当前赛题专用建模代码补齐。"
        )
        result_items.append(
            {
                "question_id": qid,
                "title": title,
                "task_type": task_type,
                "result_type": result_type(task_type),
                "main_model": main_model,
                "baseline_model": question.get("baseline_model", ""),
                "result_summary": result_summary,
                "outputs": [],
                "parameters": [],
                "evidence_status": "needs_real_modeling",
                "status": "draft_contract",
            }
        )
        for metric in metric_templates(task_type):
            metric_items.append({"question_id": qid, "status": "to_be_filled", **metric})

        q_table_id = f"table_{qid.lower()}_result_skeleton"
        q_table_path = TABLES_DIR / f"{q_table_id}.csv"
        write_csv(q_table_path, question_table_rows({"question_id": qid, **question}))
        table_entries.append(
            {
                "table_id": q_table_id,
                "question_id": qid,
                "title": f"{title} 结果证据表骨架",
                "purpose": "列出本问应进入论文的结果表、指标表或敏感性表，供 Agent 二次填充真实结果。",
                "path": rel(q_table_path),
                "source": "paper_output/plan/model_route.json",
                "status": "draft_contract",
            }
        )

        conclusion_items.append(
            {
                "question_id": qid,
                "conclusion_text": f"{title} 的最终结论需在真实建模结果补齐后回扣原问；当前已建立结果证据契约骨架。",
                "evidence_required": ["model_results.json", "metrics.json", "table_index.json"],
                "evidence_status": "needs_real_modeling",
            }
        )

    common = {
        "schema_version": "1.0",
        "generated_by": GENERATED_BY,
        "generated_at": now(),
    }
    model_results = {
        **common,
        "source": "paper_output/plan/model_route.json",
        "data_sources": [rel(path) for path in cleaned_files],
        "questions": result_items,
        "data_summary": data_summary,
    }
    metrics = {
        **common,
        "source": "paper_output/results/model_results.json",
        "items": metric_items,
    }
    conclusions = {
        **common,
        "source": "paper_output/results/model_results.json",
        "items": conclusion_items,
    }
    table_index = {
        **common,
        "source": "paper_output/results/model_results.json",
        "tables": table_entries,
        "notes": [
            "status=draft_contract 的表格是结果证据骨架，不应直接冒充最终比赛结果。",
            "真实赛题应由 Agent 根据当前建模代码补齐表格数值后再进入最终正文。",
        ],
    }

    (RESULTS_DIR / "model_results.json").write_text(json.dumps(model_results, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / "conclusions.json").write_text(json.dumps(conclusions, ensure_ascii=False, indent=2), encoding="utf-8")
    (TABLES_DIR / "table_index.json").write_text(json.dumps(table_index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 已生成模型结果契约：{RESULTS_DIR / 'model_results.json'}")
    print(f"✅ 已生成指标契约：{RESULTS_DIR / 'metrics.json'}")
    print(f"✅ 已生成结论契约：{RESULTS_DIR / 'conclusions.json'}")
    print(f"✅ 已生成表格索引：{TABLES_DIR / 'table_index.json'}")
    print(f"✅ 已准备建模代码工作区：{MODELING_CODE_DIR / 'README.md'}")
    print(f"   子问题数量：{len(result_items)}，表格数量：{len(table_entries)}")
    if data_plan is None:
        print("⚠️ 未检测到 data_plan.json，结果契约仅根据模型路线生成。")
    if visualization_plan is None:
        print("⚠️ 未检测到 visualization_plan.json，表格证据未连接图表计划。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

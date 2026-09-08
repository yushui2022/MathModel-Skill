import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
PLAN_DIR = OUTPUT_DIR / "plan"
PROBLEM_ANALYSIS_FILE = OUTPUT_DIR / "step1" / "problem_analysis.json"
MODEL_ROUTE_FILE = PLAN_DIR / "model_route.json"
DATA_PLAN_FILE = PLAN_DIR / "data_plan.json"
VISUALIZATION_PLAN_FILE = PLAN_DIR / "visualization_plan.json"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
SEARCH_DIRS = ("problem_files", "crawled_data")
DATA_EXTENSIONS = {".csv", ".xlsx", ".xls"}
GENERATED_BY = "data-cleaning-and-visualization/scripts/build_data_visualization_plan.py"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def relative_path(path: Path) -> str:
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


def import_pandas() -> Any | None:
    try:
        import pandas as pd  # type: ignore

        return pd
    except Exception:
        return None


def find_data_files() -> list[Path]:
    files: list[Path] = []
    for dirname in SEARCH_DIRS:
        root = BASE_DIR / dirname
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith("~"):
                continue
            if path.suffix.lower() in DATA_EXTENSIONS:
                files.append(path)
    return sorted(set(files), key=lambda item: str(item).lower())


def read_with_pandas(path: Path) -> tuple[Any | None, str]:
    pd = import_pandas()
    if pd is None:
        return None, "pandas is not available"

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
                try:
                    return pd.read_csv(path, nrows=500, encoding=encoding), ""
                except UnicodeDecodeError:
                    continue
            return pd.read_csv(path, nrows=500), ""
        if suffix == ".txt":
            try:
                return pd.read_csv(path, nrows=500, sep=None, engine="python"), ""
            except Exception:
                return pd.read_csv(path, nrows=500, sep="\t"), ""
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(path, nrows=500), ""
    except Exception as exc:
        return None, str(exc)
    return None, f"unsupported data extension: {suffix}"


def fallback_columns(path: Path) -> list[str]:
    if path.suffix.lower() not in {".csv", ".txt"}:
        return []
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with path.open("r", encoding=encoding, errors="ignore", newline="") as handle:
                sample = handle.read(4096)
                if not sample.strip():
                    return []
                dialect = csv.Sniffer().sniff(sample)
                handle.seek(0)
                reader = csv.reader(handle, dialect)
                return [str(col).strip() for col in next(reader, []) if str(col).strip()]
        except Exception:
            continue
    return []


def classify_columns(df: Any) -> tuple[list[str], list[str]]:
    pd = import_pandas()
    if pd is None:
        return [], []

    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    for column in df.columns:
        name = str(column)
        series = df[column]
        if pd.api.types.is_numeric_dtype(series):
            numeric_columns.append(name)
            continue
        non_null = int(series.notna().sum())
        if non_null:
            converted = pd.to_numeric(series, errors="coerce")
            ratio = float(converted.notna().sum()) / float(non_null)
            if ratio >= 0.8:
                numeric_columns.append(name)
                continue
        categorical_columns.append(name)
    return numeric_columns, categorical_columns


def profile_data_file(path: Path) -> dict[str, Any]:
    cleaned_output = f"paper_output/data_cleaned/{path.stem}_cleaned.csv"
    role = "主建模数据" if "problem_files" in path.parts else "补充数据"
    profile: dict[str, Any] = {
        "path": relative_path(path),
        "type": path.suffix.lower().lstrip("."),
        "readable": False,
        "columns": [],
        "numeric_columns": [],
        "categorical_columns": [],
        "role": role,
        "cleaned_output": cleaned_output,
        "cleaning_tasks": ["缺失值检查", "字段类型转换", "异常值检查", "重复记录检查"],
    }

    df, error = read_with_pandas(path)
    if df is not None:
        columns = [str(col) for col in df.columns]
        numeric_columns, categorical_columns = classify_columns(df)
        profile.update(
            {
                "readable": True,
                "rows_sampled": int(len(df)),
                "columns": columns,
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
            }
        )
        return profile

    columns = fallback_columns(path)
    if columns:
        profile.update({"readable": True, "columns": columns, "categorical_columns": columns})
    elif error:
        profile["error"] = error
    return profile


def profiles_from_problem_analysis(analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not analysis:
        return []
    data_files = analysis.get("data_files")
    if not isinstance(data_files, list):
        return []

    profiles: list[dict[str, Any]] = []
    for item in data_files:
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path") or "").strip()
        if not raw_path:
            continue
        columns = item.get("columns")
        if not isinstance(columns, list) and isinstance(item.get("sheets"), list) and item["sheets"]:
            first_sheet = item["sheets"][0]
            columns = first_sheet.get("columns") if isinstance(first_sheet, dict) else []
        clean_name = Path(raw_path).stem or "dataset"
        profiles.append(
            {
                "path": raw_path.replace("\\", "/"),
                "type": str(item.get("type") or Path(raw_path).suffix.lstrip(".") or "data"),
                "readable": bool(item.get("readable", False)),
                "columns": [str(col) for col in columns] if isinstance(columns, list) else [],
                "numeric_columns": [],
                "categorical_columns": [str(col) for col in columns] if isinstance(columns, list) else [],
                "role": "主建模数据",
                "cleaned_output": f"paper_output/data_cleaned/{clean_name}_cleaned.csv",
                "cleaning_tasks": ["缺失值检查", "字段类型转换", "异常值检查"],
            }
        )
    return profiles


def normalize_question_id(value: Any, index: int) -> str:
    text = str(value or "").strip().upper()
    match = re.search(r"Q(\d+)", text)
    if match:
        return f"Q{int(match.group(1))}"
    return f"Q{index}"


def questions_from_contracts(
    analysis: dict[str, Any] | None,
    model_route: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    route_questions = model_route.get("questions") if isinstance(model_route, dict) else None
    if isinstance(route_questions, list) and route_questions:
        result = []
        for index, question in enumerate(route_questions, start=1):
            if isinstance(question, dict):
                result.append(
                    {
                        **question,
                        "question_id": normalize_question_id(
                            question.get("question_id") or question.get("id"),
                            index,
                        ),
                    }
                )
        return result

    analysis_questions = analysis.get("questions") if isinstance(analysis, dict) else None
    if isinstance(analysis_questions, list) and analysis_questions:
        result = []
        for index, question in enumerate(analysis_questions, start=1):
            if not isinstance(question, dict):
                continue
            suggestions = question.get("figure_suggestions") if isinstance(question.get("figure_suggestions"), list) else []
            result.append(
                {
                    "question_id": normalize_question_id(question.get("id"), index),
                    "title": question.get("title") or f"问题{index}",
                    "task_type": question.get("task_type") or "综合建模/统计分析",
                    "figures": [
                        {
                            "figure_id": f"fig_q{index}_{fig_index}",
                            "title": str(title),
                            "purpose": f"支撑Q{index}的结果、验证或敏感性分析",
                            "expected_path": f"paper_output/figures/fig_q{index}_{fig_index}.png",
                        }
                        for fig_index, title in enumerate(suggestions or ["数据概览图", "结果对比图"], start=1)
                    ],
                    "paper_sections": [f"问题{index}结果分析"],
                }
            )
        return result

    return [
        {
            "question_id": "Q1",
            "title": "问题一",
            "task_type": "综合建模/统计分析",
            "figures": [
                {
                    "figure_id": "fig_q1_1",
                    "title": "数据概览图",
                    "purpose": "支撑问题一的数据理解与结果展示",
                    "expected_path": "paper_output/figures/fig_q1_1.png",
                }
            ],
            "paper_sections": ["问题一结果分析"],
        }
    ]


def choose_dataset(data_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in data_files:
        if item.get("readable") and item.get("columns"):
            return item
    return data_files[0] if data_files else None


def choose_x_column(dataset: dict[str, Any] | None) -> str:
    if not dataset:
        return ""
    columns = [str(col) for col in dataset.get("columns", [])]
    categorical = [str(col) for col in dataset.get("categorical_columns", [])]
    patterns = ("year", "date", "time", "month", "day", "年份", "年度", "日期", "时间", "月份")
    for column in columns:
        lower = column.lower()
        if any(pattern in lower or pattern in column for pattern in patterns):
            return column
    if categorical:
        return categorical[0]
    return columns[0] if columns else ""


def choose_y_columns(dataset: dict[str, Any] | None, x_column: str) -> list[str]:
    if not dataset:
        return []
    numeric = [str(col) for col in dataset.get("numeric_columns", []) if str(col) != x_column]
    if numeric:
        return numeric[:3]
    columns = [str(col) for col in dataset.get("columns", []) if str(col) != x_column]
    return columns[:2]


def chart_type(task_type: str, title: str, x_column: str, y_columns: list[str]) -> str:
    title_text = str(title)
    text = f"{task_type} {title}"
    if "残差" in title_text or "误差分布" in title_text:
        return "residual_distribution"
    if "敏感性" in title_text or "灵敏度" in title_text or "扰动" in title_text:
        return "sensitivity_curve"
    if "模型对比" in title_text or "方案对比" in title_text or "对照" in title_text:
        return "model_comparison"
    if "权重" in title_text:
        return "weight_bar"
    if "得分" in title_text or "排序" in title_text or "排名" in title_text:
        return "score_ranking"
    if "热力" in title_text or "矩阵" in title_text:
        return "heatmap"
    if "真实值" in title_text or "预测值" in title_text or "预测" in title_text or "预报" in title_text:
        return "prediction_comparison"
    if "分类" in text or "识别" in text:
        return "bar"
    if "聚类" in text or "分群" in text:
        return "scatter"
    if "评价" in text or "排序" in text or "优化" in text or "规划" in text:
        return "bar"
    if "预测" in text or "回归" in text or "趋势" in text:
        return "line" if x_column else "scatter"
    if len(y_columns) >= 2:
        return "line"
    return "bar"


def template_hint(chart_type_value: str) -> str:
    hints = {
        "prediction_comparison": "plot_prediction_comparison",
        "residual_distribution": "plot_residual_distribution",
        "sensitivity_curve": "plot_sensitivity_curve",
        "model_comparison": "plot_model_comparison",
        "weight_bar": "plot_weight_bar",
        "score_ranking": "plot_score_ranking",
        "heatmap": "plot_heatmap",
        "scatter": "plot_scatter",
        "bar": "plot_model_comparison",
        "line": "plot_generic_line",
    }
    return hints.get(chart_type_value, "plot_generic_line")


def first_paper_usage(question: dict[str, Any]) -> str:
    sections = question.get("paper_sections")
    if isinstance(sections, list):
        for section in sections:
            text = str(section)
            if "结果" in text or "检验" in text:
                return text
        if sections:
            return str(sections[0])
    return str(question.get("title") or "结果分析")


def build_data_plan(
    data_files: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset = choose_dataset(data_files)
    x_column = choose_x_column(dataset)
    y_columns = choose_y_columns(dataset, x_column)
    required_fields = [field for field in [x_column, *y_columns] if field]

    question_links = []
    for question in questions:
        qid = str(question.get("question_id") or "")
        task_type = str(question.get("task_type") or "综合建模/统计分析")
        outputs = ["结果表", "误差指标表"]
        if "优化" in task_type or "规划" in task_type:
            outputs = ["方案对比表", "约束满足表"]
        elif "评价" in task_type or "排序" in task_type:
            outputs = ["指标权重表", "综合得分表"]
        question_links.append(
            {
                "question_id": qid,
                "required_fields": required_fields,
                "expected_outputs": outputs,
            }
        )

    return {
        "schema_version": "1.0",
        "generated_by": GENERATED_BY,
        "generated_at": now(),
        "source_contracts": [
            "paper_output/step1/problem_analysis.json",
            "paper_output/plan/model_route.json",
        ],
        "data_files": data_files,
        "question_links": question_links,
        "note": "本文件是数据处理交接单，用于指导 Agent 按当前赛题二次生成或修改清洗与建模代码。",
    }


def build_visualization_plan(
    data_files: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset = choose_dataset(data_files)
    data_source = str(dataset.get("cleaned_output") or "") if dataset else ""
    x_column = choose_x_column(dataset)
    y_columns = choose_y_columns(dataset, x_column)

    figures: list[dict[str, Any]] = []
    for question in questions:
        qid = str(question.get("question_id") or "Q1")
        task_type = str(question.get("task_type") or "综合建模/统计分析")
        raw_figures = question.get("figures")
        if not isinstance(raw_figures, list) or not raw_figures:
            raw_figures = [
                {
                    "figure_id": f"fig_{qid.lower()}_1",
                    "title": f"{qid}结果对比图",
                    "purpose": f"支撑{qid}的模型结果、验证或敏感性分析",
                    "expected_path": f"paper_output/figures/fig_{qid.lower()}_1.png",
                }
            ]
        for index, raw_figure in enumerate(raw_figures, start=1):
            if isinstance(raw_figure, dict):
                figure_id = str(raw_figure.get("figure_id") or f"fig_{qid.lower()}_{index}")
                title = str(raw_figure.get("title") or f"{qid}图表{index}")
                purpose = str(raw_figure.get("purpose") or f"支撑{qid}的模型结果、验证或敏感性分析")
                output_path = str(raw_figure.get("expected_path") or f"paper_output/figures/{figure_id}.png")
            else:
                figure_id = f"fig_{qid.lower()}_{index}"
                title = str(raw_figure)
                purpose = f"支撑{qid}的模型结果、验证或敏感性分析"
                output_path = f"paper_output/figures/{figure_id}.png"
            chart_type_value = chart_type(task_type, title, x_column, y_columns)
            figures.append(
                {
                    "figure_id": figure_id,
                    "question_id": qid,
                    "title": title,
                    "chart_type": chart_type_value,
                    "template_hint": template_hint(chart_type_value),
                    "data_source": data_source,
                    "candidate_x": x_column,
                    "candidate_y": y_columns,
                    "purpose": purpose,
                    "output_path": output_path.replace("\\", "/"),
                    "paper_usage": first_paper_usage(question),
                }
            )

    return {
        "schema_version": "1.0",
        "generated_by": GENERATED_BY,
        "generated_at": now(),
        "source_contracts": [
            "paper_output/plan/model_route.json",
            "paper_output/plan/data_plan.json",
        ],
        "figures": figures,
        "note": "本文件只规划图表证据，不承诺固定代码可直接适配所有赛题。",
    }


def build_figure_index(visualization_plan: dict[str, Any]) -> dict[str, Any]:
    figures = []
    for item in visualization_plan.get("figures", []):
        if not isinstance(item, dict):
            continue
        path = str(item.get("output_path") or "").replace("\\", "/")
        figures.append(
            {
                "figure_id": item.get("figure_id"),
                "path": path,
                "title": item.get("title"),
                "question_id": item.get("question_id"),
                "planned": True,
                "exists": bool(path and (BASE_DIR / path).exists()),
                "used_in": item.get("paper_usage"),
            }
        )
    return {
        "schema_version": "1.0",
        "generated_by": GENERATED_BY,
        "generated_at": now(),
        "figures": figures,
    }


def main() -> int:
    analysis = load_json(PROBLEM_ANALYSIS_FILE)
    model_route = load_json(MODEL_ROUTE_FILE)
    files = find_data_files()
    data_files = [profile_data_file(path) for path in files]
    if not data_files:
        data_files = profiles_from_problem_analysis(analysis)

    questions = questions_from_contracts(analysis, model_route)
    data_plan = build_data_plan(data_files, questions)
    visualization_plan = build_visualization_plan(data_files, questions)
    figure_index = build_figure_index(visualization_plan)

    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PLAN_FILE.write_text(json.dumps(data_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    VISUALIZATION_PLAN_FILE.write_text(json.dumps(visualization_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    FIGURE_INDEX_FILE.write_text(json.dumps(figure_index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 已生成数据处理计划：{DATA_PLAN_FILE}")
    print(f"✅ 已生成图表规划：{VISUALIZATION_PLAN_FILE}")
    print(f"✅ 已生成图表索引：{FIGURE_INDEX_FILE}")
    print(f"   数据文件数量：{len(data_files)}，计划图表数量：{len(figure_index.get('figures', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

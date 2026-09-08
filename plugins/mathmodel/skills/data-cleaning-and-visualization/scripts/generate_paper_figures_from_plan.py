import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from paper_figure_templates import plot_figure_spec


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
PLAN_DIR = OUTPUT_DIR / "plan"
VISUALIZATION_PLAN_FILE = PLAN_DIR / "visualization_plan.json"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
GENERATED_BY = "data-cleaning-and-visualization/scripts/generate_paper_figures_from_plan.py"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def read_table(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        if path.suffix.lower() == ".csv":
            for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
                try:
                    return pd.read_csv(path, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            return pd.read_csv(path)
        if path.suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(path)
    except Exception:
        return None
    return None


def resolve_path(value: Any) -> Path | None:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return None
    path = Path(text)
    return path if path.is_absolute() else BASE_DIR / path


def index_item(
    spec: dict[str, Any],
    exists: bool,
    message: str = "",
    template: str = "",
    *,
    ok: bool = False,
    placeholder: bool = False,
) -> dict[str, Any]:
    output_path = str(spec.get("output_path") or "").replace("\\", "/")
    return {
        "figure_id": spec.get("figure_id"),
        "path": output_path,
        "title": spec.get("title"),
        "question_id": spec.get("question_id"),
        "planned": True,
        "exists": exists,
        "ok": ok,
        "placeholder": placeholder,
        "status": "computed" if ok and exists and not placeholder else "placeholder",
        "used_in": spec.get("paper_usage"),
        "chart_type": spec.get("chart_type"),
        "template": template,
        "source": spec.get("data_source"),
        "message": message,
    }


def generate_one(spec: dict[str, Any]) -> dict[str, Any]:
    output_path = resolve_path(spec.get("output_path"))
    if output_path is None:
        return index_item(spec, False, "missing output_path")

    data_path = resolve_path(spec.get("data_source"))
    if data_path is None:
        return index_item(spec, False, "missing data_source")

    df = read_table(data_path)
    if df is None or df.empty:
        return index_item(spec, False, f"data source is not readable: {spec.get('data_source')}")

    result = plot_figure_spec(df, spec, output_path)
    return index_item(
        spec,
        bool(Path(result.get("path", "")).exists()),
        str(result.get("message") or ""),
        str(result.get("template") or ""),
        ok=bool(result.get("ok")),
        placeholder=bool(result.get("placeholder")),
    )


def main() -> int:
    plan = load_json(VISUALIZATION_PLAN_FILE)
    if plan is None:
        print(f"⚠️ 未找到图表规划：{VISUALIZATION_PLAN_FILE}")
        return 0

    figures = plan.get("figures")
    if not isinstance(figures, list) or not figures:
        print("⚠️ visualization_plan.json 中没有 figures[]，跳过论文级图表模板。")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    indexed = []
    generated = 0
    for spec in figures:
        if not isinstance(spec, dict):
            continue
        item = generate_one(spec)
        indexed.append(item)
        if item.get("exists"):
            generated += 1

    figure_index = {
        "schema_version": "1.0",
        "generated_by": GENERATED_BY,
        "generated_at": now(),
        "source": "paper_output/plan/visualization_plan.json",
        "figures": indexed,
        "note": "这些图是论文级图表样板。真实赛题应结合模型输出和字段含义二次修改，不应把模板图直接当作最终计算结论。",
    }
    FIGURE_INDEX_FILE.write_text(json.dumps(figure_index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 论文级图表模板已生成：{generated}/{len(indexed)}")
    print(f"✅ 图表索引已更新：{FIGURE_INDEX_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

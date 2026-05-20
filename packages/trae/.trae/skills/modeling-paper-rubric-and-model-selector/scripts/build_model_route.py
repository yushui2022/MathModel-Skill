import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "paper_output"
STEP1_DIR = OUTPUT_DIR / "step1"
PLAN_DIR = OUTPUT_DIR / "plan"
PROBLEM_ANALYSIS_FILE = STEP1_DIR / "problem_analysis.json"
MODEL_ROUTE_FILE = PLAN_DIR / "model_route.json"
RUBRIC_ALIGNMENT_FILE = PLAN_DIR / "rubric_alignment.json"
SCORING_STRATEGY_FILE = PLAN_DIR / "scoring_strategy.md"
SKILL_DIR = Path(__file__).resolve().parents[1]
PAPER_PROMPT_FILE = SKILL_DIR / "references" / "paper_prompt_default.md"


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


BACKUP_MODELS = {
    "预测": ["ARIMA", "XGBoost 回归", "随机森林回归"],
    "回归": ["岭回归", "随机森林回归", "XGBoost 回归"],
    "优化": ["整数规划", "遗传算法", "模拟退火"],
    "规划": ["线性规划", "多目标规划", "遗传算法"],
    "评价": ["熵权法", "TOPSIS", "CRITIC"],
    "排序": ["TOPSIS", "VIKOR", "AHP"],
    "分类": ["逻辑回归", "随机森林", "梯度提升树"],
    "识别": ["逻辑回归", "随机森林", "代价敏感学习"],
    "聚类": ["K-means", "DBSCAN", "GMM"],
    "仿真": ["差分方程", "参数校准仿真", "情景模拟"],
    "机理": ["微分方程", "参数反演", "不确定性分析"],
}


FORMULA_REQUIREMENTS = {
    "预测": ["定义输入特征矩阵 X", "定义预测目标 y", "说明损失函数与误差指标"],
    "回归": ["定义解释变量与响应变量", "给出回归函数或损失函数", "说明参数估计与误差指标"],
    "优化": ["定义决策变量", "写清目标函数", "列出约束条件与可行域"],
    "规划": ["定义决策变量", "写清目标函数", "列出约束条件与可行域"],
    "评价": ["构建指标矩阵", "说明标准化与权重计算", "给出综合得分或排序规则"],
    "排序": ["构建指标矩阵", "说明权重来源", "给出排序或择优规则"],
    "分类": ["定义特征与类别标签", "说明分类函数或判别规则", "给出 Precision/Recall/F1 等指标"],
    "识别": ["定义特征与识别目标", "说明判别阈值或概率输出", "给出混淆矩阵和误差指标"],
    "聚类": ["定义样本特征矩阵", "说明距离度量或相似性", "给出聚类数与稳定性指标"],
    "仿真": ["定义状态变量与参数", "写出状态转移或动力学方程", "说明参数校准与情景设定"],
    "机理": ["定义状态变量与关键参数", "写出机理方程", "说明参数反演、边界条件与检验方式"],
}


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def normalize_qid(value: Any, index: int) -> str:
    text = str(value or "").strip().upper()
    match = re.search(r"Q(\d+)", text)
    if match:
        return f"Q{int(match.group(1))}"
    return f"Q{index}"


def match_rule(task_type: str, rules: dict[str, list[str]]) -> list[str]:
    for key, values in rules.items():
        if key in task_type:
            return values
    return []


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def model_reason(task_type: str, main_model: str, question: dict[str, Any]) -> str:
    constraints = as_list(question.get("constraints"))
    summary = str(question.get("summary") or "").strip()
    if constraints:
        return f"该问属于“{task_type}”任务，{main_model} 能在保留可解释性的同时承接题目约束：{constraints[0]}。"
    if summary:
        return f"该问属于“{task_type}”任务，{main_model} 能围绕“{summary}”形成模型、结果和验证闭环。"
    return f"该问属于“{task_type}”任务，{main_model} 能同时支撑建模、求解、结果解释和后续检验。"


def figure_id(question_id: str, index: int) -> str:
    return f"fig_{question_id.lower()}_{index}"


def build_figures(question_id: str, suggestions: list[str]) -> list[dict[str, str]]:
    if not suggestions:
        suggestions = ["结果对比图", "敏感性分析图"]
    figures = []
    for index, title in enumerate(suggestions, start=1):
        fid = figure_id(question_id, index)
        figures.append(
            {
                "figure_id": fid,
                "title": title,
                "purpose": f"支撑{question_id}的模型结果、验证或敏感性分析",
                "expected_path": f"paper_output/figures/{fid}.png",
            }
        )
    return figures


def build_model_route(analysis: dict[str, Any]) -> dict[str, Any]:
    questions = analysis.get("questions")
    if not isinstance(questions, list) or not questions:
        questions = []

    route_questions: list[dict[str, Any]] = []
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        qid = normalize_qid(question.get("id"), index)
        task_type = str(question.get("task_type") or "综合建模/统计分析").strip()
        models = question.get("recommended_models") if isinstance(question.get("recommended_models"), dict) else {}
        baseline_model = str(models.get("baseline") or "可解释基线模型").strip()
        main_model = str(models.get("improved") or baseline_model or "结合题目需求的主模型").strip()
        backup_models = [m for m in match_rule(task_type, BACKUP_MODELS) if m not in {baseline_model, main_model}]
        if not backup_models:
            backup_models = ["可解释统计模型", "稳健性对照模型"]
        formula_requirements = match_rule(task_type, FORMULA_REQUIREMENTS) or [
            "定义输入变量与输出目标",
            "说明核心模型函数或目标函数",
            "给出评价指标与检验方式",
        ]
        validation = as_list(question.get("validation_plan")) or ["结果复核", "敏感性分析"]
        figure_suggestions = as_list(question.get("figure_suggestions"))

        route_questions.append(
            {
                "question_id": qid,
                "title": str(question.get("title") or f"问题{index}"),
                "task_type": task_type,
                "core_goal": str(question.get("summary") or "将原题要求转化为可计算、可验证的建模任务。"),
                "baseline_model": baseline_model,
                "main_model": main_model,
                "backup_models": backup_models[:3],
                "model_reason": model_reason(task_type, main_model, question),
                "formula_requirements": formula_requirements,
                "validation": validation,
                "figures": build_figures(qid, figure_suggestions),
                "paper_sections": [
                    f"{question.get('title') or f'问题{index}'}模型建立",
                    f"{question.get('title') or f'问题{index}'}结果分析",
                    f"{question.get('title') or f'问题{index}'}模型检验",
                ],
            }
        )

    return {
        "schema_version": "1.0",
        "generated_by": "modeling-paper-rubric-and-model-selector/scripts/build_model_route.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "paper_output/step1/problem_analysis.json",
        "paper_prompt_reference": "references/paper_prompt_default.md",
        "paper_prompt_chars": len(safe_read_text(PAPER_PROMPT_FILE)),
        "questions": route_questions,
    }


def build_rubric_alignment(model_route: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for question in model_route.get("questions", []):
        qid = question.get("question_id")
        sections = question.get("paper_sections", [])
        figures = question.get("figures", [])
        figure_titles = [fig.get("title", "") for fig in figures if isinstance(fig, dict)]
        items.extend(
            [
                {
                    "rubric_point": "题意覆盖",
                    "question_id": qid,
                    "evidence_required": ["可计算目标", "输入输出定义", "对应原问的结论"],
                    "paper_location": sections,
                    "qa_rule": "正文必须明确本问要解决什么，并在结论中回扣原题。",
                },
                {
                    "rubric_point": "模型合理性",
                    "question_id": qid,
                    "evidence_required": ["模型选择理由", "模型公式", "评价指标"],
                    "paper_location": sections,
                    "qa_rule": "正文必须同时出现模型理由、核心变量和验证指标。",
                },
                {
                    "rubric_point": "结果可信",
                    "question_id": qid,
                    "evidence_required": ["基线对照", "检验指标", "误差或敏感性分析"],
                    "paper_location": sections,
                    "qa_rule": "正文必须说明结果如何被验证，而不是只给出结论。",
                },
                {
                    "rubric_point": "图表证据",
                    "question_id": qid,
                    "evidence_required": figure_titles or ["结果图表"],
                    "paper_location": sections,
                    "qa_rule": "正文引用的图表应能在 paper_output/figures/ 下找到对应文件。",
                },
            ]
        )
    return {
        "schema_version": "1.0",
        "generated_by": "modeling-paper-rubric-and-model-selector/scripts/build_model_route.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "paper_output/plan/model_route.json",
        "items": items,
    }


def write_scoring_strategy(model_route: dict[str, Any], rubric_alignment: dict[str, Any]) -> None:
    lines = [
        "# 评分闭环与模型路线策略\n\n",
        "本文件由 `modeling-paper-rubric-and-model-selector` 根据结构化题意分析生成，用于指导后续 QA 与微单元写作。\n\n",
        "## 全局原则\n\n",
        "- 每一问必须形成“任务定义 -> 模型建立 -> 求解结果 -> 验证检验 -> 回答原问”的闭环。\n",
        "- `model_route.json` 是后续写作的模型路线交接单，不能在正文生成时随意偷换主模型。\n",
        "- `rubric_alignment.json` 是评分点与证据形式的映射，QA 应逐条检查是否落实。\n\n",
    ]
    rubric_items = rubric_alignment.get("items", [])
    for question in model_route.get("questions", []):
        qid = question.get("question_id")
        lines.append(f"## {question.get('title', qid)}\n\n")
        lines.append(f"- 任务类型：{question.get('task_type')}\n")
        lines.append(f"- 核心目标：{question.get('core_goal')}\n")
        lines.append(f"- 基线模型：{question.get('baseline_model')}\n")
        lines.append(f"- 主模型：{question.get('main_model')}\n")
        lines.append(f"- 模型理由：{question.get('model_reason')}\n")
        lines.append(f"- 公式要求：{'；'.join(question.get('formula_requirements', []))}\n")
        lines.append(f"- 验证计划：{'；'.join(question.get('validation', []))}\n")
        fig_titles = [fig.get("title", "") for fig in question.get("figures", []) if isinstance(fig, dict)]
        lines.append(f"- 图表证据：{'；'.join(fig_titles)}\n")
        matched = [item for item in rubric_items if item.get("question_id") == qid]
        if matched:
            lines.append("- 评分点落位：")
            lines.append("；".join(f"{item.get('rubric_point')} -> {'/'.join(item.get('paper_location', []))}" for item in matched))
            lines.append("\n")
        lines.append("\n")
    SCORING_STRATEGY_FILE.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    analysis = load_json(PROBLEM_ANALYSIS_FILE)
    if analysis is None:
        print(f"❌ 未找到结构化题意分析：{PROBLEM_ANALYSIS_FILE}")
        print("请先运行 problem-doc-model-selector/scripts/analyze_problem.py")
        return 1

    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    model_route = build_model_route(analysis)
    rubric_alignment = build_rubric_alignment(model_route)

    MODEL_ROUTE_FILE.write_text(json.dumps(model_route, ensure_ascii=False, indent=2), encoding="utf-8")
    RUBRIC_ALIGNMENT_FILE.write_text(json.dumps(rubric_alignment, ensure_ascii=False, indent=2), encoding="utf-8")
    write_scoring_strategy(model_route, rubric_alignment)

    print(f"✅ 已生成模型路线：{MODEL_ROUTE_FILE}")
    print(f"✅ 已生成评分点映射：{RUBRIC_ALIGNMENT_FILE}")
    print(f"✅ 已生成评分策略说明：{SCORING_STRATEGY_FILE}")
    print(f"   子问题数量：{len(model_route.get('questions', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

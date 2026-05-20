import json
from pathlib import Path


BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "paper_output"
TASKS_FILE = OUTPUT_DIR / "tasks.json"
UNITS_DIR = OUTPUT_DIR / "micro_units"


def load_results() -> dict:
    p = OUTPUT_DIR / "step2_calc_results.json"
    if not p.exists():
        return {}
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def load_placeholders() -> dict:
    p = BASE_DIR / "step3_filled_placeholder.py"
    if not p.exists():
        return {}
    ns: dict = {}
    exec(p.read_text(encoding="utf-8"), ns)
    v = ns.get("PLACEHOLDER")
    return v if isinstance(v, dict) else {}


def text_value(mapping: dict, keys: list[str], default: str) -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                return "\n".join(f"- {item}" for item in cleaned)
        text = str(value).strip()
        if text:
            return text
    return default


def result_value(results: dict, keys: list[str], default: str) -> str:
    return text_value(results, keys, default)


def unit_number(unit_id: str) -> int:
    try:
        return int(str(unit_id).split("-")[-1])
    except Exception:
        return 1


def entry_command() -> str:
    return "python skills/paper-workflow-orchestrator/scripts/run_all.py"


def render_abstract(unit_id: str, ph: dict) -> str:
    title = text_value(ph, ["论文题目", "题目"], "当前数学建模赛题")
    keywords = text_value(ph, ["关键词"], "数学建模；模型构建；数据分析；可视化；稳健性检验")
    templates = {
        "ABS-1": text_value(
            ph,
            ["摘要第一段"],
            f"本文围绕“{title}”展开研究，将题目要求拆解为可计算、可验证的建模任务，并建立从数据处理到结果分析的完整求解流程。",
        ),
        "ABS-2": text_value(
            ph,
            ["摘要第二段"],
            "针对问题一，本文先进行题意解析与变量梳理，构建可解释的基线模型，并给出相应的求解步骤与评价指标。",
        ),
        "ABS-3": text_value(
            ph,
            ["摘要第三段"],
            "针对问题二，本文在基线模型基础上结合数据特征进行改进，通过对比实验、误差分析或约束检验说明模型的有效性。",
        ),
        "ABS-4": text_value(
            ph,
            ["摘要第四段"],
            "针对问题三，本文进一步开展综合分析、敏感性检验与推广讨论，使结论能够对应题目要求并具备可复现性。",
        ),
    }
    return templates.get(unit_id, f"关键词：{keywords}")


def render_intro(unit_id: str, ph: dict) -> str:
    templates = {
        "INTRO-1": text_value(
            ph,
            ["问题重述第一段", "题目背景"],
            "题目背景需要先从现实场景、研究对象和决策需求展开，说明该问题为什么具有建模价值，并明确论文将解决的核心矛盾。",
        ),
        "INTRO-2": text_value(
            ph,
            ["问题重述第二段", "子问题概述"],
            "根据题面要求，可将任务拆解为若干子问题：先明确输入数据与输出指标，再分别建立模型、设计算法并验证结果。",
        ),
        "INTRO-3": text_value(
            ph,
            ["问题重述第三段", "论文任务定义"],
            "因此，本文的工作重点是把原始题目转化为标准化的数学问题，形成数据预处理、模型建立、求解验证和结论解释的闭环。",
        ),
    }
    return templates.get(unit_id, templates["INTRO-3"])


def render_assumption(unit_id: str, ph: dict) -> str:
    assumptions = text_value(
        ph,
        ["模型假设", "假设列表"],
        "- 假设题目所给数据来源可靠，主要误差来自测量、缺失和口径差异。\n"
        "- 假设研究时段内外部环境相对稳定，模型参数在分析区间内具有可解释性。\n"
        "- 假设缺失值、异常值和重复记录经过统一规则处理后不会改变主要结论。",
    )
    if unit_id == "ASSUMP-1":
        return assumptions
    return text_value(
        ph,
        ["假设合理性"],
        "上述假设的作用是降低问题复杂度，并保证模型能够在有限数据条件下稳定求解。后续将通过敏感性分析和误差检验评估假设对结果的影响。",
    )


def render_symbols(ph: dict) -> str:
    custom = text_value(ph, ["符号说明", "符号表"], "")
    if custom:
        return custom
    return (
        "| 符号 | 含义 | 单位/说明 |\n"
        "|---|---|---|\n"
        "| $x_i$ | 第 $i$ 个样本或决策对象 | 由题目数据定义 |\n"
        "| $y_i$ | 模型输出或评价结果 | 由题目目标定义 |\n"
        "| $w_j$ | 第 $j$ 个指标权重 | 无量纲 |\n"
        "| $f(\\cdot)$ | 建模函数或预测函数 | 由所选模型确定 |\n"
        "| $E$ | 误差、损失或评价指标 | 按问题口径定义 |\n"
    )


def render_data(unit_id: str, ph: dict, results: dict) -> str:
    n = unit_number(unit_id)
    if n == 1:
        return text_value(
            ph,
            ["数据来源说明"],
            "数据预处理首先确认附件、外部数据和题目指标的来源，记录字段含义、单位口径、时间范围和样本粒度，避免后续建模时出现口径混用。",
        )
    if n == 2:
        return text_value(
            ph,
            ["数据清洗说明"],
            "清洗阶段重点处理缺失值、异常值、重复记录和类型转换；所有规则应写入论文的数据说明部分，并将清洗后的文件统一保存到 `paper_output/data_cleaned/`。",
        )
    if n == 3:
        return text_value(
            ph,
            ["可视化说明"],
            "可视化阶段应根据当前赛题重新选择图表类型。`scripts/` 中的绘图代码主要提供尺寸、配色、标注、保存路径和论文引用格式的样板。",
        )
    summary = result_value(results, ["data_summary", "数据摘要"], "清洗和可视化结果需要结合当前赛题的数据字段进一步补充。")
    return f"数据质量概况：{summary} 后续建模应优先使用清洗后的结构化数据，并在图表标题中明确变量、单位和样本范围。"


def problem_name(section: str) -> str:
    return {"问题一": "问题一", "问题二": "问题二", "问题三": "问题三"}.get(section, section)


def list_text(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, dict):
            text = str(
                item.get("title")
                or item.get("table_id")
                or item.get("rubric_point")
                or item.get("figure_id")
                or item.get("metric_name")
                or item.get("conclusion_text")
                or ""
            ).strip()
        else:
            text = str(item).strip()
        if text:
            result.append(text)
    return result


def metric_text(metrics: object) -> str:
    if not isinstance(metrics, list):
        return ""
    parts = []
    for item in metrics:
        if not isinstance(item, dict):
            continue
        name = str(item.get("metric_name") or "").strip()
        role = str(item.get("metric_role") or "").strip()
        value = item.get("value")
        unit = str(item.get("unit") or "").strip()
        status = str(item.get("status") or "").strip()
        if value is None or value == "":
            value_text = "待真实建模补齐" if status else "待补齐"
        else:
            value_text = f"{value}{unit}"
        label = name or role
        if label:
            suffix = f"（{role}）" if role and role != label else ""
            parts.append(f"{label}{suffix}: {value_text}")
    return "；".join(parts)


def table_text(tables: object) -> str:
    if not isinstance(tables, list):
        return ""
    parts = []
    for item in tables:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("table_id") or "").strip()
        path = str(item.get("path") or "").strip()
        if title and path:
            parts.append(f"{title}（{path}）")
        elif title:
            parts.append(title)
    return "；".join(parts)


def conclusion_text(conclusions: object) -> str:
    if not isinstance(conclusions, list):
        return ""
    parts = []
    for item in conclusions:
        if isinstance(item, dict):
            text = str(item.get("conclusion_text") or "").strip()
        else:
            text = str(item).strip()
        if text:
            parts.append(text)
    return "；".join(parts)


def evidence_note(task: dict) -> str:
    status = str(task.get("evidence_status") or "").strip()
    if status == "needs_real_modeling":
        return "当前结果证据仍是契约骨架，正式提交前必须用当前赛题专用建模代码补齐真实数值。"
    if status == "missing":
        return "当前缺少结果证据契约，正文应标记真实建模结果待补。"
    return ""


def render_model(section: str, unit_id: str, ph: dict, results: dict, task: dict) -> str:
    p = problem_name(section)
    n = unit_number(unit_id)
    question_id = str(task.get("question_id") or p)
    baseline_default = str(task.get("baseline_model") or "与题目任务匹配的基线模型")
    main_default = str(task.get("main_model") or task.get("improved_model") or baseline_default or "结合题目需求的主模型")
    backup_models = list_text(task.get("backup_models"))
    model_reason = str(task.get("model_reason") or "该模型与题目目标、数据结构和评分点要求保持一致。")
    formula_requirements = list_text(task.get("formula_requirements"))
    task_type = str(task.get("task_type") or "综合建模/统计分析")
    validation_plan = task.get("validation_plan") if isinstance(task.get("validation_plan"), list) else []
    figure_suggestions = list_text(task.get("figure_suggestions")) or list_text(task.get("figures"))
    rubric_points = list_text(task.get("rubric_points"))
    task_result_summary = str(task.get("result_summary") or "").strip()
    task_metrics = metric_text(task.get("key_metrics"))
    task_tables = table_text(task.get("tables"))
    task_conclusions = conclusion_text(task.get("conclusions"))
    task_evidence_note = evidence_note(task)
    model = text_value(ph, [f"{p}模型", f"{p}方法", "核心模型"], main_default)
    algo = text_value(ph, [f"{p}算法", f"{p}求解方法", "核心算法"], main_default)
    result = task_result_summary or result_value(results, [f"{p}结果", f"{p}_result", "核心结果"], "核心数值结果需由当前赛题计算脚本生成")
    metric = text_value(
        ph,
        [f"{p}评价指标", "评价指标"],
        task_metrics or "；".join(str(item) for item in validation_plan) or "误差、得分、约束满足率或稳定性指标",
    )
    if n == 1:
        return f"{p}（{question_id}）首先需要明确输入、输出和评价口径。根据模型路线契约，本问属于“{task_type}”任务，本文选择“{model}”作为主模型。"
    if n == 2:
        return f"模型建立时必须解释“{model}”的贴题性：{model_reason} 同时需要写清{('、'.join(formula_requirements) if formula_requirements else '变量定义、目标函数和评价指标')}。"
    if n == 3:
        return f"求解过程围绕“{algo}”展开，需要给出算法步骤、关键参数和复杂度说明，保证读者能够根据论文和附录代码复现结果。"
    if n == 4:
        backup_text = "、".join(backup_models) if backup_models else "备选模型"
        return f"为了避免模型只停留在形式推导，本文应以“{baseline_default}”作为基线方案，并可用{backup_text}进行对照，比较不同方法的效果。"
    if n == 5:
        figure_text = "、".join(str(item) for item in figure_suggestions) or "表格、图形或关键数值"
        table_sentence = f" 可引用的表格证据包括：{task_tables}。" if task_tables else ""
        note_sentence = f" {task_evidence_note}" if task_evidence_note else ""
        return f"结果展示部分应围绕题目原问展开，优先给出{figure_text}。当前结果摘要为：{result}。{table_sentence}{note_sentence}"
    if n == 6:
        note_sentence = f" {task_evidence_note}" if task_evidence_note else ""
        return f"模型检验阶段使用“{metric}”评价结果可靠性，并结合残差、敏感性或约束检查说明模型是否稳定。{note_sentence}"
    if n == 7:
        rubric_text = "、".join(rubric_points) if rubric_points else "题意覆盖、模型合理性、结果可信和图表证据"
        return f"敏感性分析和结果解释应对齐评分点：{rubric_text}，并说明结论在合理扰动范围内是否保持一致。"
    conclusion = task_conclusions or f"{p}（{question_id}）必须形成“任务定义 → 模型建立 → 算法求解 → 结果验证 → 回答原问”的闭环。"
    note_sentence = f" {task_evidence_note}" if task_evidence_note else ""
    return f"综上，{conclusion}{note_sentence}"


def render_analysis(unit_id: str, ph: dict, results: dict) -> str:
    n = unit_number(unit_id)
    if n == 1:
        return text_value(ph, ["结果总述"], "结果分析应先用一段话回答各子问题的核心结论，再说明这些结论对应哪些图表和数值证据。")
    if n == 2:
        return "图表解读应避免只描述形状，而要说明变量关系、变化趋势、异常点和结论含义，并明确它们如何支撑模型判断。"
    if n == 3:
        return "误差分析需要区分数据误差、模型误差和求解误差；若有对照实验，应说明改进模型相比基线方案的优势和代价。"
    if n == 4:
        return "敏感性分析应围绕权重、参数、阈值或样本扰动展开，观察结论是否发生方向性变化。"
    return "最终分析应回到赛题要求，确认每一问都有结果、有解释、有验证，并且图表、公式和结论之间不存在断链。"


def render_evaluation(unit_id: str, ph: dict) -> str:
    n = unit_number(unit_id)
    if n == 1:
        return text_value(ph, ["模型优点"], "模型优点应结合题目任务说明，例如可解释性强、计算稳定、数据需求适中、能够直接回答原问题。")
    if n == 2:
        return text_value(ph, ["模型不足"], "模型不足应具体到数据口径、假设条件、参数敏感性或泛化范围，不宜写成空泛的自我否定。")
    return text_value(ph, ["模型推广"], "模型推广部分可以说明该方法如何迁移到相似场景，以及需要补充哪些数据或约束才能保持可靠。")


def render_conclusion(unit_id: str, ph: dict, results: dict) -> str:
    if unit_id == "CONCL-1":
        return text_value(
            ph,
            ["结论第一段"],
            "本文围绕赛题要求完成了数据处理、模型建立、算法求解和结果分析，并分别给出各子问题的可复现结论。",
        )
    result = result_value(results, ["final_summary", "结论摘要"], "最终数值和图表证据需结合当前赛题的计算结果补充。")
    return text_value(ph, ["结论第二段"], f"综合结果表明，所建模型能够形成较完整的解释与验证闭环。{result}")


def render_references(ph: dict) -> str:
    refs = text_value(ph, ["参考文献", "文献列表"], "")
    if refs:
        return refs
    return (
        "[1] 赛题官方文件及附件数据。\n"
        "[2] 与本题模型、算法和数据来源相关的公开资料或教材。\n"
        "[3] 权威数据源、统计年鉴、政府开放数据或行业报告。"
    )


def render_appendix(unit_id: str, ph: dict) -> str:
    if unit_id == "APP-1":
        return (
            "附录应给出关键代码的复现说明。数据清洗、可视化、模型计算和结果契约代码可以参考各 skill 的 `scripts/` 样板，"
            "但真实赛题应根据当前数据字段、图表需求和建模结果二次生成或修改。"
        )
    return f"复现入口建议为 `{entry_command()}`。运行前应确认 `problem_files/`、`crawled_data/`、`paper_output/` 的输入输出路径符合项目约定。"


def render_unit(task: dict, ph: dict, results: dict) -> str:
    section = str(task.get("section", ""))
    unit_id = str(task.get("id", ""))
    header = f"【{section}｜{unit_id}】\n"

    if section == "摘要":
        body = render_abstract(unit_id, ph)
    elif section == "问题重述":
        body = render_intro(unit_id, ph)
    elif section == "模型假设":
        body = render_assumption(unit_id, ph)
    elif section == "符号说明":
        body = render_symbols(ph)
    elif section == "数据预处理":
        body = render_data(unit_id, ph, results)
    elif section.startswith("问题"):
        body = render_model(section, unit_id, ph, results, task)
    elif section == "结果分析":
        body = render_analysis(unit_id, ph, results)
    elif section == "模型评价":
        body = render_evaluation(unit_id, ph)
    elif section == "结论":
        body = render_conclusion(unit_id, ph, results)
    elif section == "参考文献":
        body = render_references(ph)
    elif section == "附录":
        body = render_appendix(unit_id, ph)
    else:
        body = f"本单元用于支撑“{section}”部分，应结合当前赛题补充任务、模型、数据、图表和验证结论。"

    return header + body.rstrip() + "\n"


def main() -> int:
    if not TASKS_FILE.exists():
        print(f"❌ 未找到任务清单：{TASKS_FILE}")
        return 1

    tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        print("❌ tasks.json 格式不正确")
        return 1

    ph = load_placeholders()
    results = load_results()
    UNITS_DIR.mkdir(parents=True, exist_ok=True)
    log = []

    for t in tasks:
        fp = Path(t.get("file_path", str(UNITS_DIR / f"{t.get('id','unit')}.txt")))
        text = render_unit(t, ph, results)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(text, encoding="utf-8")
        log.append({"id": t.get("id"), "len": len(text), "file": str(fp)})

    (OUTPUT_DIR / "generate_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已生成 {len(tasks)} 个微单元：{UNITS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

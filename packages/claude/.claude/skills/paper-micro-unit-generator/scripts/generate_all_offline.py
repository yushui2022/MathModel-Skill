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
            f"本文围绕“{title}”展开研究，首先对赛题背景、研究对象、约束条件和输出目标进行结构化拆解，将原始文字要求转化为可计算、可验证、可复现的建模任务。为避免直接凭经验选模，本文按照“题意分析—模型路线—数据证据—结果检验”的顺序展开，使每个子问题都能对应明确的数据来源、模型假设、评价指标和论文落点。",
        ),
        "ABS-2": text_value(
            ph,
            ["摘要第二段"],
            "针对问题一，本文先梳理输入变量、输出指标和约束关系，建立可解释的基线模型，再根据数据特征选择主模型进行求解。建模过程中重点说明变量定义、损失函数或目标函数、参数含义和验证方式，并通过预测对比、误差分析或约束满足情况判断模型是否能够稳定回答原问题。",
        ),
        "ABS-3": text_value(
            ph,
            ["摘要第三段"],
            "针对问题二，本文在第一问建模逻辑的基础上进一步引入数据清洗、特征构造、模型对照和结果证据沉淀。通过对比基线方案与改进方案，结合评价指标、图表展示和表格证据说明模型改进是否带来实际收益，同时检查异常值、参数扰动和样本变化对结论的影响。",
        ),
        "ABS-4": text_value(
            ph,
            ["摘要第四段"],
            "针对问题三，本文进一步开展综合评价、排序分析、敏感性检验或推广讨论，将模型输出转化为能够直接回应赛题要求的结论。最终结果通过图表索引、表格索引、指标契约和结论契约进行追溯，保证正文中的关键判断都有对应证据支撑，并为后续复现和局部重跑保留清晰路径。",
        ),
    }
    return templates.get(unit_id, f"关键词：{keywords}")


def render_intro(unit_id: str, ph: dict) -> str:
    templates = {
        "INTRO-1": text_value(
            ph,
            ["问题重述第一段", "题目背景"],
            "题目背景需要从现实场景、研究对象和决策需求展开。数学建模论文不能只复述题面文字，而应说明问题所处系统中有哪些变量相互作用，决策者希望优化或解释什么指标，以及现有数据能够支撑哪些层次的定量分析。基于这一认识，本文将题目要求转化为可计算任务，并在后续章节逐步给出模型、算法和验证证据。",
        ),
        "INTRO-2": text_value(
            ph,
            ["问题重述第二段", "子问题概述"],
            "根据题面要求，本文将整体任务拆解为若干相互关联的子问题。每个子问题都需要先明确输入数据、输出指标、约束条件和评价标准，再判断其数学本质属于预测、优化、评价、分类、聚类还是机理分析。这样处理的好处是可以避免在正文中直接堆砌模型名称，而是让模型选择与题目目标形成逻辑闭环。",
        ),
        "INTRO-3": text_value(
            ph,
            ["问题重述第三段", "论文任务定义"],
            "因此，本文的核心工作不是单独完成某一步计算，而是建立从数据预处理、模型建立、算法求解、结果展示到结论解释的完整链路。后续章节将依次说明数据如何清洗，变量如何定义，模型为何适合当前任务，结果如何由指标和图表支撑，以及最终结论如何回扣原题要求。",
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
        "上述假设的作用不是回避现实复杂性，而是在有限数据和有限时间条件下明确模型可求解的边界。每条假设都应对应一个具体简化对象，例如数据误差、外部扰动、样本稳定性或约束条件变化。后续将通过敏感性分析、误差检验或对照实验评估这些假设对结果的影响，若关键结论对某一假设高度敏感，则需要在模型评价部分明确说明适用范围。",
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
            "数据预处理首先确认附件、外部数据和题目指标的来源，记录字段含义、单位口径、时间范围和样本粒度。对于同名但口径不同的变量，需要在进入模型前统一解释；对于来自不同文件的数据，需要说明连接键、时间对齐方式和样本筛选规则。这样可以避免后续建模时出现口径混用，也便于在论文中追溯每个结果对应的数据依据。",
        )
    if n == 2:
        return text_value(
            ph,
            ["数据清洗说明"],
            "清洗阶段重点处理缺失值、异常值、重复记录、字段类型转换和量纲统一。缺失值不能简单删除，应先判断其出现机制和比例；异常值也不能机械剔除，应结合题意判断是录入错误、极端样本还是具有解释价值的特殊现象。所有清洗规则都应写入论文的数据说明部分，并将清洗后的文件统一保存到 `paper_output/data_cleaned/`，作为后续建模和可视化的唯一标准输入。",
        )
    if n == 3:
        return text_value(
            ph,
            ["可视化说明"],
            "可视化阶段应根据当前赛题重新选择图表类型，而不是固定套用某一种模板。趋势型变量适合折线图，分组对比适合柱状图或箱线图，指标权重适合排序条形图，相关关系适合热力图或散点图。`scripts/` 中的绘图代码主要提供尺寸、配色、标注、保存路径和论文引用格式的样板，真实赛题中需要根据当前字段和模型输出二次生成专用绘图代码。",
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
        return f"{p}（{question_id}）首先需要明确输入、输出和评价口径。根据模型路线契约，本问属于“{task_type}”任务，本文选择“{model}”作为主模型。该选择不是简单罗列模型名称，而是基于题目目标、数据结构和评分要求确定的：输入端需要能够承接附件数据或清洗数据，输出端需要能够形成可解释的数值结果、排序结果或决策建议。"
    if n == 2:
        return f"模型建立时必须解释“{model}”的贴题性。{model_reason} 因此正文中需要写清{('、'.join(formula_requirements) if formula_requirements else '变量定义、目标函数和评价指标')}，并说明这些数学对象分别对应题面中的哪些实际含义。只有把变量、目标、约束和评价指标对齐，模型推导才不会变成脱离题目的形式化描述。"
    if n == 3:
        return f"求解过程围绕“{algo}”展开，需要给出算法步骤、关键参数和复杂度说明。若模型包含训练、迭代、归一化、权重计算或约束优化环节，应将每一步的输入输出写清楚，并说明中间结果如何传递到下一步。这样读者才能根据论文正文、附录代码和输出契约复现计算过程，而不是只能看到最终结论。"
    if n == 4:
        backup_text = "、".join(backup_models) if backup_models else "备选模型"
        return f"为了避免模型只停留在形式推导，本文应以“{baseline_default}”作为基线方案，并可用{backup_text}进行对照。对照实验不只比较最终数值大小，还应比较误差、稳定性、可解释性和对题目约束的满足程度。若主模型相比基线模型提升明显，需要说明提升来自数据特征利用、非线性表达、约束处理还是评价体系改进。"
    if n == 5:
        figure_text = "、".join(str(item) for item in figure_suggestions) or "表格、图形或关键数值"
        table_sentence = f" 可引用的表格证据包括：{task_tables}。" if task_tables else ""
        note_sentence = f" {task_evidence_note}" if task_evidence_note else ""
        return f"结果展示部分应围绕题目原问展开，优先给出{figure_text}。图表不能只是装饰，而要承担证明作用：说明模型输出的变化趋势、误差分布、方案差异或综合得分排序。当前结果摘要为：{result}。{table_sentence}{note_sentence}"
    if n == 6:
        note_sentence = f" {task_evidence_note}" if task_evidence_note else ""
        return f"模型检验阶段使用“{metric}”评价结果可靠性，并结合残差、敏感性或约束检查说明模型是否稳定。检验部分应回答两个问题：第一，模型在已有数据上是否表现合理；第二，当参数、样本或权重发生合理扰动时，结论是否仍保持一致。{note_sentence}"
    if n == 7:
        rubric_text = "、".join(rubric_points) if rubric_points else "题意覆盖、模型合理性、结果可信和图表证据"
        return f"敏感性分析和结果解释应对齐评分点：{rubric_text}。论文中需要说明哪些参数或指标最影响结果，哪些因素只改变局部数值而不改变总体判断。若排名、预测趋势或优化方案在小幅扰动下仍然稳定，可以作为模型可靠性的证据；若变化明显，则需要在适用范围中说明风险。"
    conclusion = task_conclusions or f"{p}（{question_id}）必须形成“任务定义 → 模型建立 → 算法求解 → 结果验证 → 回答原问”的闭环。"
    note_sentence = f" {task_evidence_note}" if task_evidence_note else ""
    return f"综上，{conclusion} 本问最后应回到题目原句，明确给出可执行的回答，而不是只停留在模型过程描述。{note_sentence}"


def render_analysis(unit_id: str, ph: dict, results: dict) -> str:
    n = unit_number(unit_id)
    if n == 1:
        return text_value(ph, ["结果总述"], "结果分析应先用一段话回答各子问题的核心结论，再说明这些结论对应哪些图表和数值证据。写作时应避免只说“结果较好”“模型有效”，而要明确指出好在哪里、由哪个指标支撑、与基线或题目要求相比有什么差异。")
    if n == 2:
        return "图表解读应避免只描述形状，而要说明变量关系、变化趋势、异常点和结论含义。对于趋势图，应解释上升、下降或波动背后的可能原因；对于对比图，应说明不同方案之间的差异是否具有实际意义；对于误差图，应判断误差是否集中在特定区间或特定样本上。"
    if n == 3:
        return "误差分析需要区分数据误差、模型误差和求解误差。数据误差通常来自缺失、测量或统计口径差异；模型误差来自假设简化和表达能力限制；求解误差则可能来自迭代精度、参数设置或数值稳定性。若有对照实验，应说明改进模型相比基线方案的优势和代价。"
    if n == 4:
        return "敏感性分析应围绕权重、参数、阈值或样本扰动展开，观察结论是否发生方向性变化。若只发生数值微调而结论不变，可说明模型具有稳定性；若结论对某些参数高度敏感，则应指出该参数是实际应用中的重点控制对象。"
    return "最终分析应回到赛题要求，确认每一问都有结果、有解释、有验证，并且图表、公式和结论之间不存在断链。若某一问仍缺少真实建模结果，应在 QA 报告中明确标注，避免把占位内容包装成最终结论。"


def render_evaluation(unit_id: str, ph: dict) -> str:
    n = unit_number(unit_id)
    if n == 1:
        return text_value(ph, ["模型优点"], "模型优点应结合题目任务说明，例如可解释性强、计算稳定、数据需求适中、能够直接回答原问题。对于数学建模论文而言，优点不应只写“模型简单有效”，而应说明该模型为什么适合当前数据规模、变量关系和评分要求，以及它如何帮助形成可复现的结果。")
    if n == 2:
        return text_value(ph, ["模型不足"], "模型不足应具体到数据口径、假设条件、参数敏感性或泛化范围，不宜写成空泛的自我否定。若结果依赖某些强假设，应说明这些假设在现实场景中可能被破坏的条件，并给出后续改进方向。")
    return text_value(ph, ["模型推广"], "模型推广部分可以说明该方法如何迁移到相似场景，以及需要补充哪些数据或约束才能保持可靠。推广不是简单说“可用于其他问题”，而要指出哪些部分可以复用，哪些部分必须重新估计或重新验证。")


def render_conclusion(unit_id: str, ph: dict, results: dict) -> str:
    if unit_id == "CONCL-1":
        return text_value(
            ph,
            ["结论第一段"],
            "本文围绕赛题要求完成了数据处理、模型建立、算法求解和结果分析，并分别给出各子问题的可复现结论。结论部分应以回答原问为核心，不再重复大段模型推导，而是概括各问的关键发现、证据来源和适用范围，使读者能够快速判断论文是否真正解决了题目要求。",
        )
    result = result_value(results, ["final_summary", "结论摘要"], "最终数值和图表证据需结合当前赛题的计算结果补充。")
    return text_value(ph, ["结论第二段"], f"综合结果表明，所建模型能够形成较完整的解释与验证闭环。{result} 若仍存在结果契约骨架或待补指标，应在最终提交前通过当前赛题专用建模代码补齐，并重新运行 QA 与正文生成，确保 Word 版本中的每个结论都能追溯到真实计算结果。")


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
            "但真实赛题应根据当前数据字段、图表需求和建模结果二次生成或修改。当前赛题专用代码应放在 `paper_output/code/` 下，数据处理、绘图、建模和检查脚本分别进入对应子目录，避免污染可复用 skill 包。"
        )
    return f"复现入口建议为 `{entry_command()}`。运行前应确认 `problem_files/`、`crawled_data/`、`paper_output/` 的输入输出路径符合项目约定。"


def compact_text(text: str) -> str:
    lines = [line.rstrip() for line in str(text).splitlines()]
    return "\n".join(lines).strip()


def role_expansion(task: dict) -> str:
    return ""


def enrich_text(body: str, task: dict) -> str:
    text = compact_text(body)
    section = str(task.get("section") or "")
    unit_id = str(task.get("id") or "")
    if section in {"符号说明", "参考文献"} or unit_id == "ABS-5":
        return text

    minimum = 260
    try:
        target_words = int(task.get("target_words") or 0)
        if target_words > 0:
            minimum = max(220, min(420, int(target_words * 0.9)))
    except Exception:
        pass

    additions = []
    extra = role_expansion(task)
    if extra:
        additions.append(extra)

    if task.get("main_model") and task.get("model_reason") and str(task.get("model_reason")) not in text:
        additions.append(f"其中，主模型“{task.get('main_model')}”的采用理由为：{task.get('model_reason')}")
    if task.get("validation_plan"):
        plans = list_text(task.get("validation_plan"))
        if plans:
            additions.append(f"验证环节应覆盖{('、'.join(plans))}，并在正文中说明每项检验对应的可靠性含义。")
    if task.get("figure_suggestions"):
        figs = list_text(task.get("figure_suggestions"))
        if figs:
            additions.append(f"图表部分建议围绕{('、'.join(figs))}展开，使文字结论能够与可视化证据相互印证。")
    note = evidence_note(task)
    if note:
        additions.append(note)

    for addition in additions:
        if len(text) >= minimum:
            break
        if addition and addition not in text:
            text = f"{text} {addition}"
    return text


def render_unit(task: dict, ph: dict, results: dict) -> str:
    section = str(task.get("section", ""))
    unit_id = str(task.get("id", ""))

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

    return enrich_text(body, task).rstrip() + "\n"


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

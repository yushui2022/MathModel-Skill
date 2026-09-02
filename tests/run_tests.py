from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import setup_sandbox


REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX = REPO_ROOT / "tests" / "sandbox"
ROBUST_LOADER = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "data-cleaning-and-visualization" / "scripts" / "robust_loader.py"
BUILD_RESULT_CONTRACTS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "model-code-and-result-generator" / "scripts" / "build_result_contracts.py"
EVIDENCE_GATE = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "quality-assurance-auditor" / "scripts" / "evidence_gate.py"
FORMAT_DOCX = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "format_formal_docx.py"
CHECK_PAPER_FORMAT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "check_paper_format.py"
PREPARE_AUTHORING = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "prepare_authoring.py"
VALIDATE_AUTHORING = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "validate_authoring.py"
ASSEMBLE_SECTIONS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "assemble_sections.py"
GENERATE_LEGACY = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-micro-unit-generator" / "scripts" / "generate_all_offline.py"
MERGE_LEGACY = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-micro-unit-generator" / "scripts" / "merge.py"
BUILD_PACKAGES = REPO_ROOT / "scripts" / "build_release_packages.py"
UPDATE_WORKFLOW_MEMORY = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "context-memory-keeper" / "scripts" / "update_workflow_memory.py"
CLAUDE_SKILLS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills"
CODEX_SKILLS = REPO_ROOT / "packages" / "codex" / ".agents" / "skills"
TRAE_SKILLS = REPO_ROOT / "packages" / "trae" / ".trae" / "skills"
CLAUDE_ORCHESTRATOR_SCRIPTS = CLAUDE_SKILLS / "paper-workflow-orchestrator" / "scripts"
CODEX_ORCHESTRATOR_SCRIPTS = CODEX_SKILLS / "paper-workflow-orchestrator" / "scripts"
TRAE_ORCHESTRATOR_SCRIPTS = TRAE_SKILLS / "paper-workflow-orchestrator" / "scripts"
PREFLIGHT = CLAUDE_ORCHESTRATOR_SCRIPTS / "preflight_check.py"
WORKFLOW_GUARD = CLAUDE_ORCHESTRATOR_SCRIPTS / "workflow_guard.py"
CODEX_PREFLIGHT = CODEX_ORCHESTRATOR_SCRIPTS / "preflight_check.py"
CODEX_WORKFLOW_GUARD = CODEX_ORCHESTRATOR_SCRIPTS / "workflow_guard.py"
TRAE_PREFLIGHT = TRAE_ORCHESTRATOR_SCRIPTS / "preflight_check.py"
TRAE_WORKFLOW_GUARD = TRAE_ORCHESTRATOR_SCRIPTS / "workflow_guard.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, cwd: Path) -> dict[str, object]:
    return {
        "path": path.resolve().relative_to(cwd.resolve()).as_posix(),
        "exists": path.exists(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_fresh_gate_report(output: Path) -> None:
    marker = output / "qa" / "evidence_gate_test_input.json"
    write_json(marker, {"status": "computed"})
    write_json(
        output / "qa" / "evidence_gate_report.json",
        {
            "status": "PASS",
            "failures": [],
            "input_hashes": {marker.resolve().relative_to(output.parent.resolve()).as_posix(): sha256_file(marker)},
        },
    )


def prepare_authoring_pass(cwd: Path, output: Path, source: str) -> None:
    outline_path = output / "plan" / "paper_outline.json"
    outline = load_json(outline_path)
    target = outline.setdefault("target_words", {})
    target["ideal"] = max(20, min(6000, len(re.sub(r"\s+", "", source))))
    write_json(outline_path, outline)
    result = run([sys.executable, str(PREPARE_AUTHORING), "--mode", "global"], cwd)
    assert_true(result.returncode == 0, f"authoring preparation should pass\n{result.stdout}")
    draft_path = output / "drafts" / "global_draft.md"
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(source.rstrip() + "\n\n初稿阶段保留此句用于证明最终稿经过全文统一改写。\n", encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "GLOBAL"], cwd)
    assert_true(result.returncode == 0, f"global draft audit should pass\n{result.stdout}")
    result = run([sys.executable, str(ASSEMBLE_SECTIONS)], cwd)
    assert_true(result.returncode == 0, f"authoring assembly should pass\n{result.stdout}")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--assembled"], cwd)
    assert_true(result.returncode == 0, f"assembled audit should pass\n{result.stdout}")
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--final"], cwd)
    assert_true(result.returncode == 0, f"final authoring audit should pass\n{result.stdout}")


def complete_paper_source(
    *,
    extra_body: list[str] | None = None,
    include_body_citations: bool = True,
) -> str:
    citation_sentence = "线性模型设定参考回归分析方法[1]，稳定性检验采用重采样思想[2]，复现记录遵循计算研究规范[3]。" if include_body_citations else "本文综合使用线性模型、稳定性检验和可复现实验方法。"
    lines = [
        "# 论文题目",
        "# 摘要",
        "本文围绕 Q1 建立可复现实验流程，给出数据处理、模型建立、求解算法、结果分析与检验结论。",
        "# 关键词",
        "数学建模；可复现；证据链",
        "# 1 问题重述",
        "Q1 要求根据输入数据建立模型并解释结果。本文明确变量、目标和约束。",
        "# 2 问题分析",
        citation_sentence,
        "问题需要先识别数据字段，再构建可解释模型，并使用结果回扣原问题。",
        "# 3 模型假设",
        "假设数据记录可靠，样本之间满足独立观测要求，异常值已在清洗阶段处理。",
        "# 4 符号说明",
        r"设 $x_i$ 为第 $i$ 个解释变量观测，$y_i$ 为对应目标值，$n$ 为样本量。",
        "# 5 模型的建立与求解",
        "本章给出 Q1 的建模、变量定义、算法、结果与检验。",
        "# 5.1 Q1 模型建立与求解",
        "Q1 使用可解释基线模型进行求解，并记录运行证据。",
        "# 5.1.1 建模思路",
        "先根据数据字段构造特征，再建立目标函数，最后输出可复核结果。",
        "# 5.1.2 变量定义与公式推导",
        "样本均值用于刻画输入变量的中心位置：",
        "$$",
        r"\bar{x}=\frac{1}{n}\sum_{i=1}^{n}x_i.",
        "$$",
        r"在线性关系假设下，预测函数写为 $\hat{y}_i=\beta_0+\beta_1x_i$，参数由最小二乘准则确定。",
        "# 5.1.3 求解算法",
        "Step 1 读取清洗后的数据。Step 2 构造特征矩阵。Step 3 计算模型结果。Step 4 保存证据文件。",
        "# 5.1.4 结果分析",
        "模型结果能够回答 Q1，并且所有输出均来自实际运行的代码。",
        "# 5.1.5 模型检验或灵敏度分析",
        "通过改变输入扰动检查结果稳定性，结果变化保持在可解释范围内。",
    ]
    lines.extend(extra_body or [])
    lines.extend(
        [
            "# 6 模型检验",
            "检验包括运行记录、输出表格、指标文件和结论文件的一致性检查。",
            "# 7 模型评价",
            "模型具有可解释、可复现和便于扩展的优点，局限是依赖输入数据质量。",
            "# 8 参考文献",
            "[1] 数学建模与回归分析参考资料。",
            "[2] 统计重采样与稳定性检验参考资料。",
            "[3] 可复现计算研究方法参考资料。",
            "# 附录",
            "附录给出主要代码和运行环境说明。",
        ]
    )
    return "\n".join(lines)


def prepare_formal_paper_scenario(name: str, source: str) -> tuple[Path, Path]:
    cwd = SANDBOX / name
    if cwd.exists():
        shutil.rmtree(cwd)
    output = cwd / "paper_output"
    output.mkdir(parents=True)
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")
    write_json(output / "plan" / "paper_outline.json", {"target_words": {"min": 100, "max": 5000}, "questions": [{"question_id": "Q1"}]})
    write_json(output / "figure_index.json", {"figures": []})
    write_json(output / "tables" / "table_index.json", {"tables": []})
    write_fresh_gate_report(output)
    prepare_authoring_pass(cwd, output, source)
    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 0, f"formal docx generation should pass\n{result.stdout}")
    return cwd, output


def make_problem_scenario(name: str) -> Path:
    cwd = SANDBOX / name
    if cwd.exists():
        shutil.rmtree(cwd)
    problem_files = cwd / "problem_files"
    problem_files.mkdir(parents=True)
    (problem_files / "problem.md").write_text("Build a reproducible baseline model for question one.\n", encoding="utf-8")
    (problem_files / "data.csv").write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    return cwd


def make_preflighted_scenario(name: str) -> tuple[Path, Path]:
    cwd = make_problem_scenario(name)
    result = run([sys.executable, str(PREFLIGHT)], cwd)
    assert_true(result.returncode == 0, f"{name}: preflight should pass\n{result.stdout}")
    return cwd, cwd / "paper_output"


def make_staged_scenario(name: str, through_step: str) -> tuple[Path, Path]:
    cwd, output = make_preflighted_scenario(name)
    stage_workflow(output, through_step)
    return cwd, output


def stage_workflow(output: Path, through_step: str) -> None:
    order = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    limit = order.index(through_step)
    cwd = output.parent
    if limit >= order.index("S1"):
        write_json(output / "step1" / "problem_analysis.json", {"questions": [{"question_id": "Q1", "title": "question one"}]})
    if limit >= order.index("S2"):
        write_json(output / "plan" / "model_route.json", {"questions": [{"question_id": "Q1", "title": "question one", "main_model": "baseline"}]})
        write_json(output / "plan" / "rubric_alignment.json", {"status": "PASS", "items": [{"question_id": "Q1"}]})
        (output / "plan" / "scoring_strategy.md").write_text("score by reproducible modeling evidence\n", encoding="utf-8")
    if limit >= order.index("S3"):
        write_json(output / "plan" / "data_plan.json", {"datasets": [{"path": "paper_output/data_cleaned/sample_cleaned.csv"}]})
        write_json(output / "plan" / "visualization_plan.json", {"figures": []})
        write_json(output / "figure_index.json", {"figures": []})
        write_json(
            output / "data_cleaned" / "load_report.json",
            {
                "status": "PASS",
                "input_manifest_used": True,
                "input_manifest_sha256": sha256_file(output / "input_manifest.json"),
                "summary": {"readable_data_file_count": 1},
            },
        )
    if limit >= order.index("S4"):
        (output / "code" / "modeling").mkdir(parents=True, exist_ok=True)
        (output / "code" / "modeling" / "q1_model.py").write_text("print('model ready')\n", encoding="utf-8")
        (output / "code" / "modeling" / "run_modeling.py").write_text("print('runner ready')\n", encoding="utf-8")
    if limit >= order.index("S5"):
        table_path = output / "tables" / "t1.csv"
        table_path.parent.mkdir(parents=True, exist_ok=True)
        table_path.write_text("metric,value\nscore,1\n", encoding="utf-8")
        model_script = output / "code" / "modeling" / "q1_model.py"
        model_script_hash = sha256_file(model_script)
        write_json(
            output / "results" / "model_results.json",
            {
                "questions": [
                    {
                        "question_id": "Q1",
                        "status": "computed",
                        "evidence_status": "computed",
                        "result_summary": "Computed baseline result for Q1.",
                        "execution_provenance": {
                            "source_code_path": "paper_output/code/modeling/q1_model.py",
                            "source_code_sha256": model_script_hash,
                            "run_command": "python paper_output/code/modeling/q1_model.py",
                            "run_exit_code": 0,
                            "output_artifacts": ["paper_output/tables/t1.csv"],
                        },
                    }
                ]
            },
        )
        write_json(output / "results" / "metrics.json", {"items": [{"question_id": "Q1", "status": "computed", "metric_name": "score", "value": 1}]})
        write_json(output / "results" / "conclusions.json", {"items": [{"question_id": "Q1", "status": "computed", "conclusion_text": "conclusion"}]})
        write_json(output / "tables" / "table_index.json", {"tables": [{"question_id": "Q1", "status": "computed", "table_id": "t1", "path": "paper_output/tables/t1.csv"}]})
        write_json(output / "tasks.json", [{"question_id": "Q1", "task": "computed"}])
        write_json(
            output / "results" / "run_manifest.json",
            {
                "status": "PASS",
                "runs": [
                    {
                        "script": "paper_output/code/modeling/q1_model.py",
                        "script_sha256": model_script_hash,
                        "question_ids": ["Q1"],
                        "returncode": 0,
                        "input_files": [file_record(cwd / "problem_files" / "data.csv", cwd)],
                        "output_artifacts": [file_record(table_path, cwd)],
                    }
                ],
            },
        )
    if limit >= order.index("S6"):
        result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
        assert_true(result.returncode == 0, f"staged evidence gate should pass\n{result.stdout}")
    if limit >= order.index("S7"):
        source = "# Title\n\n# 摘要\n\nFormal computed abstract.\n\n# 1 Problem Restatement\n\nFormal computed content with a complete explanation for the staged workflow.\n"
        write_json(output / "plan" / "paper_outline.json", {"target_words": {"min": 10, "max": 5000}, "questions": [{"question_id": "Q1"}]})
        prepare_authoring_pass(cwd, output, source)
        result = run([sys.executable, str(FORMAT_DOCX)], cwd)
        assert_true(result.returncode == 0, f"staged formal docx should pass\n{result.stdout}")
    if limit >= order.index("S8"):
        format_inputs = [
            output / "final_paper_source.md",
            output / "final_paper.docx",
            output / "plan" / "paper_outline.json",
            output / "figure_index.json",
            output / "tables" / "table_index.json",
            output / "qa" / "evidence_gate_report.json",
            output / "plan" / "writing_plan.json",
            output / "context" / "authoring_state.json",
        ]
        write_json(
            output / "format_check_report.json",
            {
                "status": "PASS",
                "failures": [],
                "input_hashes": {
                    path.resolve().relative_to(cwd.resolve()).as_posix(): sha256_file(path)
                    for path in format_inputs
                },
            },
        )


def assert_workflow_status(cwd: Path, output: Path, current: str, next_step: str, skill: str) -> None:
    result = run([sys.executable, str(WORKFLOW_GUARD), "--status"], cwd)
    assert_true(result.returncode == 0, f"workflow status should be diagnostic\n{result.stdout}")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(report["current_step"] == current, f"expected current_step {current}, got {report['current_step']}")
    assert_true(report["next_step"] == next_step, f"expected next_step {next_step}, got {report['next_step']}")
    assert_true(report["recommended_skill"] == skill, f"expected recommended_skill {skill}, got {report['recommended_skill']}")


def test_preflight() -> None:
    cases = [
        ("scenario_1_empty", 1, "FAIL"),
        ("scenario_2_only_doc", 1, "FAIL"),
        ("scenario_3_broken_xlsx", 1, "FAIL"),
        ("scenario_4_suspicious_template", 0, "PASS"),
        ("scenario_5_stale_output", 0, "PASS"),
        ("scenario_7_real_data", 0, "PASS"),
    ]
    for name, expected_code, expected_status in cases:
        cwd = SANDBOX / name
        result = run([sys.executable, str(PREFLIGHT)], cwd)
        assert_true(result.returncode == expected_code, f"{name}: expected exit {expected_code}, got {result.returncode}\n{result.stdout}")
        report = load_json(cwd / "paper_output" / "preflight_report.json")
        assert_true(report["status"] == expected_status, f"{name}: expected {expected_status}, got {report['status']}")
        assert_true((cwd / "paper_output" / "input_manifest.json").exists(), f"{name}: input_manifest.json should be written")

    manifest = load_json(SANDBOX / "scenario_4_suspicious_template" / "paper_output" / "input_manifest.json")
    result_templates = [item for item in manifest["entries"] if item["role"] == "result_template"]
    assert_true(len(result_templates) == 1, "scenario_4 should classify result1.xlsx as result_template")
    assert_true(result_templates[0]["usable_for_modeling"] is False, "result template must not be usable for modeling")
    assert_true(manifest["summary"]["raw_data_count"] == 0, "scenario_4 should not count result template as raw data")
    manifest = load_json(SANDBOX / "scenario_7_real_data" / "paper_output" / "input_manifest.json")
    assert_true(manifest["summary"]["raw_data_count"] == 1, "scenario_7 should classify csv as raw_data")


def test_preflight_detects_modern_and_legacy_mixed_installations() -> None:
    cwd = make_problem_scenario("scenario_mixed_skill_roots")
    entries = [
        (".agents/skills/paper-workflow-orchestrator", "standard", True),
        ("skills/mathmodel-lite", "lite", False),
        (".codex/skills/pro-workflow-orchestrator", "pro", False),
        (".claude/skills/mathmodel-lite", "lite", True),
        (".trae/skills/paper-workflow-orchestrator", "standard", True),
    ]
    for path_text, edition, marked in entries:
        skill_dir = cwd / Path(path_text)
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {edition}\n", encoding="utf-8")
        if marked:
            write_json(
                skill_dir / "MATHMODEL_EDITION.json",
                {
                    "schema_version": "1.0",
                    "product": "MathModel-Skill",
                    "edition": edition,
                    "version": "test",
                    "entry_skill": skill_dir.name,
                },
            )
    result = run([sys.executable, str(PREFLIGHT)], cwd)
    assert_true(result.returncode == 1, "mixed Standard/Lite/Pro installation should fail preflight")
    report = load_json(cwd / "paper_output" / "preflight_report.json")
    install = report["mathmodel_installation"]
    assert_true(install["detected_editions"] == ["lite", "pro", "standard"], "preflight should identify all editions")
    assert_true({item["skill_root"] for item in install["installations"]} == {item[0].rsplit("/", 1)[0] for item in entries}, "preflight should scan all five skill roots")
    assert_true(any("混装" in item for item in report["errors"]), "mixed-install failure should be explicit")


def test_missing_pypdf() -> None:
    code = f"""
import importlib.abc
import runpy
import sys
from pathlib import Path

class BlockPypdf(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pypdf" or fullname.startswith("pypdf."):
            raise ImportError("blocked pypdf for test")
        return None

sys.meta_path.insert(0, BlockPypdf())
runpy.run_path(str(Path(r"{PREFLIGHT}")), run_name="__main__")
"""
    cwd = SANDBOX / "scenario_6_no_pypdf"
    result = run([sys.executable, "-c", code], cwd)
    assert_true(result.returncode == 1, f"scenario_6_no_pypdf: expected exit 1, got {result.returncode}\n{result.stdout}")
    report = load_json(cwd / "paper_output" / "preflight_report.json")
    assert_true(report["status"] == "FAIL", "scenario_6_no_pypdf should FAIL")
    assert_true(any("pypdf" in error for error in report["errors"]), "scenario_6_no_pypdf should mention missing pypdf")


def test_robust_loader_and_workflow_guard() -> None:
    cwd = SANDBOX / "scenario_4_suspicious_template"
    result = run([sys.executable, str(ROBUST_LOADER)], cwd)
    assert_true(result.returncode == 0, f"robust_loader should pass\n{result.stdout}")
    report = load_json(cwd / "paper_output" / "data_cleaned" / "load_report.json")
    assert_true(report["status"] == "PASS", "load_report should PASS")
    assert_true(report["input_manifest_used"] is True, "robust_loader should consume input_manifest.json")
    assert_true(report["summary"]["readable_data_file_count"] == 0, "result template should not be treated as readable raw data")
    assert_true(any(item["role"] == "result_template" for item in report["skipped_files"]), "result template should be skipped by robust_loader")

    raw_cwd = SANDBOX / "scenario_7_real_data"
    result = run([sys.executable, str(ROBUST_LOADER)], raw_cwd)
    assert_true(result.returncode == 0, f"robust_loader should pass for real raw data\n{result.stdout}")
    raw_report = load_json(raw_cwd / "paper_output" / "data_cleaned" / "load_report.json")
    assert_true(raw_report["input_manifest_used"] is True, "real raw data load_report should consume input_manifest.json")
    assert_true(raw_report["summary"]["readable_data_file_count"] == 1, "raw CSV should count as readable data")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S0"], cwd)
    assert_true(result.returncode == 0, f"workflow S0 should pass after preflight\n{result.stdout}")
    result = run([sys.executable, str(WORKFLOW_GUARD), "--status"], cwd)
    assert_true(result.returncode == 0, f"workflow status should be diagnostic\n{result.stdout}")
    report = load_json(cwd / "paper_output" / "qa" / "workflow_guard_report.json")
    assert_true(report["mode"] == "status", "status report should record mode=status")
    assert_true(report["current_step"] == "S0", "status recovery should identify S0 as deepest completed step")
    assert_true(report["next_step"] == "S1", "status recovery should recommend S1 next")
    assert_true(report["recommended_skill"] == "problem-doc-model-selector", "status recovery should recommend problem-doc-model-selector")
    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S1"], cwd)
    assert_true(result.returncode == 1, "workflow S1 should fail because problem_analysis.json is absent")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--skill", "problem-doc-model-selector"], cwd)
    assert_true(result.returncode == 0, f"problem-doc-model-selector should be allowed after S0\n{result.stdout}")
    report = load_json(cwd / "paper_output" / "qa" / "workflow_guard_report.json")
    assert_true(report["skill"] == "problem-doc-model-selector", "skill guard report should record skill name")
    assert_true(report["required_step"] == "S0", "problem-doc-model-selector should require S0")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--skill", "data-cleaning-and-visualization"], cwd)
    assert_true(result.returncode == 1, "data-cleaning-and-visualization should be blocked before S2")
    report = load_json(cwd / "paper_output" / "qa" / "workflow_guard_report.json")
    assert_true(report["skill"] == "data-cleaning-and-visualization", "blocked skill report should record skill name")
    assert_true(report["required_step"] == "S2", "data-cleaning-and-visualization should require S2")


def test_orchestrator_guard_allows_fresh_entry() -> None:
    cwd = SANDBOX / "scenario_orchestrator_entry"
    if cwd.exists():
        shutil.rmtree(cwd)
    cwd.mkdir(parents=True)

    result = run([sys.executable, str(WORKFLOW_GUARD), "--skill", "paper-workflow-orchestrator"], cwd)
    assert_true(result.returncode == 0, f"orchestrator entry guard should not block a fresh project\n{result.stdout}")
    report = load_json(cwd / "paper_output" / "qa" / "workflow_guard_report.json")
    assert_true(report["mode"] == "skill", "orchestrator entry report should use mode=skill")
    assert_true(report["skill"] == "paper-workflow-orchestrator", "report should identify orchestrator skill")
    assert_true(report["required_step"] == "ENTRY", "orchestrator should be an entrypoint, not require S0 before it can start")
    assert_true(report["status"] == "PASS", "orchestrator entry guard should allow start")
    assert_true(report["next_step"] == "S0", "fresh project should recover to S0 preflight")
    assert_true(report["recommended_skill"] == "paper-workflow-orchestrator", "fresh project should stay in orchestrator")


def assert_platform_orchestrator_smoke(name: str, preflight_script: Path, workflow_guard_script: Path) -> None:
    cwd = make_problem_scenario(name)
    output = cwd / "paper_output"

    result = run([sys.executable, str(preflight_script)], cwd)
    assert_true(result.returncode == 0, f"{name}: preflight should pass\n{result.stdout}")
    preflight_report = load_json(output / "preflight_report.json")
    input_manifest = load_json(output / "input_manifest.json")
    assert_true(preflight_report["status"] == "PASS", f"{name}: preflight_report.json should PASS")
    assert_true(input_manifest["summary"]["raw_data_count"] == 1, f"{name}: input_manifest should count one raw data file")

    result = run([sys.executable, str(workflow_guard_script), "--status"], cwd)
    assert_true(result.returncode == 0, f"{name}: workflow status should be diagnostic\n{result.stdout}")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(report["current_step"] == "S0", f"{name}: expected current_step S0, got {report['current_step']}")
    assert_true(report["next_step"] == "S1", f"{name}: expected next_step S1, got {report['next_step']}")
    assert_true(report["recommended_skill"] == "problem-doc-model-selector", f"{name}: expected problem-doc-model-selector next")

    result = run([sys.executable, str(workflow_guard_script), "--skill", "problem-doc-model-selector"], cwd)
    assert_true(result.returncode == 0, f"{name}: problem-doc-model-selector should be allowed after S0\n{result.stdout}")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(report["status"] == "PASS", f"{name}: skill guard should PASS after preflight")
    assert_true(report["required_step"] == "S0", f"{name}: skill guard should require S0")


def test_codex_package_smoke() -> None:
    assert_platform_orchestrator_smoke("scenario_codex_package_smoke", CODEX_PREFLIGHT, CODEX_WORKFLOW_GUARD)


def test_trae_package_smoke() -> None:
    assert_platform_orchestrator_smoke("scenario_trae_package_smoke", TRAE_PREFLIGHT, TRAE_WORKFLOW_GUARD)


def test_workflow_status_after_code_generation() -> None:
    cwd = SANDBOX / "scenario_status_s4"
    if cwd.exists():
        shutil.rmtree(cwd)
    problem_files = cwd / "problem_files"
    problem_files.mkdir(parents=True)
    (problem_files / "problem.md").write_text("Build a reproducible baseline model for question one.\n", encoding="utf-8")
    (problem_files / "data.csv").write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    output = cwd / "paper_output"
    result = run([sys.executable, str(PREFLIGHT)], cwd)
    assert_true(result.returncode == 0, f"preflight should pass before staged workflow status test\n{result.stdout}")

    stage_workflow(output, "S4")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--status"], cwd)
    assert_true(result.returncode == 0, f"workflow status should stay diagnostic at S5 gap\n{result.stdout}")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(report["current_step"] == "S4", f"expected current_step S4, got {report['current_step']}")
    assert_true(report["next_step"] == "S5", f"expected next_step S5, got {report['next_step']}")
    assert_true(report["recommended_skill"] == "model-code-and-result-generator", "S5 recovery should route back to model-code-and-result-generator")
    assert_true(any("run_manifest" in failure or "model_results" in failure for failure in report["failures"]), "S5 failures should mention missing executed results")


def test_workflow_status_recovery_across_stages() -> None:
    cases = [
        ("S1", "S1", "S2", "modeling-paper-rubric-and-model-selector"),
        ("S3", "S3", "S4", "model-code-and-result-generator"),
        ("S5", "S5", "S6", "quality-assurance-auditor"),
        ("S7", "S7", "S8", "paper-formal-writer"),
    ]
    for through_step, current, next_step, skill in cases:
        cwd, output = make_preflighted_scenario(f"scenario_status_{through_step.lower()}")
        stage_workflow(output, through_step)
        assert_workflow_status(cwd, output, current, next_step, skill)


def test_workflow_memory_snapshot() -> None:
    cwd, output = make_preflighted_scenario("scenario_workflow_memory")
    stage_workflow(output, "S3")
    assert_workflow_status(cwd, output, "S3", "S4", "model-code-and-result-generator")

    result = run([sys.executable, str(UPDATE_WORKFLOW_MEMORY)], cwd)
    assert_true(result.returncode == 0, f"workflow memory snapshot should pass after workflow status\n{result.stdout}")
    snapshot = load_json(output / "context" / "workflow_memory.json")
    assert_true(snapshot["status"] == "PASS", "workflow memory snapshot should PASS")
    assert_true(snapshot["workflow"]["current_step"] == "S3", "snapshot should preserve current workflow step")
    assert_true(snapshot["workflow"]["next_step"] == "S4", "snapshot should preserve next workflow step")
    assert_true(snapshot["workflow"]["recommended_skill"] == "model-code-and-result-generator", "snapshot should preserve recommended skill")
    assert_true(snapshot["artifacts"]["input_manifest"]["exists"] is True, "snapshot should record input_manifest artifact")
    assert_true(snapshot["artifacts"]["load_report"]["exists"] is True, "snapshot should record load_report artifact")
    memory_md = output / "context" / "workflow_memory.md"
    assert_true(memory_md.exists(), "workflow_memory.md should be written")
    assert_true("Workflow Memory Snapshot" in memory_md.read_text(encoding="utf-8"), "memory markdown should be readable")


def test_workflow_status_complete_after_s8() -> None:
    cwd, output = make_preflighted_scenario("scenario_status_complete")
    stage_workflow(output, "S8")
    result = run([sys.executable, str(WORKFLOW_GUARD), "--status"], cwd)
    assert_true(result.returncode == 0, f"workflow status should be diagnostic at completion\n{result.stdout}")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(report["status"] == "COMPLETE", f"expected COMPLETE status, got {report['status']}")
    assert_true(report["current_step"] == "S8", f"expected current_step S8, got {report['current_step']}")
    assert_true(report["next_step"] == "", "complete workflow should not recommend another step")
    assert_true(report["recommended_skill"] == "", "complete workflow should not recommend another skill")
    assert_true(report["failures"] == [], "complete workflow should have no failures")


def test_authoring_auto_modes_and_global_fallback() -> None:
    cwd, output = make_staged_scenario("scenario_authoring_auto_modes", "S6")
    outline = {
        "target_words": {"min": 100, "ideal": 7001, "max": 9000},
        "sections": [{"section_id": "1", "title": "问题重述", "target_words": 200}],
    }
    write_json(output / "plan" / "paper_outline.json", outline)
    result = run([sys.executable, str(PREPARE_AUTHORING), "--mode", "auto"], cwd)
    assert_true(result.returncode == 0, f"long auto authoring should prepare\n{result.stdout}")
    assert_true(load_json(output / "plan" / "writing_plan.json")["mode"] == "section", "auto should choose section above 6000 chars")

    outline["target_words"]["ideal"] = 5000
    write_json(output / "plan" / "paper_outline.json", outline)
    result = run([sys.executable, str(PREPARE_AUTHORING), "--mode", "auto"], cwd)
    assert_true(result.returncode == 0, f"short auto authoring should prepare\n{result.stdout}")
    assert_true(load_json(output / "plan" / "writing_plan.json")["mode"] == "global", "auto should choose global at 6000 chars or below")

    draft = output / "drafts" / "global_draft.md"
    draft.write_text("# 完整论文草稿\n\n第一次短稿。\n", encoding="utf-8")
    first = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "GLOBAL"], cwd)
    assert_true(first.returncode == 1, "first global length failure should block the draft")
    draft.write_text("# 完整论文草稿\n\n第二次仍然过短。\n", encoding="utf-8")
    second = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "GLOBAL"], cwd)
    assert_true(second.returncode == 1, "second repeated global failure should route to section mode")
    state = load_json(output / "context" / "authoring_state.json")
    assert_true(state["mode"] == "section", "global should fall back to section after two repeated categories")
    assert_true("GLOBAL" not in state["sections"] and "1" in state["sections"], "fallback should initialize section records")
    queue = load_json(output / "qa" / "repair_queue.json")
    assert_true(all(item["strategy"] == "section-rewrite" for item in queue["issues"]), "global fallback should request section rewrites")


def test_authoring_section_micro_repair_and_block() -> None:
    cwd, output = make_staged_scenario("scenario_authoring_repair_route", "S6")
    write_json(
        output / "plan" / "paper_outline.json",
        {
            "target_words": {"min": 100, "ideal": 7000, "max": 9000},
            "sections": [{"section_id": "1", "title": "问题重述", "target_words": 500}],
        },
    )
    result = run([sys.executable, str(PREPARE_AUTHORING), "--mode", "section"], cwd)
    assert_true(result.returncode == 0, f"section authoring should prepare\n{result.stdout}")
    draft = output / "drafts" / "sections" / "1.md"

    for attempt, body in enumerate(("第一次短稿", "第二次短稿", "第三次短稿"), start=1):
        draft.write_text(f"# 问题重述\n\n{body}。\n", encoding="utf-8")
        result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "1"], cwd)
        assert_true(result.returncode == 1, f"attempt {attempt} should fail the length gate")
        state = load_json(output / "context" / "authoring_state.json")
        queue = load_json(output / "qa" / "repair_queue.json")
        if attempt == 1:
            assert_true(state["status"] == "DRAFTING", "first failure should stay with section rewrite")
            assert_true(all(item["strategy"] == "section-rewrite" for item in queue["issues"]), "first failure should not use micro repair")
        elif attempt == 2:
            assert_true(state["status"] == "REPAIR_REQUIRED", "second repeated failure should require repair")
            assert_true(all(item["strategy"] == "micro-repair" for item in queue["issues"]), "second repeated failure should use micro repair")
            status = run([sys.executable, str(WORKFLOW_GUARD), "--status"], cwd)
            assert_true(status.returncode == 0, f"workflow status should remain diagnostic\n{status.stdout}")
            report = load_json(output / "qa" / "workflow_guard_report.json")
            assert_true(report["recommended_skill"] == "paper-micro-unit-generator", "guard should dynamically route queued micro repair")
        else:
            assert_true(state["status"] == "BLOCKED", "third repeated failure should block S7")
            status = run([sys.executable, str(WORKFLOW_GUARD), "--status"], cwd)
            report = load_json(output / "qa" / "workflow_guard_report.json")
            assert_true("Lite" in report["next_action"], "blocked S7 should explain the Lite option")


def test_authoring_evidence_assembly_and_hash_invalidation() -> None:
    cwd, output = make_staged_scenario("scenario_authoring_evidence", "S6")
    write_json(
        output / "plan" / "paper_outline.json",
        {
            "target_words": {"min": 120, "ideal": 300, "max": 800},
            "front_matter": {"abstract_target_words": 50},
            "sections": [
                {
                    "section_id": "1",
                    "title": "问题重述",
                    "question_id": "Q1",
                    "target_words": 180,
                    "required_evidence": [{"type": "metric", "name": "score", "value": 1.25}],
                    "required_tables": [{"table_id": "t1", "title": "结果表", "path": "paper_output/tables/t1.csv"}],
                }
            ],
        },
    )
    result = run([sys.executable, str(PREPARE_AUTHORING), "--mode", "section"], cwd)
    assert_true(result.returncode == 0, f"evidence authoring should prepare\n{result.stdout}")
    abstract = output / "drafts" / "sections" / "abstract.md"
    section = output / "drafts" / "sections" / "1.md"
    abstract.write_text("# 摘要\n\n本文围绕问题一建立可复核模型，说明输入、方法、计算结果及验证结论，并保持术语和符号一致。\n", encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "abstract"], cwd)
    assert_true(result.returncode == 0, f"abstract should pass\n{result.stdout}")

    section.write_text("# 问题重述\n\n本节完整说明题目目标、输入条件、约束边界和输出要求，但故意遗漏证据标记与指标数值。正文长度足以触发证据审计而不是长度审计。\n", encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "1"], cwd)
    assert_true(result.returncode == 1, "missing evidence marker and value should fail")
    audit = load_json(output / "qa" / "draft_audit.json")
    categories = {item["category"] for item in audit["issues"]}
    assert_true({"evidence-coverage", "numeric-evidence"}.issubset(categories), "S7 should report missing evidence and numeric value")

    section_text = "\n".join(
        [
            "# 问题重述",
            "",
            "<!-- mathmodel-evidence: metric:Q1:score, table:t1 -->",
            "题目要求在给定数据与边界约束下形成可复核结论。我们先统一字段口径，再明确决策对象、评价指标和输出格式。",
            "实际运行得到的 score 为 1.25，该数值用于核对模型输出与题目目标的一致性，详细结果见结果表 t1.csv。",
            "正文两次引用图1与见图1保持原编号，用于验证确定性合并不会按出现次数错误重排交叉引用。",
        ]
    )
    section.write_text(section_text, encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "1"], cwd)
    assert_true(result.returncode == 0, f"evidence-complete section should pass\n{result.stdout}")
    result = run([sys.executable, str(ASSEMBLE_SECTIONS)], cwd)
    assert_true(result.returncode == 0, f"assembly should pass\n{result.stdout}")
    assembled_path = output / "drafts" / "assembled_draft.md"
    assembled = assembled_path.read_text(encoding="utf-8")
    assert_true("mathmodel-evidence" not in assembled, "assembly should remove evidence markers")
    assert_true(assembled.count("图1") == 2 and "图2" not in assembled, "assembly should preserve repeated reference numbering")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--assembled"], cwd)
    assert_true(result.returncode == 0, f"assembled audit should pass\n{result.stdout}")

    final_path = output / "final_paper_source.md"
    final_path.write_text(assembled, encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--final"], cwd)
    assert_true(result.returncode == 1, "copy-only final should fail the global revision gate")
    final_path.write_text(assembled.rstrip() + "\n\n全文统一改写后，结论与问题目标形成闭环，并统一了术语、符号和章节过渡。\n", encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--final"], cwd)
    assert_true(result.returncode == 0, f"globally revised final should pass\n{result.stdout}")
    assert_true(load_json(output / "context" / "authoring_state.json")["status"] == "PASS", "final audit should set authoring PASS")

    section.write_text(section_text + "\n审计通过后发生的手工改动。\n", encoding="utf-8")
    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 2, "changed approved section should invalidate formal DOCX generation")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--final"], cwd)
    assert_true(result.returncode == 1, "changed approved section should invalidate final authoring PASS")


def test_authoring_rejects_formula_placeholder_duplicate_and_escape() -> None:
    cwd, output = make_staged_scenario("scenario_authoring_content_failures", "S6")
    write_json(
        output / "plan" / "paper_outline.json",
        {
            "target_words": {"min": 50, "ideal": 7000, "max": 9000},
            "sections": [{"section_id": "1", "title": "问题分析", "target_words": 80}],
        },
    )
    result = run([sys.executable, str(PREPARE_AUTHORING), "--mode", "section"], cwd)
    assert_true(result.returncode == 0, f"content failure scenario should prepare\n{result.stdout}")
    repeated = "该段落用于说明输入变量、目标函数、约束条件、边界范围、求解步骤、评价指标和验证口径，内容足够长以触发归一化重复检测并阻止机械扩写。"
    draft = output / "drafts" / "sections" / "1.md"
    draft.write_text(f"# 问题分析\n\n待补\n\n{repeated}\n\n{repeated}\n\n损坏公式 $x+1\n", encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "1"], cwd)
    assert_true(result.returncode == 1, "placeholder, duplicate, and malformed formula should fail")
    audit = load_json(output / "qa" / "draft_audit.json")
    categories = {item["category"] for item in audit["issues"]}
    assert_true({"placeholder", "duplicate-paragraph", "formula"}.issubset(categories), "S7 should report all three content failures")

    state_path = output / "context" / "authoring_state.json"
    state = load_json(state_path)
    state["sections"]["1"]["path"] = "paper_output\\drafts/sections\\中文稿.md"
    write_json(state_path, state)
    chinese_path = output / "drafts" / "sections" / "中文稿.md"
    chinese_path.write_text("# 问题分析\n\n本节完整说明问题目标、数据范围、模型变量、约束边界、求解过程、评价指标和验证方法，并解释结论如何回扣原始任务。\n", encoding="utf-8")
    result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "1"], cwd)
    assert_true(result.returncode == 0, f"mixed separators and Chinese paths should be accepted\n{result.stdout}")

    for invalid_path in ("../outside.md", "C:\\outside.md", "/tmp/outside.md"):
        state = load_json(state_path)
        state["sections"]["1"]["path"] = invalid_path
        write_json(state_path, state)
        result = run([sys.executable, str(VALIDATE_AUTHORING), "--section", "1"], cwd)
        assert_true(result.returncode == 1 and "inside the project root" in result.stdout, f"S7 should reject escaping path {invalid_path}")


def test_legacy_and_quickstart_outputs_are_isolated() -> None:
    cwd = SANDBOX / "scenario_legacy_isolation"
    if cwd.exists():
        shutil.rmtree(cwd)
    output = cwd / "paper_output"
    output.mkdir(parents=True)
    write_json(
        output / "tasks.json",
        [
            {"id": "U1", "section": "结果分析", "target_words": 20, "file_path": "paper_output/micro_units/U1.txt"},
            {"id": "U2", "section": "结果分析", "target_words": 20, "file_path": "paper_output/micro_units/U2.txt"},
        ],
    )
    result = run([sys.executable, str(GENERATE_LEGACY)], cwd)
    assert_true(result.returncode == 0, f"legacy generation should pass\n{result.stdout}")
    units = output / "drafts" / "legacy" / "micro_units"
    (units / "U1.txt").write_text("结果定义为图1，后文见图1；文献依据为[1]。\n", encoding="utf-8")
    (units / "U2.txt").write_text("复核仍引用图1与[1]，不得改成新的编号。\n", encoding="utf-8")
    result = run([sys.executable, str(MERGE_LEGACY)], cwd)
    assert_true(result.returncode == 0, f"legacy merge should pass\n{result.stdout}")
    legacy = output / "drafts" / "legacy"
    merged = (legacy / "legacy_scaffold.md").read_text(encoding="utf-8")
    assert_true("图2" not in merged and merged.count("图1") >= 3, "legacy merge should not renumber repeated references")
    assert_true((legacy / "legacy_scaffold.docx").exists(), "legacy Word should use a non-formal name")
    assert_true((legacy / "legacy_ref_check.md").exists(), "legacy reference report should stay in legacy output")
    for name in ("final_paper.md", "final_paper_source.md", "final_paper.docx", "final_paper_direct.docx"):
        assert_true(not (output / name).exists(), f"legacy scripts must not create {name}")

    result = run([sys.executable, str(GENERATE_LEGACY), "--output-root", "../escape"], cwd)
    assert_true(result.returncode == 2, "legacy output root must reject path traversal")
    result = run([sys.executable, str(GENERATE_LEGACY), "--output-root", "paper_output/quickstart"], cwd)
    assert_true(result.returncode == 0, f"quickstart generation should write directly to its directory\n{result.stdout}")
    result = run(
        [sys.executable, str(MERGE_LEGACY), "--output-root", "paper_output/quickstart", "--stem", "quickstart_scaffold"],
        cwd,
    )
    assert_true(result.returncode == 0, f"quickstart merge should pass\n{result.stdout}")
    assert_true((output / "quickstart" / "quickstart_scaffold.md").exists(), "quickstart Markdown should be created directly")
    assert_true((output / "quickstart" / "quickstart_scaffold.docx").exists(), "quickstart Word should be created directly")


def test_format_gate() -> None:
    cwd = SANDBOX / "scenario_4_suspicious_template"
    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode != 0, "format_formal_docx should block without evidence gate")
    assert_true(not (cwd / "paper_output" / "final_paper.docx").exists(), "formal docx should not be created without gate")

    result = run([sys.executable, str(FORMAT_DOCX), "--allow-draft"], cwd)
    assert_true(result.returncode == 0, f"draft format should pass\n{result.stdout}")
    assert_true((cwd / "paper_output" / "final_paper_draft.docx").exists(), "draft docx should be created")
    assert_true(not (cwd / "paper_output" / "final_paper.docx").exists(), "draft mode must not create formal docx")


def test_format_formal_docx_after_evidence_gate() -> None:
    cwd = SANDBOX / "scenario_format_formal_gate_pass"
    if cwd.exists():
        shutil.rmtree(cwd)
    output = cwd / "paper_output"
    output.mkdir(parents=True)
    source = "\n".join(
            [
                "# Title",
                "",
                "# 摘要",
                "This is a formal gated draft generated after evidence gate pass.",
                "",
                "# 1 问题重述",
                "Problem restatement.",
                "",
                "# 5.1 问题一模型",
                "Model section.",
            ]
    )
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")
    write_json(output / "plan" / "paper_outline.json", {"target_words": {"min": 20, "max": 5000}, "questions": []})
    write_fresh_gate_report(output)
    prepare_authoring_pass(cwd, output, source)

    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 0, f"formal docx should be generated after evidence gate PASS\n{result.stdout}")
    assert_true((output / "final_paper.docx").exists(), "formal final_paper.docx should be created after gate PASS")
    assert_true(not (output / "final_paper_draft.docx").exists(), "formal mode should not create draft docx")


def test_check_paper_format_passes_complete_docx() -> None:
    cwd = SANDBOX / "scenario_format_check_pass"
    if cwd.exists():
        shutil.rmtree(cwd)
    output = cwd / "paper_output"
    output.mkdir(parents=True)
    write_json(output / "plan" / "paper_outline.json", {"target_words": {"min": 100, "max": 5000}, "questions": [{"question_id": "Q1"}]})
    write_json(output / "figure_index.json", {"figures": []})
    write_json(output / "tables" / "table_index.json", {"tables": []})
    source = complete_paper_source()
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")
    write_fresh_gate_report(output)
    prepare_authoring_pass(cwd, output, source)

    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 0, f"formal docx generation should pass\n{result.stdout}")
    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "skip"], cwd)
    assert_true(result.returncode == 0, f"format check should PASS for complete docx\n{result.stdout}")
    report = load_json(output / "format_check_report.json")
    assert_true(report["status"] == "PASS", "complete format report should PASS")
    assert_true(report["visual_qa"]["status"] == "PASS", "complete docx visual QA should PASS")
    assert_true(report["docx_structure"]["heading_count"] > 0, "complete docx should contain heading styles")
    assert_true(report["formula_qa"]["source_formula_count"] >= 5, "source formulas should be counted")
    assert_true(report["formula_qa"]["native_omml_count"] >= report["formula_qa"]["source_formula_count"], "every source formula should become native Word math")
    assert_true(report["citation_qa"]["body_citation_count"] >= 3, "body citations should be counted separately from bibliography entries")
    assert_true(report["input_hashes"], "format report should record input hashes for freshness checks")


def test_format_gate_rejects_control_characters() -> None:
    source = complete_paper_source(extra_body=["该公式被错误转义为控制字符：\x0crac 与 \x08ar，必须被门禁识别。"])
    cwd, output = prepare_formal_paper_scenario("scenario_control_characters", complete_paper_source())
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")

    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "skip"], cwd)
    assert_true(result.returncode == 1, "format gate should reject control characters in source markdown")
    report = load_json(output / "format_check_report.json")
    assert_true(any("控制字符" in item for item in report["failures"]), "control-character failure should be explicit")


def test_format_gate_rejects_numeric_padding_duplicates() -> None:
    repeated = [
        "在第 1 轮稳健性检验中，我们重新计算全部策略，并比较目标值、约束满足率与排序变化，从而判断结论是否稳定。",
        "在第 27 轮稳健性检验中，我们重新计算全部策略，并比较目标值、约束满足率与排序变化，从而判断结论是否稳定。",
    ]
    cwd, output = prepare_formal_paper_scenario("scenario_duplicate_padding", complete_paper_source())
    (output / "final_paper_source.md").write_text(complete_paper_source(extra_body=repeated), encoding="utf-8")

    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "skip"], cwd)
    assert_true(result.returncode == 1, "format gate should reject number-swapped duplicate padding")
    report = load_json(output / "format_check_report.json")
    assert_true(any("重复段落" in item for item in report["failures"]), "duplicate-padding failure should identify repeated paragraphs")


def test_format_gate_rejects_internal_project_language() -> None:
    source = complete_paper_source(extra_body=["本样例通过 paper_output/qa/evidence_gate.py 一键生成正式论文。"])
    cwd, output = prepare_formal_paper_scenario("scenario_internal_language", complete_paper_source())
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")

    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "skip"], cwd)
    assert_true(result.returncode == 1, "format gate should reject internal project language before the appendix")
    report = load_json(output / "format_check_report.json")
    assert_true(any("内部工程话术" in item for item in report["failures"]), "internal-language failure should be explicit")


def test_format_gate_requires_body_citations() -> None:
    cwd, output = prepare_formal_paper_scenario("scenario_missing_body_citations", complete_paper_source())
    (output / "final_paper_source.md").write_text(complete_paper_source(include_body_citations=False), encoding="utf-8")

    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "skip"], cwd)
    assert_true(result.returncode == 1, "format gate should reject a bibliography that is never cited in the body")
    report = load_json(output / "format_check_report.json")
    assert_true(any("正文没有文献引用" in item for item in report["failures"]), "missing body citations should be explicit")


def test_formal_formatter_blocks_invalid_latex_but_allows_draft_fallback() -> None:
    cwd, output = prepare_formal_paper_scenario("scenario_invalid_latex", complete_paper_source())
    (output / "final_paper.docx").unlink()
    source = complete_paper_source(extra_body=[r"该处故意放入损坏公式 $\left($ 以验证正式门禁。"])
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")

    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 2, f"formal formatter should block a source changed after S7 PASS\n{result.stdout}")
    assert_true(not (output / "final_paper.docx").exists(), "invalid LaTeX must not produce a formal Word file")

    result = run([sys.executable, str(FORMAT_DOCX), "--allow-draft"], cwd)
    assert_true(result.returncode == 0, f"draft fallback should preserve invalid LaTeX as text\n{result.stdout}")
    assert_true((output / "final_paper_draft.docx").exists(), "draft fallback should write final_paper_draft.docx")
    assert_true(not (output / "final_paper.docx").exists(), "draft fallback must not contaminate the formal output")


def test_formal_formatter_rejects_stale_evidence_gate() -> None:
    cwd, output = prepare_formal_paper_scenario("scenario_stale_gate_before_format", complete_paper_source())
    (output / "final_paper.docx").unlink()
    marker = output / "qa" / "evidence_gate_test_input.json"
    write_json(marker, {"status": "changed_after_gate"})

    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 2, "formal formatter should reject a stale PASS evidence report")
    assert_true(not (output / "final_paper.docx").exists(), "stale evidence must not produce a formal Word file")


def test_render_required_when_libreoffice_is_available() -> None:
    candidates = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
    ]
    if not any(candidate and Path(candidate).is_file() for candidate in candidates):
        return
    cwd, output = prepare_formal_paper_scenario("scenario_render_required", complete_paper_source())

    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "required"], cwd)
    assert_true(result.returncode == 0, f"required render QA should pass with LibreOffice available\n{result.stdout}")
    report = load_json(output / "format_check_report.json")
    assert_true(report["render_qa"]["status"] == "PASS", "required render QA should report PASS")
    assert_true(report["render_qa"]["page_count"] >= 1, "rendered PDF should contain at least one page")
    assert_true(report["render_qa"]["extracted_text_chars"] >= 20, "rendered PDF should contain extractable text")


def test_docx_visual_qa() -> None:
    from docx import Document

    cwd = SANDBOX / "scenario_docx_visual_qa"
    if cwd.exists():
        shutil.rmtree(cwd)
    output = cwd / "paper_output"
    output.mkdir(parents=True)

    source = "\n".join(
        [
            "# 摘要",
            "# 1 问题重述",
            "# 2 问题分析",
            "# 5.1 问题一模型",
            "analysiscontent" * 160,
        ]
    )
    (output / "final_paper_source.md").write_text(source, encoding="utf-8")
    write_json(output / "plan" / "paper_outline.json", {"target_words": {"min": 10, "max": 5000}, "questions": []})
    write_json(output / "figure_index.json", {"figures": [{"figure_id": "fig1", "title": "figure one", "path": "paper_output/figures/fig1.png"}]})
    write_json(output / "tables" / "table_index.json", {"tables": [{"table_id": "tab1", "title": "table one", "path": "paper_output/tables/tab1.csv"}]})

    doc = Document()
    doc.add_paragraph("too short body only")
    doc.save(output / "final_paper.docx")

    result = run([sys.executable, str(CHECK_PAPER_FORMAT), "--render", "skip"], cwd)
    assert_true(result.returncode == 1, f"format check should fail weak DOCX visual QA\n{result.stdout}")
    report = load_json(output / "format_check_report.json")
    assert_true(report["docx_structure"]["package_ok"] is True, "DOCX package should be readable")
    assert_true(report["docx_structure"]["nonspace_text_chars"] > 0, "DOCX text payload should be measured")
    failures = "\n".join(report["visual_qa"]["failures"])
    assert_true("DOCX text payload is too small" in failures, "visual QA should fail tiny DOCX text payload")
    assert_true("No Word heading styles" in failures, "visual QA should fail missing Word heading styles")
    assert_true("figure_index has figures but DOCX has no inline images" in failures, "visual QA should fail missing indexed figures")
    assert_true("table_index has tables but DOCX has no tables" in failures, "visual QA should fail missing indexed tables")


def test_modeling_run_manifest() -> None:
    cwd = SANDBOX / "scenario_7_real_data"
    output = cwd / "paper_output"
    write_json(
        output / "plan" / "model_route.json",
        {"questions": [{"question_id": "Q1", "title": "问题一", "task_type": "预测/回归", "main_model": "线性基线"}]},
    )
    write_json(output / "plan" / "data_plan.json", {"datasets": [{"path": "paper_output/data_cleaned/sample_cleaned.csv"}]})
    write_json(output / "plan" / "visualization_plan.json", {"figures": []})
    (output / "data_cleaned").mkdir(parents=True, exist_ok=True)
    (output / "data_cleaned" / "sample_cleaned.csv").write_text("x,y\n1,2\n2,4\n3,6\n4,8\n", encoding="utf-8")

    result = run([sys.executable, str(BUILD_RESULT_CONTRACTS)], cwd)
    assert_true(result.returncode == 0, f"build_result_contracts should pass\n{result.stdout}")
    runner = output / "code" / "modeling" / "run_modeling.py"
    result = run([sys.executable, str(runner)], cwd)
    assert_true(result.returncode == 0, f"run_modeling should pass\n{result.stdout}")

    manifest = load_json(output / "results" / "run_manifest.json")
    assert_true(manifest["status"] == "PASS", "run_manifest status should PASS")
    assert_true(len(manifest["runs"]) >= 1, "run_manifest should contain at least one run")
    first_run = manifest["runs"][0]
    assert_true("Q1" in first_run["question_ids"], "run_manifest should link the run to Q1")
    assert_true(first_run["input_files"], "run_manifest should record hashed input files")
    assert_true(first_run["output_artifacts"], "run_manifest should record output artifacts")


def test_evidence_gate_passes_for_computed_run() -> None:
    cwd = SANDBOX / "scenario_9_computed_run"
    if cwd.exists():
        shutil.rmtree(cwd)
    output = cwd / "paper_output"
    output.mkdir(parents=True)
    write_json(output / "plan" / "model_route.json", {"questions": [{"question_id": "Q1", "title": "question one", "task_type": "baseline", "main_model": "computed baseline"}]})
    write_json(output / "plan" / "data_plan.json", {"datasets": [{"path": "paper_output/data_cleaned/sample_cleaned.csv"}]})
    write_json(output / "plan" / "visualization_plan.json", {"figures": []})
    write_json(output / "figure_index.json", {"figures": []})
    (output / "data_cleaned").mkdir(parents=True, exist_ok=True)
    (output / "data_cleaned" / "sample_cleaned.csv").write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")

    result = run([sys.executable, str(BUILD_RESULT_CONTRACTS)], cwd)
    assert_true(result.returncode == 0, f"build_result_contracts should create runner\n{result.stdout}")
    q1_model = output / "code" / "modeling" / "q1_model.py"
    q1_model.write_text(
        """
from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = PROJECT_ROOT / "paper_output"
(OUTPUT / "results").mkdir(parents=True, exist_ok=True)
(OUTPUT / "tables").mkdir(parents=True, exist_ok=True)
(OUTPUT / "tables" / "q1_table.csv").write_text("metric,value\\nscore,1.0\\n", encoding="utf-8")

provenance = {
    "source_code_path": "paper_output/code/modeling/q1_model.py",
    "run_command": "python paper_output/code/modeling/q1_model.py",
    "run_exit_code": 0,
    "output_artifacts": ["paper_output/tables/q1_table.csv"],
}
(OUTPUT / "results" / "model_results.json").write_text(json.dumps({
    "questions": [{
        "question_id": "Q1",
        "status": "computed",
        "evidence_status": "computed",
        "result_summary": "computed result from q1_model.py",
        "execution_provenance": provenance,
    }]
}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUTPUT / "results" / "metrics.json").write_text(json.dumps({
    "items": [{"question_id": "Q1", "status": "computed", "metric_name": "score", "value": 1.0}]
}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUTPUT / "results" / "conclusions.json").write_text(json.dumps({
    "items": [{"question_id": "Q1", "status": "computed", "conclusion_text": "computed conclusion answers Q1"}]
}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUTPUT / "tables" / "table_index.json").write_text(json.dumps({
    "tables": [{"question_id": "Q1", "status": "computed", "table_id": "t1", "path": "paper_output/tables/q1_table.csv"}]
}, ensure_ascii=False, indent=2), encoding="utf-8")
(OUTPUT / "tasks.json").write_text(json.dumps([{"question_id": "Q1", "task": "computed"}], ensure_ascii=False, indent=2), encoding="utf-8")
print("computed Q1")
""".lstrip(),
        encoding="utf-8",
    )

    runner = output / "code" / "modeling" / "run_modeling.py"
    result = run([sys.executable, str(runner)], cwd)
    assert_true(result.returncode == 0, f"run_modeling should pass for computed model\n{result.stdout}")
    manifest = load_json(output / "results" / "run_manifest.json")
    assert_true(manifest["status"] == "PASS", "computed run_manifest should PASS")
    assert_true(manifest["runs"][0]["output_artifacts"][0]["exists"] is True, "run_manifest should confirm output artifact exists")

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 0, f"evidence gate should pass for computed run\n{result.stdout}")
    gate_report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(gate_report["status"] == "PASS", "computed evidence gate should PASS")


def test_evidence_gate_requires_run_manifest() -> None:
    cwd = SANDBOX / "scenario_8_missing_run_manifest"
    output = cwd / "paper_output"
    (output / "code" / "modeling").mkdir(parents=True, exist_ok=True)
    (output / "code" / "modeling" / "q1_model.py").write_text("print('computed')\n", encoding="utf-8")
    (output / "tables").mkdir(parents=True, exist_ok=True)
    (output / "tables" / "q1_table.csv").write_text("metric,value\nscore,1\n", encoding="utf-8")
    write_json(output / "plan" / "model_route.json", {"questions": [{"question_id": "Q1", "title": "问题一"}]})
    write_json(output / "figure_index.json", {"figures": []})
    write_json(
        output / "results" / "model_results.json",
        {
            "questions": [
                {
                    "question_id": "Q1",
                    "status": "computed",
                    "evidence_status": "computed",
                    "execution_provenance": {
                        "source_code_path": "paper_output/code/modeling/q1_model.py",
                        "run_command": "python paper_output/code/modeling/q1_model.py",
                        "run_exit_code": 0,
                        "output_artifacts": ["paper_output/tables/q1_table.csv"],
                    },
                }
            ]
        },
    )
    write_json(output / "results" / "metrics.json", {"items": [{"question_id": "Q1", "status": "computed", "metric_name": "score", "value": 1}]})
    write_json(output / "results" / "conclusions.json", {"items": [{"question_id": "Q1", "status": "computed", "conclusion_text": "结论可回扣原题。"}]})
    write_json(output / "tables" / "table_index.json", {"tables": [{"question_id": "Q1", "status": "computed", "table_id": "t1", "path": "paper_output/tables/q1_table.csv"}]})
    write_json(output / "tasks.json", [{"question_id": "Q1", "task": "verify"}])

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 1, "evidence_gate should fail without run_manifest.json")
    report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(any("run_manifest" in item for item in report["failures"]), "evidence gate failures should mention run_manifest")


def test_workflow_guard_rejects_modified_input_after_preflight() -> None:
    cwd, output = make_preflighted_scenario("scenario_modified_input")
    (cwd / "problem_files" / "data.csv").write_text("x,y\n1,2\n2,999\n", encoding="utf-8")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S0"], cwd)
    assert_true(result.returncode == 1, "workflow guard should reject input modified after preflight")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(any("内容已变化" in item for item in report["failures"]), "modified input failure should mention changed content")


def test_integrity_gates_reject_modified_modeling_script() -> None:
    cwd, output = make_staged_scenario("scenario_modified_script", "S5")
    script = output / "code" / "modeling" / "q1_model.py"
    script.write_text(script.read_text(encoding="utf-8") + "print('changed')\n", encoding="utf-8")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S5"], cwd)
    assert_true(result.returncode == 1, "workflow guard should reject a modeling script modified after execution")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(any("脚本在运行后已变化" in item for item in report["failures"]), "workflow failure should identify changed script")

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 1, "evidence gate should reject a modeling script modified after execution")
    report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(any("脚本在运行后已变化" in item or "source_code_path 内容已变化" in item for item in report["failures"]), "evidence failure should identify changed script")


def test_evidence_gate_rejects_modified_output_after_run() -> None:
    cwd, output = make_staged_scenario("scenario_modified_output", "S5")
    table = output / "tables" / "t1.csv"
    table.write_text(table.read_text(encoding="utf-8") + "changed,999\n", encoding="utf-8")

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 1, "evidence gate should reject an output modified after the recorded run")
    report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(any("运行输出" in item and "变化" in item for item in report["failures"]), "modified output failure should mention changed run output")


def test_evidence_gate_rejects_placeholder_figure() -> None:
    cwd, output = make_staged_scenario("scenario_placeholder_figure", "S5")
    figure = output / "figures" / "placeholder.png"
    figure.parent.mkdir(parents=True, exist_ok=True)
    figure.write_bytes(b"placeholder")
    write_json(
        output / "figure_index.json",
        {
            "figures": [
                {
                    "question_id": "Q1",
                    "figure_id": "fig_placeholder",
                    "status": "placeholder",
                    "placeholder": True,
                    "ok": False,
                    "path": "paper_output/figures/placeholder.png",
                    "message": "placeholder: no usable source data",
                }
            ]
        },
    )

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 1, "evidence gate should reject placeholder figures")
    report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(any("占位" in item for item in report["failures"]), "placeholder figure failure should be explicit")


def test_evidence_gate_rejects_empty_table_file() -> None:
    cwd, output = make_staged_scenario("scenario_empty_table", "S5")
    (output / "tables" / "t1.csv").write_bytes(b"")

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 1, "evidence gate should reject an empty indexed table")
    report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(any("表格 t1 文件为空" in item for item in report["failures"]), "empty table failure should identify the indexed table")


def test_evidence_gate_rejects_computed_metric_without_value() -> None:
    cwd, output = make_staged_scenario("scenario_empty_metric", "S5")
    write_json(
        output / "results" / "metrics.json",
        {"items": [{"question_id": "Q1", "status": "computed", "metric_name": "score", "value": None}]},
    )

    result = run([sys.executable, str(EVIDENCE_GATE)], cwd)
    assert_true(result.returncode == 1, "evidence gate should reject a computed metric with no value")
    report = load_json(output / "qa" / "evidence_gate_report.json")
    assert_true(any("指标 score 缺少有效 value" in item for item in report["failures"]), "empty metric failure should name the metric")


def test_workflow_guard_rejects_stale_evidence_report() -> None:
    cwd, output = make_staged_scenario("scenario_stale_evidence", "S6")
    metrics = load_json(output / "results" / "metrics.json")
    metrics["items"][0]["value"] = 2
    write_json(output / "results" / "metrics.json", metrics)

    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S6"], cwd)
    assert_true(result.returncode == 1, "workflow guard should reject a stale evidence report")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(any("报告已过期" in item for item in report["failures"]), "stale evidence failure should require re-running the gate")


def test_workflow_guard_rejects_stale_format_report() -> None:
    cwd, output = make_staged_scenario("scenario_stale_format_report", "S8")
    source = output / "final_paper_source.md"
    source.write_text(source.read_text(encoding="utf-8") + "\nchanged after format check\n", encoding="utf-8")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S8"], cwd)
    assert_true(result.returncode == 1, "workflow guard should reject a stale format report")
    report = load_json(output / "qa" / "workflow_guard_report.json")
    assert_true(any("格式门禁报告已过期" in item for item in report["failures"]), "stale format failure should require re-running the format gate")


def test_skill_docs_have_workflow_guard_contract() -> None:
    expected = {
        "authoritative-data-harvester",
        "context-memory-keeper",
        "data-cleaning-and-visualization",
        "model-code-and-result-generator",
        "modeling-paper-rubric-and-model-selector",
        "paper-formal-writer",
        "paper-micro-unit-generator",
        "paper-workflow-orchestrator",
        "problem-doc-model-selector",
        "quality-assurance-auditor",
    }
    for skill in sorted(expected):
        text = (CLAUDE_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        assert_true("workflow_guard.py" in text, f"{skill} should use the workflow guard")
        if skill != "paper-workflow-orchestrator":
            assert_true(f"workflow_guard.py --skill {skill}" in text, f"{skill} should call workflow guard with its own skill name")
        assert_true("workflow_guard.py --status" in text, f"{skill} should include workflow status recovery command")
        assert_true("paper_output/context/workflow_memory.json" in text, f"{skill} should read workflow memory snapshots")
        assert_true("update_workflow_memory.py" in text, f"{skill} should update workflow memory snapshots after handoff")


def test_skill_docs_are_readable() -> None:
    bad_fragments = ["??", "\ufffd", "杩", "缂", "鏂", "閫", "寤", "妯", "璇", "棰"]
    for root in (CLAUDE_SKILLS, CODEX_SKILLS, TRAE_SKILLS):
        for skill_doc in sorted(root.glob("*/SKILL.md")):
            text = skill_doc.read_text(encoding="utf-8")
            rel = skill_doc.relative_to(REPO_ROOT).as_posix()
            for fragment in bad_fragments:
                assert_true(fragment not in text, f"{rel} contains unreadable fragment: {fragment}")


def test_release_packages_are_isolated_and_deterministic() -> None:
    first = SANDBOX / "release-build-a"
    second = SANDBOX / "release-build-b"
    for target in (first, second):
        result = run([sys.executable, str(BUILD_PACKAGES), "--output-dir", str(target)], REPO_ROOT)
        assert_true(result.returncode == 0, f"release package build should pass\n{result.stdout}")
        result = run([sys.executable, str(BUILD_PACKAGES), "--verify", "--output-dir", str(target)], REPO_ROOT)
        assert_true(result.returncode == 0, f"release package verification should pass\n{result.stdout}")

    archives = {
        "Codex": "MathModel-Skill-Codex.zip",
        "Claude": "MathModel-Skill-Claude-Code.zip",
        "Trae": "MathModel-Skill-Trae.zip",
    }
    for name in archives.values():
        assert_true((first / name).read_bytes() == (second / name).read_bytes(), f"{name} should be byte-for-byte deterministic")
    assert_true((first / "SHA256SUMS.txt").read_bytes() == (second / "SHA256SUMS.txt").read_bytes(), "checksum manifests should be deterministic")

    with zipfile.ZipFile(first / archives["Codex"]) as archive:
        names = set(archive.namelist())
        assert_true(any(path.startswith(".agents/skills/") for path in names), "Codex archive should use .agents/skills")
        assert_true(not any(path.startswith("skills/") for path in names), "Codex archive should not retain legacy skills root")
        assert_true(".agents/skills/paper-workflow-orchestrator/MATHMODEL_EDITION.json" in names, "Codex archive should contain edition marker")
        assert_true("AGENTS.md" not in names and "CLAUDE.md" not in names, "Codex archive should not overwrite root instructions")
        assert_true(archive.read("VERSION").decode("utf-8").strip() == "2.2.0", "Codex archive should report Standard 2.2.0")
    with zipfile.ZipFile(first / archives["Claude"]) as archive:
        names = set(archive.namelist())
        assert_true(".claude/skills/paper-workflow-orchestrator/MATHMODEL_EDITION.json" in names, "Claude archive should contain edition marker")
        assert_true("CLAUDE.md" not in names and "AGENTS.md" not in names, "Claude archive should not overwrite root instructions")
    with zipfile.ZipFile(first / archives["Trae"]) as archive:
        names = set(archive.namelist())
        assert_true(".trae/skills/paper-workflow-orchestrator/MATHMODEL_EDITION.json" in names, "Trae archive should contain edition marker")
        assert_true("CLAUDE.md" not in names and "AGENTS.md" not in names, "Trae archive should not overwrite root instructions")


def test_platform_packages_stay_synced() -> None:
    for claude_skill in sorted(CLAUDE_SKILLS.glob("*/SKILL.md")):
        skill = claude_skill.parent.name
        claude_text = claude_skill.read_text(encoding="utf-8")
        codex_text = (CODEX_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        trae_text = (TRAE_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        assert_true(codex_text == claude_text.replace(".claude/skills", ".agents/skills"), f"codex SKILL.md drift: {skill}")
        assert_true(trae_text == claude_text.replace(".claude/skills", ".trae/skills"), f"trae SKILL.md drift: {skill}")

    def tracked_payload_files(root: Path) -> set[Path]:
        result = set()
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if "__pycache__" in rel.parts or "agents" in rel.parts or rel.name == "SKILL.md":
                continue
            result.add(rel)
        return result

    claude_payloads = tracked_payload_files(CLAUDE_SKILLS)
    assert_true(tracked_payload_files(CODEX_SKILLS) == claude_payloads, "codex payload file set should match claude")
    assert_true(tracked_payload_files(TRAE_SKILLS) == claude_payloads, "trae payload file set should match claude")

    for rel in sorted(claude_payloads):
        claude_path = CLAUDE_SKILLS / rel
        codex_path = CODEX_SKILLS / rel
        trae_path = TRAE_SKILLS / rel
        try:
            claude_text = claude_path.read_text(encoding="utf-8-sig")
            codex_text = codex_path.read_text(encoding="utf-8-sig")
            trae_text = trae_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            claude_bytes = claude_path.read_bytes()
            assert_true(codex_path.read_bytes() == claude_bytes, f"codex binary payload drift: {rel}")
            assert_true(trae_path.read_bytes() == claude_bytes, f"trae binary payload drift: {rel}")
            continue
        assert_true(codex_text == claude_text.replace(".claude/skills", ".agents/skills"), f"codex payload drift: {rel}")
        assert_true(trae_text == claude_text.replace(".claude/skills", ".trae/skills"), f"trae payload drift: {rel}")


def main() -> int:
    setup_sandbox.main()
    tests = [
        test_preflight,
        test_preflight_detects_modern_and_legacy_mixed_installations,
        test_missing_pypdf,
        test_robust_loader_and_workflow_guard,
        test_orchestrator_guard_allows_fresh_entry,
        test_codex_package_smoke,
        test_trae_package_smoke,
        test_workflow_status_after_code_generation,
        test_workflow_status_recovery_across_stages,
        test_workflow_memory_snapshot,
        test_workflow_status_complete_after_s8,
        test_authoring_auto_modes_and_global_fallback,
        test_authoring_section_micro_repair_and_block,
        test_authoring_evidence_assembly_and_hash_invalidation,
        test_authoring_rejects_formula_placeholder_duplicate_and_escape,
        test_legacy_and_quickstart_outputs_are_isolated,
        test_format_gate,
        test_format_formal_docx_after_evidence_gate,
        test_check_paper_format_passes_complete_docx,
        test_format_gate_rejects_control_characters,
        test_format_gate_rejects_numeric_padding_duplicates,
        test_format_gate_rejects_internal_project_language,
        test_format_gate_requires_body_citations,
        test_formal_formatter_blocks_invalid_latex_but_allows_draft_fallback,
        test_formal_formatter_rejects_stale_evidence_gate,
        test_render_required_when_libreoffice_is_available,
        test_docx_visual_qa,
        test_modeling_run_manifest,
        test_evidence_gate_passes_for_computed_run,
        test_evidence_gate_requires_run_manifest,
        test_workflow_guard_rejects_modified_input_after_preflight,
        test_integrity_gates_reject_modified_modeling_script,
        test_evidence_gate_rejects_modified_output_after_run,
        test_evidence_gate_rejects_placeholder_figure,
        test_evidence_gate_rejects_empty_table_file,
        test_evidence_gate_rejects_computed_metric_without_value,
        test_workflow_guard_rejects_stale_evidence_report,
        test_workflow_guard_rejects_stale_format_report,
        test_skill_docs_have_workflow_guard_contract,
        test_skill_docs_are_readable,
        test_release_packages_are_isolated_and_deterministic,
        test_platform_packages_stay_synced,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

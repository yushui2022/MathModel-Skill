from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import setup_sandbox


REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX = REPO_ROOT / "tests" / "sandbox"
PREFLIGHT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-workflow-orchestrator" / "scripts" / "preflight_check.py"
WORKFLOW_GUARD = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-workflow-orchestrator" / "scripts" / "workflow_guard.py"
ROBUST_LOADER = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "data-cleaning-and-visualization" / "scripts" / "robust_loader.py"
BUILD_RESULT_CONTRACTS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "model-code-and-result-generator" / "scripts" / "build_result_contracts.py"
EVIDENCE_GATE = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "quality-assurance-auditor" / "scripts" / "evidence_gate.py"
FORMAT_DOCX = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "format_formal_docx.py"
CHECK_PAPER_FORMAT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "check_paper_format.py"
UPDATE_WORKFLOW_MEMORY = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "context-memory-keeper" / "scripts" / "update_workflow_memory.py"
CLAUDE_SKILLS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills"
CODEX_SKILLS = REPO_ROOT / "packages" / "codex" / "skills"
TRAE_SKILLS = REPO_ROOT / "packages" / "trae" / ".trae" / "skills"


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


def make_preflighted_scenario(name: str) -> tuple[Path, Path]:
    cwd = SANDBOX / name
    if cwd.exists():
        shutil.rmtree(cwd)
    problem_files = cwd / "problem_files"
    problem_files.mkdir(parents=True)
    (problem_files / "problem.md").write_text("Build a reproducible baseline model for question one.\n", encoding="utf-8")
    (problem_files / "data.csv").write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    result = run([sys.executable, str(PREFLIGHT)], cwd)
    assert_true(result.returncode == 0, f"{name}: preflight should pass\n{result.stdout}")
    return cwd, cwd / "paper_output"


def stage_workflow(output: Path, through_step: str) -> None:
    order = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    limit = order.index(through_step)
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
        write_json(output / "data_cleaned" / "load_report.json", {"status": "PASS", "input_manifest_used": True, "summary": {"readable_data_file_count": 1}})
    if limit >= order.index("S4"):
        (output / "code" / "modeling").mkdir(parents=True, exist_ok=True)
        (output / "code" / "modeling" / "q1_model.py").write_text("print('model ready')\n", encoding="utf-8")
        (output / "code" / "modeling" / "run_modeling.py").write_text("print('runner ready')\n", encoding="utf-8")
    if limit >= order.index("S5"):
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
                            "run_exit_code": 0,
                        },
                    }
                ]
            },
        )
        write_json(output / "results" / "run_manifest.json", {"runs": [{"script": "paper_output/code/modeling/q1_model.py", "question_ids": ["Q1"], "returncode": 0}]})
        write_json(output / "results" / "metrics.json", {"items": [{"question_id": "Q1", "status": "computed", "metric_name": "score", "value": 1}]})
        write_json(output / "results" / "conclusions.json", {"items": [{"question_id": "Q1", "status": "computed", "conclusion_text": "conclusion"}]})
        write_json(output / "tables" / "table_index.json", {"tables": [{"question_id": "Q1", "status": "computed", "table_id": "t1", "path": "paper_output/tables/t1.csv"}]})
    if limit >= order.index("S6"):
        write_json(output / "qa" / "evidence_gate_report.json", {"status": "PASS", "failures": []})
    if limit >= order.index("S7"):
        from docx import Document

        write_json(output / "plan" / "paper_outline.json", {"target_words": {"min": 10, "max": 5000}, "questions": [{"question_id": "Q1"}]})
        (output / "final_paper_source.md").write_text("# Title\n\n# 1 Problem Restatement\n\nFormal content.\n", encoding="utf-8")
        doc = Document()
        doc.add_heading("Title", level=1)
        doc.add_paragraph("Formal content.")
        doc.save(output / "final_paper.docx")
    if limit >= order.index("S8"):
        write_json(output / "format_check_report.json", {"status": "PASS", "failures": []})


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

    write_json(output / "step1" / "problem_analysis.json", {"questions": [{"question_id": "Q1", "title": "question one"}]})
    write_json(output / "plan" / "model_route.json", {"questions": [{"question_id": "Q1", "title": "question one", "main_model": "baseline"}]})
    write_json(output / "plan" / "rubric_alignment.json", {"status": "PASS", "items": [{"question_id": "Q1"}]})
    (output / "plan" / "scoring_strategy.md").write_text("score by reproducible modeling evidence\n", encoding="utf-8")
    write_json(output / "plan" / "data_plan.json", {"datasets": [{"path": "paper_output/data_cleaned/sample_cleaned.csv"}]})
    write_json(output / "plan" / "visualization_plan.json", {"figures": []})
    write_json(output / "figure_index.json", {"figures": []})
    write_json(output / "data_cleaned" / "load_report.json", {"status": "PASS", "input_manifest_used": True, "summary": {"readable_data_file_count": 1}})
    (output / "code" / "modeling").mkdir(parents=True, exist_ok=True)
    (output / "code" / "modeling" / "q1_model.py").write_text("print('model ready')\n", encoding="utf-8")
    (output / "code" / "modeling" / "run_modeling.py").write_text("print('runner ready')\n", encoding="utf-8")

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
    write_json(output / "qa" / "evidence_gate_report.json", {"status": "PASS", "failures": []})
    (output / "final_paper_source.md").write_text(
        "\n".join(
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
        ),
        encoding="utf-8",
    )

    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode == 0, f"formal docx should be generated after evidence gate PASS\n{result.stdout}")
    assert_true((output / "final_paper.docx").exists(), "formal final_paper.docx should be created after gate PASS")
    assert_true(not (output / "final_paper_draft.docx").exists(), "formal mode should not create draft docx")


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

    result = run([sys.executable, str(CHECK_PAPER_FORMAT)], cwd)
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
        assert_true("## 全局流程协作约束（长对话防漂移）" in text, f"{skill} should include global workflow contract")
        assert_true(f"workflow_guard.py --skill {skill}" in text, f"{skill} should call workflow guard with its own skill name")
        assert_true("workflow_guard.py --status" in text, f"{skill} should include workflow status recovery command")
        assert_true("paper_output/context/workflow_memory.json" in text, f"{skill} should read workflow memory snapshots")
        assert_true("update_workflow_memory.py" in text, f"{skill} should update workflow memory snapshots after handoff")


def test_platform_packages_stay_synced() -> None:
    for claude_skill in sorted(CLAUDE_SKILLS.glob("*/SKILL.md")):
        skill = claude_skill.parent.name
        claude_text = claude_skill.read_text(encoding="utf-8")
        codex_text = (CODEX_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        trae_text = (TRAE_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        assert_true(codex_text == claude_text.replace(".claude/skills", "skills"), f"codex SKILL.md drift: {skill}")
        assert_true(trae_text == claude_text.replace(".claude/skills", ".trae/skills"), f"trae SKILL.md drift: {skill}")

    script_paths = [
        ("context-memory-keeper", "scripts/update_workflow_memory.py"),
        ("data-cleaning-and-visualization", "scripts/robust_loader.py"),
        ("model-code-and-result-generator", "scripts/build_result_contracts.py"),
        ("paper-formal-writer", "scripts/check_paper_format.py"),
        ("paper-formal-writer", "scripts/format_formal_docx.py"),
        ("paper-workflow-orchestrator", "scripts/preflight_check.py"),
        ("paper-workflow-orchestrator", "scripts/workflow_guard.py"),
        ("quality-assurance-auditor", "scripts/evidence_gate.py"),
    ]
    for skill, rel_script in script_paths:
        claude_bytes = (CLAUDE_SKILLS / skill / rel_script).read_bytes()
        codex_path = CODEX_SKILLS / skill / rel_script
        trae_path = TRAE_SKILLS / skill / rel_script
        assert_true(codex_path.exists(), f"codex missing script: {skill}/{rel_script}")
        assert_true(trae_path.exists(), f"trae missing script: {skill}/{rel_script}")
        assert_true(codex_path.read_bytes() == claude_bytes, f"codex script drift: {skill}/{rel_script}")
        assert_true(trae_path.read_bytes() == claude_bytes, f"trae script drift: {skill}/{rel_script}")


def main() -> int:
    setup_sandbox.main()
    tests = [
        test_preflight,
        test_missing_pypdf,
        test_robust_loader_and_workflow_guard,
        test_orchestrator_guard_allows_fresh_entry,
        test_workflow_status_after_code_generation,
        test_workflow_status_recovery_across_stages,
        test_workflow_memory_snapshot,
        test_workflow_status_complete_after_s8,
        test_format_gate,
        test_format_formal_docx_after_evidence_gate,
        test_docx_visual_qa,
        test_modeling_run_manifest,
        test_evidence_gate_passes_for_computed_run,
        test_evidence_gate_requires_run_manifest,
        test_skill_docs_have_workflow_guard_contract,
        test_platform_packages_stay_synced,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

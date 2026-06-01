from __future__ import annotations

import json
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
CLAUDE_SKILLS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills"


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


def test_format_gate() -> None:
    cwd = SANDBOX / "scenario_4_suspicious_template"
    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode != 0, "format_formal_docx should block without evidence gate")
    assert_true(not (cwd / "paper_output" / "final_paper.docx").exists(), "formal docx should not be created without gate")

    result = run([sys.executable, str(FORMAT_DOCX), "--allow-draft"], cwd)
    assert_true(result.returncode == 0, f"draft format should pass\n{result.stdout}")
    assert_true((cwd / "paper_output" / "final_paper_draft.docx").exists(), "draft docx should be created")
    assert_true(not (cwd / "paper_output" / "final_paper.docx").exists(), "draft mode must not create formal docx")


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


def main() -> int:
    setup_sandbox.main()
    tests = [
        test_preflight,
        test_missing_pypdf,
        test_robust_loader_and_workflow_guard,
        test_format_gate,
        test_modeling_run_manifest,
        test_evidence_gate_requires_run_manifest,
        test_skill_docs_have_workflow_guard_contract,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

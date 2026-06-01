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
FORMAT_DOCX = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "format_formal_docx.py"
FORMAT_LATEX = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "format_formal_latex.py"
CHECK_LATEX = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "paper-formal-writer" / "scripts" / "check_latex_format.py"


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


def test_preflight() -> None:
    cases = [
        ("scenario_1_empty", 1, "FAIL"),
        ("scenario_2_only_doc", 1, "FAIL"),
        ("scenario_3_broken_xlsx", 1, "FAIL"),
        ("scenario_4_suspicious_template", 0, "PASS"),
        ("scenario_5_stale_output", 0, "PASS"),
    ]
    for name, expected_code, expected_status in cases:
        cwd = SANDBOX / name
        result = run([sys.executable, str(PREFLIGHT)], cwd)
        assert_true(result.returncode == expected_code, f"{name}: expected exit {expected_code}, got {result.returncode}\n{result.stdout}")
        report = load_json(cwd / "paper_output" / "preflight_report.json")
        assert_true(report["status"] == expected_status, f"{name}: expected {expected_status}, got {report['status']}")


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
    assert_true(report["summary"]["readable_data_file_count"] >= 1, "load_report should find readable data")

    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S0"], cwd)
    assert_true(result.returncode == 0, f"workflow S0 should pass after preflight\n{result.stdout}")
    result = run([sys.executable, str(WORKFLOW_GUARD), "--step", "S1"], cwd)
    assert_true(result.returncode == 1, "workflow S1 should fail because problem_analysis.json is absent")


def test_format_gate() -> None:
    cwd = SANDBOX / "scenario_4_suspicious_template"
    result = run([sys.executable, str(FORMAT_DOCX)], cwd)
    assert_true(result.returncode != 0, "format_formal_docx should block without evidence gate")
    assert_true(not (cwd / "paper_output" / "final_paper.docx").exists(), "formal docx should not be created without gate")

    result = run([sys.executable, str(FORMAT_DOCX), "--allow-draft"], cwd)
    assert_true(result.returncode == 0, f"draft format should pass\n{result.stdout}")
    assert_true((cwd / "paper_output" / "final_paper_draft.docx").exists(), "draft docx should be created")
    assert_true(not (cwd / "paper_output" / "final_paper.docx").exists(), "draft mode must not create formal docx")


def test_latex_gate_export_and_check() -> None:
    cwd = SANDBOX / "scenario_4_suspicious_template"
    output_dir = cwd / "paper_output"
    gate_dir = output_dir / "qa"

    result = run([sys.executable, str(FORMAT_LATEX)], cwd)
    assert_true(result.returncode != 0, "formal LaTeX should block without evidence gate")
    assert_true(not (output_dir / "final_paper.tex").exists(), "formal LaTeX should not be created without gate")

    result = run([sys.executable, str(FORMAT_LATEX), "--allow-draft"], cwd)
    assert_true(result.returncode == 0, f"draft LaTeX export should pass\n{result.stdout}")
    assert_true((output_dir / "final_paper_draft.tex").exists(), "draft LaTeX should be created")
    assert_true(not (output_dir / "final_paper.tex").exists(), "draft LaTeX must not create formal final_paper.tex")

    result = run([sys.executable, str(CHECK_LATEX), "--draft"], cwd)
    assert_true(result.returncode == 0, f"draft LaTeX check should pass\n{result.stdout}")
    draft_check_report = load_json(output_dir / "latex_check_report.json")
    assert_true(draft_check_report["status"] == "PASS", "draft LaTeX check report should PASS")

    gate_dir.mkdir(parents=True, exist_ok=True)
    (gate_dir / "evidence_gate_report.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    result = run([sys.executable, str(FORMAT_LATEX)], cwd)
    assert_true(result.returncode == 0, f"formal LaTeX export should pass after gate\n{result.stdout}")
    assert_true((output_dir / "final_paper.tex").exists(), "formal final_paper.tex should be created after gate")
    assert_true((output_dir / "latex_build_report.json").exists(), "formal LaTeX export report should be created")

    result = run([sys.executable, str(CHECK_LATEX)], cwd)
    assert_true(result.returncode == 0, f"formal LaTeX check should pass\n{result.stdout}")
    formal_check_report = load_json(output_dir / "latex_check_report.json")
    assert_true(formal_check_report["status"] == "PASS", "formal LaTeX check report should PASS")


def main() -> int:
    setup_sandbox.main()
    tests = [
        test_preflight,
        test_missing_pypdf,
        test_robust_loader_and_workflow_guard,
        test_format_gate,
        test_latex_gate_export_and_check,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

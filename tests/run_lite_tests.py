from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document


REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX = REPO_ROOT / "tests" / "lite_sandbox"
SKILL_ROOT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "mathmodel-lite"
PREFLIGHT = SKILL_ROOT / "scripts" / "lite_preflight.py"
RUNNER = SKILL_ROOT / "scripts" / "lite_run.py"
FINALIZER = SKILL_ROOT / "scripts" / "lite_finalize.py"


def run(script: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def prepare(name: str) -> Path:
    cwd = SANDBOX / name
    if cwd.exists():
        shutil.rmtree(cwd)
    problem = cwd / "problem_files"
    problem.mkdir(parents=True)
    (problem / "problem.txt").write_text("Q1: fit a linear model and report the slope.\n", encoding="utf-8")
    (problem / "data.csv").write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    completed = run(PREFLIGHT, cwd)
    assert_true(completed.returncode == 0, f"preflight failed\n{completed.stdout}")
    output = cwd / "paper_output_lite"
    write_json(
        output / "plan.json",
        {"questions": [{"id": "Q1", "task": "estimate slope", "model": "least squares", "output": "slope"}]},
    )
    model_source = '''from pathlib import Path
import json

root = Path.cwd()
output = root / "paper_output_lite"
table = output / "tables" / "q1.csv"
table.write_text("metric,value\\nslope,2.0\\n", encoding="utf-8")
result = {
    "status": "computed",
    "questions": [{
        "id": "Q1",
        "answer": "The fitted slope is 2.0.",
        "method": "least squares",
        "metrics": {"slope": 2.0},
        "evidence": ["paper_output_lite/tables/q1.csv"]
    }]
}
(output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
'''
    (output / "code" / "model.py").write_text(model_source, encoding="utf-8")
    (output / "paper.md").write_text(
        "\n".join(
            [
                "# Linear Modeling Paper",
                "# 摘要",
                "本文针对 Q1 建立线性模型并计算斜率。",
                "# 1 问题重述",
                "Q1 要求根据数据估计线性关系。",
                "# 2 模型假设",
                "观测误差独立且数据口径一致。",
                "# 3 模型建立与求解",
                "Q1 使用最小二乘模型。",
                "# 4 结果与检验",
                "Q1 的斜率为 2.0，结果与原始数据一致。",
                "# 5 模型评价",
                "模型简单且可解释。",
                "# 6 结论",
                "Q1 已得到明确数值答案。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return cwd


def test_lite_happy_path() -> None:
    cwd = prepare("happy")
    completed = run(RUNNER, cwd)
    assert_true(completed.returncode == 0, f"runner failed\n{completed.stdout}")
    completed = run(FINALIZER, cwd)
    assert_true(completed.returncode == 0, f"finalizer failed\n{completed.stdout}")
    report = json.loads((cwd / "paper_output_lite" / "lite_report.json").read_text(encoding="utf-8"))
    assert_true(report["status"] == "PASS", "Lite report should pass")
    docx_path = cwd / "paper_output_lite" / "paper.docx"
    assert_true(docx_path.stat().st_size > 0, "Lite DOCX should be nonempty")
    docx_text = "\n".join(paragraph.text for paragraph in Document(docx_path).paragraphs)
    assert_true("Q1" in docx_text and "2.0" in docx_text, "Lite DOCX should preserve the computed result")


def test_lite_rejects_modified_input() -> None:
    cwd = prepare("modified_input")
    (cwd / "problem_files" / "data.csv").write_text("x,y\n1,3\n", encoding="utf-8")
    completed = run(RUNNER, cwd)
    assert_true(completed.returncode != 0, "runner should reject modified input")


def test_lite_rejects_modified_model_after_run() -> None:
    cwd = prepare("modified_model")
    assert_true(run(RUNNER, cwd).returncode == 0, "runner should pass before modification")
    model = cwd / "paper_output_lite" / "code" / "model.py"
    model.write_text(model.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    completed = run(FINALIZER, cwd)
    assert_true(completed.returncode != 0, "finalizer should reject modified model")


def test_lite_rejects_placeholder_paper() -> None:
    cwd = prepare("placeholder")
    assert_true(run(RUNNER, cwd).returncode == 0, "runner should pass")
    paper = cwd / "paper_output_lite" / "paper.md"
    paper.write_text(paper.read_text(encoding="utf-8") + "\n待补结果。\n", encoding="utf-8")
    completed = run(FINALIZER, cwd)
    assert_true(completed.returncode != 0, "finalizer should reject placeholder paper")


def test_lite_preflight_rejects_standard_install() -> None:
    cwd = SANDBOX / "lite_rejects_standard"
    problem = cwd / "problem_files"
    problem.mkdir(parents=True)
    (problem / "problem.txt").write_text("Q1: test isolation.\n", encoding="utf-8")
    standard_entry = cwd / "skills" / "paper-workflow-orchestrator" / "SKILL.md"
    standard_entry.parent.mkdir(parents=True)
    standard_entry.write_text("---\nname: paper-workflow-orchestrator\n---\n", encoding="utf-8")
    completed = run(PREFLIGHT, cwd)
    assert_true(completed.returncode != 0, "Lite preflight should reject a mixed Standard installation")
    manifest = json.loads((cwd / "paper_output_lite" / "input_manifest.json").read_text(encoding="utf-8"))
    assert_true(any("不得混装" in item for item in manifest["failures"]), "mixed-edition failure should be explicit")


def main() -> int:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)
    tests = [
        test_lite_happy_path,
        test_lite_rejects_modified_input,
        test_lite_rejects_modified_model_after_run,
        test_lite_rejects_placeholder_paper,
        test_lite_preflight_rejects_standard_install,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("All Lite tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

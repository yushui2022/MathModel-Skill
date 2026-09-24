from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[1]
SANDBOX = REPO_ROOT / "tests" / "flash_sandbox"
SKILL_ROOT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills" / "mathmodel-flash"
PREFLIGHT = SKILL_ROOT / "scripts" / "flash_preflight.py"
RUNNER = SKILL_ROOT / "scripts" / "flash_run.py"
FINALIZER = SKILL_ROOT / "scripts" / "flash_finalize.py"


def run(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], cwd=str(cwd),
                          text=True, encoding="utf-8", errors="replace",
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def prepare(name: str, mode: str = "smoke-test") -> Path:
    cwd = SANDBOX / name
    if cwd.exists():
        shutil.rmtree(cwd)
    problem = cwd / "problem_files"
    problem.mkdir(parents=True)
    (problem / "problem.txt").write_text("Q1: fit a linear model and report the slope.\n", encoding="utf-8")
    (problem / "data.csv").write_text("x,y\n1,2\n2,4\n3,6\n", encoding="utf-8")
    completed = run(PREFLIGHT, cwd)
    assert_true(completed.returncode == 0, f"preflight failed\n{completed.stdout}")
    output = cwd / "paper_output_flash"
    delivery = {"mode": mode}
    if mode != "basic-long-paper":
        delivery["reason"] = "Synthetic Flash test fixture"
    else:
        delivery["target_pages"] = 20
    write_json(output / "plan.json", {
        "delivery": delivery,
        "questions": [{"id": "Q1", "task": "estimate slope", "model": "least squares", "output": "slope"}],
    })
    model_source = """from pathlib import Path
import json

root = Path.cwd()
output = root / "paper_output_flash"
table = output / "tables" / "q1.csv"
table.write_text("metric,value\\nslope,2.0\\n", encoding="utf-8")
result = {
    "status": "computed",
    "questions": [{
        "id": "Q1",
        "answer": "The fitted slope is 2.0.",
        "method": "least squares",
        "metrics": {"slope": 2.0},
        "evidence": ["paper_output_flash/tables/q1.csv"]
    }]
}
(output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
"""
    (output / "code" / "model.py").write_text(model_source, encoding="utf-8")
    paper = """# Linear Modeling Paper
# 摘要
本文针对 Q1 建立线性模型并计算斜率。
# 1 问题重述
Q1 要求根据数据估计线性关系。
# 2 模型假设
观测误差独立且数据口径一致。
# 3 模型建立与求解
## Q1 方法、结果与检验
Q1 使用最小二乘模型，斜率为 2.0。通过逐点代入原始数据验证拟合关系；这个构造算例没有测量噪声，不能据此宣称真实样本也有相同表现。
# 4 实验设计
实验读取输入表格并以逐点误差检查模型输出。
# 5 结果与检验
Q1 的斜率为 2.0，结果与原始数据一致。
# 6 模型评价
模型简单且可解释。
# 7 结论
Q1 已得到明确数值答案。
"""
    (output / "paper.md").write_text(paper, encoding="utf-8")
    return cwd


def test_happy_path() -> None:
    cwd = prepare("happy")
    assert_true(run(RUNNER, cwd).returncode == 0, "runner should pass")
    completed = run(FINALIZER, cwd)
    assert_true(completed.returncode == 0, completed.stdout)
    report = json.loads((cwd / "paper_output_flash" / "flash_report.json").read_text(encoding="utf-8"))
    assert_true(report["status"] == "PASS", "Flash report should pass")
    docx_path = cwd / "paper_output_flash" / "paper.docx"
    text = "\n".join(p.text for p in Document(docx_path).paragraphs)
    assert_true(docx_path.stat().st_size > 0 and "Q1" in text and "2.0" in text, "DOCX should preserve result")


def test_long_paper_gate() -> None:
    cwd = prepare("long_gate", "basic-long-paper")
    assert_true(run(RUNNER, cwd).returncode == 0, "runner should pass")
    assert_true(run(FINALIZER, cwd).returncode != 0, "short text must not pass long-paper mode")


def test_modified_input_rejected() -> None:
    cwd = prepare("modified_input")
    (cwd / "problem_files" / "data.csv").write_text("x,y\n1,3\n", encoding="utf-8")
    assert_true(run(RUNNER, cwd).returncode != 0, "runner should reject modified input")


def test_foreign_installation_rejected() -> None:
    cwd = SANDBOX / "foreign"
    if cwd.exists():
        shutil.rmtree(cwd)
    (cwd / "problem_files").mkdir(parents=True)
    (cwd / "problem_files" / "problem.txt").write_text("Q1 test", encoding="utf-8")
    foreign = cwd / ".agents" / "skills" / "paper-workflow-orchestrator"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("---\nname: paper-workflow-orchestrator\n---\n", encoding="utf-8")
    completed = run(PREFLIGHT, cwd)
    assert_true(completed.returncode != 0 and "standard" in completed.stdout.lower(), "Flash must reject Standard mixing")


def test_packages_are_deterministic_and_flash_only() -> None:
    builder = REPO_ROOT / "scripts" / "build_release_packages.py"
    first = SANDBOX / "release-first"
    second = SANDBOX / "release-second"
    for output in (first, second):
        completed = subprocess.run([sys.executable, str(builder), "--output-dir", str(output)],
                                   cwd=REPO_ROOT, text=True, encoding="utf-8",
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        assert_true(completed.returncode == 0, completed.stdout)
    names = sorted(path.name for path in first.glob("*.zip"))
    expected = ["MathModel-Skill-Flash-Claude-Code.zip", "MathModel-Skill-Flash-Codex.zip", "MathModel-Skill-Flash-Trae.zip"]
    assert_true(names == expected, "Flash should build exactly three platform archives")
    assert_true((first / "SHA256SUMS.txt").read_bytes() == (second / "SHA256SUMS.txt").read_bytes(), "checksum files should match")
    for name in names:
        assert_true((first / name).read_bytes() == (second / name).read_bytes(), f"nondeterministic archive: {name}")
        with zipfile.ZipFile(first / name) as archive:
            entries = archive.namelist()
            marker = next(item for item in entries if item.endswith("mathmodel-flash/MATHMODEL_EDITION.json"))
            marker_data = json.loads(archive.read(marker).decode("utf-8"))
            assert_true(marker_data["edition"] == "flash", "Flash marker should be present")
            assert_true(marker_data["version"] == (REPO_ROOT / "VERSION").read_text().strip(), "marker version should match")
            assert_true(not any("mathmodel-lite" in item or "paper-workflow-orchestrator" in item for item in entries), "archive must not include another edition")
            assert_true("AGENTS.md" not in entries and "CLAUDE.md" not in entries, "archives must not overwrite root instructions")


def main() -> int:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)
    tests = [test_happy_path, test_long_paper_gate, test_modified_input_rejected, test_foreign_installation_rejected, test_packages_are_deterministic_and_flash_only]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print("All Flash tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

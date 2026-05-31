import os
import subprocess
import sys
from pathlib import Path


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def run_step(args, **kwargs):
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    if "env" in kwargs:
        env.update(kwargs.pop("env"))
    return subprocess.run(args, env=env, **kwargs)


def main() -> int:
    configure_utf8_stdio()
    root = Path(__file__).resolve().parents[4]
    os.chdir(root)

    print("=== MathModel Skill Quickstart / Smoke Test ===")
    print("本脚本只验证安装、目录和基础契约链路，不代表正式比赛论文质量。")
    print("正式赛题应由 Agent 读取 paper-workflow-orchestrator/SKILL.md 后生成专用代码、真实结果和最终论文。")
    print()

    print("=== Step-0 输出目录规划 ===")
    layout_script = root / ".trae/skills/paper-workflow-orchestrator/scripts/prepare_output_layout.py"
    if layout_script.exists():
        run_step([sys.executable, str(layout_script)], check=False)
    else:
        print("   未检测到输出目录规划脚本，跳过。")

    print("=== Step-1 赛题结构化分析 ===")
    analyzer_script = root / ".trae/skills/problem-doc-model-selector/scripts/analyze_problem.py"
    if analyzer_script.exists():
        r_analyze = run_step(
            [sys.executable, str(analyzer_script)],
            check=False,
        )
        if r_analyze.returncode != 0:
            print("⚠️ 赛题结构化分析未成功执行，后续将使用通用任务模板。")
    else:
        print("   未检测到赛题分析脚本，跳过。")

    print("=== Step-2 模型路线与评分闭环 ===")
    model_route_script = root / ".trae/skills/modeling-paper-rubric-and-model-selector/scripts/build_model_route.py"
    if model_route_script.exists():
        r_route = run_step(
            [sys.executable, str(model_route_script)],
            check=False,
        )
        if r_route.returncode != 0:
            print("⚠️ 模型路线契约未成功生成，QA 将回退到结构化题意分析。")
    else:
        print("   未检测到模型路线脚本，跳过。")

    print("=== Step-3 外部资源获取 (可选) ===")
    harvester_script = root / ".trae/skills/authoritative-data-harvester/scripts/run.py"
    if harvester_script.exists():
        print("   正在检查外部数据源...")
        run_step(
            [sys.executable, str(harvester_script)],
            check=False,
        )
    else:
        print("   未检测到外部数据获取脚本，跳过。")

    print("=== Step-4 数据与图表计划、清洗与可视化 ===")
    r_clean = run_step(
        [sys.executable, ".trae/skills/data-cleaning-and-visualization/scripts/run_pipeline.py"],
        check=False,
    )
    if r_clean.returncode != 0:
        print("⚠️ 数据清洗步骤未成功执行（可能是没有数据文件），继续后续步骤...")

    print("=== Step-5 结果计算与出图（可选自定义） ===")
    calc_script = Path("step2_calc_results.py")
    if calc_script.exists():
        r_calc = run_step(
            [sys.executable, "step2_calc_results.py"],
            check=False,
        )
        if r_calc.returncode != 0:
            print("⚠️ 结果计算脚本执行失败，但流程继续...")
    else:
        print("ℹ️ 未找到 step2_calc_results.py，跳过自定义计算步骤。")

    print("=== Step-6 建模代码与结果证据生成 ===")
    result_contract_script = root / ".trae/skills/model-code-and-result-generator/scripts/build_result_contracts.py"
    if result_contract_script.exists():
        r_result = run_step(
            [sys.executable, str(result_contract_script)],
            check=False,
        )
        if r_result.returncode != 0:
            print("⚠️ 结果证据契约未成功生成，QA 将提示真实建模结果待补。")
    else:
        print("   未检测到结果证据生成脚本，跳过。")

    print("=== Step-7 质量审计与任务清单 ===")
    r0 = run_step(
        [sys.executable, ".trae/skills/quality-assurance-auditor/scripts/pipeline.py"],
        check=False,
    )
    if r0.returncode != 0:
        return r0.returncode

    print("=== Step-8 微单元离线生成 ===")
    r1 = run_step(
        [sys.executable, ".trae/skills/paper-micro-unit-generator/scripts/generate_all_offline.py"],
        check=False,
    )
    if r1.returncode != 0:
        return r1.returncode

    print("=== Step-9 合并 ===")
    r2 = run_step(
        [sys.executable, ".trae/skills/paper-micro-unit-generator/scripts/merge.py"],
        check=False,
    )
    if r2.returncode != 0:
        return r2.returncode

    print("=== Step-10 转换为 Word (docx，写入 quickstart 草稿目录) ===")
    print("⚠️ Quickstart 不会覆盖 paper_output/final_paper.docx；草稿写到 paper_output/quickstart/。")

    direct_docx = root / "paper_output/final_paper_direct.docx"
    quickstart_dir = root / "paper_output/quickstart"
    quickstart_dir.mkdir(parents=True, exist_ok=True)
    draft_docx = quickstart_dir / "quickstart_draft.docx"

    if direct_docx.exists():
        import shutil

        try:
            shutil.copy(direct_docx, draft_docx)
            print(f"✅ 已写入 quickstart 草稿 Word：{draft_docx}")
        except Exception as e:
            print(f"⚠️ 写入 quickstart 草稿失败: {e}")
    else:
        try:
            run_step(["pandoc", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            md_path = root / "paper_output/final_paper.md"
            if md_path.exists():
                print("ℹ️ 未检测到直接生成的 Word，尝试使用 Pandoc 转换 quickstart 草稿...")
                run_step(
                    ["pandoc", str(md_path), "-o", str(draft_docx), "--reference-doc=reference.docx"],
                    check=False,
                )
                if not draft_docx.exists():
                    run_step(
                        ["pandoc", str(md_path), "-o", str(draft_docx)],
                        check=False,
                    )
                if draft_docx.exists():
                    print(f"✅ 已通过 Pandoc 生成 quickstart 草稿 Word：{draft_docx}")
                else:
                    print("⚠️ Word 转换失败：pandoc 执行未生成文件")
            else:
                print("⚠️ 未找到 Markdown 源文件，跳过转换")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ 未检测到 pandoc 且未安装 python-docx，无法生成 Word 草稿。")

    print("=== Step-11 迁移正式命名中间产物到 quickstart 目录 ===")
    import shutil as _shutil
    _migrations = [
        (root / "paper_output/final_paper.md", quickstart_dir / "quickstart_draft.md"),
        (root / "paper_output/final_paper_direct.docx", quickstart_dir / "quickstart_direct.docx"),
    ]
    migrated: list[Path] = []
    for src, dst in _migrations:
        if src.exists():
            try:
                if dst.exists():
                    dst.unlink()
                _shutil.move(str(src), str(dst))
                migrated.append(dst)
                print(f"   迁移：{src.relative_to(root).as_posix()} -> {dst.relative_to(root).as_posix()}")
            except Exception as e:
                print(f"   ⚠️ 迁移 {src} 失败：{e}")

    print("✅ Quickstart 验证流程结束。以下文件是验证草稿，不代表正式比赛稿：")
    if draft_docx.exists():
        print(f"   - Word 草稿: {draft_docx.relative_to(root).as_posix()}")
    for path in migrated:
        print(f"   - {path.relative_to(root).as_posix()}")
    print("   注意：正式 paper_output/final_paper.docx / final_paper.md 不会被 quickstart 写入；正式稿走 paper-formal-writer 流程。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

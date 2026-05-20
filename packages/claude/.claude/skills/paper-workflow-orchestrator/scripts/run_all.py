import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path.cwd().resolve()
    os.chdir(root)

    print("=== Step--1 赛题结构化分析 ===")
    analyzer_script = root / ".claude/skills/problem-doc-model-selector/scripts/analyze_problem.py"
    if analyzer_script.exists():
        r_analyze = subprocess.run(
            [sys.executable, str(analyzer_script)],
            check=False,
        )
        if r_analyze.returncode != 0:
            print("⚠️ 赛题结构化分析未成功执行，后续将使用通用任务模板。")
    else:
        print("   未检测到赛题分析脚本，跳过。")

    print("=== Step--0 模型路线与评分闭环 ===")
    model_route_script = root / ".claude/skills/modeling-paper-rubric-and-model-selector/scripts/build_model_route.py"
    if model_route_script.exists():
        r_route = subprocess.run(
            [sys.executable, str(model_route_script)],
            check=False,
        )
        if r_route.returncode != 0:
            print("⚠️ 模型路线契约未成功生成，QA 将回退到结构化题意分析。")
    else:
        print("   未检测到模型路线脚本，跳过。")

    print("=== Step-Optional 外部资源获取 (Silent) ===")
    harvester_script = root / ".claude/skills/authoritative-data-harvester/scripts/run.py"
    if harvester_script.exists():
        print("   正在检查外部数据源...")
        subprocess.run(
            [sys.executable, str(harvester_script)],
            check=False,
        )
    else:
        print("   未检测到外部数据获取脚本，跳过。")

    print("=== Step-0 数据与图表计划、清洗与可视化 ===")
    r_clean = subprocess.run(
        [sys.executable, ".claude/skills/data-cleaning-and-visualization/scripts/run_pipeline.py"],
        check=False,
    )
    if r_clean.returncode != 0:
        print("⚠️ 数据清洗步骤未成功执行（可能是没有数据文件），继续后续步骤...")

    print("=== Step-1 结果计算与出图 ===")
    calc_script = Path("step2_calc_results.py")
    if calc_script.exists():
        r_calc = subprocess.run(
            [sys.executable, "step2_calc_results.py"],
            check=False,
        )
        if r_calc.returncode != 0:
            print("⚠️ 结果计算脚本执行失败，但流程继续...")
    else:
        print("ℹ️ 未找到 step2_calc_results.py，跳过自定义计算步骤。")

    print("=== Step-1.5 建模代码与结果证据生成 ===")
    result_contract_script = root / ".claude/skills/model-code-and-result-generator/scripts/build_result_contracts.py"
    if result_contract_script.exists():
        r_result = subprocess.run(
            [sys.executable, str(result_contract_script)],
            check=False,
        )
        if r_result.returncode != 0:
            print("⚠️ 结果证据契约未成功生成，QA 将提示真实建模结果待补。")
    else:
        print("   未检测到结果证据生成脚本，跳过。")

    print("=== Step-2 质量审计与任务清单 ===")
    r0 = subprocess.run(
        [sys.executable, ".claude/skills/quality-assurance-auditor/scripts/pipeline.py"],
        check=False,
    )
    if r0.returncode != 0:
        return r0.returncode

    print("=== Step-3 微单元离线生成 ===")
    r1 = subprocess.run(
        [sys.executable, ".claude/skills/paper-micro-unit-generator/scripts/generate_all_offline.py"],
        check=False,
    )
    if r1.returncode != 0:
        return r1.returncode

    print("=== Step-4 合并 ===")
    r2 = subprocess.run(
        [sys.executable, ".claude/skills/paper-micro-unit-generator/scripts/merge.py"],
        check=False,
    )
    if r2.returncode != 0:
        return r2.returncode

    print("=== Step-5 转换为 Word (docx) ===")

    direct_docx = root / "paper_output/final_paper_direct.docx"
    final_docx = root / "paper_output/final_paper.docx"

    if direct_docx.exists():
        import shutil

        try:
            shutil.copy(direct_docx, final_docx)
            print(f"✅ 已直接生成 Word 文档：{final_docx}")
            print("   (注：此版本由脚本直接构建，公式保留为 LaTeX 源码)")
        except Exception as e:
            print(f"⚠️ 移动文件失败: {e}")
    else:
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            md_path = root / "paper_output/final_paper.md"
            if md_path.exists():
                print("ℹ️ 未检测到直接生成的 Word，尝试使用 Pandoc 转换...")
                subprocess.run(
                    ["pandoc", str(md_path), "-o", str(final_docx), "--reference-doc=reference.docx"],
                    check=False,
                )
                if not final_docx.exists():
                    subprocess.run(
                        ["pandoc", str(md_path), "-o", str(final_docx)],
                        check=False,
                    )
                if final_docx.exists():
                    print(f"✅ 已通过 Pandoc 生成 Word 文档：{final_docx}")
                else:
                    print("⚠️ Word 转换失败：pandoc 执行未生成文件")
            else:
                print("⚠️ 未找到 Markdown 源文件，跳过转换")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ 未检测到 pandoc 且未安装 python-docx，无法生成 Word 文档。")

    print("✅ 全流程结束。最终产物：")
    print("   - Markdown: paper_output/final_paper.md")
    if final_docx.exists():
        print("   - Word:     paper_output/final_paper.docx")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

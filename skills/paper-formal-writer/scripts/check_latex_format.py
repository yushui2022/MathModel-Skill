from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from latex_integrity import sha256, safe_path


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
TEX_FILE = OUTPUT_DIR / "final_paper.tex"
DRAFT_TEX_FILE = OUTPUT_DIR / "final_paper_draft.tex"
PDF_FILE = OUTPUT_DIR / "final_paper.pdf"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
TABLE_INDEX_FILE = OUTPUT_DIR / "tables" / "table_index.json"
REPORT_JSON = OUTPUT_DIR / "latex_check_report.json"
REPORT_MD = OUTPUT_DIR / "latex_check_report.md"

PLACEHOLDERS = ["TODO", "待补", "内容生成中", "关键词1"]
REQUIRED_TEXT = ["摘要", "关键词", "问题重述", "问题分析", "模型假设", "符号说明", "模型的建立与求解", "参考文献", "附录"]


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc)}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def index_count(data: Any, key: str) -> int:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return len(data[key])
    return 0


def evaluate(tex_file: Path, require_pdf: bool) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    pdf_file = tex_file.with_suffix(".pdf")
    build = load_json(OUTPUT_DIR / ("latex_draft_report.json" if tex_file == DRAFT_TEX_FILE else "latex_build_report.json"))
    text = ""
    if not tex_file.exists():
        failures.append(f"缺少 LaTeX 文件：{rel(tex_file)}")
    else:
        text = tex_file.read_text(encoding="utf-8")

    if text:
        if "\\documentclass" not in text:
            failures.append("缺少 \\documentclass。")
        if "\\begin{document}" not in text or "\\end{document}" not in text:
            failures.append("缺少 \\begin{document} 或 \\end{document}。")
        if "\\usepackage" not in text:
            warnings.append("未检测到 \\usepackage，模板可能过于简化。")

        section_count = len(re.findall(r"\\section\{", text))
        subsection_count = len(re.findall(r"\\subsection\{", text))
        subsubsection_count = len(re.findall(r"\\subsubsection\{", text))
        includegraphics_count = len(re.findall(r"\\includegraphics", text))
        longtable_count = len(re.findall(r"\\begin\{longtable\}", text))
        formula_count = len(re.findall(r"\\\[", text))

        if section_count < 6:
            failures.append(f"LaTeX 一级章节数量不足：{section_count} < 6")
        if subsection_count == 0:
            warnings.append("未检测到 \\subsection，模型章节层级可能不足。")
        for item in REQUIRED_TEXT:
            if item not in text:
                failures.append(f"LaTeX 中缺少正式论文结构关键词：{item}")
        for placeholder in PLACEHOLDERS:
            if placeholder in text:
                failures.append(f"LaTeX 中存在占位符或待补文本：{placeholder}")
    else:
        section_count = subsection_count = subsubsection_count = includegraphics_count = longtable_count = formula_count = 0
        if tex_file.exists():
            failures.append("LaTeX source is empty")

    figure_index = load_json(FIGURE_INDEX_FILE)
    table_index = load_json(TABLE_INDEX_FILE)
    expected_figures = index_count(figure_index, "figures")
    expected_tables = index_count(table_index, "tables")

    if expected_figures > 0 and includegraphics_count == 0:
        failures.append("figure_index.json 有图片计划，但 LaTeX 中没有 \\includegraphics。")
    elif includegraphics_count < expected_figures:
        warnings.append(f"LaTeX 图片数量少于 figure_index.json：{includegraphics_count} < {expected_figures}")

    if expected_tables > 0 and longtable_count == 0:
        failures.append("table_index.json 有表格计划，但 LaTeX 中没有 longtable。")
    elif longtable_count < expected_tables:
        warnings.append(f"LaTeX 表格数量少于 table_index.json：{longtable_count} < {expected_tables}")

    page_count = 0
    if require_pdf:
        try:
            from pypdf import PdfReader
            if build.get("tex_sha256") != sha256(tex_file) or build.get("compile", {}).get("status") != "PASS":
                failures.append("TeX/PDF lacks a successful current compile receipt")
            if build.get("compile", {}).get("pdf_sha256") != sha256(pdf_file):
                failures.append("PDF has changed since compilation")
            if not build.get("input_hashes"):
                failures.append("build lacks source/evidence input hashes")
            for name, expected in build.get("input_hashes", {}).items():
                if sha256(safe_path(BASE_DIR, name)) != expected:
                    failures.append(f"build input changed: {name}")
            pages = list(PdfReader(str(pdf_file)).pages)
            page_count = len(pages)
            extracted = "\n".join(page.extract_text() or "" for page in pages)
            if not pages or len(re.sub(r"\s+", "", extracted)) < 100:
                failures.append("PDF is empty or has insufficient extractable text")
            outline = load_json(OUTPUT_DIR / "plan/paper_outline.json")
            scope = outline.get("delivery", {"mode": "competition"})
            short = scope.get("mode") in {"short-report", "smoke-test"} and bool(scope.get("reason"))
            if not short and page_count < 18:
                failures.append("complete competition report is below the 18-page planning minimum; explicitly declare a justified short scope if requested")
            if not short:
                warnings.append("Total PDF pages do not certify substantive body length or contest-specific page limits; inspect body/appendix boundaries manually.")
                source = safe_path(BASE_DIR, build.get("source", "")).read_text(encoding="utf-8")
                source = re.sub(r"<!--.*?-->|```.*?```|~~~.*?~~~", "", source, flags=re.S)
                source = re.split(r"(?mi)^\s*#{1,6}\s+(?:附录|Appendix|Appendices)(?:\s|$)", source, maxsplit=1)[0]
                source = re.sub(r"!\[[^\]]*\]\([^)]+\)|(?m:^\s*#{1,6}\s+.*$)", "", source)
                if len(re.sub(r"\s+", "", source)) < 8000:
                    failures.append("main manuscript is below the 8000-character completeness floor")
            from format_formal_latex import check_evidence_gate
            fresh, reason = check_evidence_gate()
            if tex_file != DRAFT_TEX_FILE and not fresh:
                failures.append(reason)
        except Exception as exc:
            failures.append(f"invalid PDF or build receipt: {exc}")

    return {
        "schema_version": "1.0",
        "generated_by": "paper-formal-writer/scripts/check_latex_format.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": ("PASS" if require_pdf else "SOURCE_ONLY") if not failures else "FAIL",
        "acceptance_scope": "LEGACY_LATEX_EXPORT_ONLY" if require_pdf and not failures else "NOT_ACCEPTED",
        "tex": rel(tex_file),
        "pdf": rel(pdf_file) if pdf_file.exists() else "",
        "counts": {
            "pages": page_count,
            "sections": section_count,
            "subsections": subsection_count,
            "subsubsections": subsubsection_count,
            "figures": includegraphics_count,
            "tables": longtable_count,
            "formulas": formula_count,
            "expected_figures": expected_figures,
            "expected_tables": expected_tables,
        },
        "failures": failures,
        "warnings": warnings,
    }


def write_reports(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# LaTeX Format Check Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- TeX: `{report['tex']}`",
        f"- PDF: `{report['pdf']}`",
        "",
        "## Counts",
    ]
    for key, value in report["counts"].items():
        lines.append(f"- {key}: `{value}`")
    if report["failures"]:
        lines.append("")
        lines.append("## Failures")
        lines.extend(f"- {item}" for item in report["failures"])
    if report["warnings"]:
        lines.append("")
        lines.append("## Warnings")
        lines.extend(f"- {item}" for item in report["warnings"])
    REPORT_MD.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Check generated LaTeX paper structure.")
    parser.add_argument("--draft", action="store_true", help="检查 final_paper_draft.tex 而不是 final_paper.tex。")
    parser.add_argument("--require-pdf", action="store_true", help="要求 final_paper.pdf 已生成。")
    args = parser.parse_args()

    report = evaluate(DRAFT_TEX_FILE if args.draft else TEX_FILE, args.require_pdf)
    write_reports(report)
    print(f"LaTeX 检查报告：{rel(REPORT_MD)}")
    if report["status"] == "PASS":
        print("[LATEX CHECK PASS]")
        return 0
    if report["status"] == "SOURCE_ONLY":
        print("[LATEX SOURCE ONLY] PDF delivery is not verified; run --require-pdf after compilation.")
        return 0
    print("[LATEX CHECK FAIL]")
    for failure in report["failures"][:12]:
        print(f" - {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

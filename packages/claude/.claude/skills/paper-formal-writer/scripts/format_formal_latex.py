from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
SOURCE_FILE = OUTPUT_DIR / "final_paper_source.md"
FALLBACK_SOURCE_FILE = OUTPUT_DIR / "final_paper.md"
OUTLINE_FILE = OUTPUT_DIR / "plan" / "paper_outline.json"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
TABLE_INDEX_FILE = OUTPUT_DIR / "tables" / "table_index.json"
EVIDENCE_GATE_REPORT = OUTPUT_DIR / "qa" / "evidence_gate_report.json"

TEX_FILE_FORMAL = OUTPUT_DIR / "final_paper.tex"
TEX_FILE_DRAFT = OUTPUT_DIR / "final_paper_draft.tex"
PDF_FILE_FORMAL = OUTPUT_DIR / "final_paper.pdf"
PDF_FILE_DRAFT = OUTPUT_DIR / "final_paper_draft.pdf"
REPORT_JSON_FORMAL = OUTPUT_DIR / "latex_build_report.json"
REPORT_JSON_DRAFT = OUTPUT_DIR / "latex_draft_report.json"
REPORT_MD_FORMAL = OUTPUT_DIR / "latex_build_report.md"
REPORT_MD_DRAFT = OUTPUT_DIR / "latex_draft_report.md"


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
    except Exception:
        return {}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def resolve_path(path_text: str) -> Path:
    path = Path(str(path_text or "").strip().strip("<>"))
    if path.is_absolute():
        return path
    return BASE_DIR / str(path).replace("\\", "/")


def source_path() -> Path:
    if SOURCE_FILE.exists():
        return SOURCE_FILE
    return FALLBACK_SOURCE_FILE


def check_evidence_gate() -> tuple[bool, str]:
    if not EVIDENCE_GATE_REPORT.exists():
        return False, f"未找到证据门禁报告：{rel(EVIDENCE_GATE_REPORT)}。请先运行 evidence_gate.py --mode official。"
    try:
        data = json.loads(EVIDENCE_GATE_REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"证据门禁报告无法解析：{type(exc).__name__}: {exc}"
    status = str(data.get("status") or "").strip().upper()
    if status != "PASS":
        return False, f"证据门禁状态为 `{status or 'UNKNOWN'}`，正式 LaTeX 不得生成。"
    return True, ""


def latex_escape(text: object) -> str:
    value = str(text or "")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def clean_inline(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    parts = re.split(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$", text.strip())
    rendered: list[str] = []
    for idx, part in enumerate(parts):
        if not part:
            continue
        if idx % 2 == 1:
            rendered.append(f"${part.strip()}$")
        else:
            rendered.append(latex_escape(part))
    return "".join(rendered).strip()


def build_lookup(index: Any, list_key: str, id_key: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in index.get(list_key, []) if isinstance(index, dict) else []:
        if isinstance(item, dict) and item.get(id_key):
            lookup[str(item[id_key])] = item
    return lookup


def read_csv_rows(path: Path, max_rows: int = 28, max_cols: int = 8) -> list[list[str]]:
    if not path.exists():
        return []
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                rows = [[str(cell) for cell in row[:max_cols]] for row in csv.reader(handle)]
            return rows[:max_rows]
        except Exception:
            continue
    return []


def latex_table(rows: list[list[str]], caption: str | None = None) -> str:
    if not rows:
        return "\n".join([r"\begin{quote}", "表格数据暂不可读取，正式提交前需检查表格索引和 CSV 文件。", r"\end{quote}"])
    col_count = max(len(row) for row in rows)
    width = max(0.10, min(0.24, 0.92 / max(col_count, 1)))
    spec = "|" + "|".join([f"p{{{width:.2f}\\textwidth}}" for _ in range(col_count)]) + "|"
    lines = [r"\begin{center}", rf"\begin{{longtable}}{{{spec}}}", r"\hline"]
    if caption:
        lines.append(rf"\caption{{{clean_inline(caption)}}}\\")
        lines.append(r"\hline")
    for row_index, row in enumerate(rows):
        cells = [clean_inline(row[col]) if col < len(row) else "" for col in range(col_count)]
        lines.append(" & ".join(cells) + r" \\")
        lines.append(r"\hline")
        if row_index == 0:
            lines.append(r"\endfirsthead")
            lines.append(r"\hline")
    lines.extend([r"\end{longtable}", r"\end{center}"])
    return "\n".join(lines)


def latex_figure(path: Path, caption: str | None = None) -> str:
    if not path.exists():
        return "\n".join([r"\begin{quote}", f"图片文件未找到：{latex_escape(rel(path))}。", r"\end{quote}"])
    caption_text = clean_inline(caption or path.stem)
    path_text = rel(path)
    return "\n".join(
        [
            r"\begin{figure}[H]",
            r"\centering",
            rf"\includegraphics[width=0.92\textwidth]{{{path_text}}}",
            rf"\caption{{{caption_text}}}",
            r"\end{figure}",
        ]
    )


def indexed_table(table_id: str, table_lookup: dict[str, dict[str, Any]]) -> tuple[str, bool]:
    item = table_lookup.get(table_id)
    if not item:
        return (f"\\textbf{{[TABLE:{latex_escape(table_id)} 未找到]}}", False)
    caption = str(item.get("caption") or item.get("title") or table_id)
    path = resolve_path(str(item.get("path") or ""))
    return latex_table(read_csv_rows(path), caption), True


def indexed_figure(figure_id: str, figure_lookup: dict[str, dict[str, Any]]) -> tuple[str, bool]:
    item = figure_lookup.get(figure_id)
    if not item:
        return (f"\\textbf{{[FIGURE:{latex_escape(figure_id)} 未找到]}}", False)
    caption = str(item.get("caption") or item.get("title") or figure_id)
    path = resolve_path(str(item.get("path") or item.get("expected_path") or ""))
    return latex_figure(path, caption), path.exists()


def markdown_table(lines: list[str]) -> str:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", stripped):
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    return latex_table(rows)


def render_markdown_to_latex(text: str, table_lookup: dict[str, dict[str, Any]], figure_lookup: dict[str, dict[str, Any]]) -> tuple[str, dict[str, int]]:
    stats = {"headings": 0, "tables": 0, "figures": 0, "code_blocks": 0, "formulas": 0}
    out: list[str] = []
    lines = text.splitlines()
    idx = 0
    in_code = False
    code_lines: list[str] = []
    in_formula = False
    formula_lines: list[str] = []
    in_itemize = False

    def close_itemize() -> None:
        nonlocal in_itemize
        if in_itemize:
            out.append(r"\end{itemize}")
            in_itemize = False

    while idx < len(lines):
        line = lines[idx].rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            close_itemize()
            if in_code:
                out.extend([r"\begin{verbatim}", "\n".join(code_lines), r"\end{verbatim}"])
                stats["code_blocks"] += 1
                code_lines = []
                in_code = False
            else:
                in_code = True
                code_lines = []
            idx += 1
            continue
        if in_code:
            code_lines.append(line)
            idx += 1
            continue

        if stripped == "$$":
            close_itemize()
            if in_formula:
                out.append(r"\[")
                out.extend(formula_lines)
                out.append(r"\]")
                stats["formulas"] += 1
                formula_lines = []
                in_formula = False
            else:
                in_formula = True
                formula_lines = []
            idx += 1
            continue
        if in_formula:
            formula_lines.append(line)
            idx += 1
            continue

        if not stripped:
            close_itemize()
            out.append("")
            idx += 1
            continue

        table_marker = re.fullmatch(r"\[\[TABLE:([A-Za-z0-9_\-]+)\]\]", stripped, flags=re.IGNORECASE)
        if table_marker:
            close_itemize()
            rendered, ok = indexed_table(table_marker.group(1), table_lookup)
            out.append(rendered)
            if ok:
                stats["tables"] += 1
            idx += 1
            continue

        figure_marker = re.fullmatch(r"\[\[FIGURE:([A-Za-z0-9_\-]+)\]\]", stripped, flags=re.IGNORECASE)
        if figure_marker:
            close_itemize()
            rendered, ok = indexed_figure(figure_marker.group(1), figure_lookup)
            out.append(rendered)
            if ok:
                stats["figures"] += 1
            idx += 1
            continue

        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", stripped)
        if image_match:
            close_itemize()
            out.append(latex_figure(resolve_path(image_match.group(2)), image_match.group(1)))
            stats["figures"] += 1
            idx += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            close_itemize()
            table_lines = [stripped]
            idx += 1
            while idx < len(lines) and lines[idx].strip().startswith("|") and "|" in lines[idx].strip()[1:]:
                table_lines.append(lines[idx].strip())
                idx += 1
            out.append(markdown_table(table_lines))
            stats["tables"] += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            close_itemize()
            level = len(heading.group(1))
            title = clean_inline(heading.group(2))
            if level == 1:
                out.append(rf"\section{{{title}}}")
            elif level == 2:
                out.append(rf"\subsection{{{title}}}")
            else:
                out.append(rf"\subsubsection{{{title}}}")
            stats["headings"] += 1
            idx += 1
            continue

        numbered_heading = re.match(r"^((?:\d+\.){0,2}\d+)\s+(.+)$", stripped)
        if numbered_heading and len(stripped) <= 80:
            close_itemize()
            level = numbered_heading.group(1).count(".") + 1
            title = clean_inline(stripped)
            if level == 1:
                out.append(rf"\section{{{title}}}")
            elif level == 2:
                out.append(rf"\subsection{{{title}}}")
            else:
                out.append(rf"\subsubsection{{{title}}}")
            stats["headings"] += 1
            idx += 1
            continue

        list_item = re.match(r"^[-*]\s+(.+)$", stripped)
        if list_item:
            if not in_itemize:
                out.append(r"\begin{itemize}")
                in_itemize = True
            out.append(rf"\item {clean_inline(list_item.group(1))}")
            idx += 1
            continue

        close_itemize()
        out.append(clean_inline(stripped) + r"\par")
        idx += 1

    close_itemize()
    if code_lines:
        out.extend([r"\begin{verbatim}", "\n".join(code_lines), r"\end{verbatim}"])
        stats["code_blocks"] += 1
    if formula_lines:
        out.append(r"\[")
        out.extend(formula_lines)
        out.append(r"\]")
        stats["formulas"] += 1
    return "\n".join(out).strip() + "\n", stats


def latex_preamble(title: str) -> str:
    safe_title = clean_inline(title or "数学建模论文")
    return "\n".join(
        [
            r"\documentclass[UTF8,a4paper,12pt]{ctexart}",
            r"\usepackage{geometry}",
            r"\usepackage{amsmath,amssymb}",
            r"\usepackage{graphicx}",
            r"\usepackage{booktabs}",
            r"\usepackage{longtable}",
            r"\usepackage{array}",
            r"\usepackage{float}",
            r"\usepackage{hyperref}",
            r"\usepackage{caption}",
            r"\geometry{left=2.8cm,right=2.6cm,top=2.54cm,bottom=2.54cm}",
            r"\linespread{1.35}",
            r"\setlength{\parindent}{2em}",
            r"\setlength{\parskip}{0.35em}",
            r"\hypersetup{colorlinks=true,linkcolor=black,citecolor=black,urlcolor=blue}",
            rf"\title{{{safe_title}}}",
            r"\author{}",
            r"\date{}",
            "",
            r"\begin{document}",
            r"\maketitle",
            r"\tableofcontents",
            r"\newpage",
            "",
        ]
    )


def build_latex_document(markdown_text: str, outline: Any, table_index: Any, figure_index: Any) -> tuple[str, dict[str, int]]:
    title = outline.get("title", "") if isinstance(outline, dict) else ""
    body, stats = render_markdown_to_latex(
        markdown_text,
        build_lookup(table_index, "tables", "table_id"),
        build_lookup(figure_index, "figures", "figure_id"),
    )
    return latex_preamble(title) + body + "\n\\end{document}\n", stats


def compile_pdf(tex_file: Path, pdf_file: Path) -> dict[str, Any]:
    xelatex = shutil.which("xelatex")
    if not xelatex:
        return {"status": "SKIPPED", "reason": "未检测到 xelatex；已生成 .tex，PDF 编译跳过。"}
    command = [
        xelatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(OUTPUT_DIR),
        str(tex_file),
    ]
    runs = []
    status = "PASS"
    for _ in range(2):
        result = subprocess.run(command, cwd=str(BASE_DIR), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        runs.append({"returncode": result.returncode, "output_tail": result.stdout[-4000:]})
        if result.returncode != 0:
            status = "FAIL"
            break
    return {"status": status if pdf_file.exists() else "FAIL", "command": command, "pdf": rel(pdf_file), "runs": runs}


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# LaTeX Export Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Mode: `{report['mode']}`",
        f"- Source: `{report['source']}`",
        f"- TeX: `{report['tex']}`",
        f"- PDF: `{report.get('pdf', '')}`",
        f"- Compile status: `{report['compile']['status']}`",
        f"- Generated at: `{report['generated_at']}`",
        "",
        "## Stats",
    ]
    for key, value in report["stats"].items():
        lines.append(f"- {key}: `{value}`")
    if report.get("warnings"):
        lines.append("")
        lines.append("## Warnings")
        lines.extend(f"- {item}" for item in report["warnings"])
    if report.get("failures"):
        lines.append("")
        lines.append("## Failures")
        lines.extend(f"- {item}" for item in report["failures"])
    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Export final_paper_source.md to a CTeX LaTeX document.")
    parser.add_argument("--allow-draft", action="store_true", help="证据门禁未通过时生成 final_paper_draft.tex，不覆盖正式 LaTeX。")
    parser.add_argument("--compile", action="store_true", help="若本机有 xelatex，则尝试编译 PDF。")
    args = parser.parse_args()

    gate_passed, gate_reason = check_evidence_gate()
    draft_mode = False
    if not gate_passed:
        if not args.allow_draft:
            print("[LATEX BLOCKED] 证据门禁未通过，禁止生成正式 final_paper.tex。", file=sys.stderr)
            print(f"  原因：{gate_reason}", file=sys.stderr)
            print("  如需先看 LaTeX 草稿，请加 --allow-draft。", file=sys.stderr)
            return 2
        draft_mode = True
        print(f"[DRAFT MODE] 证据门禁未通过：{gate_reason}")

    source = source_path()
    if not source.exists():
        print(f"缺少正式论文 Markdown：{rel(SOURCE_FILE)}", file=sys.stderr)
        return 1

    tex_file = TEX_FILE_DRAFT if draft_mode else TEX_FILE_FORMAL
    pdf_file = PDF_FILE_DRAFT if draft_mode else PDF_FILE_FORMAL
    report_json = REPORT_JSON_DRAFT if draft_mode else REPORT_JSON_FORMAL
    report_md = REPORT_MD_DRAFT if draft_mode else REPORT_MD_FORMAL
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outline = load_json(OUTLINE_FILE)
    table_index = load_json(TABLE_INDEX_FILE)
    figure_index = load_json(FIGURE_INDEX_FILE)
    text = source.read_text(encoding="utf-8")
    latex_text, stats = build_latex_document(text, outline, table_index, figure_index)
    tex_file.write_text(latex_text, encoding="utf-8")

    compile_report = compile_pdf(tex_file, pdf_file) if args.compile else {"status": "SKIPPED", "reason": "未请求 --compile，仅生成 .tex。"}
    failures = []
    warnings = []
    if compile_report["status"] == "FAIL":
        failures.append("xelatex 编译失败，详见 latex_build_report.json。")
    elif compile_report["status"] == "SKIPPED":
        warnings.append(str(compile_report.get("reason", "PDF 编译跳过。")))

    report = {
        "schema_version": "1.0",
        "generated_by": "paper-formal-writer/scripts/format_formal_latex.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "FAIL" if failures else "GENERATED",
        "mode": "draft" if draft_mode else "formal",
        "source": rel(source),
        "tex": rel(tex_file),
        "pdf": rel(pdf_file) if pdf_file.exists() else "",
        "stats": stats,
        "compile": compile_report,
        "warnings": warnings,
        "failures": failures,
    }
    write_reports(report, report_json, report_md)

    label = "草稿 LaTeX" if draft_mode else "正式 LaTeX"
    print(f"{label}已生成：{rel(tex_file)}")
    print(f"LaTeX 报告已生成：{rel(report_md)}")
    if compile_report["status"] == "PASS":
        print(f"PDF 已生成：{rel(pdf_file)}")
    elif compile_report["status"] == "SKIPPED":
        print(f"[WARN] {compile_report.get('reason', '')}")
    else:
        print("[LATEX COMPILE FAIL] xelatex 编译失败，详见报告。", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

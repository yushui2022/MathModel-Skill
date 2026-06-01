"""Preflight check for MathModel Skill.

This script is the mandatory entry guard for the paper-workflow-orchestrator.
It produces an "input asset health report" and an exit code that downstream
agents must check before generating any paper content.

Design notes (per Codex review v2):
- Dependency checks are *triggered by file types present*, not a fixed list.
- We actually open candidate documents (PDF/DOCX/XLSX/CSV) instead of trusting
  file extensions.
- A lone .doc file does NOT count as an extractable problem document.
- PDFs: extract first 5 pages, escalate to 20 if zero chars; warn when char
  count is suspiciously low (< 200).
- Suspicious result template files (result*.xlsx / 结果*.xlsx) are flagged.
- A stale paper_output/final_paper.docx is a warning, not a failure.
- Exit code 0 only when no errors. Status string mirrors exit code.
- ASCII-only stdout (no emoji) to avoid Windows GBK issues.
- Writes JSON report to paper_output/preflight_report.json.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

DOC_EXTS = {".pdf", ".docx", ".md", ".txt"}
LEGACY_DOC_EXTS = {".doc"}
DATA_EXTS = {".xlsx", ".xls", ".csv", ".tsv", ".json"}
SUSPICIOUS_NAME_HINTS = ("result", "结果", "submit", "提交")

DEP_IMPORT_TO_PACKAGE = {
    "pypdf": "pypdf",
    "docx": "python-docx",
    "openpyxl": "openpyxl",
    "xlrd": "xlrd",
    "pandas": "pandas",
}


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def safe_import(module_name: str):
    try:
        return import_module(module_name)
    except Exception:
        return None


def list_problem_files(root: Path) -> list[Path]:
    pf = root / "problem_files"
    if not pf.exists() or not pf.is_dir():
        return []
    return sorted(p for p in pf.rglob("*") if p.is_file())


def rel_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def is_suspicious_name(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in SUSPICIOUS_NAME_HINTS)


def inspect_pdf(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": ".pdf",
        "extractable": False,
        "char_count": 0,
        "pages_sampled": 0,
        "warnings": [],
        "errors": [],
    }
    pypdf = safe_import("pypdf")
    if pypdf is None:
        info["errors"].append(
            "依赖缺失：pypdf。请运行 `pip install pypdf`（import 名也是 pypdf）。"
        )
        return info
    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as exc:
        info["errors"].append(f"无法打开 PDF：{type(exc).__name__}: {exc}")
        return info
    total_pages = len(reader.pages)
    info["total_pages"] = total_pages
    first_pass_limit = min(5, total_pages)
    text_chars = 0
    for i in range(first_pass_limit):
        try:
            text_chars += len(reader.pages[i].extract_text() or "")
        except Exception:
            pass
    info["pages_sampled"] = first_pass_limit
    if text_chars == 0 and total_pages > first_pass_limit:
        deeper_limit = min(20, total_pages)
        for i in range(first_pass_limit, deeper_limit):
            try:
                text_chars += len(reader.pages[i].extract_text() or "")
            except Exception:
                pass
        info["pages_sampled"] = deeper_limit
    info["char_count"] = text_chars
    if text_chars == 0:
        info["warnings"].append(
            "未抽出任何文本，可能是扫描版 PDF；需 OCR 或手动转录为 docx/md。"
        )
    elif text_chars < 200:
        info["warnings"].append(
            f"仅抽出 {text_chars} 个字符，文本量很少，请确认题面是否完整。"
        )
    else:
        info["extractable"] = True
    return info


def inspect_docx(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": ".docx",
        "extractable": False,
        "paragraphs": 0,
        "char_count": 0,
        "warnings": [],
        "errors": [],
    }
    docx_mod = safe_import("docx")
    if docx_mod is None:
        info["errors"].append(
            "依赖缺失：python-docx。请运行 `pip install python-docx`（import 名是 docx）。"
        )
        return info
    try:
        document = docx_mod.Document(str(path))
    except Exception as exc:
        info["errors"].append(f"无法打开 DOCX：{type(exc).__name__}: {exc}")
        return info
    paragraphs = list(document.paragraphs)
    info["paragraphs"] = len(paragraphs)
    chars = sum(len(p.text) for p in paragraphs)
    info["char_count"] = chars
    if chars == 0:
        info["warnings"].append("DOCX 段落总字符数为 0，文档可能为空。")
    else:
        info["extractable"] = True
    return info


def inspect_text_file(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": path.suffix.lower(),
        "extractable": False,
        "char_count": 0,
        "warnings": [],
        "errors": [],
    }
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            text = path.read_text(encoding=encoding)
            info["encoding"] = encoding
            info["char_count"] = len(text)
            info["extractable"] = len(text) > 0
            if len(text) == 0:
                info["warnings"].append("文件为空。")
            return info
        except Exception:
            continue
    info["errors"].append("无法以 utf-8 / gbk 等常见编码读取文件。")
    return info


def inspect_legacy_doc(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "ext": ".doc",
        "extractable": False,
        "warnings": [
            "老 .doc 格式无法可靠解析；请另存为 .docx 或 .pdf 后再放入 problem_files/。"
        ],
        "errors": [],
    }


def inspect_xlsx(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": path.suffix.lower(),
        "readable": False,
        "sheets": [],
        "warnings": [],
        "errors": [],
    }
    openpyxl = safe_import("openpyxl")
    if openpyxl is None:
        info["errors"].append(
            "依赖缺失：openpyxl。请运行 `pip install openpyxl`。"
        )
        return info
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        info["errors"].append(f"无法打开 XLSX：{type(exc).__name__}: {exc}")
        return info
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = ws.max_row or 0
            cols = ws.max_column or 0
            sample_cols: list[str] = []
            if rows > 0 and cols > 0:
                first_row = next(
                    ws.iter_rows(min_row=1, max_row=1, max_col=min(cols, 8), values_only=True),
                    None,
                )
                if first_row is not None:
                    sample_cols = [str(c) if c is not None else "" for c in first_row]
            info["sheets"].append(
                {"name": sheet_name, "rows": rows, "cols": cols, "sample_cols": sample_cols}
            )
            if rows == 0 or cols == 0:
                info["warnings"].append(f"工作表 {sheet_name} 为空。")
    finally:
        wb.close()
    # Merged cell detection requires non-read-only mode; do a cheap second open
    try:
        wb2 = openpyxl.load_workbook(path, read_only=False, data_only=True)
        merged_total = sum(len(wb2[s].merged_cells.ranges) for s in wb2.sheetnames)
        if merged_total > 0:
            info["warnings"].append(
                f"检测到 {merged_total} 处合并单元格，pandas/openpyxl 读取后可能错位，请人工核对。"
            )
        wb2.close()
    except Exception:
        pass
    info["readable"] = not info["errors"]
    return info


def inspect_xls(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": ".xls",
        "readable": False,
        "sheets": [],
        "warnings": [],
        "errors": [],
    }
    xlrd = safe_import("xlrd")
    if xlrd is None:
        info["errors"].append(
            "依赖缺失：xlrd（用于老 .xls）。请运行 `pip install xlrd`，或把文件另存为 .xlsx。"
        )
        return info
    try:
        book = xlrd.open_workbook(str(path))
    except Exception as exc:
        info["errors"].append(f"无法打开 XLS：{type(exc).__name__}: {exc}")
        return info
    for sheet in book.sheets():
        info["sheets"].append(
            {"name": sheet.name, "rows": sheet.nrows, "cols": sheet.ncols, "sample_cols": []}
        )
    info["readable"] = True
    return info


def inspect_csv(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": path.suffix.lower(),
        "readable": False,
        "encoding": None,
        "sep": None,
        "sample_cols": [],
        "warnings": [],
        "errors": [],
    }
    pandas = safe_import("pandas")
    if pandas is None:
        info["errors"].append(
            "依赖缺失：pandas。请运行 `pip install pandas`。"
        )
        return info
    last_exc: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        for sep in (None, ",", "\t", ";"):
            try:
                df = pandas.read_csv(
                    path, nrows=5, encoding=encoding,
                    sep=sep, engine="python",
                )
                info["encoding"] = encoding
                info["sep"] = sep if sep is not None else "auto"
                info["sample_cols"] = [str(c) for c in df.columns.tolist()]
                info["readable"] = True
                return info
            except Exception as exc:
                last_exc = exc
                continue
    info["errors"].append(
        f"无法以常见编码/分隔符读取 CSV。最后错误：{type(last_exc).__name__}: {last_exc}"
    )
    return info


def inspect_json(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": path.as_posix(),
        "ext": ".json",
        "readable": False,
        "warnings": [],
        "errors": [],
    }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        info["readable"] = True
        if isinstance(data, list):
            info["top_level"] = f"list[len={len(data)}]"
        elif isinstance(data, dict):
            info["top_level"] = f"dict[keys={list(data.keys())[:8]}]"
        else:
            info["top_level"] = type(data).__name__
    except Exception as exc:
        info["errors"].append(f"JSON 解析失败：{type(exc).__name__}: {exc}")
    return info


def classify_and_inspect(files: list[Path]) -> tuple[list[dict], list[dict], list[str]]:
    doc_candidates: list[dict] = []
    data_candidates: list[dict] = []
    suspicious: list[str] = []
    for p in files:
        ext = p.suffix.lower()
        if is_suspicious_name(p.name) and ext in {".xlsx", ".xls", ".csv"}:
            suspicious.append(p.as_posix())
        if ext == ".pdf":
            doc_candidates.append(inspect_pdf(p))
        elif ext == ".docx":
            doc_candidates.append(inspect_docx(p))
        elif ext in {".md", ".txt"}:
            doc_candidates.append(inspect_text_file(p))
        elif ext in LEGACY_DOC_EXTS:
            doc_candidates.append(inspect_legacy_doc(p))
        elif ext == ".xlsx":
            data_candidates.append(inspect_xlsx(p))
        elif ext == ".xls":
            data_candidates.append(inspect_xls(p))
        elif ext in {".csv", ".tsv"}:
            data_candidates.append(inspect_csv(p))
        elif ext == ".json":
            data_candidates.append(inspect_json(p))
    return doc_candidates, data_candidates, suspicious


def _by_resolved_path(items: list[dict]) -> dict[Path, dict]:
    result: dict[Path, dict] = {}
    for item in items:
        try:
            result[Path(str(item.get("path", ""))).resolve()] = item
        except Exception:
            continue
    return result


def build_input_manifest(
    root: Path,
    files: list[Path],
    doc_candidates: list[dict],
    data_candidates: list[dict],
    suspicious: list[str],
) -> dict[str, Any]:
    doc_by_path = _by_resolved_path(doc_candidates)
    data_by_path = _by_resolved_path(data_candidates)
    suspicious_set = {Path(item).resolve() for item in suspicious}
    entries: list[dict[str, Any]] = []

    for path in files:
        resolved = path.resolve()
        ext = path.suffix.lower()
        info = doc_by_path.get(resolved) or data_by_path.get(resolved) or {}
        warnings = list(info.get("warnings", []) or [])
        errors = list(info.get("errors", []) or [])
        role = "unsupported"
        confidence = 0.2
        usable_for_modeling = False
        requires_user_confirmation = False

        if resolved in suspicious_set:
            role = "result_template"
            confidence = 0.95
            warnings.append("文件名疑似结果提交模板，不可当作原始建模数据。")
        elif ext in {".pdf", ".docx", ".md", ".txt"}:
            role = "problem_statement" if info.get("extractable") else "problem_statement_unreadable"
            confidence = 0.85 if info.get("extractable") else 0.55
            requires_user_confirmation = not bool(info.get("extractable"))
        elif ext in LEGACY_DOC_EXTS:
            role = "problem_statement_unreadable"
            confidence = 0.75
            requires_user_confirmation = True
        elif ext in DATA_EXTS:
            role = "raw_data" if info.get("readable") else "raw_data_unreadable"
            confidence = 0.8 if info.get("readable") else 0.45
            usable_for_modeling = bool(info.get("readable"))
            requires_user_confirmation = not bool(info.get("readable"))
        else:
            warnings.append("不属于当前自动识别的题面或数据格式，需要人工确认用途。")
            requires_user_confirmation = True

        entry: dict[str, Any] = {
            "path": rel_path(path, root),
            "ext": ext,
            "role": role,
            "role_confidence": confidence,
            "usable_for_modeling": usable_for_modeling,
            "requires_user_confirmation": requires_user_confirmation,
            "warnings": warnings,
            "errors": errors,
        }
        for key in (
            "extractable",
            "char_count",
            "paragraphs",
            "readable",
            "sheets",
            "encoding",
            "sep",
            "sample_cols",
            "top_level",
        ):
            if key in info:
                entry[key] = info[key]
        entries.append(entry)

    role_counts: dict[str, int] = {}
    for entry in entries:
        role_counts[entry["role"]] = role_counts.get(entry["role"], 0) + 1

    return {
        "schema_version": "1.0",
        "generated_by": "paper-workflow-orchestrator/scripts/preflight_check.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": root.as_posix(),
        "entries": entries,
        "summary": {
            "file_count": len(entries),
            "role_counts": role_counts,
            "problem_statement_count": role_counts.get("problem_statement", 0),
            "raw_data_count": role_counts.get("raw_data", 0),
            "result_template_count": role_counts.get("result_template", 0),
            "requires_user_confirmation": any(item["requires_user_confirmation"] for item in entries),
        },
    }


def collect_dep_status(doc_candidates: list[dict], data_candidates: list[dict]) -> dict[str, Any]:
    needed: set[str] = set()
    for info in doc_candidates:
        ext = info.get("ext")
        if ext == ".pdf":
            needed.add("pypdf")
        elif ext == ".docx":
            needed.add("docx")
    for info in data_candidates:
        ext = info.get("ext")
        if ext == ".xlsx":
            needed.add("openpyxl")
        elif ext == ".xls":
            needed.add("xlrd")
        elif ext in {".csv", ".tsv"}:
            needed.add("pandas")
    missing: list[str] = []
    present: list[str] = []
    for mod in sorted(needed):
        if safe_import(mod) is None:
            missing.append(f"{DEP_IMPORT_TO_PACKAGE.get(mod, mod)} (import {mod})")
        else:
            present.append(mod)
    return {"required": sorted(needed), "missing": missing, "present": present}


def evaluate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    pf_dir = root / "problem_files"
    pf_exists = pf_dir.exists() and pf_dir.is_dir()
    files = list_problem_files(root) if pf_exists else []

    if not pf_exists:
        errors.append("缺少 problem_files/ 目录。请创建并放入题面 PDF/Word 和数据附件。")
    elif not files:
        errors.append("problem_files/ 为空。请放入题面（PDF/DOCX/MD/TXT）与数据附件。")

    doc_candidates, data_candidates, suspicious = classify_and_inspect(files)

    extractable_docs = [d for d in doc_candidates if d.get("extractable")]
    if files and not extractable_docs:
        errors.append(
            "problem_files/ 中没有可解析的题面文档。需要 .pdf / .docx / .md / .txt 之一，"
            "且能成功抽取到文本。"
        )

    # surface per-file errors into top-level errors
    for info in doc_candidates + data_candidates:
        for e in info.get("errors", []) or []:
            errors.append(f"{info['path']}: {e}")
        for w in info.get("warnings", []) or []:
            warnings.append(f"{info['path']}: {w}")

    deps = collect_dep_status(doc_candidates, data_candidates)
    if deps["missing"]:
        for m in deps["missing"]:
            errors.append(f"缺少依赖：{m}")

    if suspicious:
        for s in suspicious:
            warnings.append(
                f"{s}: 文件名疑似结果模板（含 result/结果/submit/提交），不可当作原始数据使用。"
            )

    stale_docx = root / "paper_output" / "final_paper.docx"
    stale = stale_docx.exists()
    if stale:
        warnings.append(
            f"{stale_docx.as_posix()}: 检测到旧的 final_paper.docx；如属历史产物建议归档或删除，"
            "以免误导 Agent 认为流程已完成。"
        )

    input_manifest = build_input_manifest(root, files, doc_candidates, data_candidates, suspicious)
    status = "PASS" if not errors else "FAIL"
    return {
        "schema_version": "1.0",
        "generated_by": "paper-workflow-orchestrator/scripts/preflight_check.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "root": root.as_posix(),
        "problem_files": {
            "exists": pf_exists,
            "non_empty": bool(files),
            "file_count": len(files),
            "doc_candidates": doc_candidates,
            "data_candidates": data_candidates,
            "suspicious_template_files": suspicious,
        },
        "deps": deps,
        "stale_output": {"final_paper_docx_exists": stale},
        "input_manifest": {
            "path": "paper_output/input_manifest.json",
            "summary": input_manifest["summary"],
        },
        "_input_manifest_payload": input_manifest,
        "errors": errors,
        "warnings": warnings,
    }


def write_report(report: dict[str, Any], root: Path) -> Path:
    out_dir = root / "paper_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = report.pop("_input_manifest_payload", None)
    if isinstance(manifest, dict):
        (out_dir / "input_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    out_file = out_dir / "preflight_report.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file


def main() -> int:
    configure_utf8_stdio()
    root = Path.cwd().resolve()
    report = evaluate(root)
    out_file = write_report(report, root)

    if report["status"] == "PASS":
        print("[PRECHECK PASS]")
        print(f"  Report: {out_file.relative_to(root).as_posix()}")
        for w in report["warnings"][:8]:
            print(f"  [warn] {w}")
        rest = len(report["warnings"]) - 8
        if rest > 0:
            print(f"  [warn] ...另有 {rest} 条警告，详见报告。")
        return 0

    print("[PRECHECK FAIL]")
    print(f"  Report: {out_file.relative_to(root).as_posix()}")
    for e in report["errors"][:12]:
        print(f"  - {e}")
    rest = len(report["errors"]) - 12
    if rest > 0:
        print(f"  - ...另有 {rest} 条错误，详见报告。")
    print()
    print("修复后请重新运行本脚本。在 [PRECHECK PASS] 出现前，禁止生成论文内容。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

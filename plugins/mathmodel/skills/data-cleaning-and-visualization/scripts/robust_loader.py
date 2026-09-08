from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any


BASE_DIR = Path.cwd().resolve()
OUTPUT_DIR = BASE_DIR / "paper_output"
REPORT_FILE = OUTPUT_DIR / "data_cleaned" / "load_report.json"
INPUT_MANIFEST_FILE = OUTPUT_DIR / "input_manifest.json"

DATA_EXTS = {".xlsx", ".xls", ".csv", ".tsv", ".json"}
PDF_EXTS = {".pdf"}


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def safe_import(name: str):
    try:
        return import_module(name)
    except Exception:
        return None


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_entry(path: Path, kind: str) -> dict[str, Any]:
    return {
        "path": rel(path),
        "kind": kind,
        "ext": path.suffix.lower(),
        "readable": False,
        "warnings": [],
        "errors": [],
    }


def inspect_xlsx(path: Path) -> dict[str, Any]:
    info = file_entry(path, "spreadsheet")
    openpyxl = safe_import("openpyxl")
    if openpyxl is None:
        info["errors"].append("缺少依赖 openpyxl，无法读取 .xlsx。")
        return info
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        info["errors"].append(f"无法打开 xlsx：{type(exc).__name__}: {exc}")
        return info
    sheets = []
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = ws.max_row or 0
            cols = ws.max_column or 0
            sample_cols: list[str] = []
            if rows and cols:
                first_row = next(ws.iter_rows(min_row=1, max_row=1, max_col=min(cols, 12), values_only=True), None)
                if first_row:
                    sample_cols = [str(value) if value is not None else "" for value in first_row]
            sheets.append({"name": sheet_name, "rows": rows, "cols": cols, "sample_cols": sample_cols})
            if rows == 0 or cols == 0:
                info["warnings"].append(f"工作表 {sheet_name} 为空。")
    finally:
        wb.close()
    try:
        wb2 = openpyxl.load_workbook(path, read_only=False, data_only=True)
        merged_count = sum(len(wb2[name].merged_cells.ranges) for name in wb2.sheetnames)
        wb2.close()
        if merged_count:
            info["warnings"].append(f"检测到 {merged_count} 处合并单元格，自动读取结果需人工核对。")
    except Exception:
        pass
    info["readable"] = True
    info["sheets"] = sheets
    return info


def inspect_xls(path: Path) -> dict[str, Any]:
    info = file_entry(path, "spreadsheet")
    xlrd = safe_import("xlrd")
    if xlrd is None:
        info["errors"].append("缺少依赖 xlrd，无法读取老 .xls；建议另存为 .xlsx。")
        return info
    try:
        book = xlrd.open_workbook(str(path))
    except Exception as exc:
        info["errors"].append(f"无法打开 xls：{type(exc).__name__}: {exc}")
        return info
    info["sheets"] = [{"name": sheet.name, "rows": sheet.nrows, "cols": sheet.ncols, "sample_cols": []} for sheet in book.sheets()]
    info["readable"] = True
    return info


def inspect_csv(path: Path) -> dict[str, Any]:
    info = file_entry(path, "table")
    pandas = safe_import("pandas")
    if pandas is not None:
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            for sep in (None, ",", "\t", ";"):
                try:
                    df = pandas.read_csv(path, nrows=20, encoding=encoding, sep=sep, engine="python")
                    info.update(
                        {
                            "readable": True,
                            "encoding": encoding,
                            "sep": sep if sep is not None else "auto",
                            "rows_sampled": int(len(df)),
                            "cols": int(len(df.columns)),
                            "sample_cols": [str(col) for col in df.columns.tolist()],
                        }
                    )
                    if df.empty:
                        info["warnings"].append("CSV 读取成功但样本为空。")
                    return info
                except Exception as exc:
                    last_error = exc
        info["errors"].append(f"pandas 无法读取：{type(last_error).__name__}: {last_error}")
        return info

    # Fallback without pandas.
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(4096)
                dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
                handle.seek(0)
                reader = csv.reader(handle, dialect)
                first = next(reader, [])
            info.update({"readable": True, "encoding": encoding, "sep": getattr(dialect, "delimiter", ","), "sample_cols": [str(item) for item in first]})
            return info
        except Exception:
            continue
    info["errors"].append("无法以常见编码读取 CSV/TSV。")
    return info


def inspect_json(path: Path) -> dict[str, Any]:
    info = file_entry(path, "json")
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            info["readable"] = True
            info["encoding"] = encoding
            if isinstance(data, dict):
                info["top_level"] = "dict"
                info["sample_keys"] = list(data.keys())[:12]
            elif isinstance(data, list):
                info["top_level"] = "list"
                info["length"] = len(data)
                if data and isinstance(data[0], dict):
                    info["sample_keys"] = list(data[0].keys())[:12]
            else:
                info["top_level"] = type(data).__name__
            return info
        except Exception:
            continue
    info["errors"].append("JSON 无法以常见编码解析。")
    return info


def inspect_pdf(path: Path) -> dict[str, Any]:
    info = file_entry(path, "pdf_diagnostic")
    info["readable"] = False
    pypdf = safe_import("pypdf")
    if pypdf is None:
        info["warnings"].append("缺少 pypdf，无法诊断 PDF 文本。")
    else:
        try:
            reader = pypdf.PdfReader(str(path))
            total_pages = len(reader.pages)
            sample_pages = min(5, total_pages)
            char_count = 0
            for index in range(sample_pages):
                try:
                    char_count += len(reader.pages[index].extract_text() or "")
                except Exception:
                    pass
            info["pdf_pages"] = total_pages
            info["text_pages_sampled"] = sample_pages
            info["text_char_count"] = char_count
            if char_count == 0:
                info["warnings"].append("PDF 前几页未抽出文本，可能是扫描版；请 OCR 或人工转为 CSV/XLSX。")
            elif char_count < 200:
                info["warnings"].append("PDF 可抽文本很少，请核对题面/表格是否完整。")
        except Exception as exc:
            info["warnings"].append(f"PDF 文本诊断失败：{type(exc).__name__}: {exc}")

    pdfplumber = safe_import("pdfplumber")
    if pdfplumber is None:
        info["table_diagnostic"] = {"available": False, "warning": "未安装 pdfplumber，未做 PDF 表格诊断。"}
    else:
        try:
            table_count = 0
            table_samples: list[dict[str, Any]] = []
            with pdfplumber.open(path) as pdf:
                for page_index, page in enumerate(pdf.pages[:5], start=1):
                    tables = page.extract_tables() or []
                    table_count += len(tables)
                    for table in tables[:3]:
                        table_samples.append(
                            {
                                "page": page_index,
                                "rows": len(table),
                                "cols": max((len(row) for row in table), default=0),
                            }
                        )
            info["table_diagnostic"] = {
                "available": True,
                "table_count_first_5_pages": table_count,
                "samples": table_samples[:8],
                "warning": "PDF 表格抽取仅供诊断，不能直接视为可信原始数据；正式建模建议转 CSV/XLSX 后人工核对。",
            }
        except Exception as exc:
            info["table_diagnostic"] = {"available": False, "warning": f"PDF 表格诊断失败：{type(exc).__name__}: {exc}"}
    return info


def iter_input_files(input_dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for text in input_dirs:
        path = (BASE_DIR / text).resolve()
        if path.exists() and path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
    return sorted(files, key=lambda item: item.as_posix().lower())


def load_input_manifest() -> dict[str, Any] | None:
    if not INPUT_MANIFEST_FILE.exists():
        return None
    try:
        data = json.loads(INPUT_MANIFEST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def resolve_manifest_path(path_text: str) -> Path:
    path = Path(str(path_text or ""))
    if path.is_absolute():
        return path
    return BASE_DIR / path


def iter_manifest_raw_data(manifest: dict[str, Any]) -> tuple[list[Path], list[dict[str, Any]]]:
    files: list[Path] = []
    skipped: list[dict[str, Any]] = []
    entries = manifest.get("entries") if isinstance(manifest, dict) else []
    if not isinstance(entries, list):
        return files, skipped
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path_text = str(entry.get("path") or "")
        role = str(entry.get("role") or "")
        usable = bool(entry.get("usable_for_modeling"))
        path = resolve_manifest_path(path_text)
        if role == "raw_data" and usable:
            files.append(path)
        else:
            skipped.append(
                {
                    "path": path_text,
                    "role": role,
                    "reason": "not_raw_modeling_data" if role != "raw_data" else "not_usable_for_modeling",
                }
            )
    return sorted(files, key=lambda item: item.as_posix().lower()), skipped


def inspect_file(path: Path) -> dict[str, Any] | None:
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return inspect_xlsx(path)
    if ext == ".xls":
        return inspect_xls(path)
    if ext in {".csv", ".tsv"}:
        return inspect_csv(path)
    if ext == ".json":
        return inspect_json(path)
    if ext == ".pdf":
        return inspect_pdf(path)
    return None


def evaluate(input_dirs: list[str], use_manifest: bool = True) -> dict[str, Any]:
    input_manifest = load_input_manifest() if use_manifest else None
    skipped_files: list[dict[str, Any]] = []
    if input_manifest:
        files, skipped_files = iter_manifest_raw_data(input_manifest)
    else:
        files = iter_input_files(input_dirs)
    data_files: list[dict[str, Any]] = []
    pdf_diagnostics: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    if use_manifest and input_manifest is None and INPUT_MANIFEST_FILE.exists():
        warnings.append("input_manifest.json 存在但无法解析，已回退为扫描 input_dirs。")
    if input_manifest:
        warnings.extend(
            f"{item['path']}: 跳过 role={item['role']}（{item['reason']}）。"
            for item in skipped_files
            if item.get("role") in {"result_template", "problem_statement", "problem_statement_unreadable"}
        )

    for path in files:
        info = inspect_file(path)
        if info is None:
            continue
        if path.suffix.lower() in PDF_EXTS:
            pdf_diagnostics.append(info)
        else:
            data_files.append(info)
        for item in info.get("warnings", []) or []:
            warnings.append(f"{info['path']}: {item}")
        for item in info.get("errors", []) or []:
            errors.append(f"{info['path']}: {item}")

    readable_data = [item for item in data_files if item.get("readable")]
    if not data_files:
        warnings.append("未发现 xlsx/xls/csv/tsv/json 数据文件；若数据在 PDF 中，请先人工核对并转为 CSV/XLSX。")
    elif not readable_data:
        errors.append("发现数据文件但没有任何文件可读。")

    return {
        "schema_version": "1.0",
        "generated_by": "data-cleaning-and-visualization/scripts/robust_loader.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASS" if not errors else "FAIL",
        "input_dirs": input_dirs,
        "input_manifest_used": bool(input_manifest),
        "input_manifest": rel(INPUT_MANIFEST_FILE) if input_manifest else "",
        "input_manifest_sha256": sha256_file(INPUT_MANIFEST_FILE) if input_manifest else "",
        "skipped_files": skipped_files,
        "data_files": data_files,
        "pdf_diagnostics": pdf_diagnostics,
        "summary": {
            "file_count_scanned": len(files),
            "data_file_count": len(data_files),
            "readable_data_file_count": len(readable_data),
            "pdf_file_count": len(pdf_diagnostics),
        },
        "warnings": warnings,
        "errors": errors,
    }


def write_report(report: dict[str, Any]) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Diagnose MathModel input data files and write load_report.json.")
    parser.add_argument("--input-dir", action="append", dest="input_dirs", default=None, help="Input directory to scan. Can be repeated.")
    args = parser.parse_args()
    input_dirs = args.input_dirs or ["problem_files", "crawled_data"]
    report = evaluate(input_dirs, use_manifest=args.input_dirs is None)
    write_report(report)
    print(f"load report: {rel(REPORT_FILE)}")
    if report["status"] == "PASS":
        print("[LOAD PASS]")
        for warning in report["warnings"][:8]:
            print(f" [warn] {warning}")
        return 0
    print("[LOAD FAIL]")
    for error in report["errors"][:12]:
        print(f" - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

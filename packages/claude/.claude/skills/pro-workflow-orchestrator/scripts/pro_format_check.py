from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

from pro_contracts import contract, output_root, read_json, sha256_file, write_json


def ngrams(text: str, size: int = 3) -> set[str]:
    normalized = re.sub(r"\s+", "", text).casefold()
    return {normalized[index:index + size] for index in range(max(0, len(normalized) - size + 1))}


def result(status: bool, **details) -> dict:
    return {"status": "PASS" if status else "BLOCKED", **details}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Pro DOCX/PDF rendering and source consistency.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    root = output_root(args.project_root.resolve(), args.output_root)
    source = root / "final_paper_source.md"
    docx = root / "final_paper.docx"
    pdf = root / "final_paper.pdf"
    errors: list[str] = []
    source_text = source.read_text(encoding="utf-8") if source.is_file() else ""
    docx_text = ""
    formula_count = 0
    figure_count = 0
    if not source_text:
        errors.append("formal Markdown source is missing or empty")
    try:
        with zipfile.ZipFile(docx) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        docx_text = re.sub(r"<[^>]+>", "", xml)
        formula_count = xml.count("<m:oMath")
        figure_count = xml.count("<w:drawing")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        errors.append(f"DOCX cannot be inspected: {exc}")
    pdf_text = ""
    page_count = 0
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf))
        page_count = len(reader.pages)
        pdf_text = "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        errors.append(f"PDF cannot be inspected: {exc}")

    source_ngrams = ngrams(source_text)
    docx_ngrams = ngrams(docx_text)
    pdf_ngrams = ngrams(pdf_text)
    docx_pdf_overlap = len(docx_ngrams & pdf_ngrams) / max(1, min(len(docx_ngrams), len(pdf_ngrams)))
    source_docx_overlap = len(source_ngrams & docx_ngrams) / max(1, min(len(source_ngrams), len(docx_ngrams)))
    formula_ok = formula_count > 0
    figure_ok = figure_count > 0
    pagination_ok = page_count > 0 and len(pdf_text.strip()) >= 200
    consistency_ok = docx_pdf_overlap >= 0.65 and source_docx_overlap >= 0.55
    if not formula_ok:
        errors.append("DOCX contains no native OMML formula")
    if not figure_ok:
        errors.append("DOCX contains no embedded figure")
    if not pagination_ok:
        errors.append("PDF has no pages or insufficient extractable text")
    if not consistency_ok:
        errors.append("Markdown/DOCX/PDF text consistency is below threshold")

    source_ledger = read_json(root / "source_ledger.json") if (root / "source_ledger.json").is_file() else {"sources": []}
    source_ids = {item.get("source_id") for item in source_ledger.get("sources", []) if item.get("source_id")}
    cited_ids = set(re.findall(r"\[(S[\w.-]+)\]", source_text))
    citation_ok = not source_ids or source_ids <= cited_ids
    if not citation_ok:
        errors.append("formal source does not cite every source_ledger source ID")

    hashes = {
        name: sha256_file(path)
        for name, path in {
            "final_paper_source.md": source,
            "final_paper.docx": docx,
            "final_paper.pdf": pdf,
        }.items()
        if path.is_file()
    }
    report = contract(
        producer_role="p9-docx-pdf-verifier",
        status="PASS" if not errors else "BLOCKED",
        input_hashes=hashes,
        formula_check=result(formula_ok, omml_count=formula_count),
        figure_check=result(figure_ok, drawing_count=figure_count),
        pagination_check=result(pagination_ok, page_count=page_count, extractable_characters=len(pdf_text.strip())),
        citation_check=result(citation_ok, source_ids=sorted(source_ids), cited_source_ids=sorted(cited_ids)),
        docx_pdf_consistency=result(consistency_ok, docx_pdf_ngram_overlap=docx_pdf_overlap, source_docx_ngram_overlap=source_docx_overlap),
        errors=errors,
    )
    write_json(root / "final_format_report.json", report)
    for error in errors:
        print(f"[BLOCKED] {error}")
    print(f"[{'PASS' if not errors else 'BLOCKED'}] Pro DOCX/PDF format gate")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import importlib.util
import io
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

from pro_contracts import check_hashes, contract, output_root, read_json, sha256_file, write_json
from pro_paper_audit import check_paper
from pro_authoring_policy import check_page_counts, locate_pdf_sections, read_policy


def normalized(text: str) -> str:
    return re.sub(r"\W+", "", text).casefold()


def ngrams(text: str, size: int = 3) -> Counter:
    text = normalized(text)
    return Counter(text[i:i + size] for i in range(max(0, len(text) - size + 1)))


def text_coverage(expected: str, actual: str) -> tuple[float, float]:
    left, right = ngrams(expected), ngrams(actual)
    shared = sum((left & right).values())
    return shared / max(1, sum(left.values())), shared / max(1, sum(right.values()))


def expected_docx(root: Path) -> bytes:
    writer_dir = Path(__file__).resolve().parents[2] / "paper-formal-writer" / "scripts"
    sys.path.insert(0, str(writer_dir))
    spec = importlib.util.spec_from_file_location("pro_expected_writer", writer_dir / "format_formal_docx.py")
    writer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(writer)
    writer.BASE_DIR, writer.OUTPUT_DIR = root.parent, root
    from docx import Document
    document = Document()
    writer.configure_document(document)
    writer.render_markdown(document, (root / "final_paper_source.md").read_text(encoding="utf-8"), {}, {})
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def canonical_xml(value: bytes) -> bytes:
    root = etree.fromstring(value, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    for node in root.iter():
        for key in list(node.attrib):
            if "rsid" in key:
                del node.attrib[key]
    return etree.tostring(root, method="c14n")


def inspect_documents(root: Path, *, require_visual: bool = True) -> tuple[list[str], dict]:
    errors = check_paper(root)
    plan = read_json(root / "paper_plan.json")
    with zipfile.ZipFile(root / "final_paper.docx") as actual, zipfile.ZipFile(io.BytesIO(expected_docx(root))) as expected:
        actual_xml = actual.read("word/document.xml")
        if canonical_xml(actual_xml) != canonical_xml(expected.read("word/document.xml")):
            errors.append("DOCX content does not match the complete formal source")
        for name in ("word/styles.xml", "word/numbering.xml"):
            if canonical_xml(actual.read(name)) != canonical_xml(expected.read(name)):
                errors.append(f"DOCX formatting differs from the formal source: {name}")
        media = lambda archive: {n: archive.read(n) for n in archive.namelist() if n.startswith("word/media/")}
        if media(actual) != media(expected):
            errors.append("DOCX embedded figures differ from the formal source")
        xml = etree.fromstring(actual_xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
        docx_text = "".join(xml.xpath("//w:t/text() | //m:t/text()", namespaces=ns))
        formula_count = len(xml.xpath("//m:oMath", namespaces=ns))
        figure_count = len(xml.xpath("//w:drawing", namespaces=ns))
    from formula_omml import source_formula_tokens
    source = (root / "final_paper_source.md").read_text(encoding="utf-8")
    source = re.sub(r"```.*?```|<!--.*?-->", "", source, flags=re.S)
    if formula_count != len(source_formula_tokens(source)):
        errors.append("some source formulas were not preserved as native Word equations")
    import pymupdf
    pages = []
    with pymupdf.open(root / "final_paper.pdf") as pdf:
        text = "".join(page.get_text() for page in pdf)
        for index, page in enumerate(pdf, 1):
            if len(page.get_text().strip()) < 20 and not page.get_images():
                errors.append(f"PDF page {index} is blank")
            for block in page.get_text("blocks"):
                if block[0] < -1 or block[1] < -1 or block[2] > page.rect.width + 1 or block[3] > page.rect.height + 1:
                    errors.append(f"PDF page {index} has content outside page bounds")
            pages.append(index)
        try:
            page_errors, page_details = check_page_counts(read_policy(root), locate_pdf_sections(plan, pdf), len(pdf))
            errors.extend(page_errors)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"paper page accounting failed: {exc}")
            page_details = {}
    coverage, precision = text_coverage(docx_text, text)
    if not pages or coverage < 0.90 or precision < 0.85:
        errors.append("DOCX/PDF bidirectional text coverage failed")
    for section in plan["sections"]:
        if normalized(section["title"]) not in normalized(text):
            errors.append(f"PDF is missing section: {section['section_id']}")
    for claim in read_json(root / "claim_evidence_map.json")["claims"]:
        for item in claim.get("numeric_evidence", []):
            if not re.search(r"(?<![\d.])" + re.escape(item["display"]) + r"(?!\d|\.\d)", text):
                errors.append(f"PDF omits computed value for {claim['claim_id']}")
    render_path = root / "render_manifest.json"
    render = read_json(render_path)
    expected_hashes = {n: sha256_file(root / n) for n in ("final_paper.docx", "final_paper.pdf")}
    if render.get("input_hashes") != expected_hashes or not render.get("libreoffice_version") or render.get("exit_code") != 0:
        errors.append("PDF is not bound to a successful current LibreOffice rendering")
    render_pages = render.get("pages", [])
    if [p.get("page") for p in render_pages] != pages:
        errors.append("rendered page inventory differs from PDF")
    errors += check_hashes(root, {p["path"]: p.get("sha256") for p in render_pages})
    if require_visual:
        visual = read_json(root / "visual_review.json")
        if visual.get("render_manifest_sha256") != sha256_file(render_path) or visual.get("status") != "PASS":
            errors.append("visual review is missing or stale")
        reviews = visual.get("pages", [])
        if [p.get("page") for p in reviews] != pages:
            errors.append("visual review must cover every page exactly once")
        for item, rendered in zip(reviews, render_pages):
            if (item.get("image_sha256") != rendered.get("sha256") or item.get("status") != "PASS"
                    or not item.get("observations") or item.get("issues") != []):
                errors.append(f"page {item.get('page')}: visual review incomplete or has unresolved issues")
    return errors, {"page_count": len(pages), "docx_to_pdf_coverage": coverage, "pdf_to_docx_coverage": precision,
                    "native_formulas": formula_count, "figures": figure_count, "paper_scope": page_details}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate full manuscript, DOCX, rendered PDF and every reviewed page.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = output_root(args.project_root.resolve())
    details = {}
    try:
        errors, details = inspect_documents(root)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        errors = [str(exc)]
    names = ("final_paper_source.md", "final_paper.docx", "final_paper.pdf", "paper_plan.json", "render_manifest.json", "visual_review.json", "pro_config.json", "problem_consensus.json")
    write_json(root / "final_format_report.json", contract(
        producer_role="pro-format-verifier", status="BLOCKED" if errors else "PASS",
        input_hashes={n: sha256_file(root / n) for n in names if (root / n).is_file()}, details=details, errors=errors,
    ))
    for error in errors:
        print(f"[BLOCKED] {error}")
    print(f"[{'BLOCKED' if errors else 'PASS'}] Complete DOCX/PDF and visual gate")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

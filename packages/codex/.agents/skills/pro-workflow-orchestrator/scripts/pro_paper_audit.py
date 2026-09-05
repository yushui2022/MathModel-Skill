from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from pro_contracts import check_hashes, contract, output_root, read_json, safe_path, sha256_file, write_json
from pro_validation import objects, unique


def visible_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    return re.sub(r"[`#*|]", "", text)


def check_paper(root: Path) -> list[str]:
    errors = []
    text = (root / "final_paper_source.md").read_text(encoding="utf-8")
    plan = read_json(root / "paper_plan.json")
    claims = unique(objects(read_json(root / "claim_evidence_map.json").get("claims"), "claims"), "claim_id")
    sections = unique(objects(plan.get("sections"), "paper sections"), "section_id")
    if not plan.get("title") or not plan.get("language"):
        errors.append("paper plan needs title and language")
    target = plan.get("target_characters")
    length = len(re.sub(r"\s+", "", visible_text(text)))
    if type(target) is not int or target < 1000 or length < target * 0.8:
        errors.append("manuscript is shorter than 80% of its declared substantive length")
    if re.search(r"TODO|TBD|lorem ipsum|待补充|待完善|图片文件未找到|图片无法插入|表格数据文件暂不可读取|checkpoint_ledger|pro_gate_report", text, re.I):
        errors.append("manuscript contains placeholders or internal workflow text")
    headings = [(m.start(), m.group(2).strip(), len(m.group(1))) for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.M)]
    if [title for _, title, level in headings if level == 1] != [plan.get("title")]:
        errors.append("formal manuscript title does not match its writing plan")
    spans = {}
    previous = -1
    for section_id, section in sections.items():
        matches = [i for i, (_, title, _) in enumerate(headings) if title == section.get("title")]
        if len(matches) != 1:
            errors.append(f"missing or duplicate paper section: {section_id}")
            continue
        index = matches[0]
        start = headings[index][0]
        end = next((h[0] for h in headings[index + 1:] if h[2] <= headings[index][2]), len(text))
        if start <= previous:
            errors.append("paper sections do not follow the declared order")
        previous = start
        spans[section_id] = text[start:end]
        if len(re.sub(r"\s+", "", visible_text(spans[section_id]))) < section.get("minimum_characters", 50):
            errors.append(f"paper section is underdeveloped: {section_id}")
    markers = re.findall(r"<!--\s*claim:([A-Za-z0-9_.-]+)\s*-->", text)
    if set(markers) != set(claims):
        errors.append("manuscript claim markers do not cover exactly the frozen claims")
    for claim_id, claim in claims.items():
        section_text = spans.get(claim.get("section_id"), "")
        paragraphs = [p for p in re.split(r"\n\s*\n", section_text) if re.search(r"<!--\s*claim:" + re.escape(claim_id) + r"\s*-->", p)]
        if not paragraphs:
            errors.append(f"{claim_id}: claim is missing from its planned section")
        for ref in claim.get("numeric_evidence", []):
            token = re.escape(str(ref.get("display", "")))
            if not any(re.search(r"(?<![\d.])" + token + r"(?!\d|\.\d)", p) for p in paragraphs):
                errors.append(f"{claim_id}: required computed number missing from claim paragraph")
    cited = set(re.findall(r"\[(S[A-Za-z0-9_.-]+)\]", text))
    sources = unique(objects(read_json(root / "source_ledger.json").get("sources"), "sources", empty=True), "source_id")
    required_sources = {i for c in claims.values() for i in c.get("source_ids", [])}
    if cited - set(sources) or required_sources - cited:
        errors.append("manuscript citations contain unknown IDs or omit a claim source")
    paragraphs = [re.sub(r"\W+", "", p).casefold() for p in re.split(r"\n\s*\n", visible_text(text))]
    if any(n > 1 for p, n in Counter(p for p in paragraphs if len(p) >= 100).items()):
        errors.append("manuscript contains duplicated substantive paragraphs")
    from difflib import SequenceMatcher
    substantive = [p for p in paragraphs if len(p) >= 150]
    if any(SequenceMatcher(None, a, b, autojunk=False).ratio() > 0.92 for i, a in enumerate(substantive) for b in substantive[i + 1:]):
        errors.append("manuscript contains near-duplicate substantive paragraphs")
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    expected_images = objects(plan.get("figures", []), "paper figures", empty=True)
    planned_paths = {item.get("path") for item in expected_images}
    if set(images) != planned_paths or len(images) != len(planned_paths):
        errors.append("manuscript figures do not match the plan")
    freeze = read_json(root / "evidence_freeze.json")
    from PIL import Image, ImageStat
    for item in expected_images:
        name = item["path"]
        errors.extend(check_hashes(root, {name: item.get("sha256")}))
        if freeze.get("file_hashes", {}).get(name) != item.get("sha256"):
            errors.append(f"paper figure not frozen: {name}")
        with Image.open(safe_path(root, name)) as image:
            image.load()
            if min(image.size) < 100 or max(ImageStat.Stat(image.convert("RGB")).stddev) < 2:
                errors.append(f"placeholder or blank figure: {name}")
    if "[[TABLE:" in text or "[[FIGURE:" in text:
        errors.append("use explicit Markdown tables and images in the formal source")
    writer_dir = Path(__file__).resolve().parents[2] / "paper-formal-writer" / "scripts"
    import sys
    sys.path.insert(0, str(writer_dir))
    from formula_omml import source_formula_tokens, latex_to_omml
    math_text = re.sub(r"```.*?```", "", text, flags=re.S)
    tokens = source_formula_tokens(math_text)
    remaining = list(math_text)
    for formula in tokens:
        remaining[formula.start:formula.end] = " " * (formula.end - formula.start)
        try:
            depth = 0
            for brace in re.findall(r"(?<!\\)[{}]", formula.latex):
                depth += 1 if brace == "{" else -1
                if depth < 0:
                    raise ValueError("unbalanced LaTeX braces")
            if depth:
                raise ValueError("unbalanced LaTeX braces")
            latex_to_omml(formula.latex)
        except Exception as exc:
            errors.append(f"formula cannot be converted: {exc}")
    if re.search(r"(?<!\\)\$|\\[\[\]()]", "".join(remaining)):
        errors.append("manuscript has unmatched math delimiters; escape literal currency dollars")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the formal manuscript against frozen evidence and its writing plan.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = output_root(args.project_root.resolve())
    from pro_checkpoint import require_checkpoints
    from pro_validation import check_freeze
    errors = require_checkpoints(args.project_root.resolve(), root, 3)
    try:
        errors += check_freeze(root, read_json(root / "evidence_freeze.json"))
        errors += check_paper(root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    write_json(root / "paper_audit.json", contract(
        producer_role="pro-paper-auditor", status="BLOCKED" if errors else "PASS",
        input_hashes={n: sha256_file(root / n) for n in ("final_paper_source.md", "paper_plan.json", "evidence_freeze.json") if (root / n).is_file()},
        errors=errors,
    ))
    for error in errors:
        print(f"[BLOCKED] {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

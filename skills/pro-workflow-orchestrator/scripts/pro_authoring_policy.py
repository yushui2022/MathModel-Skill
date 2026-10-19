"""Checkpoint-bound delivery scope and observable long-paper completeness checks."""
from __future__ import annotations

import re
from pathlib import Path

from pro_contracts import read_json, sha256_file


MODES = ("competition", "short-report", "smoke-test")
COMPONENTS = ("rationale", "derivation", "method", "results", "validation", "limitations")
SECTION_KINDS = {"abstract", "body", "references", "appendix", "ai-disclosure", "frontmatter"}
CONTESTS = {
    "generic": {"page_scope": "main", "hard_max_pages": None, "abstract_max_pages": None, "source_url": None},
    "cumcm-2026": {
        "page_scope": "body", "hard_max_pages": 30, "abstract_max_pages": 1,
        "source_url": "https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html",
    },
    "mcm-2026": {
        "page_scope": "solution", "hard_max_pages": 25, "abstract_max_pages": 1,
        "source_url": "https://www.contest.comap.com/undergraduate/contests/mcm/contests/2026/problems/2026_MCM_Problem_C.pdf",
    },
}


def make_policy(mode="competition", contest="generic", target_pages=None,
                minimum_body_characters=None, scope_reason="") -> dict:
    if mode not in MODES or contest not in CONTESTS:
        raise ValueError("unknown paper delivery mode or contest profile")
    default_target = [18, 24] if mode == "competition" else [1, 8]
    default_minimum = 8000 if mode == "competition" else 1000
    target = default_target if target_pages is None else target_pages
    minimum = default_minimum if minimum_body_characters is None else minimum_body_characters
    if (not isinstance(target, list) or len(target) != 2 or any(type(n) is not int for n in target)
            or not 1 <= target[0] <= target[1]):
        raise ValueError("target_pages needs two positive ordered integers")
    if type(minimum) is not int or minimum < 1000:
        raise ValueError("minimum_body_characters must be an integer of at least 1000")
    rules = CONTESTS[contest]
    if rules["hard_max_pages"] and target[1] > rules["hard_max_pages"]:
        raise ValueError("planning target exceeds the contest page limit")
    if not isinstance(scope_reason, str):
        raise ValueError("scope_reason must be text")
    if (mode != "competition" or target != default_target or minimum != default_minimum) and not scope_reason.strip():
        raise ValueError("short/test mode or a custom length requires an explicit scope_reason for checkpoint 1")
    return {"mode": mode, "contest": contest, "target_pages": target,
            "minimum_body_characters": minimum, "scope_reason": scope_reason, **rules}


def read_policy(root: Path) -> dict:
    policy = read_json(root / "pro_config.json").get("paper_delivery")
    if not isinstance(policy, dict):
        raise ValueError("missing paper_delivery; rerun P0 and confirm paper scope at checkpoint 1")
    expected = make_policy(policy.get("mode"), policy.get("contest"), policy.get("target_pages"),
                           policy.get("minimum_body_characters"), policy.get("scope_reason", ""))
    if policy != expected:
        raise ValueError("paper_delivery is incomplete or modifies the selected contest rules")
    return policy


def plan_inputs(root: Path) -> dict[str, str]:
    return {name: sha256_file(root / name) for name in
            ("pro_config.json", "problem_consensus.json", "evidence_freeze.json")}


def prose(text: str) -> str:
    text = re.sub(r"<!--.*?-->|```.*?```|~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.M)
    return re.sub(r"[`#*|\s]", "", text)


def indexed(items, key: str) -> dict:
    if not isinstance(items, list) or not items:
        raise ValueError(f"missing nonempty {key} records")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip() or item[key] in result:
            raise ValueError(f"invalid or duplicate {key}")
        result[item[key]] = item
    return result


def check_authoring_scope(root: Path, plan: dict, spans: dict[str, str], claims: dict) -> list[str]:
    policy = read_policy(root)
    errors = []
    if plan.get("input_hashes") != plan_inputs(root):
        errors.append("paper plan is stale for the approved scope, subproblems or frozen evidence")
    if plan.get("delivery_mode") != policy["mode"]:
        errors.append("paper plan cannot silently change the approved delivery mode")
    sections = indexed(plan.get("sections"), "section_id")
    if any(s.get("kind") not in SECTION_KINDS for s in sections.values()):
        errors.append("every paper section needs an explicit kind for page accounting")
    kinds = [s.get("kind") for s in sections.values()]
    if "ai-disclosure" in kinds and (kinds.count("ai-disclosure") != 1 or kinds[-1] != "ai-disclosure"):
        errors.append("AI disclosure must be a single final section, never a container for the solution")
    if "appendix" in kinds and any(k in {"abstract", "body", "references"} for k in kinds[kinds.index("appendix") + 1:]):
        errors.append("appendices must follow the complete main paper")
    if policy["contest"] == "cumcm-2026" and (not kinds or kinds[0] != "abstract" or "frontmatter" in kinds):
        errors.append("CUMCM electronic submission must begin with the abstract, without identifying cover sheets")
    body_ids = [i for i, s in sections.items() if s.get("kind") == "body"]
    if not body_ids or sum(len(prose(spans.get(i, ""))) for i in body_ids) < policy["minimum_body_characters"]:
        errors.append("substantive body is below the checkpoint-approved minimum; appendices, headings and code do not count")
    if policy["mode"] != "competition":
        return errors
    if not any(s.get("kind") == "abstract" for s in sections.values()):
        errors.append("competition paper needs an abstract section")
    questions = indexed(read_json(root / "problem_consensus.json").get("subproblems"), "subproblem_id")
    coverage = indexed(plan.get("subproblem_coverage"), "subproblem_id")
    if set(questions) != set(coverage):
        errors.append("paper must cover exactly every confirmed subproblem")
    all_anchors = []
    for qid, item in coverage.items():
        section_ids = item.get("section_ids", [])
        if (not isinstance(section_ids, list) or not section_ids
                or any(not isinstance(i, str) or i not in body_ids for i in section_ids)):
            errors.append(f"{qid}: arguments must reference substantive body sections")
            continue
        claim_ids = item.get("claim_ids", [])
        if (not isinstance(claim_ids, list) or not claim_ids
                or any(not isinstance(c, str) or c not in claims or claims[c].get("section_id") not in section_ids for c in claim_ids)):
            errors.append(f"{qid}: missing frozen answer/validation claims in the mapped sections")
        arguments = item.get("arguments")
        if not isinstance(arguments, dict) or set(arguments) != set(COMPONENTS):
            errors.append(f"{qid}: needs rationale, derivation, method, results, validation and limitations")
            continue
        for component, ref in arguments.items():
            if not isinstance(ref, dict):
                errors.append(f"{qid}/{component}: invalid argument reference")
                continue
            sid, anchor = ref.get("section_id"), ref.get("anchor")
            if sid not in section_ids or not isinstance(anchor, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]+", anchor):
                errors.append(f"{qid}/{component}: invalid section or argument anchor")
                continue
            all_anchors.append(anchor)
            marker = re.compile(r"<!--\s*argument:" + re.escape(anchor) + r"\s*-->")
            section = spans.get(sid, "")
            paragraphs = [p for p in re.split(r"\n\s*\n", section) if marker.search(p)]
            if len(marker.findall(section)) != 1 or len(paragraphs) != 1 or len(prose(paragraphs[0])) < 80:
                errors.append(f"{qid}/{component}: missing or skeletal argument paragraph")
            elif component in {"results", "validation"} and not any(
                re.search(r"<!--\s*claim:" + re.escape(c) + r"\s*-->", paragraphs[0]) for c in claim_ids if isinstance(c, str)
            ):
                errors.append(f"{qid}/{component}: argument paragraph needs a mapped frozen claim")
    if len(all_anchors) != len(set(all_anchors)):
        errors.append("different subproblem arguments cannot reuse one anchor")
    return errors


def check_page_counts(policy: dict, section_pages: list[dict], total_pages: int) -> tuple[list[str], dict]:
    errors = []
    scope = policy["page_scope"]
    included = {"body"} if scope == "body" else (
        {"abstract", "body", "references"} if scope == "main" else SECTION_KINDS - {"ai-disclosure"})
    counted = {page for s in section_pages if s["kind"] in included for page in s["pages"]}
    if scope == "solution":
        ai_pages = {page for s in section_pages if s["kind"] == "ai-disclosure" for page in s["pages"]}
        # A page shared with the solution still counts; only exclusively AI pages are exempt.
        counted = set(range(1, total_pages + 1)) - (ai_pages - counted)
    abstract = {page for s in section_pages if s["kind"] == "abstract" for page in s["pages"]}
    lower, upper = policy["target_pages"]
    if len(counted) < lower:
        errors.append(f"paper has only {len(counted)} {scope} pages; approved minimum is {lower}; expand substantive work or reconfirm scope at checkpoint 1")
    maximum = policy["hard_max_pages"]
    if maximum and len(counted) > maximum:
        errors.append(f"contest page limit exceeded: {len(counted)} > {maximum} ({scope})")
    if policy["abstract_max_pages"] and len(abstract) > policy["abstract_max_pages"]:
        errors.append("abstract exceeds the selected contest's one-page limit")
    return errors, {"delivery_mode": policy["mode"], "contest": policy["contest"], "page_scope": scope,
                    "counted_pages": len(counted), "total_pages": total_pages, "target_pages": [lower, upper],
                    "above_planning_target": len(counted) > upper, "hard_max_pages": maximum,
                    "section_pages": section_pages}


def locate_pdf_sections(plan: dict, pdf) -> list[dict]:
    """Use real text-line positions, not model-declared page numbers or substring matches."""
    titles = {re.sub(r"\W+", "", s["title"]).casefold(): s for s in plan["sections"]}
    if len(titles) != len(plan["sections"]):
        raise ValueError("section titles are ambiguous after PDF normalization")
    found = {key: [] for key in titles}
    for page_no, page in enumerate(pdf, 1):
        for block in page.get_text("dict")["blocks"]:
            lines = block.get("lines", [])
            for start, line in enumerate(lines):
                combined = ""
                for end in range(start, min(start + 4, len(lines))):
                    combined += "".join(s["text"] for s in lines[end]["spans"])
                    key = re.sub(r"\W+", "", combined).casefold()
                    if key in found:
                        found[key].append((page_no, line["bbox"][1]))
    ordered = []
    for section in plan["sections"]:
        matches = found[re.sub(r"\W+", "", section["title"]).casefold()]
        if len(matches) != 1:
            raise ValueError(f"PDF needs one identifiable section heading: {section['section_id']}")
        ordered.append((matches[0], section))
    if [pos for pos, _ in ordered] != sorted(pos for pos, _ in ordered):
        raise ValueError("PDF sections differ from planned order")
    # Sections count on every page they actually occupy, including shared boundary pages.
    result = []
    for index, (start, section) in enumerate(ordered):
        following = ordered[index + 1][0] if index + 1 < len(ordered) else None
        end_page = following[0] if following else len(pdf)
        if following and following[0] > start[0]:
            page = pdf[following[0] - 1]
            before = [b for b in page.get_text("blocks") if b[1] < following[1] - 1 and b[3] > 50]
            if not before:
                end_page -= 1
        result.append({"section_id": section["section_id"], "kind": section["kind"],
                       "pages": list(range(start[0], end_page + 1))})
    return result

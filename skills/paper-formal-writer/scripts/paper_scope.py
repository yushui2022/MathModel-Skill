"""Lightweight Standard scope; no Pro checkpoints or reviewer contracts."""
from __future__ import annotations

import re


def delivery_scope(mode="competition", reason="", min_pages=None, min_body_chars=None):
    if mode not in {"competition", "short-report", "smoke-test"}:
        raise ValueError("unknown delivery mode")
    pages = (18 if mode == "competition" else 1) if min_pages is None else min_pages
    chars = (8000 if mode == "competition" else 100) if min_body_chars is None else min_body_chars
    if type(pages) is not int or pages < 1 or type(chars) is not int or chars < 100:
        raise ValueError("scope needs positive pages and at least 100 body characters")
    if (mode != "competition" or pages != 18 or chars != 8000) and not str(reason).strip():
        raise ValueError("short/test/custom scope needs the user's scope reason")
    return {"mode": mode, "reason": reason, "min_pages": pages, "min_body_chars": chars}


def checked_scope(plan):
    value = plan.get("delivery")
    if not isinstance(value, dict):
        raise ValueError("missing delivery scope; rerun prepare_authoring.py")
    expected = delivery_scope(value.get("mode"), value.get("reason", ""), value.get("min_pages"), value.get("min_body_chars"))
    if value != expected:
        raise ValueError("invalid delivery scope")
    return value


def visible_prose(text):
    text = re.sub(r"<!--.*?-->|```.*?```|~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"^\s*#{1,6}\s+.*$", "", text, flags=re.M)


def body_text(text):
    text = re.sub(r"<!--.*?-->|```.*?```|~~~.*?~~~", "", text, flags=re.S)
    return re.split(r"(?mi)^\s*#{1,6}\s+(?:\d+[.、 ]\s*)?(?:附录[^\n]*|(?:Appendix|Appendices)(?:\s|$))", text, maxsplit=1)[0]


def scope_errors(text, plan):
    scope = checked_scope(plan)
    errors = []
    body = body_text(text)
    count = len(re.sub(r"\s+", "", visible_prose(body)))
    if count < scope["min_body_chars"]:
        errors.append(f"substantive main paper too short: {count} < {scope['min_body_chars']}; code/comments/appendices cannot fill the gap")
    if scope["mode"] == "competition":
        questions = plan.get("question_ids", [])
        if not isinstance(questions, list) or not questions or any(not isinstance(q, str) or not q.strip() for q in questions):
            return errors + ["complete paper needs the confirmed question IDs"]
        if len(set(questions)) != len(questions):
            errors.append("complete paper needs the confirmed question IDs")
        for index, qid in enumerate(questions, 1):
            match = re.search(rf"(?m)^\s*#{{1,6}}\s+5\.{index}\s+[^\n]+", body)
            if not match:
                errors.append(f"missing substantive model section for {qid}")
                continue
            tail = re.split(r"(?m)^\s*#{1,6}\s+(?:5\.\d+\s|[6-9]\s)", body[match.end():], maxsplit=1)[0]
            if len(re.sub(r"\s+", "", visible_prose(tail))) < 300:
                errors.append(f"{qid}: model/results/validation section is skeletal")
    return errors


def check_rendered_scope(page_texts, plan):
    scope = checked_scope(plan)
    counted = len(page_texts)
    for index, text in enumerate(page_texts if scope["mode"] == "competition" else []):
        if re.search(r"(?mi)^\s*(?:\d+[.、 ]\s*)?(?:附\s*录|Appendix|Appendices)(?:[ \t]+[^\n]*|[A-Z0-9][^\n]*)?[ \t]*$", text):
            counted = index  # Conservatively exclude a shared appendix boundary page.
            break
    errors = []
    if any(not page.strip() for page in page_texts[:counted]):
        errors.append("main paper contains a page without extractable text; inspect empty or image-only pages")
    if counted < scope["min_pages"]:
        errors.append(f"rendered main paper has {counted} pages, below declared {scope['min_pages']}; expand reasoning or explicitly revise scope")
    return errors, {"counted_main_pages": counted, "total_pages": len(page_texts), "delivery_mode": scope["mode"]}


def render_delivery_errors(plan, render):
    scope = checked_scope(plan)
    if scope["mode"] != "smoke-test" and (
        render.get("status") != "PASS" or not render.get("pdf") or not render.get("pdf_sha256")
    ):
        return ["delivery requires a fresh rendered PDF; --render skip/auto unavailable cannot complete S8"]
    return []

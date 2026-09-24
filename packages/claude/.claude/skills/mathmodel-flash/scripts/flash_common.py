"""Shared path, console, and fast long-paper integrity helpers."""
from __future__ import annotations

import re
import sys
from pathlib import Path, PureWindowsPath


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def safe_path(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("path must be a nonempty relative string")
    text = value.replace("\\", "/")
    if Path(text).is_absolute() or PureWindowsPath(text).drive or ":" in text or ".." in text.split("/"):
        raise ValueError(f"path must stay inside the project: {value}")
    path = (root / text).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"path escapes project: {value}")
    return path


def visible(text: str) -> str:
    text = re.sub(r"<!--.*?-->|```.*?```|~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    return re.sub(r"(?m)^\s*#{1,6}\s+.*$", "", text)


def paper_checks(text: str, plan: dict, results: dict) -> list[str]:
    failures: list[str] = []
    scope = plan.get("delivery", {})
    if not isinstance(scope, dict) or scope.get("mode") not in {"basic-long-paper", "short-report", "smoke-test"}:
        return ["invalid Flash delivery mode"]
    mode = scope["mode"]
    if mode != "basic-long-paper" and not str(scope.get("reason") or "").strip():
        failures.append("short/test scope requires an explicit user reason")
    minimum, per_question = {
        "basic-long-paper": (9000, 700),
        "short-report": (300, 80),
        "smoke-test": (50, 30),
    }[mode]
    visible_text = visible(text)
    effective = len(re.sub(r"\s+", "", visible_text))
    if effective < minimum:
        failures.append(f"paper body too short: requires {minimum} effective characters for {mode}")
    for item in plan.get("questions", []):
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or "")
        clean = re.sub(r"<!--.*?-->|```.*?```", "", text, flags=re.S)
        pattern = r"(?m)^\s*(#{1,6})\s+" + re.escape(qid) + r"(?![A-Za-z0-9_])[^\n]*"
        matches = list(re.finditer(pattern, clean))
        if len(matches) != 1:
            failures.append(f"{qid}: requires one dedicated Markdown question heading")
            continue
        match = matches[0]
        level = len(match.group(1))
        block = re.split(rf"(?m)^\s*#{{1,{level}}}\s+", clean[match.end():], maxsplit=1)[0]
        if len(re.sub(r"\s+", "", visible(block))) < per_question:
            failures.append(f"{qid}: missing substantive method/result/validation explanation")
        for name, value in (results.get(qid, {}).get("metrics") or {}).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            variants = {str(value), f"{value:g}", f"{value:.2f}", f"{value:.4f}"}
            if not any(re.search(r"(?<![\d.])" + re.escape(v) + r"(?!\d|\.\d)", block.replace(",", "")) for v in variants):
                failures.append(f"{qid}: computed metric {name} is missing from its answer block")
    paragraphs = [re.sub(r"\W", "", p).casefold() for p in re.split(r"\n\s*\n", visible_text)]
    long_paragraphs = [p for p in paragraphs if len(p) >= 80]
    if len(set(long_paragraphs)) != len(long_paragraphs):
        failures.append("repeated substantive paragraphs")
    return failures

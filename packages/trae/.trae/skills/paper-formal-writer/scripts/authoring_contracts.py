from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "2.2"
OUTPUT_DIR_NAME = "paper_output"
EVIDENCE_MARKER = re.compile(r"<!--\s*mathmodel-evidence\s*:\s*([^>]+?)\s*-->", re.IGNORECASE)
ALL_MATHMODEL_MARKERS = re.compile(r"<!--\s*mathmodel-[\s\S]*?-->", re.IGNORECASE)
PLACEHOLDERS = (
    "待补",
    "待填写",
    "内容生成中",
    "真实建模结果待补",
    "示例结果",
    "假设已经运行",
    "to be filled",
    "placeholder",
    "todo",
)
INTERNAL_LANGUAGE = (
    "workflow_guard",
    "evidence_gate.py",
    "微单元编号",
    "本 skill",
    "本脚本",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def output_root(project_root: Path) -> Path:
    return project_root.resolve() / OUTPUT_DIR_NAME


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON contract {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON contract must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative(path: Path, project_root: Path) -> str:
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def safe_relative_path(project_root: Path, value: object) -> Path:
    text = str(value or "").strip().replace("\\", "/")
    candidate = Path(text)
    if (
        not text
        or candidate.is_absolute()
        or text.startswith("/")
        or text.startswith("//")
        or re.match(r"^[A-Za-z]:", text)
        or ".." in text.split("/")
    ):
        raise ValueError(f"Path must stay inside the project root: {value!r}")
    resolved = (project_root.resolve() / candidate).resolve()
    if not resolved.is_relative_to(project_root.resolve()):
        raise ValueError(f"Path escapes the project root: {value!r}")
    return resolved


def contract(*, producer_role: str, status: str, input_hashes: dict[str, str], **payload: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "producer_role": producer_role,
        "input_hashes": input_hashes,
        "status": status,
        **payload,
    }


def validate_hashes(project_root: Path, hashes: object, label: str) -> list[str]:
    if not isinstance(hashes, dict) or not hashes:
        return [f"{label} has no input_hashes"]
    errors: list[str] = []
    for path_text, expected in hashes.items():
        try:
            path = safe_relative_path(project_root, path_text)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"{label} input is missing: {path_text}")
        elif sha256_file(path) != str(expected or "").strip().lower():
            errors.append(f"{label} input changed: {path_text}")
    return errors


def approved_draft_errors(project_root: Path, plan: dict[str, Any], state: dict[str, Any]) -> list[str]:
    records = state.get("sections")
    if not isinstance(records, dict) or not records:
        return ["authoring state has no section records"]
    if state.get("mode") == "global":
        expected_ids = ["GLOBAL"]
    else:
        expected_ids = [
            str(item.get("section_id"))
            for item in plan.get("sections", [])
            if isinstance(item, dict) and item.get("section_id")
        ]
    errors: list[str] = []
    for section_id in expected_ids:
        record = records.get(section_id)
        if not isinstance(record, dict):
            errors.append(f"missing authoring state for section {section_id}")
            continue
        if str(record.get("status") or "").upper() != "PASS":
            errors.append(f"section {section_id} is not PASS")
        try:
            path = safe_relative_path(project_root, record.get("path"))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        expected_hash = str(record.get("approved_sha256") or "").strip().lower()
        if not path.is_file():
            errors.append(f"section {section_id} draft is missing: {record.get('path')}")
        elif not expected_hash:
            errors.append(f"section {section_id} has no approved_sha256")
        elif sha256_file(path) != expected_hash:
            errors.append(f"section {section_id} changed after validation")
    return errors


def authoring_pass_errors(project_root: Path) -> list[str]:
    out = output_root(project_root)
    plan_path = out / "plan" / "writing_plan.json"
    state_path = out / "context" / "authoring_state.json"
    try:
        plan = read_json(plan_path)
        state = read_json(state_path)
    except ValueError as exc:
        return [str(exc)]
    errors: list[str] = []
    if str(plan.get("schema_version") or "") != SCHEMA_VERSION or str(plan.get("status") or "").upper() != "PASS":
        errors.append("writing plan envelope is not Standard 2.2 PASS")
    if str(state.get("schema_version") or "") != SCHEMA_VERSION:
        errors.append("authoring state schema_version is not 2.2")
    if str(state.get("status") or "").upper() != "PASS":
        errors.append("authoring state is not PASS")
    errors.extend(validate_hashes(project_root, state.get("input_hashes"), "authoring state"))
    errors.extend(validate_hashes(project_root, plan.get("input_hashes"), "writing plan"))
    _, gate_errors = fresh_evidence_gate(project_root)
    errors.extend(gate_errors)
    errors.extend(approved_draft_errors(project_root, plan, state))
    for label in ("assembled", "final"):
        record = state.get(label)
        if not isinstance(record, dict):
            errors.append(f"authoring state has no {label} record")
            continue
        if str(record.get("status") or "").upper() != "PASS":
            errors.append(f"{label} authoring record is not PASS")
        try:
            path = safe_relative_path(project_root, record.get("path"))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        expected_hash = str(record.get("sha256") or "").strip().lower()
        if not path.is_file():
            errors.append(f"{label} authoring file is missing: {record.get('path')}")
        elif not expected_hash:
            errors.append(f"{label} authoring record has no sha256")
        elif sha256_file(path) != expected_hash:
            errors.append(f"{label} authoring file changed after validation")
    final_record = state.get("final") or {}
    if str(final_record.get("path") or "").replace("\\", "/") != "paper_output/final_paper_source.md":
        errors.append("formal source must be paper_output/final_paper_source.md")
    from paper_scope import scope_errors
    try:
        source = out / "final_paper_source.md"
        if source.is_file():
            errors.extend(scope_errors(source.read_text(encoding="utf-8"), plan))
    except ValueError as exc:
        errors.append(str(exc))
    return sorted(set(errors))


def fresh_evidence_gate(project_root: Path) -> tuple[dict[str, Any], list[str]]:
    gate_path = output_root(project_root) / "qa" / "evidence_gate_report.json"
    if not gate_path.is_file():
        return {}, ["missing paper_output/qa/evidence_gate_report.json"]
    try:
        gate = read_json(gate_path)
    except ValueError as exc:
        return {}, [str(exc)]
    errors = [] if str(gate.get("status") or "").upper() == "PASS" else ["evidence gate status is not PASS"]
    errors.extend(validate_hashes(project_root, gate.get("input_hashes"), "evidence gate"))
    return gate, errors


def slug(value: object) -> str:
    text = re.sub(r"[^0-9A-Za-z._-]+", "_", str(value or "").strip()).strip("_.")
    return text or "section"


def effective_chars(text: str) -> int:
    from paper_scope import visible_prose
    visible = visible_prose(text)
    return len(re.sub(r"\s+", "", visible))


def evidence_ids(text: str) -> set[str]:
    result: set[str] = set()
    for match in EVIDENCE_MARKER.finditer(text):
        result.update(item.strip() for item in match.group(1).split(",") if item.strip())
    return result


def strip_markers(text: str) -> str:
    return ALL_MATHMODEL_MARKERS.sub("", text).strip() + "\n"


def normalized_paragraph(value: str) -> str:
    value = re.sub(r"\d+(?:\.\d+)?", "#", value.casefold())
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value)


def duplicate_paragraphs(text: str) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for paragraph in re.split(r"\n\s*\n", ALL_MATHMODEL_MARKERS.sub("", text)):
        compact = normalized_paragraph(paragraph)
        if len(compact) < 40:
            continue
        if compact in seen:
            duplicates.append(paragraph.strip()[:120])
        else:
            seen[compact] = paragraph
    return duplicates


def formula_errors(text: str) -> list[str]:
    errors: list[str] = []
    if text.count("$$") % 2:
        errors.append("display formula delimiter $$ is not closed")
    without_display = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
    if len(re.findall(r"(?<!\\)\$", without_display)) % 2:
        errors.append("inline formula delimiter $ is not closed")
    formulas = re.findall(r"\$\$([\s\S]*?)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$", text)
    try:
        from latex2mathml.converter import convert
    except ImportError:
        return errors
    for display, inline in formulas:
        formula = (display or inline).strip()
        if not formula:
            errors.append("empty LaTeX formula")
            continue
        try:
            convert(formula)
        except Exception as exc:
            errors.append(f"invalid LaTeX formula {formula[:60]!r}: {exc}")
    return errors


def numeric_variants(value: object) -> set[str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return set()
    number = float(value)
    if not math.isfinite(number):
        return set()
    variants = {str(value), f"{number:g}", f"{number:.2f}", f"{number:.3f}", f"{number:.4f}"}
    return {item.rstrip("0").rstrip(".") if "." in item else item for item in variants}


def collect_requirements(section: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result = {"evidence": [], "figures": [], "tables": [], "formulas": []}

    def visit(node: dict[str, Any], current_qid: str = "") -> None:
        qid = str(node.get("question_id") or current_qid or "ALL")
        for index, item in enumerate(node.get("required_evidence") or [], 1):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or "evidence")
            name = item.get("name") or item.get("role") or index
            eid = str(item.get("evidence_id") or f"{kind}:{qid}:{slug(name)}")
            result["evidence"].append({"evidence_id": eid, "question_id": qid, **item})
        for key, destination, id_key in (
            ("required_figures", "figures", "figure_id"),
            ("required_tables", "tables", "table_id"),
        ):
            for item in node.get(key) or []:
                if isinstance(item, dict):
                    identifier = str(item.get(id_key) or slug(item.get("title") or item.get("path")))
                    result[destination].append({"evidence_id": f"{destination[:-1]}:{identifier}", **item})
        for item in node.get("required_formulas") or []:
            if isinstance(item, dict):
                identifier = item.get("formula_id") or slug(item.get("description") or item.get("latex"))
                result["formulas"].append({"evidence_id": f"formula:{qid}:{identifier}", **item})
            elif str(item).strip():
                result["formulas"].append({"evidence_id": f"formula:{qid}:{slug(item)}", "description": str(item)})
        for child in node.get("subsections") or []:
            if isinstance(child, dict):
                visit(child, qid)

    visit(section)
    for key, values in result.items():
        deduped: dict[str, dict[str, Any]] = {}
        for item in values:
            deduped[str(item["evidence_id"])] = item
        result[key] = list(deduped.values())
    return result


def all_required_ids(section: dict[str, Any]) -> set[str]:
    requirements = section.get("requirements") or {}
    return {
        str(item.get("evidence_id"))
        for key in ("evidence", "figures", "tables", "formulas")
        for item in requirements.get(key, [])
        if isinstance(item, dict) and item.get("evidence_id")
    }


def flatten_numeric_requirements(section: dict[str, Any]) -> list[tuple[str, object, list[str]]]:
    requirements = section.get("requirements") or {}
    return [
        (
            str(item.get("evidence_id")),
            item.get("value"),
            [
                str(item.get(key)).strip()
                for key in ("name", "metric_name", "role", "metric_role", "unit")
                if str(item.get(key) or "").strip()
            ],
        )
        for item in requirements.get("evidence", [])
        if isinstance(item, dict) and numeric_variants(item.get("value"))
    ]


def merge_requirements(sections: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    merged = {"evidence": [], "figures": [], "tables": [], "formulas": []}
    for section in sections:
        for key in merged:
            merged[key].extend((section.get("requirements") or {}).get(key, []))
    for key, items in merged.items():
        merged[key] = list({item["evidence_id"]: item for item in items}.values())
    return merged


def section_issue_signature(issues: list[dict[str, Any]]) -> str:
    categories = sorted({str(item.get("category") or "unknown") for item in issues})
    return hashlib.sha256("\n".join(categories).encode("utf-8")).hexdigest()


def write_audit(output: Path, *, scope: str, status: str, input_hashes: dict[str, str], issues: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    audit_path = output / "qa" / "draft_audit.json"
    history: list[dict[str, Any]] = []
    if audit_path.is_file():
        try:
            history = read_json(audit_path).get("history", [])
        except ValueError:
            history = []
    if not isinstance(history, list):
        history = []
    history.append({"scope": scope, "status": status, "created_at_utc": utc_now(), "issues": issues, "metrics": metrics})
    write_json(audit_path, contract(
        producer_role="standard-authoring-auditor",
        status=status,
        input_hashes=input_hashes,
        latest_scope=scope,
        issues=issues,
        metrics=metrics,
        history=history[-50:],
    ))

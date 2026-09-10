"""Read-only source-linked recovery. Records are never treated as approvals."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_HASH_BYTES = 100 * 1024 * 1024


def safe_file(root: Path, relative: str) -> Path:
    value = str(relative).replace("\\", "/")
    if not value or "\x00" in value or ":" in value or PureWindowsPath(value).drive:
        raise ValueError("expected a relative project file")
    part = Path(value)
    if part.is_absolute() or ".." in part.parts:
        raise ValueError("path escapes the project")
    target = (root / part).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError("linked path escapes the project")
    return target


def digest_file(path: Path) -> str:
    if path.stat().st_size > MAX_HASH_BYTES:
        raise ValueError("file exceeds context hashing limit; use the full evidence validator")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_contract(root: Path, relative: str) -> tuple[dict | None, dict]:
    source: dict[str, Any] = {"path": relative, "pointer": "", "state": "missing"}
    try:
        path = safe_file(root, relative)
        if not path.is_file():
            return None, source
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("contract exceeds 2 MiB; open the registered artifact")
        data = path.read_bytes()
        source["sha256"] = hashlib.sha256(data).hexdigest()
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key}")
                result[key] = value
            return result
        def invalid(value):
            raise ValueError(f"non-finite JSON number: {value}")
        def finite_float(value):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("non-finite JSON number")
            return number
        result = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite_float)
        if not isinstance(result, dict):
            raise ValueError("contract must be a JSON object")
        source["state"] = "recorded"
        return result, source
    except (OSError, ValueError, UnicodeError) as exc:
        source.update(state="unknown", error=str(exc))
        return None, source


def _clip(value: Any, limit: int = 1000) -> Any:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value if len(text) <= limit else {"excerpt": text[:limit], "truncated": True}


def _qid(item: dict) -> str:
    return str(item.get("subproblem_id") or item.get("question_id") or "")


def _hash_errors(base: Path, hashes: Any) -> list[str]:
    if not isinstance(hashes, dict):
        return ["invalid hash map"]
    errors = []
    for relative, expected in hashes.items():
        try:
            if not re.fullmatch(r"[a-f0-9]{64}", str(expected)) or digest_file(safe_file(base, relative)) != expected:
                errors.append(f"changed or missing: {relative}")
        except (OSError, ValueError):
            errors.append(f"unverifiable: {relative}")
    return errors


def collect_facts(project: Path, output_name: str, question_id: str | None, *, verified_receipts: bool = False) -> tuple[list[dict], list[str], list[dict]]:
    base = safe_file(project, output_name)
    facts, diagnostics, sources = [], [], {}
    def read(name):
        if name not in sources:
            data, source = read_contract(project, f"{output_name}/{name}")
            if data is not None:
                list_keys = ("files", "subproblems", "runs", "decisions", "subproblem_coverage", "sections", "claims", "findings")
                malformed = [key for key in list_keys if key in data and not isinstance(data[key], list)]
                if malformed:
                    source.update(state="unknown", error="expected list fields: " + ", ".join(malformed))
                    data = None
            if data is not None:
                errors = _hash_errors(base, data.get("input_hashes", {}))
                if errors:
                    source.update(state="stale", reasons=errors[:6])
            if source.get("error"):
                diagnostics.append(f"{name}: {source['error']}")
            sources[name] = (data or {}, source)
        return sources[name]

    config, _ = read("pro_config.json")
    identity = config.get("project_root")
    foreign = bool(identity and (not isinstance(identity, str) or Path(identity).resolve() != project))
    if foreign:
        diagnostics.append("Project identity differs from pro_config.json; approvals and conclusions cannot be reused.")
    original, _ = read("input_manifest.json")
    original_entries = original.get("files", [])
    original_hashes = {f["path"]: f.get("sha256") for f in original_entries if isinstance(f, dict) and isinstance(f.get("path"), str) and f["path"]}
    original_errors = _hash_errors(project, original_hashes)
    if len(original_entries) != len(original_hashes):
        original_errors.append("original manifest contains invalid or duplicate file paths")
    try:
        current_inputs = {p.relative_to(project).as_posix() for p in safe_file(project, "problem_files").rglob("*") if p.is_file()}
        if original_hashes and current_inputs != set(original_hashes):
            original_errors.append("original files added or removed after preflight")
    except (OSError, ValueError):
        original_errors.append("cannot inspect original inputs")
    diagnostics.extend(original_errors[:6])

    def add(category, title, value, name, pointer, qid="", state=None):
        _, source = read(name)
        marker = "stale" if foreign or original_errors else source["state"]
        if marker not in {"stale", "unknown", "missing"} and state:
            marker = state
        facts.append({"category": category, "question_id": qid, "title": title, "value": _clip(value),
                      "state": marker, "source": {k: v for k, v in {**source, "pointer": pointer}.items() if k != "state"}})

    consensus, _ = read("problem_consensus.json")
    questions = [q for q in consensus.get("subproblems", []) if isinstance(q, dict)]
    ids = [_qid(q) for q in questions]
    if question_id and question_id not in ids:
        raise ValueError(f"Unknown question {question_id!r}; available: {', '.join(ids) or 'none (interpret the problem first)'}")
    for i, q in enumerate(consensus.get("subproblems", [])):
        if not isinstance(q, dict):
            continue
        if not question_id or _qid(q) == question_id:
            add("question", f"问题 {_qid(q)}", q, "problem_consensus.json", f"/subproblems/{i}", _qid(q))
    for key, title in (("consensus", "题意共识"), ("assumptions", "建模假设"), ("disagreements", "未决分歧")):
        if consensus.get(key):
            add("interpretation", title, consensus[key], "problem_consensus.json", f"/{key}")

    tournament, _ = read("tournament_report.json")
    manifest, _ = read("experiment_manifest.json")
    receipt_hashes = {r["receipt_path"]: r.get("receipt_sha256") for r in manifest.get("runs", []) if isinstance(r, dict) and isinstance(r.get("receipt_path"), str)}
    if len(receipt_hashes) != len(manifest.get("runs", [])):
        diagnostics.append("experiment_manifest.json contains invalid or duplicate receipt paths")
    candidate, _ = read("candidate_routes.json")
    route_questions = {}
    for q in candidate.get("subproblems", []):
        if isinstance(q, dict):
            routes = q.get("routes", [])
            if isinstance(routes, list):
                route_questions.update({str(r.get("route_id")): _qid(q) for r in routes if isinstance(r, dict)})
    for i, d in enumerate(tournament.get("decisions", [])):
        if not isinstance(d, dict) or question_id and _qid(d) != question_id:
            continue
        add("route", "选中路线、备用路线与淘汰理由", d, "tournament_report.json", f"/decisions/{i}", _qid(d))
        for j, q in enumerate(candidate.get("subproblems", [])):
            if isinstance(q, dict) and _qid(q) == _qid(d):
                add("candidates", "候选路线与预登记评分", q, "candidate_routes.json", f"/subproblems/{j}", _qid(q))

    plan, _ = read("paper_plan.json")
    sections = set()
    for i, coverage in enumerate(plan.get("subproblem_coverage", [])):
        if isinstance(coverage, dict) and (not question_id or _qid(coverage) == question_id):
            members = coverage.get("section_ids", [])
            if isinstance(members, list):
                sections.update(str(x) for x in members)
            add("writing", "逐问论证与写作定位", coverage, "paper_plan.json", f"/subproblem_coverage/{i}", _qid(coverage))
    for i, section in enumerate(plan.get("sections", [])):
        if isinstance(section, dict) and (not question_id or section.get("section_id") in sections):
            add("section", "章节计划", section, "paper_plan.json", f"/sections/{i}", question_id or "")

    for path in sorted(safe_file(project, f"{output_name}/experiments").glob("*/receipt.json")):
        name = path.relative_to(base).as_posix()
        receipt, source = read(name)
        if not receipt:
            continue
        qid = route_questions.get(str(receipt.get("route_id")), "")
        if question_id and qid != question_id:
            continue
        errors = _hash_errors(base, receipt.get("script_hashes", {})) + _hash_errors(base, receipt.get("output_hashes", {}))
        if isinstance(receipt.get("spec_path"), str) and receipt["spec_path"]:
            errors += _hash_errors(base, {receipt["spec_path"]: receipt.get("spec_sha256")})
        else:
            errors.append("invalid run-spec path")
        if not isinstance(receipt.get("metrics_file"), str):
            errors.append("invalid metrics path")
        if receipt_hashes.get(name) != source.get("sha256"):
            errors.append("receipt is missing or changed in experiment_manifest.json")
        if not all(receipt.get(k) for k in ("input_hashes", "script_hashes", "output_hashes", "spec_path", "spec_sha256")):
            errors.append("receipt lacks execution provenance")
        valid = receipt.get("status") == "PASS" and receipt.get("exit_code") == 0 and not errors and source["state"] != "stale"
        detail = {k: receipt.get(k) for k in ("run_id", "route_id", "implementation_id", "seed", "exit_code", "failure_reason", "started_at_utc", "finished_at_utc", "metrics_file")}
        detail["hash_issues"] = errors[:5]
        add("experiment", "可追溯运行回执", detail, name, "", qid, "current" if valid and verified_receipts else "recorded" if valid else "stale" if errors else "failed")
        if valid and receipt.get("metrics_file"):
            metrics, _ = read(receipt["metrics_file"])
            recorded_hash = receipt.get("output_hashes", {}).get(receipt["metrics_file"])
            add("metrics", f"{receipt.get('run_id')} 的记录指标", metrics.get("metrics", {}), receipt["metrics_file"], "/metrics", qid, "current" if recorded_hash and verified_receipts else "recorded" if recorded_hash else "unknown")

    claims, _ = read("claim_evidence_map.json")
    for i, claim in enumerate(claims.get("claims", [])):
        if not isinstance(claim, dict):
            continue
        qid = _qid(claim)
        if question_id and qid != question_id and claim.get("section_id") not in sections:
            continue
        add("claim", "论文结论及证据定位", claim, "claim_evidence_map.json", f"/claims/{i}", qid or question_id or "")
    for path in sorted(safe_file(project, f"{output_name}/reviews").glob("**/*.json")):
        name = path.relative_to(base).as_posix()
        review, _ = read(name)
        for i, finding in enumerate(review.get("findings", [])):
            if isinstance(finding, dict) and str(finding.get("disposition", "")).lower() not in {"resolved", "accepted"}:
                qid = _qid(finding)
                if not question_id or not qid or qid == question_id:
                    add("review", "未解决审稿问题", finding, name, f"/findings/{i}", qid)
    priority = {"question": 0, "route": 1, "interpretation": 2, "review": 3, "experiment": 4, "metrics": 5, "writing": 6, "claim": 7, "section": 8, "candidates": 9}
    facts.sort(key=lambda f: priority.get(f["category"], 10))
    return facts, diagnostics, questions


def memory_consistency(project: Path, output_name: str, guard: dict) -> dict:
    memory, source = read_contract(project, f"{output_name}/context/workflow_memory.json")
    mismatches = []
    if source["state"] == "unknown":
        mismatches.append({"field": "file", "reason": source.get("error")})
    if memory:
        workflow = memory.get("workflow", memory)
        if not isinstance(workflow, dict):
            workflow = {}
            mismatches.append({"field": "workflow", "reason": "invalid memory structure"})
        phase = workflow.get("current_phase") or workflow.get("next_step")
        if phase and phase != (guard.get("next_step") or guard.get("phase")):
            mismatches.append({"field": "phase", "memory": phase, "guard": guard.get("next_step") or guard.get("phase")})
        for error in _hash_errors(safe_file(project, output_name), memory.get("artifact_hashes", {})):
            mismatches.append({"field": "artifact_hashes", "reason": error})
        stored_project = memory.get("project") if isinstance(memory.get("project"), dict) else {}
        stored = memory.get("project_root") or stored_project.get("root")
        if stored and (not isinstance(stored, str) or Path(stored).resolve() != project):
            mismatches.append({"field": "project_root", "reason": "memory belongs to another project"})
    return {"present": memory is not None, "matches_guard": not mismatches, "mismatches": mismatches[:8], "source_of_truth": "live_pro_status", "source": source}


def write_snapshot(project: Path, packet: dict) -> Path:
    """Explicit persistence only; no changes to Pro approval or QA contracts."""
    directory = safe_file(project, ".mathmodel/context")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "resume.json"
    fd, temporary = tempfile.mkstemp(prefix="resume-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
            json.dump(packet, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write("\n")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target

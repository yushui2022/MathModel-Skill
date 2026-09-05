from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable


SCHEMA_VERSION = "3.3"
OUTPUT_DIR_NAME = "paper_output_pro"
REQUIRED_META = {
    "schema_version",
    "created_at_utc",
    "producer_role",
    "input_hashes",
    "status",
}

CHECKPOINT_ARTIFACTS = {
    "1": (
        "pro_config.json",
        "input_manifest.json",
        "instruction_manifest.json",
        "instruction_audit.json",
        "problem_consensus.json",
    ),
    "2": (
        "problem_consensus.json",
        "source_ledger.json",
        "candidate_routes.json",
        "tournament_report.json",
    ),
    "3": (
        "tournament_report.json",
        "experiment_manifest.json",
        "replication_report.json",
        "robustness_report.json",
        "ablation_report.json",
        "claim_evidence_map.json",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def output_root(project_root: Path, override: str | Path | None = None) -> Path:
    expected = (project_root.resolve() / OUTPUT_DIR_NAME).resolve()
    if not expected.is_relative_to(project_root.resolve()):
        raise ValueError("Pro output directory escapes the project")
    if override and Path(override).resolve() != expected:
        raise ValueError("Pro output must be project_root/paper_output_pro")
    return expected


def safe_path(base: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("artifact path must be a non-empty relative string")
    normalized = value.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute() or PureWindowsPath(value).drive or ".." in path.parts or ":" in value:
        raise ValueError(f"unsafe artifact path: {value}")
    resolved = (base / path).resolve()
    if not resolved.is_relative_to(base.resolve()) or resolved == base.resolve():
        raise ValueError(f"artifact escapes its root: {value}")
    return resolved


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def valid_utc(value: Any) -> bool:
    try:
        return isinstance(value, str) and value.endswith("Z") and datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset().total_seconds() == 0
    except (ValueError, AttributeError):
        return False


def check_hashes(base: Path, hashes: Any, *, required: bool = True) -> list[str]:
    if not isinstance(hashes, dict) or (required and not hashes):
        return ["missing file hashes"]
    errors = []
    for name, expected in hashes.items():
        try:
            path = safe_path(base, name)
            if not valid_sha256(expected) or not path.is_file() or sha256_file(path) != expected:
                errors.append(f"missing or changed artifact: {name}")
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    return errors


def check_original_inputs(project_root: Path, root: Path) -> list[str]:
    try:
        manifest = read_json(root / "input_manifest.json")
        if read_json(root / "pro_config.json").get("project_root") != project_root.resolve().as_posix():
            return ["approval belongs to a different project root; rerun P0 and obtain new decisions"]
        records = manifest.get("files", [])
        expected = {item["path"]: item["sha256"] for item in records}
        if len(expected) != len(records) or not expected:
            return ["input manifest contains missing or duplicate inputs"]
        problem_dir = project_root / "problem_files"
        current = {p.relative_to(project_root).as_posix() for p in problem_dir.rglob("*") if p.is_file()}
        errors = check_hashes(project_root, expected)
        if current != set(expected):
            errors.append("original inputs were added or removed after P0")
        return errors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"invalid original input manifest: {exc}"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def relative_key(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"artifact outside root: {path}") from exc


def hash_paths(paths: Iterable[Path], base: Path) -> dict[str, str]:
    return {
        relative_key(path, base): sha256_file(path)
        for path in sorted((item for item in paths if item.is_file()), key=lambda item: item.as_posix())
    }


def read_json(path: Path) -> dict[str, Any]:
    try:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key}")
                result[key] = value
            return result

        def invalid_constant(value):
            raise ValueError(f"non-finite JSON number: {value}")

        def finite_float(value):
            import math
            result = float(value)
            if not math.isfinite(result):
                raise ValueError("non-finite JSON numeric value")
            return result

        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant, parse_float=finite_float)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON contract {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Contract must be a JSON object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            previous = read_json(path)
            stable = lambda value: {k: v for k, v in value.items() if k != "created_at_utc"}
            if stable(previous) == stable(data):
                return
        except ValueError:
            pass
    serialized = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def contract(
    *,
    producer_role: str,
    status: str,
    input_hashes: dict[str, str] | None = None,
    **payload: Any,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "producer_role": producer_role,
        "input_hashes": input_hashes or {},
        "status": status,
        **payload,
    }


def validate_envelope(path: Path, allowed_statuses: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing contract: {path.name}"]
    try:
        data = read_json(path)
    except ValueError as exc:
        return [str(exc)]
    missing = sorted(REQUIRED_META - set(data))
    if missing:
        errors.append(f"{path.name}: missing metadata fields {missing}")
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{path.name}: unsupported schema_version {data.get('schema_version')!r}")
    if not isinstance(data.get("input_hashes"), dict):
        errors.append(f"{path.name}: input_hashes must be an object")
    elif any(not valid_sha256(value) for value in data["input_hashes"].values()):
        errors.append(f"{path.name}: invalid SHA-256")
    if not valid_utc(data.get("created_at_utc")) or not data.get("producer_role"):
        errors.append(f"{path.name}: invalid UTC timestamp or producer role")
    if allowed_statuses and data.get("status") not in allowed_statuses:
        errors.append(f"{path.name}: status must be one of {sorted(allowed_statuses)}")
    return errors


def checkpoint_hashes(root: Path, checkpoint: str) -> dict[str, str]:
    result: dict[str, str] = {}
    missing: list[str] = []
    for relative in CHECKPOINT_ARTIFACTS[checkpoint]:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        else:
            result[relative] = sha256_file(path)
    if missing:
        raise FileNotFoundError(f"Checkpoint {checkpoint} missing artifacts: {', '.join(missing)}")
    if checkpoint == "1":
        for item in read_json(root / "problem_consensus.json").get("independent_analyses", []):
            result[item["path"]] = sha256_file(safe_path(root, item["path"]))
    elif checkpoint == "2":
        for item in read_json(root / "source_ledger.json").get("sources", []):
            for key in ("snapshot_path", "retrieval_receipt"):
                result[item[key]] = sha256_file(safe_path(root, item[key]))
    elif checkpoint == "3":
        from pro_validation import evidence_files
        result.update(evidence_files(root))
    return result


def approval_is_fresh(root: Path, entry: dict[str, Any]) -> bool:
    recorded = entry.get("artifact_hashes")
    if not isinstance(recorded, dict) or not recorded:
        return False
    return not check_hashes(root, recorded) and canonical_json_hash(recorded) == entry.get("approval_hash")

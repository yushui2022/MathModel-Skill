from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "3.0"
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
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def output_root(project_root: Path, override: str | Path | None = None) -> Path:
    return Path(override).resolve() if override else (project_root / OUTPUT_DIR_NAME).resolve()


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
    except ValueError:
        return path.resolve().as_posix()


def hash_paths(paths: Iterable[Path], base: Path) -> dict[str, str]:
    return {
        relative_key(path, base): sha256_file(path)
        for path in sorted((item for item in paths if item.is_file()), key=lambda item: item.as_posix())
    }


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON contract {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Contract must be a JSON object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    return result


def approval_is_fresh(root: Path, entry: dict[str, Any]) -> bool:
    recorded = entry.get("artifact_hashes")
    if not isinstance(recorded, dict) or not recorded:
        return False
    for relative, expected in recorded.items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            return False
    return canonical_json_hash(recorded) == entry.get("approval_hash")

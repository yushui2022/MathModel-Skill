from __future__ import annotations

import hashlib
from pathlib import Path, PureWindowsPath


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root: Path, value: str):
    value = str(value).replace("\\", "/")
    if not value or Path(value).is_absolute() or PureWindowsPath(value).drive or ":" in value or ".." in value.split("/"):
        raise ValueError("artifact path must be relative to the project")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("artifact path escapes the project")
    return path


def evidence_snapshot(root):
    out = root / "paper_output"
    paths = [out / p for p in ("plan/model_route.json", "figure_index.json", "tables/table_index.json")]
    for folder in (root / "problem_files", out / "code", out / "results", out / "tables", out / "figures"):
        paths.extend(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    result = {}
    for path in sorted(set(paths)):
        if path.is_file():
            key = path.relative_to(root).as_posix()
            result[key] = sha256(safe_path(root, key))
    return result

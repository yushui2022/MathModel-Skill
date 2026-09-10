#!/usr/bin/env python3
"""Refresh bundled plugin skills from the generated Codex Pro package.

The plugin copy is a generated payload.  Keep the plugin-only entry skill in
place while synchronising every other file, and remove files deleted from the
canonical source.  Cache directories and bytecode are never shipped.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SKIP_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def payload_files(root: Path) -> dict[Path, Path]:
    result: dict[Path, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts) or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        result[relative] = path
    return result


def expected_bytes(path: Path) -> bytes:
    """Return the Codex-compatible generated representation of *path*."""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Codex is already generated from canonical Claude by the platform sync.
    # Never replace platform strings in runtime Python (installation scanners
    # deliberately understand more than one platform).
    return text.encode("utf-8")


def copy_tree(source: Path, target: Path) -> int:
    changed = 0
    target.mkdir(parents=True, exist_ok=True)
    source_files = payload_files(source)
    target_files = payload_files(target)
    for relative, source_file in source_files.items():
        target_file = target / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        expected = expected_bytes(source_file)
        if not target_file.exists() or target_file.read_bytes() != expected:
            target_file.write_bytes(expected)
            changed += 1
    # Keep the plugin entry skill and remove stale generated files.
    for relative in sorted(set(target_files) - set(source_files)):
        if relative.parts[:1] == ("mathmodel-plugin-entry",):
            continue
        stale = target / relative
        stale.unlink()
        parent = stale.parent
        while parent != target and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without changing files")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    # Refuse a stale intermediate payload: canonical -> Codex -> plugin is the
    # only supported generation chain. Check mode never changes either tree.
    check = subprocess.run([sys.executable, "-B", str(repo / "scripts/sync_platform_packages.py"), "--check"], cwd=repo)
    if check.returncode:
        print("Run scripts/sync_platform_packages.py before syncing plugin skills.")
        return check.returncode
    source = repo / "packages" / "codex" / ".agents" / "skills"
    target = Path(__file__).resolve().parents[1] / "skills"
    companions = {"core-requirements.txt": repo / "requirements.txt", "LICENSE": repo / "LICENSE"}
    if not source.is_dir():
        raise SystemExit(f"Canonical skill directory not found: {source}")
    if args.check:
        source_files = payload_files(source)
        target_files = payload_files(target)
        missing = sorted(p for p in source_files if not (target / p).exists())
        changed = sorted(p for p in source_files if (target / p).exists() and (target / p).read_bytes() != expected_bytes(source_files[p]))
        stale = sorted(p for p in target_files if p not in source_files and p.parts[:1] != ("mathmodel-plugin-entry",))
        companion_drift = [Path("..") / name for name, path in companions.items()
                           if not (target.parent / name).is_file() or (target.parent / name).read_bytes() != expected_bytes(path)]
        drift = missing + changed + stale + companion_drift
        if drift:
            print("Plugin skill copy is out of sync:")
            print("\n".join(f"- {path}" for path in drift))
            return 1
        print("Plugin skill copy is in sync.")
        return 0
    changed = copy_tree(source, target)
    for name, path in companions.items():
        output = target.parent / name
        expected = expected_bytes(path)
        if not output.is_file() or output.read_bytes() != expected:
            output.write_bytes(expected)
            changed += 1
    print(f"Synced {changed} skill files into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

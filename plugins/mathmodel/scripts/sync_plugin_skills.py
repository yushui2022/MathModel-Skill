#!/usr/bin/env python3
"""Refresh the plugin's bundled skills from the canonical Codex package."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path


def copy_tree(source: Path, target: Path) -> int:
    changed = 0
    target.mkdir(parents=True, exist_ok=True)
    for source_file in source.rglob("*"):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(source)
        target_file = target / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if not target_file.exists() or not filecmp.cmp(source_file, target_file, shallow=False):
            shutil.copy2(source_file, target_file)
            changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without changing files")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    source = repo / "packages" / "codex" / ".agents" / "skills"
    target = Path(__file__).resolve().parents[1] / "skills"
    if not source.is_dir():
        raise SystemExit(f"Canonical skill directory not found: {source}")
    if args.check:
        source_files = {p.relative_to(source) for p in source.rglob("*") if p.is_file()}
        missing = sorted(p for p in source_files if not (target / p).exists())
        changed = sorted(p for p in source_files if (target / p).exists() and not filecmp.cmp(source / p, target / p, shallow=False))
        drift = missing + changed
        if drift:
            print("Plugin skill copy is out of sync:")
            print("\n".join(f"- {path}" for path in drift))
            return 1
        print("Plugin skill copy is in sync.")
        return 0
    changed = copy_tree(source, target)
    print(f"Synced {changed} skill files into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

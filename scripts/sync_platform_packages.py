from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills"
TARGETS = (
    (REPO_ROOT / "packages" / "codex" / "skills", ".claude/skills", "skills"),
    (REPO_ROOT / "packages" / "trae" / ".trae" / "skills", ".claude/skills", ".trae/skills"),
)
SKIP_PARTS = {"__pycache__", "agents"}


def payload_files(root: Path) -> dict[Path, Path]:
    result: dict[Path, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        result[relative] = path
    return result


def transformed_bytes(path: Path, source_prefix: str, target_prefix: str) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data
    return text.replace(source_prefix, target_prefix).encode("utf-8")


def normalized_existing_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig").encode("utf-8")
    except UnicodeDecodeError:
        return data


def sync_target(target_root: Path, source_prefix: str, target_prefix: str, check: bool) -> list[str]:
    source_files = payload_files(SOURCE_ROOT)
    target_files = payload_files(target_root) if target_root.exists() else {}
    failures: list[str] = []

    for relative, source_path in source_files.items():
        expected = transformed_bytes(source_path, source_prefix, target_prefix)
        target_path = target_root / relative
        if check:
            if not target_path.exists():
                failures.append(f"missing: {target_path.relative_to(REPO_ROOT)}")
            elif normalized_existing_bytes(target_path) != expected:
                failures.append(f"drift: {target_path.relative_to(REPO_ROOT)}")
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists() or normalized_existing_bytes(target_path) != expected:
            target_path.write_bytes(expected)

    stale = sorted(set(target_files) - set(source_files))
    for relative in stale:
        target_path = target_root / relative
        if check:
            failures.append(f"stale: {target_path.relative_to(REPO_ROOT)}")
        else:
            target_path.unlink()
            parent = target_path.parent
            while parent != target_root and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize Claude canonical skill payloads to Codex and Trae.")
    parser.add_argument("--check", action="store_true", help="Report drift without modifying files.")
    args = parser.parse_args()

    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(f"Missing canonical skill root: {SOURCE_ROOT}")

    failures: list[str] = []
    for target_root, source_prefix, target_prefix in TARGETS:
        failures.extend(sync_target(target_root, source_prefix, target_prefix, args.check))

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("[PASS] Platform skill payloads are synchronized." if args.check else "Platform skill payloads synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

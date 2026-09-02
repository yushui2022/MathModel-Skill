from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "packages" / "claude" / ".claude" / "skills"
TARGET_ROOT = REPO_ROOT / "packages" / "codex" / ".agents" / "skills"
SKIP_PARTS = {"__pycache__"}


def payload_files(root: Path) -> dict[Path, Path]:
    result: dict[Path, Path] = {}
    if not root.exists():
        return result
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        result[relative] = path
    return result


def transformed_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace(".claude/skills", ".agents/skills").encode("utf-8")


def normalized_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        return text.encode("utf-8")
    except UnicodeDecodeError:
        return data


def sync(check: bool) -> list[str]:
    source_files = payload_files(SOURCE_ROOT)
    target_files = payload_files(TARGET_ROOT)
    failures: list[str] = []
    for relative, source in source_files.items():
        target = TARGET_ROOT / relative
        expected = transformed_bytes(source)
        if check:
            if not target.is_file():
                failures.append(f"missing: {target.relative_to(REPO_ROOT)}")
            elif normalized_bytes(target) != expected:
                failures.append(f"drift: {target.relative_to(REPO_ROOT)}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file() or normalized_bytes(target) != expected:
                target.write_bytes(expected)
    for relative in sorted(set(target_files) - set(source_files)):
        target = TARGET_ROOT / relative
        if check:
            failures.append(f"stale: {target.relative_to(REPO_ROOT)}")
        else:
            target.unlink()
    if not check and TARGET_ROOT.exists():
        for directory in sorted((path for path in TARGET_ROOT.rglob("*") if path.is_dir()), reverse=True):
            if not any(directory.iterdir()):
                directory.rmdir()
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize canonical Claude Pro skills to Codex .agents/skills.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not SOURCE_ROOT.is_dir():
        raise FileNotFoundError(f"Missing canonical skill root: {SOURCE_ROOT}")
    failures = sync(args.check)
    for failure in failures:
        print(f"[FAIL] {failure}")
    if failures:
        return 1
    print("[PASS] Pro Claude and Codex skill payloads are synchronized." if args.check else "Pro Codex payload synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

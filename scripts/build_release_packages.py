from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
VERSION_FILE = REPO_ROOT / "VERSION"
BUILD_MANIFEST = "MATHMODEL_BUILD.json"
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", "problem_files", "crawled_data", "paper_output", "paper_output_pro"}
EXCLUDED_FILES = {".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class PackageSpec:
    name: str
    archive_name: str
    source_root: Path
    archive_root: Path


SPECS = (
    PackageSpec("Pro Claude Code", "MathModel-Skill-Pro-Claude-Code.zip", REPO_ROOT / "packages" / "claude" / ".claude", Path(".claude")),
    PackageSpec("Pro Codex", "MathModel-Skill-Pro-Codex.zip", REPO_ROOT / "packages" / "codex" / ".agents", Path(".agents")),
)
COMMON_FILES = (
    (REPO_ROOT / "README.md", Path("README-MathModel-Skill-Pro.md")),
    (REPO_ROOT / "requirements.txt", Path("requirements.txt")),
    (REPO_ROOT / "docs" / "pro-start-prompt.md", Path("START_HERE.md")),
    (REPO_ROOT / "docs" / "pro-contracts.md", Path("docs/pro-contracts.md")),
)


def version() -> str:
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("VERSION is empty")
    return value


def should_skip(path: Path) -> bool:
    return path.name in EXCLUDED_FILES or path.suffix.lower() in EXCLUDED_SUFFIXES or any(part in EXCLUDED_DIRS for part in path.parts)


def source_entries(spec: PackageSpec) -> dict[str, bytes]:
    if not spec.source_root.is_dir():
        raise FileNotFoundError(f"Missing package root: {spec.source_root}")
    entries: dict[str, bytes] = {}
    for path in sorted((item for item in spec.source_root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().casefold()):
        relative = path.relative_to(spec.source_root)
        if not should_skip(relative):
            entries[(spec.archive_root / relative).as_posix()] = path.read_bytes()
    for source, target in COMMON_FILES:
        if not source.is_file():
            raise FileNotFoundError(f"Missing package document: {source}")
        entries[target.as_posix()] = source.read_bytes()
    entries["VERSION"] = (version() + "\n").encode("utf-8")
    return dict(sorted(entries.items()))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(spec: PackageSpec, entries: dict[str, bytes]) -> bytes:
    hashes = {name: sha256(data) for name, data in entries.items()}
    digest = hashlib.sha256()
    for name, file_hash in hashes.items():
        digest.update(name.encode("utf-8") + b"\0" + file_hash.encode("ascii") + b"\n")
    payload = {
        "schema_version": "3.0",
        "edition": "pro",
        "package": spec.name,
        "version": version(),
        "file_count": len(entries),
        "payload_sha256": digest.hexdigest(),
        "files": hashes,
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def expected(spec: PackageSpec) -> dict[str, bytes]:
    entries = source_entries(spec)
    entries[BUILD_MANIFEST] = manifest(spec, entries)
    return dict(sorted(entries.items()))


def build(spec: PackageSpec, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / spec.archive_name
    with zipfile.ZipFile(target, "w") as archive:
        for name, data in expected(spec).items():
            write_entry(archive, name, data)
    return target


def verify(spec: PackageSpec, output_dir: Path) -> list[str]:
    target = output_dir / spec.archive_name
    if not target.is_file():
        return [f"missing archive: {target}"]
    wanted = expected(spec)
    errors: list[str] = []
    with zipfile.ZipFile(target) as archive:
        names = sorted(item.filename for item in archive.infolist() if not item.is_dir())
        if names != sorted(wanted):
            errors.append(f"{spec.name}: archive entry set differs")
        for name, data in wanted.items():
            try:
                if archive.read(name) != data:
                    errors.append(f"{spec.name}: stale entry {name}")
            except KeyError:
                errors.append(f"{spec.name}: missing entry {name}")
        forbidden = [name for name in names if name.startswith((".trae/", "skills/")) or name in {"AGENTS.md", "CLAUDE.md"} or "mathmodel-lite" in name or "paper-workflow-orchestrator" in name]
        if forbidden:
            errors.append(f"{spec.name}: forbidden edition/root files {forbidden}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic MathModel Skill Pro packages.")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DIST_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    if args.verify:
        errors = [error for spec in SPECS for error in verify(spec, output_dir)]
        for error in errors:
            print(f"[FAIL] {error}")
        if errors:
            return 1
        print(f"[PASS] Pro archives match source version {version()}.")
        return 0
    if args.clean:
        for spec in SPECS:
            target = output_dir / spec.archive_name
            if target.is_file():
                target.unlink()
    for spec in SPECS:
        target = build(spec, output_dir)
        print(f"[+] {spec.name}: {target} ({target.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

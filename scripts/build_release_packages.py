from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
VERSION_FILE = REPO_ROOT / "VERSION"
BUILD_MANIFEST = "MATHMODEL_BUILD.json"
CHECKSUM_FILE = "SHA256SUMS.txt"
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "problem_files",
    "crawled_data",
    "paper_output",
    "paper_output_lite",
}
EXCLUDED_FILES = {
    "data_requirements.json",
    ".DS_Store",
    "Thumbs.db",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


@dataclass(frozen=True)
class PackageSpec:
    name: str
    archive_name: str
    roots: tuple[tuple[Path, Path], ...]
    extra_files: tuple[tuple[Path, Path], ...]


COMMON_DOCS = (
    (REPO_ROOT / "LICENSE", Path("LICENSE")),
    (REPO_ROOT / "requirements.txt", Path("requirements.txt")),
    (REPO_ROOT / "docs" / "lite-workflow.md", Path("docs/lite-workflow.md")),
    (REPO_ROOT / "docs" / "lite-starter-prompt.md", Path("docs/lite-starter-prompt.md")),
)


PACKAGE_SPECS = (
    PackageSpec(
        name="Lite Trae",
        archive_name="MathModel-Skill-Lite-Trae.zip",
        roots=((REPO_ROOT / "packages" / "trae" / ".trae", Path(".trae")),),
        extra_files=(
            (REPO_ROOT / "packages" / "trae" / "README.md", Path("README-MathModel-Skill-Lite.md")),
            *COMMON_DOCS,
        ),
    ),
    PackageSpec(
        name="Lite Claude Code",
        archive_name="MathModel-Skill-Lite-Claude-Code.zip",
        roots=((REPO_ROOT / "packages" / "claude" / ".claude", Path(".claude")),),
        extra_files=(
            (REPO_ROOT / "packages" / "claude" / "README.md", Path("README-MathModel-Skill-Lite.md")),
            *COMMON_DOCS,
        ),
    ),
    PackageSpec(
        name="Lite Codex",
        archive_name="MathModel-Skill-Lite-Codex.zip",
        roots=((REPO_ROOT / "packages" / "codex" / "skills", Path(".agents/skills")),),
        extra_files=(
            (REPO_ROOT / "packages" / "codex" / "README.md", Path("README-MathModel-Skill-Lite.md")),
            *COMMON_DOCS,
        ),
    ),
)


def should_skip(path: Path) -> bool:
    if path.name in EXCLUDED_FILES:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return any(part in EXCLUDED_DIRS for part in path.parts)


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix().lower())


def package_version() -> str:
    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"Missing version file: {VERSION_FILE}")
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version:
        raise RuntimeError("VERSION is empty")
    return version


def normalized_source_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def source_entries(spec: PackageSpec) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    for source_root, archive_root in spec.roots:
        if not source_root.exists():
            raise FileNotFoundError(f"Missing package root: {source_root}")
        for path in iter_files(source_root):
            archive_path = (archive_root / path.relative_to(source_root)).as_posix()
            entries[archive_path] = normalized_source_bytes(path)
    for source_file, archive_path in spec.extra_files:
        if not source_file.exists():
            raise FileNotFoundError(f"Missing extra file: {source_file}")
        entries[archive_path.as_posix()] = normalized_source_bytes(source_file)
    entries["VERSION"] = (package_version() + "\n").encode("utf-8")
    return dict(sorted(entries.items()))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(spec: PackageSpec, entries: dict[str, bytes]) -> bytes:
    file_hashes = {path: sha256_bytes(data) for path, data in entries.items()}
    digest = hashlib.sha256()
    for path, file_hash in file_hashes.items():
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    payload = {
        "schema_version": "1.0",
        "edition": "lite",
        "package": spec.name,
        "version": package_version(),
        "file_count": len(entries),
        "payload_sha256": digest.hexdigest(),
        "files": file_hashes,
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_zip_entry(archive: zipfile.ZipFile, path: str, data: bytes) -> None:
    info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_package(spec: PackageSpec, output_dir: Path) -> tuple[Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / spec.archive_name
    entries = source_entries(spec)
    entries[BUILD_MANIFEST] = build_manifest(spec, entries)

    with zipfile.ZipFile(output, "w") as archive:
        for archive_path, data in entries.items():
            write_zip_entry(archive, archive_path, data)

    return output, len(entries)


def verify_package(spec: PackageSpec, output_dir: Path) -> list[str]:
    output = output_dir / spec.archive_name
    if not output.exists():
        return [f"Missing archive: {output}"]

    expected = source_entries(spec)
    expected[BUILD_MANIFEST] = build_manifest(spec, expected)
    failures: list[str] = []
    with zipfile.ZipFile(output) as archive:
        actual_names = sorted(item.filename for item in archive.infolist() if not item.is_dir())
        expected_names = sorted(expected)
        if actual_names != expected_names:
            missing = sorted(set(expected_names) - set(actual_names))
            extra = sorted(set(actual_names) - set(expected_names))
            if missing:
                failures.append(f"{spec.name}: archive missing entries: {missing}")
            if extra:
                failures.append(f"{spec.name}: archive has unexpected entries: {extra}")
        for path, expected_bytes in expected.items():
            try:
                actual_bytes = archive.read(path)
            except KeyError:
                continue
            if actual_bytes != expected_bytes:
                failures.append(f"{spec.name}: stale archive entry: {path}")
    return failures


def clean_dist(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for spec in PACKAGE_SPECS:
        target = output_dir / spec.archive_name
        if target.exists():
            target.unlink()
    staging = output_dir / "_staging"
    if staging.exists():
        resolved = staging.resolve()
        if output_dir.resolve() == DIST_DIR.resolve() and not resolved.is_relative_to(REPO_ROOT.resolve()):
            raise RuntimeError(f"Refusing to delete outside repo: {resolved}")
        shutil.rmtree(staging)
    checksum_path = output_dir / CHECKSUM_FILE
    if checksum_path.exists():
        checksum_path.unlink()


def checksum_payload(output_dir: Path) -> str:
    lines = []
    for spec in sorted(PACKAGE_SPECS, key=lambda item: item.archive_name):
        path = output_dir / spec.archive_name
        if not path.is_file():
            raise FileNotFoundError(f"Missing archive for checksum: {path}")
        lines.append(f"{sha256_bytes(path.read_bytes())}  {path.name}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic MathModel Skill native release packages.")
    parser.add_argument("--clean", action="store_true", help="Remove previously generated release zips before building.")
    parser.add_argument("--verify", action="store_true", help="Verify existing archives against the current source tree.")
    parser.add_argument("--output-dir", type=Path, default=DIST_DIR, help="Directory for generated archives.")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()

    if args.verify:
        failures = [failure for spec in PACKAGE_SPECS for failure in verify_package(spec, output_dir)]
        checksum_path = output_dir / CHECKSUM_FILE
        if not checksum_path.is_file():
            failures.append(f"Missing checksum file: {checksum_path}")
        elif checksum_path.read_text(encoding="utf-8").replace("\r\n", "\n") != checksum_payload(output_dir):
            failures.append(f"Stale checksum file: {checksum_path}")
        if failures:
            for failure in failures:
                print(f"[FAIL] {failure}")
            return 1
        print(f"[PASS] Release archives match source version {package_version()}.")
        return 0

    if args.clean:
        clean_dist(output_dir)

    print(f"Building release packages into {output_dir}")
    for spec in PACKAGE_SPECS:
        output, file_count = build_package(spec, output_dir)
        size_kb = output.stat().st_size / 1024
        print(f"[+] {spec.name}: {output} ({file_count} files, {size_kb:.1f} KB)")
    checksum_path = output_dir / CHECKSUM_FILE
    checksum_path.write_text(checksum_payload(output_dir), encoding="utf-8", newline="\n")
    print(f"[+] Checksums: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

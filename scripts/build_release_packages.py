from __future__ import annotations

import argparse
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "problem_files",
    "crawled_data",
    "paper_output",
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


PACKAGE_SPECS = (
    PackageSpec(
        name="Trae",
        archive_name="MathModel-Skill-Trae.zip",
        roots=((REPO_ROOT / "packages" / "trae" / ".trae", Path(".trae")),),
        extra_files=(
            (REPO_ROOT / "packages" / "trae" / "README.md", Path("README-MathModel-Skill.md")),
            (REPO_ROOT / "requirements.txt", Path("requirements.txt")),
            (REPO_ROOT / "docs" / "starter-prompts.md", Path("starter-prompts.md")),
            (REPO_ROOT / "docs" / "output-layout.md", Path("output-layout.md")),
        ),
    ),
    PackageSpec(
        name="Claude Code",
        archive_name="MathModel-Skill-Claude-Code.zip",
        roots=((REPO_ROOT / "packages" / "claude" / ".claude", Path(".claude")),),
        extra_files=(
            (REPO_ROOT / "packages" / "claude" / "CLAUDE.md", Path("CLAUDE.md")),
            (REPO_ROOT / "packages" / "claude" / "README.md", Path("README-MathModel-Skill.md")),
            (REPO_ROOT / "requirements.txt", Path("requirements.txt")),
            (REPO_ROOT / "docs" / "starter-prompts.md", Path("starter-prompts.md")),
            (REPO_ROOT / "docs" / "output-layout.md", Path("output-layout.md")),
        ),
    ),
    PackageSpec(
        name="Codex",
        archive_name="MathModel-Skill-Codex.zip",
        roots=((REPO_ROOT / "packages" / "codex" / "skills", Path("skills")),),
        extra_files=(
            (REPO_ROOT / "packages" / "codex" / "AGENTS.md", Path("AGENTS.md")),
            (REPO_ROOT / "packages" / "codex" / "README.md", Path("README-MathModel-Skill.md")),
            (REPO_ROOT / "requirements.txt", Path("requirements.txt")),
            (REPO_ROOT / "docs" / "starter-prompts.md", Path("starter-prompts.md")),
            (REPO_ROOT / "docs" / "output-layout.md", Path("output-layout.md")),
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


def add_tree(archive: zipfile.ZipFile, source_root: Path, archive_root: Path) -> int:
    count = 0
    for path in iter_files(source_root):
        relative = path.relative_to(source_root)
        archive.write(path, (archive_root / relative).as_posix())
        count += 1
    return count


def build_package(spec: PackageSpec) -> tuple[Path, int]:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output = DIST_DIR / spec.archive_name
    if output.exists():
        output.unlink()

    file_count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source_root, archive_root in spec.roots:
            if not source_root.exists():
                raise FileNotFoundError(f"Missing package root: {source_root}")
            file_count += add_tree(archive, source_root, archive_root)
        for source_file, archive_path in spec.extra_files:
            if not source_file.exists():
                raise FileNotFoundError(f"Missing extra file: {source_file}")
            archive.write(source_file, archive_path.as_posix())
            file_count += 1

    return output, file_count


def clean_dist() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for spec in PACKAGE_SPECS:
        target = DIST_DIR / spec.archive_name
        if target.exists():
            target.unlink()
    staging = DIST_DIR / "_staging"
    if staging.exists():
        resolved = staging.resolve()
        if not resolved.is_relative_to(REPO_ROOT.resolve()):
            raise RuntimeError(f"Refusing to delete outside repo: {resolved}")
        shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MathModel Skill native release packages.")
    parser.add_argument("--clean", action="store_true", help="Remove previously generated release zips before building.")
    args = parser.parse_args()

    if args.clean:
        clean_dist()

    print(f"Building release packages into {DIST_DIR}")
    for spec in PACKAGE_SPECS:
        output, file_count = build_package(spec)
        size_kb = output.stat().st_size / 1024
        print(f"[+] {spec.name}: {output.relative_to(REPO_ROOT)} ({file_count} files, {size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

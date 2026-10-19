"""Standard-library installation checks shared by the installer and preflight."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

PLATFORMS = {"codex": ".agents/skills", "claude": ".claude/skills", "trae": ".trae/skills"}
SKILL_ROOTS = ("skills", ".agents/skills", ".codex/skills", ".claude/skills", ".trae/skills")
EDITION = "pro"
ENTRY = "pro-workflow-orchestrator"
LEGACY_ENTRIES = {"paper-workflow-orchestrator": "standard", "mathmodel-lite": "lite",
                  "mathmodel-flash": "flash", "pro-workflow-orchestrator": "pro"}
SKILLS = tuple(sorted((
    "authoritative-data-harvester", "context-memory-keeper", "data-cleaning-and-visualization", "model-code-and-result-generator", "paper-formal-writer", "pro-model-tournament", "pro-review-board", "pro-workflow-orchestrator", "problem-doc-model-selector", "quality-assurance-auditor",
)))
KNOWN_SKILLS = set(LEGACY_ENTRIES) | {"paper-formal-writer", "paper-micro-unit-generator", "pro-review-board", "pro-model-tournament", "model-code-and-result-generator", "quality-assurance-auditor", "data-cleaning-and-visualization", "context-memory-keeper", "problem-doc-model-selector", "authoritative-data-harvester", "modeling-paper-rubric-and-model-selector"}
RECORD = ".mathmodel/install.json"
JOURNAL = ".mathmodel/transaction.json"
BUILD = "MATHMODEL_BUILD.json"
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}


class InstallError(ValueError):
    pass


def rel_name(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise InstallError(f"Invalid relative path: {value!r}")
    parts = value.split("/")
    if any(p in ("", ".", "..") or p.endswith((" ", ".")) for p in parts):
        raise InstallError(f"Unsafe relative path: {value!r}")
    if PurePosixPath(value).is_absolute():
        raise InstallError(f"Absolute path forbidden: {value}")
    return value


def no_links(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            stat = part.lstat()
        except FileNotFoundError:
            continue
        if part.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            # macOS exposes these root-owned system directories through fixed aliases.
            # Project-local links and junctions remain forbidden.
            if (sys.platform == "darwin" and part.as_posix() in ("/var", "/tmp", "/etc")
                    and stat.st_uid == 0 and part.resolve() == Path("/private") / part.name):
                no_links(Path("/private") / part.name)
                continue
            raise InstallError(f"Symlink or reparse point forbidden: {part}")


def inside(root: Path, relative: str) -> Path:
    path = root / rel_name(relative)
    no_links(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise InstallError(f"Path escapes project: {relative}")
    return path


def sha256(path: Path) -> str:
    no_links(path)
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load(path: Path) -> dict:
    no_links(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InstallError(f"Expected JSON object: {path}")
    return data


def atomic_json(path: Path, data: dict) -> None:
    no_links(path)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def files_under(root: Path) -> dict[str, Path]:
    no_links(root)
    if not root.is_dir():
        return {}
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in dirs + files:
            no_links(base / name)
        dirs[:] = [name for name in dirs if name not in CACHE_DIRS]
        for name in files:
            path = base / name
            result[path.relative_to(root).as_posix()] = path
    return result


def hash_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise InstallError("Missing nonempty file hash map")
    seen = set()
    for name, digest in value.items():
        rel_name(name)
        if name.casefold() in seen or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise InstallError(f"Invalid hash or colliding path: {name}")
        seen.add(name.casefold())
    return value


def payload_digest(files: dict) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(files.items()):
        digest.update(f"{name}\0{value}\n".encode("utf-8"))
    return digest.hexdigest()


def version_key(version: str) -> tuple:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?", str(version))
    if not match:
        raise InstallError(f"Unsupported version: {version}")
    pre = match[4]
    return (*map(int, match.group(1, 2, 3)), pre is None,
            tuple((0, int(x)) if x.isdigit() else (1, x) for x in pre.split(".")) if pre else ())


def validate_source(source: Path) -> dict:
    no_links(source)
    manifest = load(source / BUILD)
    if (manifest.get("schema_version") != "2.0" or manifest.get("edition") != EDITION
            or manifest.get("entry_skill") != ENTRY or manifest.get("skills") != list(SKILLS)):
        raise InstallError("Not a supported Pro universal package")
    version_key(manifest.get("version", ""))
    hashes = hash_map(manifest.get("files"))
    actual = files_under(source)
    if set(actual) != set(hashes) | {BUILD}:
        raise InstallError(f"Package file list differs: {sorted(set(actual) ^ (set(hashes) | {BUILD}))}")
    for name, digest in hashes.items():
        if sha256(actual[name]) != digest:
            raise InstallError(f"Package file changed: {name}")
    if manifest.get("payload_sha256") != payload_digest(hashes):
        raise InstallError("Package payload hash mismatch")
    if (source / "VERSION").read_text(encoding="utf-8").strip() != manifest["version"]:
        raise InstallError("Package VERSION mismatch")
    marker = load(source / f"skills/{ENTRY}/MATHMODEL_EDITION.json")
    if marker.get("version") != manifest["version"] or marker.get("edition") != EDITION:
        raise InstallError("Edition marker mismatch")
    required = sorted(p.removeprefix("skills/") for p in hashes if p.startswith("skills/")
                      and p != f"skills/{ENTRY}/MATHMODEL_EDITION.json")
    declared = marker.get("required_files")
    if not isinstance(declared, list) or not all(isinstance(p, str) for p in declared) or sorted(declared) != required:
        raise InstallError("Edition payload inventory mismatch")
    for skill in SKILLS:
        if f"skills/{skill}/SKILL.md" not in hashes:
            raise InstallError(f"Incomplete package: {skill}")
    for name in hashes:
        if name.startswith("skills/") and name.split("/")[1] not in SKILLS:
            raise InstallError(f"Unknown packaged skill: {name}")
    return manifest


def validate_record(record: dict) -> dict:
    if (not isinstance(record, dict) or record.get("schema_version") != "1.0" or record.get("product") != "MathModel-Skill"
            or record.get("edition") != EDITION or record.get("entry_skill") != ENTRY
            or record.get("target") not in PLATFORMS.values() or record.get("skills") != list(SKILLS)):
        raise InstallError("Invalid managed installation record; do not overwrite it")
    version_key(record.get("version", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("payload_sha256", ""))):
        raise InstallError("Invalid installed payload hash")
    prefix = record["target"] + "/"
    hashes = hash_map(record.get("files"))
    for name in hashes:
        if not name.startswith(prefix) or name[len(prefix):].split("/")[0] not in SKILLS:
            raise InstallError(f"Unowned path in installation record: {name}")
    for skill in SKILLS:
        if f"{prefix}{skill}/SKILL.md" not in hashes:
            raise InstallError(f"Incomplete installation record: {skill}")
    return record


def verify_owned(project: Path, record: dict) -> None:
    validate_record(record)
    actual = {}
    for skill in record["skills"]:
        prefix = record["target"] + "/" + skill
        root = inside(project, prefix)
        actual.update({f"{prefix}/{name}": path for name, path in files_under(root).items()})
    expected = record["files"]
    conflicts = sorted(set(actual) ^ set(expected))
    conflicts += [name for name in expected if name in actual and sha256(actual[name]) != expected[name]]
    if conflicts:
        raise InstallError("Managed files missing, added or modified: " + ", ".join(conflicts))


def scan_installations(project: Path) -> list[dict]:
    installations = []
    for root_text in SKILL_ROOTS:
        root = inside(project, root_text)
        if not root.exists():
            continue
        if not root.is_dir():
            raise InstallError(f"Skill root is not a directory: {root_text}")
        entries = []
        for path in sorted(root.iterdir()):
            marker_path = path / "MATHMODEL_EDITION.json"
            if path.name not in LEGACY_ENTRIES and not marker_path.exists():
                continue
            no_links(path)
            if not path.is_dir():
                raise InstallError(f"Skill entry is not a directory: {path}")
            marker = load(marker_path) if marker_path.exists() else {}
            if marker.get("product") not in (None, "", "MathModel-Skill"):
                continue
            edition = marker.get("edition") or LEGACY_ENTRIES.get(path.name)
            if not isinstance(edition, str) or edition not in {"standard", "lite", "flash", "pro", "latex"}:
                raise InstallError(f"Unknown MathModel edition marker: {marker_path}")
            if path.name in LEGACY_ENTRIES and edition != LEGACY_ENTRIES[path.name] and not (
                path.name == "paper-workflow-orchestrator" and edition == "latex"
            ):
                raise InstallError(f"Entry and edition disagree: {marker_path}")
            entries.append({"edition": edition, "version": marker.get("version", "legacy-unmarked"),
                "entry_skill": marker.get("entry_skill", path.name), "skill_root": root_text,
                "path": path.relative_to(project).as_posix(),
                "marker": marker_path.relative_to(project).as_posix() if marker else None,
                "marker_error": None})
        # Partial installs still conflict even when the orchestrator is missing.
        if not entries and any((root / name).exists() for name in KNOWN_SKILLS):
            entries.append({"edition": EDITION, "version": "partial-unmarked",
                            "entry_skill": ENTRY, "skill_root": root_text, "path": root_text,
                            "marker": None, "marker_error": "Incomplete Pro installation"})
        if any(item["edition"] == EDITION for item in entries):
            unexpected = sorted(name for name in KNOWN_SKILLS - set(SKILLS) if (root / name).exists())
            if unexpected:
                raise InstallError(f"Foreign partial MathModel payload at {root_text}: {unexpected}")
        installations.extend(entries)
    return installations


def installation_errors(project: Path, expected_version: str) -> list[str]:
    try:
        if inside(project, JOURNAL).exists():
            return ["Interrupted installation: run install.py --recover before continuing"]
        found = scan_installations(project)
        if len(found) > 1 or any(x["edition"] != EDITION for x in found):
            return ["Mixed or duplicate MathModel installations: " + ", ".join(x["path"] for x in found)]
        record_path = inside(project, RECORD)
        if record_path.exists():
            record = load(record_path)
            verify_owned(project, record)
            if not found or found[0]["skill_root"] != record["target"] or record["version"] != expected_version:
                raise InstallError("Installation record differs from active Pro payload")
        if found:
            item = found[0]
            if item["version"] != expected_version or item.get("marker_error"):
                raise InstallError(f"Missing or incompatible edition marker at {item['path']}; reinstall the complete bundle")
            root = inside(project, item["skill_root"])
            marker = load(root / ENTRY / "MATHMODEL_EDITION.json")
            required = marker.get("required_files")
            if not isinstance(required, list) or not required:
                raise InstallError("Manual installation lacks the payload inventory; copy the complete current bundle")
            for name in required:
                if not inside(root, name).is_file():
                    raise InstallError(f"Incomplete manual installation: {name}")
            for skill in SKILLS:
                entry = inside(root, f"{skill}/SKILL.md")
                if not entry.is_file():
                    raise InstallError(f"Incomplete manual installation: {skill}")
            # Detect linked resources even in a manual installation.
            for skill in SKILLS:
                files_under(root / skill)
        return []
    except (InstallError, OSError) as exc:
        return [str(exc)]


def new_record(manifest: dict, target: str) -> dict:
    return {"schema_version": "1.0", "product": "MathModel-Skill", "edition": EDITION,
            "version": manifest["version"], "entry_skill": ENTRY, "target": target,
            "skills": list(SKILLS), "payload_sha256": manifest["payload_sha256"],
            "files": {target + "/" + p.removeprefix("skills/"): h
                      for p, h in manifest["files"].items() if p.startswith("skills/")},
            "installed_at": datetime.now(timezone.utc).isoformat()}


def installation_plan(project: Path, incoming: dict, upgrade: bool) -> tuple[str, dict | None]:
    if inside(project, JOURNAL).exists():
        raise InstallError("Interrupted installation: use --recover first")
    record_path = inside(project, RECORD)
    old = load(record_path) if record_path.exists() else None
    found = scan_installations(project)
    if old:
        verify_owned(project, old)
        if old["target"] != incoming["target"]:
            raise InstallError("Another install location is already managed; do not install twice")
        if len(found) != 1 or found[0]["skill_root"] != old["target"] or found[0]["edition"] != EDITION:
            raise InstallError("Unexpected additional or missing MathModel installation")
        if old["payload_sha256"] == incoming["payload_sha256"] and old["files"] == incoming["files"] and old["version"] == incoming["version"]:
            return "unchanged", old
        before, after = version_key(old["version"]), version_key(incoming["version"])
        if after <= before or before[0] != after[0]:
            raise InstallError("Downgrades, same-version replacements and major-version upgrades are not supported")
        if not upgrade:
            raise InstallError("Managed installation exists; review with --check --upgrade then use --upgrade")
        return "upgrade", old
    if found:
        raise InstallError("Unmanaged/legacy MathModel installation; back up and resolve manually: " +
                           ", ".join(item["path"] for item in found))
    if upgrade:
        raise InstallError("--upgrade requires an existing managed installation")
    for skill in SKILLS:
        target = inside(project, incoming["target"] + "/" + skill)
        if target.exists():
            raise InstallError(f"Unowned destination already exists: {target}")
    return "install", None


@contextmanager
def installation_lock(project: Path):
    meta = inside(project, ".mathmodel")
    meta.mkdir(exist_ok=True)
    lock_path = inside(project, ".mathmodel/install.lock")
    with lock_path.open("a+b") as handle:
        if lock_path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise InstallError("Another installer is running") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def tree_matches(root: Path, record: dict, skill: str) -> bool:
    prefix = record["target"] + "/" + skill + "/"
    expected = {name[len(prefix):]: value for name, value in record["files"].items() if name.startswith(prefix)}
    actual = files_under(root)
    return set(actual) == set(expected) and all(sha256(actual[p]) == h for p, h in expected.items())


def remove_owned_tree(root: Path, record: dict, skill: str) -> None:
    if not tree_matches(root, record, skill):
        raise InstallError(f"Refusing to remove modified tree: {root}")
    no_links(root)
    shutil.rmtree(root)


def recover(project: Path) -> None:
    journal_path = inside(project, JOURNAL)
    journal = load(journal_path)
    if journal.get("schema_version") != "1.0" or not re.fullmatch(r"[0-9a-f]{32}", str(journal.get("id", ""))):
        raise InstallError("Invalid recovery journal")
    new = validate_record(journal.get("new", {}))
    old = journal.get("old")
    if old is not None:
        validate_record(old)
        if old["target"] != new["target"]:
            raise InstallError("Recovery target mismatch")
    stage = inside(project, f".mathmodel/staging/{journal['id']}")
    record_path = inside(project, RECORD)
    if record_path.exists() and load(record_path) not in (old, new):
        raise InstallError("Installation record was modified during the transaction")
    # Check every destination before undoing anything, so user edits are never erased.
    for skill in SKILLS:
        target = inside(project, new["target"] + "/" + skill)
        backup = inside(stage, "old/" + skill)
        if backup.exists() and (old is None or not tree_matches(backup, old, skill)):
            raise InstallError(f"Modified recovery backup: {backup}")
        if target.exists():
            expected = old if old and not backup.exists() else new
            if not tree_matches(target, expected, skill):
                raise InstallError(f"Modified recovery destination or missing backup: {target}")
        if old and not backup.exists() and not target.exists():
            raise InstallError(f"Missing recovery backup and destination: {skill}")
    for skill in SKILLS:
        target = inside(project, new["target"] + "/" + skill)
        backup = inside(stage, "old/" + skill)
        if backup.exists():
            if target.exists():
                remove_owned_tree(target, new, skill)
            os.replace(backup, target)
        elif not old and target.exists():
            remove_owned_tree(target, new, skill)
    if old:
        atomic_json(record_path, old)
    else:
        record_path.unlink(missing_ok=True)
    journal_path.unlink()
    cleanup_stage(stage, new, old)


def cleanup_stage(stage: Path, new: dict, old: dict | None) -> None:
    for kind, record in (("new", new), ("old", old)):
        directory = inside(stage, kind)
        if not directory.exists():
            continue
        for child in directory.iterdir():
            if record is None or child.name not in SKILLS:
                raise InstallError(f"Unknown staging entry: {child}")
            remove_owned_tree(child, record, child.name)
        directory.rmdir()
    if stage.exists():
        stage.rmdir()


def apply_install(project: Path, source: Path, incoming: dict, old: dict | None) -> None:
    stage = inside(project, f".mathmodel/staging/{uuid4().hex}")
    stage.mkdir(parents=True)
    # Finish and verify staging before recording an operation that can modify live skills.
    for skill in SKILLS:
        for name in incoming["files"]:
            prefix = incoming["target"] + "/" + skill + "/"
            if not name.startswith(prefix):
                continue
            relative = name[len(prefix):]
            destination = inside(stage, f"new/{skill}/{relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(inside(source, f"skills/{skill}/{relative}"), destination)
        if not tree_matches(stage / "new" / skill, incoming, skill):
            raise InstallError(f"Staged payload mismatch: {skill}")
    journal_path = inside(project, JOURNAL)
    atomic_json(journal_path, {"schema_version": "1.0", "id": stage.name, "old": old, "new": incoming})
    try:
        for skill in SKILLS:
            destination = inside(project, incoming["target"] + "/" + skill)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if old:
                if not tree_matches(destination, old, skill):
                    raise InstallError(f"Destination changed during upgrade: {skill}")
                backup = inside(stage, "old/" + skill)
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination, backup)
            elif destination.exists():
                raise InstallError(f"Destination appeared during install: {destination}")
            os.replace(inside(stage, "new/" + skill), destination)
        verify_owned(project, incoming)
        atomic_json(inside(project, RECORD), incoming)
    except BaseException:
        recover(project)
        raise
    journal_path.unlink()
    cleanup_stage(stage, incoming, old)

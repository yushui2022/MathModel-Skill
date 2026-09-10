"""Build and verify the deterministic, self-contained MathModel plugin payload."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "mathmodel"
BUILD_MANIFEST = "MATHMODEL_PLUGIN_BUILD.json"
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "node_modules", ".git", ".mathmodel"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log"}
PAYLOAD_DIRS = {".codex-plugin", "skills", "scripts", "dashboard", "assets", "docs"}
PAYLOAD_ROOT_FILES = {".mcp.json", ".app.json", "README.md", "LICENSE", "requirements.txt", "core-requirements.txt", "core.lock.json"}


def normalized_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() not in {".md", ".py", ".json", ".txt", ".yaml", ".yml", ".js", ".css", ".html", ".svg"} and path.name != "LICENSE":
        return data
    return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def files(plugin: Path | None = None) -> list[Path]:
    base = (plugin or PLUGIN).resolve()
    result = []
    for path in base.rglob("*"):
        rel = path.relative_to(base)
        if any(p in SKIP_PARTS for p in rel.parts) or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if rel.parts[0] not in PAYLOAD_DIRS and rel.as_posix() not in PAYLOAD_ROOT_FILES:
            continue
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Plugin payload cannot contain links/junctions: {rel}")
        if not path.resolve().is_relative_to(base):
            raise ValueError(f"Plugin file escapes its root: {rel}")
        if path.is_file():
            result.append(path)
    return sorted(result, key=lambda p: p.relative_to(base).as_posix())


def _json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("Manifest must be a JSON object")
    return value


def _metadata(entries: dict[str, bytes]) -> tuple[dict, dict]:
    manifest = _json(entries[".codex-plugin/plugin.json"])
    core = _json(entries["core.lock.json"])
    if manifest.get("name") != "mathmodel" or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", str(manifest.get("version", ""))):
        raise ValueError("Plugin requires the MathModel name and a semantic version")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        raise ValueError("Plugin description is required")
    if manifest.get("skills") != "./skills/":
        raise ValueError("Plugin must load only its bundled skills directory")
    for field in ("mcpServers", "apps"):
        if field in manifest:
            value = manifest[field]
            if not isinstance(value, str) or not value.startswith("./") or value[2:] not in entries:
                raise ValueError(f"Plugin {field} must point to a bundled companion file")
            _json(entries[value[2:]])
    expected = {"core_edition": "pro", "contract_schema": "3.3", "entry_skill": "pro-workflow-orchestrator", "output_directory": "paper_output_pro"}
    if any(core.get(k) != v for k, v in expected.items()) or not re.fullmatch(r"[a-f0-9]{40}", str(core.get("source_commit", ""))):
        raise ValueError("Invalid Pro core lock")
    marker = _json(entries["skills/pro-workflow-orchestrator/MATHMODEL_EDITION.json"])
    if marker.get("edition") != core["core_edition"] or marker.get("version") != core.get("core_version"):
        raise ValueError("Bundled Pro edition marker differs from the core lock")
    if any(name.startswith(("skills/paper-workflow-orchestrator/", "skills/mathmodel-lite/")) for name in entries):
        raise ValueError("Mixed Standard/Lite/Pro workflow entrypoints cannot be shipped")
    if "skills/mathmodel-plugin-entry/SKILL.md" not in entries:
        raise ValueError("Plugin-specific entry skill is missing")
    return manifest, core


def source_entries(plugin: Path | None = None) -> dict[str, bytes]:
    base = (plugin or PLUGIN).resolve()
    entries = {p.relative_to(base).as_posix(): normalized_bytes(p) for p in files(base)}
    for name, source in (("core-requirements.txt", ROOT / "requirements.txt"), ("LICENSE", ROOT / "LICENSE")):
        if name not in entries or entries[name] != normalized_bytes(source):
            raise ValueError(f"Plugin companion {name} is missing or out of sync; run sync_plugin_skills.py")
    return dict(sorted(entries.items()))


def build_manifest(entries: dict[str, bytes]) -> bytes:
    manifest, core = _metadata(entries)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}
    digest = hashlib.sha256()
    for name, value in hashes.items():
        digest.update(name.encode("utf-8") + b"\0" + value.encode("ascii") + b"\n")
    result = {
        "schema_version": "2.0", "plugin": manifest["name"], "version": manifest["version"],
        "plugin_version": manifest["version"], "payload_sha256": digest.hexdigest(),
        "file_count": len(entries), "files": hashes,
        **{k: core[k] for k in ("core_edition", "core_version", "source_commit", "contract_schema")},
    }
    return (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build(output: Path, plugin: Path | None = None) -> Path:
    base = (plugin or PLUGIN).resolve()
    if output.resolve().is_relative_to(base):
        raise ValueError("Build outputs must be outside the plugin source directory")
    entries = source_entries(base)
    entries[BUILD_MANIFEST] = build_manifest(entries)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output


def verify(output: Path, plugin: Path | None = None) -> list[str]:
    if not output.is_file():
        return [f"Missing archive: {output}"]
    expected = source_entries(plugin)
    expected[BUILD_MANIFEST] = build_manifest(expected)
    failures = []
    try:
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                failures.append("Archive contains duplicate entries")
            if set(names) != set(expected):
                failures.append(f"Archive entries differ: missing={sorted(set(expected)-set(names))}, extra={sorted(set(names)-set(expected))}")
            for name in sorted(set(names) & set(expected)):
                if archive.read(name) != expected[name]:
                    failures.append(f"Stale or modified archive entry: {name}")
            if BUILD_MANIFEST in names:
                metadata = _json(archive.read(BUILD_MANIFEST))
                if metadata != _json(expected[BUILD_MANIFEST]):
                    failures.append("Build manifest/version/core/payload digest does not match source")
    except (zipfile.BadZipFile, ValueError, OSError, RuntimeError) as exc:
        failures.append(f"Invalid archive: {exc}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/MathModel-Codex-Plugin.zip")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            failures = verify(args.output)
            for failure in failures:
                print(f"[FAIL] {failure}")
            if failures:
                return 1
            print(f"Plugin archive verified against bytes and manifest: {args.output}")
        else:
            print(f"Built {build(args.output)}")
    except (ValueError, OSError, KeyError, UnicodeDecodeError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

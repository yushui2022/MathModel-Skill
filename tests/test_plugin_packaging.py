"""Archive integrity regressions using isolated source/ZIP copies."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_plugin_package as packaging


class PluginPackagingTests(unittest.TestCase):
    def setUp(self):
        temp = Path(os.environ.get("MATHMODEL_TEST_TEMP", "G:/DevCache/Temp/mathmodel-plugin" if os.name == "nt" else tempfile.gettempdir())).resolve()
        temp.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="packaging-", dir=temp)
        self.root = Path(self.temporary.name)
        self.source = self.root / "mathmodel"
        shutil.copytree(packaging.PLUGIN, self.source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.archive = self.root / "plugin.zip"

    def tearDown(self):
        self.temporary.cleanup()

    def test_build_twice_and_verify_manifest(self):
        packaging.build(self.archive, self.source)
        other = self.root / "second.zip"
        packaging.build(other, self.source)
        self.assertEqual(self.archive.read_bytes(), other.read_bytes())
        self.assertEqual(packaging.verify(self.archive, self.source), [])
        with zipfile.ZipFile(self.archive) as archive:
            manifest = json.loads(archive.read(packaging.BUILD_MANIFEST))
            self.assertEqual(manifest["core_edition"], "pro")
            self.assertEqual(manifest["contract_schema"], "3.3")
            self.assertEqual(manifest["file_count"], len(manifest["files"]))
            self.assertIn("core-requirements.txt", archive.namelist())
            self.assertIn("LICENSE", archive.namelist())
            self.assertNotIn("skills/paper-workflow-orchestrator/SKILL.md", archive.namelist())

    def test_source_install_dependencies_and_license_cannot_drift(self):
        for name in ("core-requirements.txt", "LICENSE"):
            path = self.source / name
            original = path.read_bytes()
            path.write_bytes(original + b"\nchanged\n")
            with self.assertRaisesRegex(ValueError, "out of sync"):
                packaging.build(self.archive, self.source)
            path.write_bytes(original)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                packaging.build(self.archive, self.source)
            path.write_bytes(original)

    def test_changed_source_same_name_is_rejected(self):
        packaging.build(self.archive, self.source)
        path = self.source / "README.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nsource changed\n", encoding="utf-8")
        self.assertTrue(any("README.md" in e for e in packaging.verify(self.archive, self.source)))

    def test_changed_archive_bytes_are_rejected(self):
        packaging.build(self.archive, self.source)
        with zipfile.ZipFile(self.archive) as archive:
            entries = {n: archive.read(n) for n in archive.namelist()}
        entries["README.md"] += b"\ntampered\n"
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        self.assertTrue(any("README.md" in e for e in packaging.verify(self.archive, self.source)))

    def test_version_change_and_manifest_tampering_are_rejected(self):
        packaging.build(self.archive, self.source)
        path = self.source / ".codex-plugin/plugin.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["version"] = "99.0.0"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        errors = packaging.verify(self.archive, self.source)
        self.assertTrue(any("plugin.json" in e for e in errors))
        self.assertTrue(any("manifest" in e.lower() for e in errors))

    def test_duplicate_or_extra_entry_rejected(self):
        packaging.build(self.archive, self.source)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "a") as archive:
                archive.writestr("README.md", b"duplicate")
                archive.writestr("../escape.txt", b"outside")
        errors = packaging.verify(self.archive, self.source)
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("escape.txt" in e for e in errors))

    def test_stale_core_marker_and_mixed_entry_rejected(self):
        path = self.source / "skills/pro-workflow-orchestrator/MATHMODEL_EDITION.json"
        original = path.read_bytes()
        marker = json.loads(original)
        marker["version"] = "0.0.0"
        path.write_text(json.dumps(marker), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "core lock"):
            packaging.build(self.archive, self.source)
        path.write_bytes(original)
        stale = self.source / "skills/paper-workflow-orchestrator/SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("legacy", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Mixed"):
            packaging.build(self.archive, self.source)

    def test_cache_and_local_runtime_configuration_are_not_shipped(self):
        cache = self.source / "scripts/__pycache__/private.pyc"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"cache")
        (self.source / ".mcp.local.json").write_text('{"token":"must not ship"}', encoding="utf-8")
        packaging.build(self.archive, self.source)
        with zipfile.ZipFile(self.archive) as archive:
            self.assertNotIn(".mcp.local.json", archive.namelist())
            self.assertFalse(any("__pycache__" in n for n in archive.namelist()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

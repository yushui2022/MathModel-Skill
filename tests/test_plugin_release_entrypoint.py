"""The retained Standard publisher cannot label/write mixed Pro payloads."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_release_packages as release


class HistoricalReleaseEntrypointTests(unittest.TestCase):
    def setUp(self):
        cache = Path(os.environ.get("MATHMODEL_TEST_TEMP", "G:/DevCache/Temp/mathmodel-plugin" if os.name == "nt" else tempfile.gettempdir()))
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="release-entry-", dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fingerprint(self, root):
        return {p.relative_to(root).as_posix(): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                for p in root.rglob("*") if p.is_file()}

    def test_current_pro_tree_blocks_clean_build_and_verify_before_any_write(self):
        output = self.root / "old-dist"
        output.mkdir()
        for name in [*(spec.archive_name for spec in release.PACKAGE_SPECS), release.CHECKSUM_FILE, "_staging/keep.txt"]:
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("preserved historical bytes", encoding="utf-8")
        before = self.fingerprint(output)
        repository_before = self.fingerprint(REPO / "dist")
        for mode in ([], ["--clean"], ["--verify"]):
            result = subprocess.run([sys.executable, "-B", str(REPO / "scripts/build_release_packages.py"), *mode, "--output-dir", str(output)],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("[BLOCKED]", result.stdout)
            self.assertIn("--edition standard --packages-only", result.stdout)
            self.assertIn("--edition pro --packages-only", result.stdout)
            self.assertEqual(before, self.fingerprint(output))
            self.assertEqual(repository_before, self.fingerprint(REPO / "dist"))

    def test_direct_mutator_calls_are_also_closed_before_directory_creation(self):
        output = self.root / "must-not-exist"
        with self.assertRaisesRegex(RuntimeError, "historical Standard"):
            release.build_package(release.PACKAGE_SPECS[0], output)
        with self.assertRaisesRegex(RuntimeError, "historical Standard"):
            release.clean_dist(output)
        self.assertFalse(output.exists())

    def test_matching_standard_markers_remain_valid_and_version_or_mixed_entry_fails(self):
        native = self.root / ".agents"
        entry = native / "skills/paper-workflow-orchestrator"
        entry.mkdir(parents=True)
        (entry / "SKILL.md").write_text("historical Standard fixture", encoding="utf-8")
        marker = {"product": "MathModel-Skill", "edition": "standard", "version": "2.3.0", "entry_skill": "paper-workflow-orchestrator"}
        (entry / "MATHMODEL_EDITION.json").write_text(json.dumps(marker), encoding="utf-8")
        version = self.root / "VERSION"
        version.write_text("2.3.0\n", encoding="utf-8")
        spec = release.PackageSpec("Codex", "historical.zip", ((native, Path(".agents")),), ())
        with mock.patch.object(release, "PACKAGE_SPECS", (spec,)), mock.patch.object(release, "VERSION_FILE", version):
            release.require_standard_release_tree()
            version.write_text("3.3.0-pro.1\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "marker does not match"):
                release.require_standard_release_tree()
            version.write_text("2.3.0\n", encoding="utf-8")
            (native / "skills/pro-workflow-orchestrator").mkdir()
            with self.assertRaisesRegex(RuntimeError, "mixed Pro/Lite"):
                release.require_standard_release_tree()


if __name__ == "__main__":
    unittest.main(verbosity=2)

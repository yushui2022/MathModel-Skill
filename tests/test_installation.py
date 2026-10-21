from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills/pro-workflow-orchestrator/scripts"))
sys.path.insert(0, str(REPO / "scripts"))
import installation as inst
import build_release_packages as build



def next_version(version: str) -> str:
    match = re.match(r"^(.*?)(\d+)$", version)
    return f"{match.group(1)}{int(match.group(2)) + 1}" if match else f"{version}.1"
def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class InstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="mathmodel-install-")
        cls.base = Path(cls.workspace.name)
        cls.source = cls.base / "download"
        cls.source.mkdir()
        cls.archive = build.package_bytes(build.PACKAGE_SPECS[0])
        with zipfile.ZipFile(io.BytesIO(cls.archive)) as archive:
            archive.extractall(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="case-", dir=self.base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "中文 contest space"
        self.project.mkdir()

    def cli(self, *args, source=None):
        return subprocess.run([sys.executable, "-S", str((source or self.source) / "install.py"),
            "--project-root", str(self.project), *args], cwd=self.root, text=True,
            encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def install(self, platform="codex"):
        result = self.cli("--platform", platform)
        self.assertEqual(result.returncode, 0, result.stdout)
        return inst.load(self.project / inst.RECORD)

    def modified_source(self, version=None):
        if version is None:
            version = next_version((self.source / "VERSION").read_text().strip())
        target = self.root / "upgrade bundle"
        shutil.copytree(self.source, target, ignore=shutil.ignore_patterns("__pycache__"))
        (target / "VERSION").write_text(version + "\n", encoding="utf-8")
        marker = target / f"skills/{inst.ENTRY}/MATHMODEL_EDITION.json"
        data = inst.load(marker)
        data["version"] = version
        marker.write_text(json.dumps(data), encoding="utf-8")
        manifest = inst.load(target / inst.BUILD)
        manifest["version"] = version
        manifest["files"] = {p: inst.sha256(target / p) for p in manifest["files"]}
        manifest["payload_sha256"] = inst.payload_digest(manifest["files"])
        (target / inst.BUILD).write_text(json.dumps(manifest), encoding="utf-8")
        return target

    def test_all_platforms_copy_identical_bytes_and_preserve_project(self):
        for platform, target in inst.PLATFORMS.items():
            with self.subTest(platform=platform):
                self.project = self.root / platform
                self.project.mkdir()
                for name in ("AGENTS.md", "CLAUDE.md", "requirements.txt", "problem_files/input.csv",
                             "paper_output/final_paper.docx", f"{target}/unrelated/SKILL.md"):
                    path = self.project / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"user-owned content")
                before = snapshot(self.project)
                record = self.install(platform)
                for name, data in before.items():
                    self.assertEqual((self.project / name).read_bytes(), data)
                inst.verify_owned(self.project, record)
                for name in record["files"]:
                    self.assertEqual((self.project / name).read_bytes(),
                                     (self.source / "skills" / name.removeprefix(target + "/")).read_bytes())
                self.assertEqual(inst.installation_errors(self.project, record["version"]), [])

    def test_check_writes_nothing_and_install_is_idempotent(self):
        before = snapshot(self.project)
        result = self.cli("--platform", "codex", "--check")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(snapshot(self.project), before)
        self.assertFalse((self.project / ".mathmodel").exists())
        self.install()
        before = snapshot(self.project)
        result = self.cli("--platform", "codex")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(snapshot(self.project), before)

    def test_installer_logs_unicode_with_legacy_console_encoding(self):
        env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        command = [sys.executable, "-S", str(self.source / "install.py"),
                   "--project-root", str(self.project), "--platform", "codex"]
        result = subprocess.run(command, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.project.name, result.stdout.decode("utf-8"))
        changed = self.project / ".agents/skills/pro-workflow-orchestrator/SKILL.md"
        changed.write_text("user customization", encoding="utf-8")
        before = snapshot(self.project)
        result = subprocess.run(command, capture_output=True, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Managed files", result.stderr.decode("utf-8"))
        self.assertEqual(snapshot(self.project), before)

    @unittest.skipUnless(sys.platform == "darwin", "macOS system aliases")
    def test_macos_system_alias_is_allowed_but_nested_link_is_not(self):
        with tempfile.TemporaryDirectory(dir="/var/tmp", prefix="mathmodel-alias-") as directory:
            project = Path(directory) / "contest"
            project.mkdir()
            result = subprocess.run([sys.executable, "-S", str(self.source / "install.py"),
                "--project-root", str(project), "--platform", "codex"], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = inst.load(project / inst.RECORD)
            inst.verify_owned(project, record)
            link = Path(directory) / "linked-project"
            link.symlink_to(project, target_is_directory=True)
            with self.assertRaises(inst.InstallError):
                inst.inside(link, ".agents/skills")

    def test_unmanaged_and_legacy_installs_in_all_roots_block_without_writes(self):
        for index, target in enumerate(inst.SKILL_ROOTS):
            for entry in ("paper-workflow-orchestrator", "mathmodel-lite", "mathmodel-flash", "pro-workflow-orchestrator"):
                self.project = self.root / f"project-{index}-{entry}"
                path = self.project / target / entry / "SKILL.md"
                path.parent.mkdir(parents=True)
                path.write_text("legacy", encoding="utf-8")
                before = snapshot(self.project)
                result = self.cli("--platform", "codex")
                self.assertNotEqual(result.returncode, 0, (target, entry))
                self.assertEqual(snapshot(self.project), before)

    def test_partial_install_blocks(self):
        path = self.project / ".agents/skills/paper-formal-writer"
        path.mkdir(parents=True)
        self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)
        self.assertFalse((self.project / inst.RECORD).exists())

    def test_manual_install_works_but_not_adopted(self):
        target = self.project / ".claude/skills"
        shutil.copytree(self.source / "skills", target)
        version = (self.source / "VERSION").read_text().strip()
        self.assertEqual(inst.installation_errors(self.project, version), [])
        self.assertNotEqual(self.cli("--platform", "claude").returncode, 0)
        (target / "pro-workflow-orchestrator/scripts/installation.py").unlink()
        self.assertTrue(inst.installation_errors(self.project, version))

    def test_changed_and_added_managed_files_block_upgrade(self):
        record = self.install()
        incoming = self.modified_source()
        path = self.project / record["target"] / "pro-workflow-orchestrator/SKILL.md"
        path.write_text("user customization", encoding="utf-8")
        before = snapshot(self.project)
        result = self.cli("--platform", "codex", "--upgrade", source=incoming)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(snapshot(self.project), before)
        shutil.copyfile(self.source / "skills/pro-workflow-orchestrator/SKILL.md", path)
        (path.parent / "personal-notes.txt").write_text("keep", encoding="utf-8")
        self.assertNotEqual(self.cli("--platform", "codex", "--upgrade", source=incoming).returncode, 0)

    def test_managed_upgrade_requires_flag_and_preserves_evidence(self):
        old = self.install()
        paper = self.project / "paper_output/qa/evidence_gate_report.json"
        paper.parent.mkdir(parents=True)
        paper.write_text('{"status":"PASS","old_evidence":true}', encoding="utf-8")
        source = self.modified_source()
        self.assertNotEqual(self.cli("--platform", "codex", source=source).returncode, 0)
        result = self.cli("--platform", "codex", "--upgrade", source=source)
        self.assertEqual(result.returncode, 0, result.stdout)
        new = inst.load(self.project / inst.RECORD)
        self.assertNotEqual(new["payload_sha256"], old["payload_sha256"])
        inst.verify_owned(self.project, new)
        self.assertEqual(paper.read_text(), '{"status":"PASS","old_evidence":true}')
        self.assertFalse((self.project / inst.JOURNAL).exists())

    def test_downgrade_same_version_and_major_upgrade_block(self):
        self.install()
        for version in ("0.0.1", (self.source / "VERSION").read_text().strip(), "4.0.0"):
            with self.subTest(version=version):
                source = self.modified_source(version)
                self.assertNotEqual(self.cli("--platform", "codex", "--upgrade", source=source).returncode, 0)
                shutil.rmtree(source)

    def test_duplicate_and_flash_after_install_block_preflight(self):
        record = self.install()
        self.assertNotEqual(self.cli("--platform", "trae").returncode, 0)
        path = self.project / ".trae/skills/mathmodel-flash"
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text("legacy flash", encoding="utf-8")
        self.assertTrue(inst.installation_errors(self.project, record["version"]))

    def test_package_tampering_rejected_before_target_writes(self):
        source = self.modified_source()
        (source / "skills/pro-workflow-orchestrator/SKILL.md").write_text("tampered", encoding="utf-8")
        self.assertNotEqual(self.cli("--platform", "codex", source=source).returncode, 0)
        self.assertEqual(snapshot(self.project), {})

    def test_manifest_traversal_and_case_collisions_rejected(self):
        for value in ("../outside", "/absolute", "C:/outside", "a/../b", "a\\b", "a//b"):
            with self.assertRaises(inst.InstallError):
                inst.rel_name(value)
        with self.assertRaises(inst.InstallError):
            inst.hash_map({"a/file": "0" * 64, "a/FILE": "0" * 64})

    def test_record_cannot_claim_unrelated_files(self):
        record = self.install()
        record["files"]["AGENTS.md"] = "0" * 64
        (self.project / inst.RECORD).write_text(json.dumps(record), encoding="utf-8")
        self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)

    def test_concurrent_installer_rejected(self):
        with inst.installation_lock(self.project):
            result = self.cli("--platform", "codex")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Another installer", result.stdout)
        self.assertFalse((self.project / inst.RECORD).exists())

    def test_upgrade_exception_rolls_back(self):
        old = self.install()
        source = self.modified_source()
        new = inst.new_record(inst.validate_source(source), old["target"])
        replace = os.replace
        def fail_new(src, dst):
            if "/new/" in str(src).replace("\\", "/"):
                raise OSError("simulated failed rename")
            return replace(src, dst)
        with inst.installation_lock(self.project), mock.patch.object(inst.os, "replace", side_effect=fail_new):
            with self.assertRaises(OSError):
                inst.apply_install(self.project, source, new, old)
        inst.verify_owned(self.project, old)
        self.assertEqual(inst.load(self.project / inst.RECORD), old)
        self.assertFalse((self.project / inst.JOURNAL).exists())

    def test_first_install_exception_leaves_no_active_payload(self):
        incoming = inst.new_record(inst.validate_source(self.source), ".agents/skills")
        replace = os.replace
        calls = 0
        def fail_second(src, dst):
            nonlocal calls
            if "/new/" in str(src).replace("\\", "/"):
                calls += 1
                if calls == min(2, len(inst.SKILLS)):
                    raise OSError("simulated second rename failure")
            return replace(src, dst)
        with inst.installation_lock(self.project), mock.patch.object(inst.os, "replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                inst.apply_install(self.project, self.source, incoming, None)
        self.assertEqual(inst.scan_installations(self.project), [])
        self.assertFalse((self.project / inst.RECORD).exists())
        self.assertFalse((self.project / inst.JOURNAL).exists())

    def test_recovery_never_erases_user_edits(self):
        old = self.install()
        source = self.modified_source()
        new = inst.new_record(inst.validate_source(source), old["target"])
        replace = os.replace
        def fail_new(src, dst):
            if "/new/" in str(src).replace("\\", "/"):
                raise OSError("interruption")
            return replace(src, dst)
        with inst.installation_lock(self.project), mock.patch.object(inst.os, "replace", side_effect=fail_new), \
                mock.patch.object(inst, "recover", side_effect=inst.InstallError("interrupted")):
            with self.assertRaises(inst.InstallError):
                inst.apply_install(self.project, source, new, old)
        journal = inst.load(self.project / inst.JOURNAL)
        backup = self.project / f".mathmodel/staging/{journal['id']}/old/{inst.SKILLS[0]}/SKILL.md"
        backup.write_text("user-edited recovery backup", encoding="utf-8")
        before = snapshot(self.project)
        self.assertNotEqual(self.cli("--recover").returncode, 0)
        self.assertEqual(snapshot(self.project), before)

    def test_hard_interruption_blocks_until_recovery(self):
        old = self.install()
        source = self.modified_source()
        script = (
            "import sys,os; from pathlib import Path; "
            f"sys.path.insert(0, {str(self.source / 'skills/pro-workflow-orchestrator/scripts')!r}); "
            "import installation as i\n"
            f"p=Path({str(self.project)!r}); s=Path({str(source)!r})\n"
            "old=i.load(p/i.RECORD); new=i.new_record(i.validate_source(s),old['target'])\n"
            "replace=os.replace\ndef interrupt(src,dst):\n"
            " if '/new/' in str(src).replace(chr(92),'/'): os._exit(77)\n"
            " return replace(src,dst)\nos.replace=interrupt\n"
            "with i.installation_lock(p): i.apply_install(p,s,new,old)\n"
        )
        result = subprocess.run([sys.executable, "-S", "-c", script], capture_output=True)
        self.assertEqual(result.returncode, 77, result.stderr)
        self.assertTrue(inst.installation_errors(self.project, old["version"]))
        self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)
        result = self.cli("--recover")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(inst.load(self.project / inst.RECORD), old)
        inst.verify_owned(self.project, old)

    def test_package_in_download_subdirectory_is_not_active(self):
        shutil.copytree(self.source / "skills", self.project / "downloads/bundle/skills")
        self.install()

    def test_source_cannot_be_used_as_contest_root(self):
        result = subprocess.run([sys.executable, "-S", str(self.source / "install.py"),
            "--project-root", str(self.source), "--platform", "codex"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_home_and_global_config_directories_are_not_projects(self):
        home = self.root / "fake home"
        home.mkdir()
        for project in (home, home / ".agents", home / ".codex/work"):
            project.mkdir(parents=True, exist_ok=True)
            before = snapshot(home)
            result = subprocess.run([sys.executable, "-S", str(self.source / "install.py"),
                "--project-root", str(project), "--platform", "codex"], capture_output=True,
                env={**os.environ, "HOME": str(home), "USERPROFILE": str(home), "CODEX_HOME": str(home / ".codex")})
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(snapshot(home), before)

    def test_symlink_destination_rejected(self):
        external = self.root / "outside"
        external.mkdir()
        link = self.project / ".agents"
        try:
            link.symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        try:
            self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)
            self.assertEqual(snapshot(external), {})
        finally:
            link.unlink()

    @unittest.skipUnless(os.name == "nt", "Windows junctions")
    def test_windows_junction_destination_rejected(self):
        external = self.root / "outside"
        external.mkdir()
        link = self.project / ".agents"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(external)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)
            self.assertEqual(snapshot(external), {})
        finally:
            link.rmdir()



    def test_partial_foreign_payload_beside_owned_entry_is_blocked(self):
        record = self.install()
        foreign = "pro-review-board" if inst.EDITION != "pro" else "paper-micro-unit-generator"
        path = self.project / record["target"] / foreign
        path.mkdir()
        (path / "SKILL.md").write_text("foreign partial payload", encoding="utf-8")
        before = snapshot(self.project)
        self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)
        self.assertTrue(inst.installation_errors(self.project, record["version"]))
        self.assertEqual(snapshot(self.project), before)

    def test_latex_marker_is_recognized_and_never_adopted(self):
        path = self.project / ".claude/skills/paper-workflow-orchestrator"
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text("legacy latex", encoding="utf-8")
        (path / "MATHMODEL_EDITION.json").write_text(json.dumps({
            "product": "MathModel-Skill", "edition": "latex",
            "version": "2.0.0-latex.1", "entry_skill": "paper-workflow-orchestrator",
        }), encoding="utf-8")
        self.assertEqual(inst.scan_installations(self.project)[0]["edition"], "latex")
        before = snapshot(self.project)
        self.assertNotEqual(self.cli("--platform", "codex").returncode, 0)
        self.assertEqual(snapshot(self.project), before)

    def test_universal_archive_has_one_payload_and_standard_library_installer(self):
        with zipfile.ZipFile(io.BytesIO(self.archive)) as archive:
            names = archive.namelist()
            self.assertIn("install.py", names)
            self.assertIn(inst.BUILD, names)
            self.assertNotIn("AGENTS.md", names)
            self.assertNotIn("CLAUDE.md", names)
            self.assertFalse(any(p.startswith((".agents/", ".claude/", ".trae/", "packages/")) for p in names))
            actual = sorted(p.split("/")[1] for p in names if p.startswith("skills/") and p.endswith("/SKILL.md"))
            self.assertEqual(actual, list(inst.SKILLS))
            self.assertTrue(all(i.compress_type == zipfile.ZIP_STORED for i in archive.infolist()))
            manifest = json.loads(archive.read(inst.BUILD))
            self.assertEqual(manifest["edition"], inst.EDITION)
            self.assertEqual(manifest["entry_skill"], inst.ENTRY)

if __name__ == "__main__":
    unittest.main()

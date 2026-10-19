"""Offline installed workflow checks, not host UI or model quality acceptance."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_flash_tests as workflow
from install_fixture import install_bundle


class InstalledWorkflowTests(unittest.TestCase):
    def test_three_install_locations_run_the_same_evidence_chain(self):
        for platform in ("codex", "claude", "trae"):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory(prefix="flash-installed-") as temporary:
                original = workflow.run
                installed = {}
                def run(script, cwd, *args):
                    if cwd not in installed:
                        installed[cwd] = install_bundle(cwd, platform)
                    script = installed[cwd] / script.relative_to(workflow.SKILL_ROOT.parent)
                    return original(script, cwd, *args)
                with patch.object(workflow, "SANDBOX", Path(temporary) / "中文 contest space"), patch.object(workflow, "run", side_effect=run):
                    workflow.test_happy_path()
                project, skills = next(iter(installed.items()))
                self.assertFalse(any(skills.rglob("paper_output_flash")))
                entry = skills / "mathmodel-flash/scripts/flash_preflight.py"
                # Preflight must revalidate managed files, not trust a prior PASS.
                (skills / "mathmodel-flash/SKILL.md").write_text("user customization", encoding="utf-8")
                result = original(entry, project)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                report = json.loads((project / "paper_output_flash/input_manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

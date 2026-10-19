"""Installed synthetic pipeline with real LibreOffice, no model/API calls."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from install_fixture import install_bundle, ROOT


class InstalledWorkflowTests(unittest.TestCase):
    def test_three_install_locations_run_the_frozen_evidence_pipeline(self):
        for platform in ("codex", "claude", "trae"):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory(prefix="pro-installed-") as temporary:
                project = Path(temporary) / "中文 contest space"
                project.mkdir()
                skills = install_bundle(project, platform)
                code = (
                    "import sys; from pathlib import Path; "
                    f"sys.path.insert(0, {str(ROOT / 'tests')!r}); "
                    "from pro_fixture import complete; "
                    f"complete(Path({str(project)!r}))"
                )
                result = subprocess.run([sys.executable, "-c", code], cwd=project,
                    env={**os.environ, "MATHMODEL_TEST_SKILLS": str(skills),
                         "MATHMODEL_TEST_PLATFORM": "claude-code" if platform == "claude" else platform},
                    capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((project / "paper_output_pro/pro_gate_report.json").is_file())
                self.assertFalse(any(skills.rglob("paper_output_pro")))


if __name__ == "__main__":
    unittest.main()

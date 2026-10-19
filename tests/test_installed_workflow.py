"""Installed S6 -> TeX export; does not claim real XeLaTeX rendering."""
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_evidence_gate as workflow
from install_fixture import install_bundle


class InstalledWorkflowTests(unittest.TestCase):
    def test_three_install_locations_preserve_evidence_and_tex_checks(self):
        for platform in ("codex", "claude", "trae"):
            with self.subTest(platform=platform):
                case = workflow.EvidenceTests("test_valid_and_policy_version")
                case.setUp()
                try:
                    skills = install_bundle(case.root, platform)
                    problem = case.root / "problem_files"
                    problem.mkdir()
                    (problem / "task.md").write_text("# Synthetic optimization task\nFind and explain the minimum cost with documented input data.\n", encoding="utf-8")
                    def run(relative):
                        return subprocess.run([sys.executable, str(skills / relative)], cwd=case.root,
                            capture_output=True, text=True, encoding="utf-8")
                    result = run("paper-workflow-orchestrator/scripts/preflight_check.py")
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    source = case.out / "final_paper_source.md"
                    source.write_text("# Paper\n\nThe computed cost is 2.\n", encoding="utf-8")
                    with patch.object(workflow, "GATE", skills / "quality-assurance-auditor/scripts/evidence_gate.py"):
                        case.test_valid_and_policy_version()
                        result = run("paper-formal-writer/scripts/format_formal_latex.py")
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertTrue((case.out / "final_paper.tex").is_file())
                        report = json.loads((case.out / "latex_build_report.json").read_text(encoding="utf-8"))
                        self.assertEqual(report["compile"]["status"], "SKIPPED")
                        self.assertFalse((case.out / "final_paper.pdf").exists())
                        (case.out / "tables/q1.csv").write_text("metric,value\ncost,999\n", encoding="utf-8")
                        self.assertNotEqual(run("paper-formal-writer/scripts/format_formal_latex.py").returncode, 0)
                    self.assertFalse(any(skills.rglob("paper_output")))
                    (skills / "paper-formal-writer/SKILL.md").write_text("user customization", encoding="utf-8")
                    self.assertNotEqual(run("paper-workflow-orchestrator/scripts/preflight_check.py").returncode, 0)
                finally:
                    case.doCleanups()


if __name__ == "__main__":
    unittest.main()

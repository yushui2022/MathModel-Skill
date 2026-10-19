"""Offline host-directory validation, not a claim of host UI auto-discovery."""
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import run_tests as workflow
from install_fixture import install_bundle
import test_validation_integration as validation_cases


class InstalledWorkflowTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("scipy"), "optional scipy missing")
    def test_installed_evidence_chains(self):
        for platform in ("codex", "claude", "trae"):
            with self.subTest(platform=platform):
                case = validation_cases.ValidationIntegrationTests("test_two_forward_cases_and_real_claim_audit")
                case.install_platform = platform
                result = unittest.TestResult()
                case.run(result)
                self.assertTrue(result.wasSuccessful(), result.failures + result.errors)

    def test_installed_render_pipeline(self):
        original = workflow.run
        installed = {}
        def run(cmd, cwd, env=None):
            if len(cmd) > 1:
                script = workflow.Path(cmd[1])
                if script.is_absolute() and script.is_relative_to(workflow.SKILLS):
                    if cwd not in installed:
                        installed[cwd] = install_bundle(cwd, "claude")
                    if script == workflow.PREPARE_AUTHORING and "--delivery" not in cmd:
                        cmd = [*cmd, "--delivery", "smoke-test", "--scope-reason", "Installed synthetic fixture"]
                    cmd = [cmd[0], str(installed[cwd] / script.relative_to(workflow.SKILLS)), *cmd[2:]]
            return original(cmd, cwd, env)
        with patch.object(workflow, "run", side_effect=run):
            workflow.test_render_required_when_libreoffice_is_available()
        if os.environ.get("MATHMODEL_REQUIRE_RENDER") == "1":
            self.assertTrue(installed, "Required installed rendering did not execute")

    def test_quickstart_from_different_cwd_and_guard_rechecks_installation(self):
        cwd = workflow.make_problem_scenario("scenario_universal_quickstart")
        skills = install_bundle(cwd, "codex")
        script = skills / "paper-workflow-orchestrator/scripts/quickstart_run.py"
        result = workflow.run([sys.executable, str(script), "--project-root", str(cwd)], workflow.REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue((cwd / "paper_output/quickstart/quickstart_scaffold.docx").exists())
        self.assertFalse((cwd / "paper_output/final_paper.docx").exists())
        self.assertFalse(any(skills.glob("*/paper_output")))
        preflight = skills / "paper-workflow-orchestrator/scripts/preflight_check.py"
        self.assertEqual(workflow.run([sys.executable, str(preflight)], cwd).returncode, 0)
        changed = skills / "paper-formal-writer/SKILL.md"
        changed.write_text("user change", encoding="utf-8")
        guard = skills / "paper-workflow-orchestrator/scripts/workflow_guard.py"
        result = workflow.run([sys.executable, str(guard), "--skill", "problem-doc-model-selector"], cwd)
        self.assertNotEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()

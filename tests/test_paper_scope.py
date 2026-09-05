"""Scope checks are separate from the small workflow/render smoke fixtures."""
import sys
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_tests as workflow

sys.path.insert(0, str(workflow.PREPARE_AUTHORING.parent))
from paper_scope import body_text, check_rendered_scope, delivery_scope, scope_errors, render_delivery_errors
from authoring_contracts import safe_relative_path


class PaperScopeTests(unittest.TestCase):
    def plan(self, **kwargs):
        return {"delivery": delivery_scope(**kwargs), "question_ids": ["Q1", "Q2"]}

    def test_default_auto_does_not_accept_short_outline_as_competition(self):
        cwd, output = workflow.make_staged_scenario("scope_default", "S6")
        workflow.write_json(output / "plan/paper_outline.json", {
            "target_words": {"ideal": 300}, "questions": [{"question_id": "Q1"}],
        })
        result = workflow.run([sys.executable, str(workflow.PREPARE_AUTHORING), "--delivery", "competition"], cwd)
        self.assertEqual(result.returncode, 0, result.stdout)
        plan = workflow.load_json(output / "plan/writing_plan.json")
        self.assertEqual(plan["mode"], "section")
        self.assertGreaterEqual(plan["target_chars"]["ideal"], 14000)
        self.assertEqual(plan["delivery"]["min_body_chars"], 8000)

    def test_scope_exceptions_require_reason(self):
        for kwargs in ({"mode": "short-report"}, {"min_pages": 2}, {"min_body_chars": 100}):
            with self.assertRaises(ValueError):
                delivery_scope(**kwargs)
        self.assertEqual(delivery_scope("short-report", "User requested a short report")["min_pages"], 1)

    def test_small_declared_target_does_not_bypass_floor(self):
        plan = self.plan()
        plan["target_chars"] = {"ideal": 1}
        self.assertTrue(any("too short" in e for e in scope_errors("answer", plan)))

    def test_comments_code_appendix_cannot_pad_length(self):
        text = "# 5.1 Q1\nAnswer.\n<!--" + "hidden" * 2000 + "-->\n```python\n" + "code" * 2000 + "\n```\n# 附录\n" + "appendix" * 2000
        self.assertTrue(any("too short" in e for e in scope_errors(text, self.plan())))

    def test_hidden_question_heading_does_not_count(self):
        text = "<!--\n# 5.1 Q1\n-->\n" + "a" * 8100 + "\n# 5.2 Q2\n" + "b" * 400
        self.assertTrue(any("missing" in e and "Q1" in e for e in scope_errors(text, self.plan())))

    def test_each_question_needs_body(self):
        text = "# 5.1 Q1\n" + "a" * 8100 + "\n# 5.2 Q2\nshort"
        self.assertTrue(any("Q2" in e for e in scope_errors(text, self.plan())))
        self.assertEqual(scope_errors(text + "b" * 400, self.plan()), [])

    def test_real_pages_not_word_metadata(self):
        errors, _ = check_rendered_scope(["page"] * 5, self.plan())
        self.assertTrue(errors)
        self.assertEqual(check_rendered_scope(["page"] * 18, self.plan())[0], [])

    def test_appendix_pages_excluded(self):
        errors, counts = check_rendered_scope(["body"] * 5 + ["Appendix A"] + ["code"] * 20, self.plan())
        self.assertTrue(errors)
        self.assertEqual(counts["counted_main_pages"], 5)
        errors, counts = check_rendered_scope(["body"] * 5 + ["附录 A 补充算法"] + ["code"] * 20, self.plan())
        self.assertEqual(counts["counted_main_pages"], 5)
        self.assertTrue(errors)
        self.assertTrue(check_rendered_scope([""] * 18, self.plan())[0])

    def test_short_scope_remains_explicit(self):
        plan = self.plan(mode="smoke-test", reason="Synthetic fixture")
        self.assertEqual(check_rendered_scope(["body"], plan)[0], [])

    def test_skipped_render_does_not_finish_formal_delivery(self):
        self.assertTrue(render_delivery_errors(self.plan(), {"status": "SKIPPED"}))
        self.assertTrue(render_delivery_errors(self.plan(mode="short-report", reason="user request"), {"status": "UNAVAILABLE"}))
        self.assertEqual(render_delivery_errors(self.plan(mode="smoke-test", reason="fixture"), {"status": "SKIPPED"}), [])

    def test_workflow_guard_does_not_trust_skipped_render_pass(self):
        spec = importlib.util.spec_from_file_location("scope_guard", workflow.WORKFLOW_GUARD)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            out = root / "paper_output"
            plan = out / "plan/writing_plan.json"
            workflow.write_json(plan, self.plan())
            workflow.write_json(out / "format_check_report.json", {
                "status": "PASS", "render_qa": {"status": "SKIPPED"},
                "input_hashes": {"paper_output/plan/writing_plan.json": workflow.sha256_file(plan)},
            })
            with patch.multiple(guard, BASE_DIR=root, OUTPUT_DIR=out):
                report = guard.check_s8()
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(any("rendered PDF" in f for f in report["failures"]), report)

    def test_workflow_guard_rechecks_rendered_pdf_hash(self):
        spec = importlib.util.spec_from_file_location("pdf_guard", workflow.WORKFLOW_GUARD)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            out = root / "paper_output"
            plan = out / "plan/writing_plan.json"
            workflow.write_json(plan, self.plan())
            pdf = out / "rendered.pdf"
            pdf.write_bytes(b"old test artifact")
            render = {"status": "PASS", "pdf": "paper_output/rendered.pdf", "pdf_sha256": workflow.sha256_file(pdf)}
            workflow.write_json(out / "format_check_report.json", {
                "status": "PASS", "render_qa": render,
                "input_hashes": {"paper_output/plan/writing_plan.json": workflow.sha256_file(plan)},
            })
            pdf.write_bytes(b"tampered")
            with patch.multiple(guard, BASE_DIR=root, OUTPUT_DIR=out):
                report = guard.check_s8()
            self.assertTrue(any("PDF is missing or changed" in f for f in report["failures"]), report)

    def test_path_roots_and_drives(self):
        for value in ("C:escape.md", "C:/escape.md", "../escape.md", "/tmp/escape", "a\\..\\escape"):
            with self.assertRaises(ValueError):
                safe_relative_path(Path.cwd(), value)

    def test_platform_preflight_keeps_foreign_roots(self):
        for script in (workflow.CODEX_PREFLIGHT, workflow.TRAE_PREFLIGHT):
            text = script.read_text(encoding="utf-8")
            for root in (".claude/skills", ".agents/skills", ".codex/skills", ".trae/skills"):
                self.assertIn(root, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

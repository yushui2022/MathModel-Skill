"""Scope/long-paper regressions. Generated prose/PDF fixtures are not competition papers."""
from __future__ import annotations

import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pro_fixture import SCRIPTS, envelope, run
from pro_contracts import read_json, write_json
from pro_authoring_policy import (
    COMPONENTS, check_authoring_scope, check_page_counts, locate_pdf_sections,
    make_policy, plan_inputs, prose, read_policy,
)


class AuthoringPolicyTests(unittest.TestCase):
    def setUp(self):
        self.project = Path(tempfile.mkdtemp(prefix="pro-authoring-", dir=os.environ.get("MATHMODEL_TEST_TEMP", tempfile.gettempdir())))
        self.root = self.project / "paper_output_pro"
        self.root.mkdir()
        write_json(self.root / "pro_config.json", envelope("fixture", paper_delivery=make_policy()))
        write_json(self.root / "problem_consensus.json", envelope("fixture", subproblems=[{"subproblem_id": "q1"}]))
        write_json(self.root / "evidence_freeze.json", envelope("fixture"))
        self.plan = {"delivery_mode": "competition", "input_hashes": plan_inputs(self.root), "sections": [
            {"section_id": "abstract", "title": "Abstract", "kind": "abstract"},
            {"section_id": "model", "title": "Question One", "kind": "body"}],
            "subproblem_coverage": [{"subproblem_id": "q1", "section_ids": ["model"], "claim_ids": ["C1"],
                "arguments": {c: {"section_id": "model", "anchor": f"q1:{c}"} for c in COMPONENTS}}]}
        self.claims = {"C1": {"section_id": "model"}}
        # Repetition is deliberate here: this tests scope plumbing, not the existing prose-quality audit.
        self.spans = {"abstract": "Fixture summary.", "model": "\n\n".join(
            (f"Fixture discussion of {c} and its documented scope. " * 45)
            + f"<!-- argument:q1:{c} -->" + (" <!-- claim:C1 -->" if c in {"results", "validation"} else "")
            for c in COMPONENTS)}

    def tearDown(self):
        shutil.rmtree(self.project)

    def errors(self):
        return check_authoring_scope(self.root, self.plan, self.spans, self.claims)

    def test_complete_scope_mapping_passes_structural_check(self):
        self.assertFalse(self.errors())

    def test_default_is_full_competition_not_short_report(self):
        policy = make_policy()
        self.assertEqual(policy["mode"], "competition")
        self.assertEqual(policy["target_pages"], [18, 24])
        self.assertEqual(policy["minimum_body_characters"], 8000)

    def test_short_and_custom_scopes_require_reason(self):
        for kwargs in ({"mode": "short-report"}, {"mode": "smoke-test"}, {"target_pages": [2, 5]}, {"minimum_body_characters": 1000}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                make_policy(**kwargs)
        self.assertEqual(make_policy(mode="short-report", scope_reason="User requests a short report")["mode"], "short-report")

    def test_invalid_numeric_scope_and_contest_override_rejected(self):
        for target in ([0, 20], [20, 2], [True, 20], [18.0, 24], [1], "18-24"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                make_policy(target_pages=target, scope_reason="fixture")
        with self.assertRaises(ValueError):
            make_policy(contest="mcm-2026", target_pages=[20, 30])
        config = read_json(self.root / "pro_config.json")
        config["paper_delivery"]["hard_max_pages"] = 100
        write_json(self.root / "pro_config.json", config)
        with self.assertRaises(ValueError):
            read_policy(self.root)

    def test_preflight_preserves_explicit_short_scope_on_resume(self):
        (self.project / "problem_files").mkdir()
        (self.project / "problem_files/task.txt").write_text("small fixture", encoding="utf-8")
        args = ["--project-root", self.project, "--platform", "codex", "--model", "astra"]
        run(SCRIPTS / "pro_preflight.py", *args, "--paper-mode", "short-report", "--scope-reason", "User asks for a short report")
        before = read_policy(self.root)
        run(SCRIPTS / "pro_preflight.py", *args)
        self.assertEqual(before, read_policy(self.root))

    def test_changing_approved_scope_makes_plan_stale(self):
        config = read_json(self.root / "pro_config.json")
        config["paper_delivery"] = make_policy(mode="short-report", scope_reason="Changed user scope")
        write_json(self.root / "pro_config.json", config)
        self.assertTrue(any("stale" in e for e in self.errors()))

    def test_plan_cannot_silently_downgrade_mode(self):
        self.plan["delivery_mode"] = "smoke-test"
        self.assertTrue(any("silently" in e for e in self.errors()))

    def test_new_question_requires_answer_not_just_new_title(self):
        write_json(self.root / "problem_consensus.json", envelope("fixture", subproblems=[{"subproblem_id": "q1"}, {"subproblem_id": "q2"}]))
        self.plan["input_hashes"] = plan_inputs(self.root)
        self.assertTrue(any("every confirmed subproblem" in e for e in self.errors()))

    def test_missing_component_blocks_full_paper(self):
        del self.plan["subproblem_coverage"][0]["arguments"]["derivation"]
        self.assertTrue(any("derivation" in e for e in self.errors()))

    def test_skeletal_argument_is_not_covered_by_a_heading(self):
        self.spans["model"] = self.spans["model"].replace("<!-- argument:q1:method -->", "") + "\n\nMethod. <!-- argument:q1:method -->"
        self.assertTrue(any("skeletal" in e for e in self.errors()))

    def test_frozen_results_and_validation_cannot_be_empty_claims(self):
        self.spans["model"] = self.spans["model"].replace("<!-- claim:C1 -->", "")
        self.assertTrue(any("frozen claim" in e for e in self.errors()))

    def test_reusing_one_argument_anchor_cannot_cover_several_components(self):
        self.plan["subproblem_coverage"][0]["arguments"]["method"]["anchor"] = "q1:derivation"
        self.assertTrue(any("reuse" in e for e in self.errors()))

    def test_appendix_cannot_replace_subproblem_body(self):
        self.plan["sections"][1]["kind"] = "appendix"
        self.assertTrue(any("body" in e for e in self.errors()))

    def test_comments_code_headings_urls_and_images_do_not_inflate_prose(self):
        value = "# " + "heading" * 2000 + "\n<!-- " + "hidden" * 2000 + " -->\n```python\n" + "code" * 2000 + "\n```\n[visible](https://example.com/" + "url" * 2000 + ")\n![figure](x.png)"
        self.assertEqual(prose(value), "visible")

    def test_five_page_short_paper_is_not_full_competition_acceptance(self):
        pages = [{"section_id": "q1", "kind": "body", "pages": list(range(1, 6))}]
        self.assertTrue(check_page_counts(make_policy(), pages, 5)[0])
        self.assertFalse(check_page_counts(make_policy(mode="smoke-test", scope_reason="engineering fixture"), pages, 5)[0])

    def test_appendices_do_not_satisfy_main_length_target(self):
        pages = [{"section_id": "q1", "kind": "body", "pages": list(range(1, 6))},
                 {"section_id": "a", "kind": "appendix", "pages": list(range(6, 26))}]
        errors, details = check_page_counts(make_policy(), pages, 25)
        self.assertTrue(errors)
        self.assertEqual(details["counted_pages"], 5)

    def test_cumcm_counts_body_not_unlimited_appendix(self):
        pages = [{"section_id": "abstract", "kind": "abstract", "pages": [1]},
                 {"section_id": "q1", "kind": "body", "pages": list(range(2, 22))},
                 {"section_id": "appendix", "kind": "appendix", "pages": list(range(22, 50))}]
        self.assertFalse(check_page_counts(make_policy(contest="cumcm-2026"), pages, 49)[0])
        pages[1]["pages"] = list(range(2, 33))
        self.assertTrue(any("limit exceeded" in e for e in check_page_counts(make_policy(contest="cumcm-2026"), pages, 49)[0]))

    def test_mcm_counts_appendix_and_cover_but_excludes_only_ai_pages(self):
        pages = [{"section_id": "main", "kind": "body", "pages": list(range(2, 23))},
                 {"section_id": "appendix", "kind": "appendix", "pages": [23, 24, 25]},
                 {"section_id": "ai", "kind": "ai-disclosure", "pages": [25, 26, 27]}]
        errors, details = check_page_counts(make_policy(contest="mcm-2026"), pages, 27)
        self.assertFalse(errors)
        self.assertEqual(details["counted_pages"], 25)
        pages[1]["pages"].append(26)
        self.assertTrue(check_page_counts(make_policy(contest="mcm-2026"), pages, 27)[0])

    def test_planning_upper_target_is_not_an_invented_competition_limit(self):
        pages = [{"section_id": "q1", "kind": "body", "pages": list(range(1, 27))}]
        errors, details = check_page_counts(make_policy(contest="cumcm-2026"), pages, 26)
        self.assertFalse(errors)
        self.assertTrue(details["above_planning_target"])

    def test_abstract_over_one_page_is_blocking_for_contest_profiles(self):
        pages = [{"section_id": "abstract", "kind": "abstract", "pages": [1, 2]},
                 {"section_id": "q1", "kind": "body", "pages": list(range(3, 23))}]
        self.assertTrue(any("abstract" in e for e in check_page_counts(make_policy(contest="cumcm-2026"), pages, 22)[0]))

    def test_twenty_real_pdf_pages_are_counted_from_positions(self):
        import pymupdf
        with pymupdf.open() as pdf:
            for index in range(21):
                page = pdf.new_page()
                page.insert_text((72, 80), "Abstract" if index == 0 else "Question One" if index == 1 else f"Continuation {index}")
                page.insert_text((72, 120), "Synthetic pagination test, not mathematical evidence.")
            pages = locate_pdf_sections(self.plan, pdf)
            self.assertEqual(pages[0]["pages"], [1])
            self.assertEqual(pages[1]["pages"], list(range(2, 22)))
            errors, details = check_page_counts(make_policy(contest="cumcm-2026"), pages, len(pdf))
            self.assertFalse(errors)
            self.assertEqual(details["counted_pages"], 20)

    def test_ambiguous_pdf_heading_is_rejected_not_guessed(self):
        import pymupdf
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((72, 80), "Abstract\nQuestion One\nQuestion One")
            with self.assertRaises(ValueError):
                locate_pdf_sections(self.plan, pdf)


if __name__ == "__main__":
    unittest.main()

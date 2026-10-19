"""Numerical statements must retain meaning through S7 and the DOCX gate."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/paper-formal-writer/scripts"
sys.path.insert(0, str(SCRIPTS))
from authoring_contracts import collect_requirements, sha256_file, write_json, authoring_pass_errors
from claim_bindings import VERSION, build_catalog, audit_claims, claims_path, record_errors, check_plan


class ClaimBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="metric-claims-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.out = self.root / "paper_output"
        self.table = self.out / "tables/results.csv"
        self.table.parent.mkdir(parents=True)
        self.table.write_text("id,value,unit\ntest.rmse,1.25,万元\n", encoding="utf-8")
        self.metric = {
            "metric_id": "test.rmse", "question_id": "Q1", "metric_name": "RMSE",
            "value": 1.25, "unit": "万元", "status": "computed", "split": "test",
            "sample_scope": "2024年留出样本", "claim_strength": "observed",
            "source_table": {"path": "paper_output/tables/results.csv", "row": {"id": "test.rmse"},
                             "value_column": "value", "unit_column": "unit"},
        }
        self.outline = {"target_words": {"ideal": 150}, "front_matter": {"abstract_target_words": 10},
                        "sections": [{"section_id": "1", "title": "结果", "target_words": 50,
                                      "question_id": "Q1", "required_evidence": [
                                          {"type": "metric", "metric_id": "test.rmse", "name": "RMSE", "value": 1.25}]}]}
        self.section = {"requirements": collect_requirements(self.outline["sections"][0])}
        self.quote = "2024年留出样本的测试集 RMSE 为 1.25万元。"
        self.claim = {"metric_id": "test.rmse", "quote": self.quote, "value": 1.25, "unit": "万元"}
        self.draft = self.out / "drafts/sections/1.md"
        self.draft.parent.mkdir(parents=True)
        self.refresh()

    def refresh(self, extra_metrics=None, extra_artifacts=None):
        self.run = {"run_id": "experiment-001", "status": "PASS", "returncode": 0, "question_ids": ["Q1"],
                    "output_artifacts": [{"path": "paper_output/tables/results.csv", "sha256": sha256_file(self.table)},
                                         *(extra_artifacts or [])]}
        write_json(self.out / "results/run_manifest.json", {"status": "PASS", "runs": [self.run]})
        write_json(self.out / "results/metrics.json", {"items": [self.metric, *(extra_metrics or [])]})
        self.gate = {"status": "PASS", "input_hashes": {
            f"paper_output/results/{name}.json": sha256_file(self.out / f"results/{name}.json")
            for name in ("metrics", "run_manifest")}}
        write_json(self.out / "qa/evidence_gate_report.json", self.gate)

    def plan(self):
        catalog, hashes = build_catalog(self.root, [self.section], self.gate)
        return {"claim_binding_version": VERSION, "metric_catalog": catalog, "input_hashes": hashes,
                "delivery": {"mode": "short-report"}}

    def audit(self, text=None, claims=None, plan=None):
        self.draft.write_text("# 结果\n\n" + (self.quote if text is None else text), encoding="utf-8")
        write_json(claims_path(self.draft), {"schema_version": "1", "source_sha256": sha256_file(self.draft),
                                           "claims": [self.claim] if claims is None else claims})
        return audit_claims(self.root, self.draft, self.plan() if plan is None else plan, self.section)

    def test_correct_claim_resolves_run_sample_and_table(self):
        errors, resolved, hashes = self.audit()
        self.assertEqual(errors, [])
        self.assertEqual(resolved[0]["run_id"], "experiment-001")
        self.assertEqual(resolved[0]["source_table"]["row"], {"id": "test.rmse"})
        self.assertEqual(len(hashes), 1)

    def test_cached_old_claim_policy_cannot_bypass_solver_checks(self):
        plan = self.plan()
        plan['claim_binding_version'] = 1
        self.assertTrue(check_plan(plan))

    def test_wrong_split_scope_unit_or_value_is_blocked(self):
        for old, new in [("测试集", "训练集"), ("2024", "2023"), ("万元", "元"), ("万元", "万元/年"),
                         ("万元", "万元每年"), ("1.25", "2.25")]:
            with self.subTest(new=new):
                quote = self.quote.replace(old, new)
                errors, _, _ = self.audit(quote, [{**self.claim, "quote": quote}])
                self.assertTrue(errors)

    def test_train_metric_cannot_be_described_as_test(self):
        self.metric["split"] = "train"
        self.refresh()
        self.assertTrue(self.audit()[0])

    def test_stale_or_missing_sidecar_is_blocked(self):
        self.audit()
        self.draft.write_text("# Changed\n" + self.quote, encoding="utf-8")
        self.assertTrue(audit_claims(self.root, self.draft, self.plan(), self.section)[0])
        claims_path(self.draft).unlink()
        self.assertTrue(audit_claims(self.root, self.draft, self.plan(), self.section)[0])

    def test_malformed_claim_fields_are_blocked_not_crashes(self):
        for claim in ([], None, {**self.claim, "metric_id": []}, {**self.claim, "assertion": []},
                      {**self.claim, "value": True}, {**self.claim, "value": "NaN"},
                      {**self.claim, "decimals": True}, {**self.claim, "transform": {}}):
            with self.subTest(claim=claim):
                self.assertTrue(self.audit(claims=[claim])[0])

    def test_true_number_in_comment_or_code_does_not_count(self):
        for text in (f"<!-- {self.quote} -->", f"```\n{self.quote}\n```", f"![{self.quote}](image.png)"):
            self.assertTrue(self.audit(text)[0])

    def test_formula_definition_does_not_need_a_result_binding(self):
        plan = self.plan()
        self.section = {"requirements": {"evidence": []}}
        self.assertEqual(self.audit("误差定义为 $RMSE = n^{-1/2} \\sqrt{SSE}$。", [], plan)[0], [])

    def test_wrong_occurrence_cannot_hide_behind_correct_one(self):
        self.assertTrue(self.audit(self.quote + "\n" + self.quote.replace("1.25", "9.25"))[0])

    def test_detached_optimality_assertion_is_rejected(self):
        self.assertTrue(self.audit(self.quote + "\n该方案是全局最优解。")[0])

    def test_extra_number_in_bound_sentence_is_rejected(self):
        quote = self.quote[:-1] + "，也为9.25万元。"
        self.assertTrue(self.audit(quote, [{**self.claim, "quote": quote}])[0])

    def test_metadata_cannot_be_overridden_in_binding(self):
        for key in ("run_id", "split", "sample_scope", "source_table"):
            self.assertTrue(self.audit(claims=[{**self.claim, key: "wrong"}])[0])

    def test_wrong_or_ambiguous_experiment_is_rejected(self):
        self.metric["run_id"] = "wrong-run"
        self.refresh()
        with self.assertRaises(ValueError):
            self.plan()
        self.metric.pop("run_id")
        self.refresh()
        manifest = {"status": "PASS", "runs": [self.run, {**self.run, "run_id": "experiment-002"}]}
        path = self.out / "results/run_manifest.json"
        write_json(path, manifest)
        self.gate["input_hashes"]["paper_output/results/run_manifest.json"] = sha256_file(path)
        with self.assertRaises(ValueError):
            self.plan()

    def test_changed_source_metadata_invalidates_plan_hashes(self):
        from authoring_contracts import validate_hashes
        plan = self.plan()
        self.metric["split"] = "train"
        self.refresh()
        self.assertTrue(validate_hashes(self.root, plan["input_hashes"], "writing plan"))

    def test_undeclared_percentage_conversion_is_rejected(self):
        self.metric.update(value=0.125, unit="1")
        self.section["requirements"]["evidence"][0]["value"] = 0.125
        self.table.write_text("id,value,unit\ntest.rmse,0.125,1\n", encoding="utf-8")
        self.refresh()
        quote = self.quote.replace("1.25万元", "12.5%")
        claim = {**self.claim, "quote": quote, "value": 12.5, "unit": "%", "transform": "ratio_to_percent"}
        self.assertTrue(self.audit(quote, [claim])[0])
        self.metric["allowed_transforms"] = ["identity", "ratio_to_percent"]
        self.refresh()
        self.assertEqual(self.audit(quote, [claim])[0], [])
        self.assertTrue(self.audit(quote.replace("12.5%", "0.125%"), [{**claim, "quote": quote.replace("12.5%", "0.125%"), "value": 0.125}])[0])

    def test_rounding_is_explicit_and_signed_scientific_values_work(self):
        quote = self.quote.replace("1.25万元", "1.3万元")
        self.assertTrue(self.audit(quote, [{**self.claim, "quote": quote, "value": 1.3}])[0])
        self.assertEqual(self.audit(quote, [{**self.claim, "quote": quote, "value": 1.3, "decimals": 1}])[0], [])
        self.metric["value"] = -0.00125
        self.section["requirements"]["evidence"][0]["value"] = -0.00125
        self.table.write_text("id,value,unit\ntest.rmse,-0.00125,万元\n", encoding="utf-8")
        self.refresh()
        quote = self.quote.replace("1.25万元", "-1.25e-3万元")
        self.assertEqual(self.audit(quote, [{**self.claim, "quote": quote, "value": -0.00125}])[0], [])

    def test_missing_metadata_does_not_fall_back_to_nearby_labels(self):
        for field in ("metric_id", "unit", "split", "sample_scope", "source_table"):
            metric = self.metric.copy()
            self.metric.pop(field)
            self.refresh()
            with self.assertRaises(ValueError):
                self.plan()
            self.metric = metric

    def test_ambiguous_ids_or_rows_are_rejected(self):
        self.refresh(extra_metrics=[copy.deepcopy(self.metric)])
        with self.assertRaises(ValueError):
            self.plan()
        self.refresh()
        self.table.write_text("id,value,unit\ntest.rmse,1.25,万元\ntest.rmse,1.25,万元\n", encoding="utf-8")
        self.refresh()
        with self.assertRaises(ValueError):
            self.plan()

    def test_metrics_value_must_equal_source_table(self):
        self.metric["value"] = 999
        self.section["requirements"]["evidence"][0]["value"] = 999
        self.refresh()
        with self.assertRaisesRegex(ValueError, "disagrees"):
            self.plan()

    def test_unrecorded_changed_or_escaping_source_is_rejected(self):
        self.table.write_text("changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.plan()
        for path in ("../results.csv", "C:/results.csv", "/results.csv"):
            self.metric["source_table"]["path"] = path
            self.refresh()
            with self.assertRaises(ValueError):
                self.plan()

    def test_same_metric_name_for_train_and_test_is_unambiguous_by_id(self):
        plan = self.plan()
        train = {**plan["metric_catalog"]["test.rmse"], "metric_id": "train.rmse", "split": "train"}
        plan["metric_catalog"]["train.rmse"] = train
        self.assertEqual(self.audit(plan=plan)[0], [])

    def test_feasible_or_optimal_requires_verification_evidence(self):
        quote = self.quote[:-1] + "，取得全局最优解。"
        self.assertTrue(self.audit(quote, [{**self.claim, "quote": quote, "assertion": "optimal"}])[0])
        self.metric["claim_strength"] = "optimal"
        self.refresh()
        with self.assertRaises(ValueError):
            self.plan()
        proof = self.out / "results/verification.json"
        self.metric["verification_path"] = "paper_output/results/verification.json"
        report = {"status": "PASS", "metric_id": "test.rmse", "objective_value": 1.25, "unit": "万元",
                  "feasibility_verified": True, "optimality_verified": False}
        write_json(proof, report)
        self.refresh(extra_artifacts=[{"path": self.metric["verification_path"], "sha256": sha256_file(proof)}])
        with self.assertRaises(ValueError):
            self.plan()
        report["optimality_verified"] = True
        write_json(proof, report)
        self.refresh(extra_artifacts=[{"path": self.metric["verification_path"], "sha256": sha256_file(proof)}])
        with self.assertRaisesRegex(ValueError, "solver evidence"):
            self.plan()
        # Legacy feasibility records remain readable; optimum needs solver evidence.
        self.metric["claim_strength"] = "feasible"
        report["optimality_verified"] = False
        write_json(proof, report)
        self.refresh(extra_artifacts=[{"path": self.metric["verification_path"], "sha256": sha256_file(proof)}])
        self.plan()
        report["unit"] = "元"
        write_json(proof, report)
        self.refresh(extra_artifacts=[{"path": self.metric["verification_path"], "sha256": sha256_file(proof)}])
        with self.assertRaises(ValueError):
            self.plan()

    def test_chinese_and_english_overclaim_and_negation(self):
        for tail in ("，为最优解。", "，未证明最优但取得全局最优解。", ", globally optimal.", ", a feasible solution."):
            quote = self.quote[:-1] + tail
            self.assertTrue(self.audit(quote, [{**self.claim, "quote": quote}])[0])
        for tail in ("，未证明全局最优。", ", not proven optimal."):
            quote = self.quote[:-1] + tail
            self.assertEqual(self.audit(quote, [{**self.claim, "quote": quote}])[0], [])

    def test_changed_binding_invalidates_approved_record(self):
        _, _, hashes = self.audit()
        record = {"claims_sha256": next(iter(hashes.values()))}
        self.assertEqual(record_errors(self.root, self.draft, record, self.plan()), [])
        write_json(claims_path(self.draft), {"claims": []})
        self.assertTrue(record_errors(self.root, self.draft, record, self.plan()))

    def test_old_formal_plans_need_migration_but_smoke_tests_remain_explicit(self):
        self.assertTrue(check_plan({"delivery": {"mode": "competition"}}))
        self.assertEqual(check_plan({"delivery": {"mode": "smoke-test"}}), [])
        plan = self.plan()
        plan.update(metric_catalog={}, sections=[self.section])
        self.assertTrue(check_plan(plan))

    def test_end_to_end_prepare_section_assembly_final_and_export_freshness(self):
        write_json(self.out / "plan/paper_outline.json", self.outline)

        def command(script, *args):
            result = subprocess.run([sys.executable, str(SCRIPTS / script), "--project-root", str(self.root), *args],
                                    cwd=self.root, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        command("prepare_authoring.py", "--mode", "section", "--delivery", "short-report", "--scope-reason", "unit-test report")
        abstract = self.out / "drafts/sections/abstract.md"
        abstract.write_text("# 摘要\n\n本文研究留出样本的预测误差。", encoding="utf-8")
        write_json(claims_path(abstract), {"schema_version": "1", "source_sha256": sha256_file(abstract), "claims": []})
        command("validate_authoring.py", "--section", "abstract")
        self.audit(text=self.quote + "\n\n该实验固定数据划分与预处理方案，使用留出样本评价预测误差。量纲跟随目标变量，误差用于评价本次实验的预测质量，不外推到未观察的样本。\n\n<!-- mathmodel-evidence: metric:Q1:test.rmse -->")
        command("validate_authoring.py", "--section", "1")
        command("assemble_sections.py")
        command("validate_authoring.py", "--assembled")
        final = self.out / "final_paper_source.md"
        assembly = self.out / "drafts/assembled_draft.md"
        final.write_text(assembly.read_text(encoding="utf-8") + "\n本文的验证结论仅适用于已声明的数据范围，未来推广仍需外部样本支持。\n", encoding="utf-8")
        data = json.loads(claims_path(assembly).read_text(encoding="utf-8"))
        data["source_sha256"] = sha256_file(final)
        write_json(claims_path(final), data)
        command("validate_authoring.py", "--final")
        self.assertEqual(authoring_pass_errors(self.root), [])
        approved_text = final.read_text(encoding="utf-8")
        approved_data = copy.deepcopy(data)
        final.write_text(approved_text.replace("测试集", "训练集"), encoding="utf-8")
        data["source_sha256"] = sha256_file(final)
        data["claims"][0]["quote"] = self.quote.replace("测试集", "训练集")
        write_json(claims_path(final), data)
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_authoring.py"), "--project-root", str(self.root), "--final"],
                                cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        audit = json.loads((self.out / "qa/draft_audit.json").read_text(encoding="utf-8"))
        self.assertTrue(any(i["category"] == "claim-binding" for i in audit["issues"]))
        final.write_text(approved_text, encoding="utf-8")
        data = approved_data
        write_json(claims_path(final), data)
        command("validate_authoring.py", "--final")
        guard_path = SCRIPTS.parents[1] / "paper-workflow-orchestrator/scripts/workflow_guard.py"
        spec = importlib.util.spec_from_file_location("claim_workflow_guard", guard_path)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        guard.BASE_DIR, guard.OUTPUT_DIR = self.root, self.out
        (self.out / "final_paper.docx").write_bytes(b"test-only existence fixture")
        self.assertEqual(guard.check_s7()["status"], "PASS")
        data["claims"][0]["unit"] = "元"
        write_json(claims_path(final), data)
        self.assertTrue(any("claim bindings" in error for error in authoring_pass_errors(self.root)))
        self.assertEqual(guard.check_s7()["status"], "FAIL")
        result = subprocess.run([sys.executable, str(SCRIPTS / "format_formal_docx.py")], cwd=self.root,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

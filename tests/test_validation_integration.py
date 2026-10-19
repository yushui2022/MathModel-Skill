"""Actual runner -> S6 -> S7 numerical claims, on two transparent synthetic tasks."""
from __future__ import annotations

import importlib.util
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / 'skills'
FIXTURES = REPO / 'benchmarks/validation'
sys.path.insert(0, str(SKILLS / 'paper-formal-writer/scripts'))
from authoring_contracts import sha256_file, write_json
from claim_bindings import VERSION, build_catalog, audit_claims, claims_path


@unittest.skipUnless(importlib.util.find_spec('scipy'), 'optional scipy not installed')
class ValidationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mathmodel-validation-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.skill_root = SKILLS
        if getattr(self, 'install_platform', None):
            from install_fixture import install_bundle
            self.skill_root = install_bundle(self.root, self.install_platform)
        self.output = self.root / 'paper_output'
        source = self.root / 'problem_files/series.csv'
        source.parent.mkdir()
        shutil.copyfile(FIXTURES / 'series.csv', source)
        write_json(self.output / 'input_manifest.json', {'entries': [
            {'path': 'problem_files/series.csv', 'role': 'raw_data', 'usable_for_modeling': True, 'sha256': sha256_file(source)}]})
        self.invoke(self.skill_root / 'data-cleaning-and-visualization/scripts/clean_data.py')
        self.route = json.loads((FIXTURES / 'cases.json').read_text(encoding='utf-8'))
        write_json(self.output / 'plan/model_route.json', self.route)
        self.invoke(self.skill_root / 'model-code-and-result-generator/scripts/build_result_contracts.py')
        for q in self.route['questions']:
            shutil.copyfile(FIXTURES / 'benchmark_question.py', self.output / f'code/modeling/{q["question_id"].lower()}_model.py')
        write_json(self.output / 'figure_index.json', {'figures': []})
        self.runner = self.output / 'code/modeling/run_modeling.py'

    def invoke(self, script, success=True):
        result = subprocess.run([sys.executable, str(script)], cwd=self.root, capture_output=True,
                                text=True, encoding='utf-8', timeout=90,
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def load(self, path):
        return json.loads((self.output / path).read_text(encoding='utf-8'))

    def gate(self):
        self.invoke(self.skill_root / 'quality-assurance-auditor/scripts/evidence_gate.py')
        return self.load('qa/evidence_gate_report.json')

    def section(self, metric):
        return {'requirements': {'evidence': [{'type': 'metric', 'question_id': metric['question_id'],
                 'metric_id': metric['metric_id'], 'name': metric['metric_name'], 'value': metric['value']}]}}

    def inject_metric_error(self, qid, metric_id, field, value):
        # A buggy producer, not a post-run edit: S7 must still catch semantic errors
        # even when execution hashes correctly attest to those exact wrong outputs.
        original = (FIXTURES / 'benchmark_question.py').read_text(encoding='utf-8')
        mutation = ('    data = load_json(RESULTS_DIR / "metrics.json", {})\n'
                    f'    metric = next(m for m in data["items"] if m.get("metric_id") == {metric_id!r})\n'
                    f'    metric[{field!r}] = {value!r}\n'
                    '    write_json(RESULTS_DIR / "metrics.json", data)\n')
        (self.output / f'code/modeling/{qid.lower()}_model.py').write_text(
            original.replace('    return 0', mutation + '    return 0'), encoding='utf-8')

    def test_two_forward_cases_and_real_claim_audit(self):
        self.invoke(self.runner)
        gate = self.gate()
        receipt = self.load('results/run_manifest.json')
        self.assertEqual(len(receipt['runs']), 2)
        backtest = self.load('results/q1_backtest.json')
        self.assertTrue(all(abs(p['actual'] - p['predicted']) < 1e-10 for p in backtest['predictions']))
        optimum = max(3 * x + y for x, y in itertools.product(range(3), repeat=2) if x + y <= 3)
        self.assertEqual(self.load('results/q2_optimization.json')['objective_value'], optimum)
        selected = [m for m in self.load('results/metrics.json')['items']
                    if m['metric_id'] in ('Q1.backtest.pooled.RMSE', 'Q2.optimization.objective')]
        self.assertEqual(len(selected), 2)
        for metric in selected:
            with self.subTest(metric=metric['metric_id']):
                section = self.section(metric)
                catalog, hashes = build_catalog(self.root, [section], gate)
                plan = {'claim_binding_version': VERSION, 'metric_catalog': catalog, 'input_hashes': hashes,
                        'delivery': {'mode': 'short-report'}}
                assertion = metric.get('claim_strength', 'observed')
                split = 'test set ' if metric['split'] == 'test' else ''
                suffix = ', optimal' if assertion == 'optimal' else ''
                quote = f"{metric['sample_scope']} {split}{metric['metric_name']} = {metric['value']}{metric['unit']}{suffix}."
                draft = self.output / f"drafts/{metric['question_id']}.md"
                draft.parent.mkdir(exist_ok=True)
                draft.write_text('# Results\n\n' + quote, encoding='utf-8')
                write_json(claims_path(draft), {'schema_version': '1', 'source_sha256': sha256_file(draft), 'claims': [
                    {'metric_id': metric['metric_id'], 'quote': quote, 'value': metric['value'],
                     'unit': metric['unit'], 'assertion': assertion}]})
                self.assertEqual(audit_claims(self.root, draft, plan, section)[0], [])
                self.assertTrue(catalog[metric['metric_id']]['run_id'])

    def test_generated_scaffold_is_not_automatically_formal_evidence(self):
        # Rebuild managed question scripts in a fresh location without fixture promotion.
        code = self.output / 'code/modeling/q1_model.py'
        code.unlink()
        self.invoke(self.skill_root / 'model-code-and-result-generator/scripts/build_result_contracts.py')
        self.invoke(self.runner)
        result = self.invoke(self.skill_root / 'quality-assurance-auditor/scripts/evidence_gate.py', success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.load('qa/evidence_gate_report.json')['status'], 'FAIL')

    def test_modified_solver_report_invalidates_run_evidence(self):
        self.invoke(self.runner)
        self.gate()
        report = self.load('results/q2_optimization.json')
        report['objective_value'] = 999
        write_json(self.output / 'results/q2_optimization.json', report)
        result = self.invoke(SKILLS / 'quality-assurance-auditor/scripts/evidence_gate.py', success=False)
        self.assertNotEqual(result.returncode, 0)

    def test_metric_csv_disagreement_is_blocked_before_writing(self):
        self.inject_metric_error('Q2', 'Q2.optimization.objective', 'value', 999)
        self.invoke(self.runner)
        data = self.load('results/metrics.json')
        metric = next(m for m in data['items'] if m['metric_id'] == 'Q2.optimization.objective')
        gate = self.gate()
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            build_catalog(self.root, [self.section(metric)], gate)

    def test_infeasible_run_preserves_failure_and_blocks_gate(self):
        self.invoke(self.runner)
        self.route['questions'][1]['optimization']['problem']['b_ub'] = [-1]
        write_json(self.output / 'plan/model_route.json', self.route)
        result = self.invoke(self.runner, success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.load('results/run_manifest.json')['status'], 'FAIL')
        self.assertEqual(self.load('results/q2_optimization.json')['solver_status'], 'INFEASIBLE')
        result = self.invoke(SKILLS / 'quality-assurance-auditor/scripts/evidence_gate.py', success=False)
        self.assertNotEqual(result.returncode, 0)

    def test_metric_context_must_agree_with_recorded_csv(self):
        for field, changed in [('split', 'train'), ('sample_scope', 'different sample'), ('metric_name', 'MAE')]:
            self.inject_metric_error('Q1', 'Q1.backtest.pooled.RMSE', field, changed)
            self.invoke(self.runner)
            data = self.load('results/metrics.json')
            metric = next(m for m in data['items'] if m['metric_id'] == 'Q1.backtest.pooled.RMSE')
            gate = self.gate()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f'{field} disagrees'):
                build_catalog(self.root, [self.section(metric)], gate)


if __name__ == '__main__':
    unittest.main()

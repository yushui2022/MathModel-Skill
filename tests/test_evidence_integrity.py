"""Regressions for the independent contest test; no model calls or contest outputs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_validation_integration as fixtures

SKILLS = Path(__file__).resolve().parents[1] / 'skills'
for name in ('quality-assurance-auditor', 'problem-doc-model-selector', 'data-cleaning-and-visualization',
             'paper-workflow-orchestrator', 'paper-formal-writer'):
    sys.path.insert(0, str(SKILLS / name / 'scripts'))
import evidence_gate as gate
import evidence_policy as policy
import analyze_problem as analysis
import review_problem as review
import generate_paper_figures_from_plan as previews
import build_data_visualization_plan as plot_plan
import workflow_guard as guard
from authoring_contracts import fresh_evidence_gate, sha256_file, write_json


class PolicyTests(unittest.TestCase):
    def test_status_is_fail_closed_including_conflicting_fields(self):
        for value in ('FAIL', 'ERROR', 'unknown', '', None, True, 'needs_real_modeling', 'scaffold'):
            for item in ({'status': value}, {'evidence_status': value},
                         {'status': value, 'evidence_status': 'computed'},
                         {'status': 'computed', 'evidence_status': value}):
                with self.subTest(item=item):
                    self.assertFalse(policy.accepted_status(item))
        self.assertFalse(policy.accepted_status({}))
        for value in ('computed', 'PASS', 'verified', 'validated'):
            self.assertTrue(policy.accepted_status({'status': value}))

    def test_metrics_must_be_finite_numbers(self):
        for value in (True, False, '1.25', 'passed', None, float('nan'), float('inf'), [], {}):
            with self.subTest(value=value):
                self.assertTrue(gate.metric_value_failures([{'value': value}]))
        for value in (0, -2, 1.25):
            self.assertFalse(gate.metric_value_failures([{'value': value}]))

    def test_old_policy_reports_need_reaudit(self):
        for value in (None, 1, '2', True):
            self.assertTrue(policy.policy_errors({'status': 'PASS', 'policy_version': value}))
        self.assertFalse(policy.policy_errors({'policy_version': 2}))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'marker.txt'
            marker.write_text('fresh content', encoding='utf-8')
            write_json(root / 'paper_output/qa/evidence_gate_report.json', {
                'status': 'PASS', 'input_hashes': {'marker.txt': sha256_file(marker)}})
            self.assertTrue(fresh_evidence_gate(root)[1])

    def test_heatmap_intent_is_not_mapped_to_bar(self):
        self.assertEqual(plot_plan.chart_type('优化/规划', '道路距离热图', 'destination', ['distance_km']), 'heatmap')

    def test_status_change_cannot_promote_exploratory_picture(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder, patch.object(gate, 'BASE_DIR', Path(folder)):
            Image.new('RGB', (20, 20), 'white').save(Path(folder) / 'preview.png')
            errors = gate.indexed_artifact_failures({'figure_id': 'f1', 'path': 'preview.png',
                'status': 'computed', 'evidence_role': 'exploratory'}, 'figure')
            self.assertTrue(any('探索' in e for e in errors))

    def test_artifact_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for value in ('../outside.png', 'C:\\outside.png', '/outside.png', 'sub/../../x', '', '\x00'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    policy.project_artifact(root, value)

    def test_invalid_tables_are_not_formal_evidence(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(gate, 'BASE_DIR', Path(folder)):
            path = Path(folder) / 'table.csv'
            item = {'table_id': 't1', 'path': 'table.csv', 'status': 'computed'}
            for content in ('', 'x,y\n', 'x,x\n1,2\n', 'x,y\n1,2,3\n', 'x,y\n"unterminated,2\n'):
                path.write_text(content, encoding='utf-8')
                self.assertTrue(gate.indexed_artifact_failures(item, 'table'))
            path.write_text('x,y\n1,2\n', encoding='utf-8')
            self.assertEqual(gate.indexed_artifact_failures(item, 'table'), [])

    def test_previews_are_never_computed_experiments(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(previews, 'BASE_DIR', Path(folder)):
            root = Path(folder)
            (root / 'raw.csv').write_text('destination,pit,distance_km,minimum_tonnes\nA,1,2,100\nB,2,3,200\n', encoding='utf-8')
            spec = {'figure_id': 'f1', 'question_id': 'Q1', 'data_source': 'raw.csv', 'output_path': 'plot.png',
                    'chart_type': 'sensitivity_curve', 'title': 'Sensitivity', 'x': 'destination', 'y': ['pit', 'distance_km']}
            with patch.object(previews, 'plot_figure_spec') as plotter:
                item = previews.generate_one(spec)
                plotter.assert_not_called()
                self.assertFalse(item['exists'])
            self.assertFalse((root / 'plot.png').exists())
            from PIL import Image
            Image.new('RGB', (20, 20), 'white').save(root / 'plot.png')
            spec['chart_type'] = 'line'
            spec['title'] = 'Data preview'
            with patch.object(previews, 'plot_figure_spec', return_value={
                    'path': str(root / 'plot.png'), 'ok': True, 'placeholder': False}) as plotter:
                item = previews.generate_one(spec)
                self.assertEqual(item['status'], 'needs_review')
                self.assertEqual(item['evidence_role'], 'exploratory')
                self.assertIn('非正式', plotter.call_args.args[1]['title'])


class ProblemReviewTests(unittest.TestCase):
    def test_ambiguous_numbering_requires_review(self):
        data = analysis.build_analysis('1. Minimize cost.\n2. Maximize output.', [], [])
        self.assertEqual(data['extraction_status'], 'NEEDS_REVIEW')
        self.assertTrue(review.review_errors(Path.cwd(), data))

    def test_explicit_questions_do_not_need_fallback_review(self):
        data = analysis.build_analysis('问题1：预测未来销量。\n问题2：优化运输成本。', [], [])
        self.assertEqual(len(data['questions']), 2)
        self.assertEqual(data['review_requirements'], [])

    def test_embedded_math_and_images_trigger_review(self):
        from docx import Document
        from docx.oxml import OxmlElement
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'problem.docx'
            doc = Document()
            paragraph = doc.add_paragraph('问题1：29.5%1% and 28')
            paragraph._p.append(OxmlElement('w:object'))
            paragraph._p.append(OxmlElement('m:oMath'))
            paragraph._p.append(OxmlElement('w:drawing'))
            doc.save(path)
            risks = analysis.extraction_risks(path, analysis.read_docx(path))
            self.assertTrue(any('Formula' in r for r in risks))
            self.assertTrue(any('image' in r for r in risks))

    def test_review_command_blocks_stale_sources_and_routes(self):
        with tempfile.TemporaryDirectory(prefix='problem-review-') as folder:
            root = Path(folder)
            source = root / 'problem.txt'
            source.write_text('1. Minimize cost.\n2. Maximize output.', encoding='utf-8')
            data = analysis.build_analysis(source.read_text(), [
                {'path': 'problem.txt', 'sha256': sha256_file(source)}], [])
            path = root / 'paper_output/step1/problem_analysis.json'
            write_json(path, data)
            route_script = SKILLS / 'modeling-paper-rubric-and-model-selector/scripts/build_model_route.py'
            result = subprocess.run([sys.executable, str(route_script)], cwd=root, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            result = subprocess.run([sys.executable, str(SKILLS / 'problem-doc-model-selector/scripts/review_problem.py'),
                                     '--project-root', str(root), '--reviewer', 'test-agent', '--note', 'Reviewed both objectives',
                                     '--confirm'], cwd=root, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(review.review_errors(root, data), [])
            result = subprocess.run([sys.executable, str(route_script)], cwd=root, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data['questions'][0]['summary'] = 'changed goal'
            self.assertTrue(review.review_errors(root, data))
            source.write_text('changed units', encoding='utf-8')
            self.assertTrue(any('document changed' in x for x in review.review_errors(root, data)))


@unittest.skipUnless(importlib.util.find_spec('scipy'), 'scipy not installed')
class ActualRunnerEvidenceTests(unittest.TestCase):
    setUp = fixtures.ValidationIntegrationTests.setUp
    invoke = fixtures.ValidationIntegrationTests.invoke
    load = fixtures.ValidationIntegrationTests.load

    def gate(self, passed):
        result = self.invoke(self.skill_root / 'quality-assurance-auditor/scripts/evidence_gate.py', success=False)
        self.assertEqual(result.returncode, 0 if passed else 1, result.stdout + result.stderr)
        report = self.load('qa/evidence_gate_report.json')
        self.assertEqual(report['status'], 'PASS' if passed else 'FAIL')
        return report

    def producer(self, mutation):
        original = (fixtures.FIXTURES / 'benchmark_question.py').read_text(encoding='utf-8')
        (self.output / 'code/modeling/q1_model.py').write_text(
            original.replace('    return 0', mutation + '\n    return 0'), encoding='utf-8')

    def test_rerun_failure_and_conflicting_status_never_pass(self):
        for key, value in [('status', 'FAIL'), ('evidence_status', 'FAIL'), ('status', 'unknown')]:
            self.producer(
                '    data = load_json(RESULTS_DIR / "model_results.json", {})\n'
                '    result = next(r for r in data["questions"] if r["question_id"] == qid)\n'
                f'    result[{key!r}] = {value!r}\n'
                '    write_json(RESULTS_DIR / "model_results.json", data)')
            self.invoke(self.runner)
            self.assertEqual(self.load('results/run_manifest.json')['status'], 'PASS')
            with self.subTest(key=key, value=value):
                report = self.gate(False)
                self.assertTrue(any('模型结果状态' in e for e in report['failures']))
                with patch.object(guard, 'BASE_DIR', self.root), patch.object(guard, 'OUTPUT_DIR', self.output):
                    self.assertEqual(guard.check_s5()['status'], 'FAIL')

    def figure_producer(self, invalid=False):
        create = ('    picture.write_bytes(b"corrupt but nonempty PNG")' if invalid else
                  '    from PIL import Image\n    Image.new("RGB", (40, 40), "white").save(picture)')
        self.producer(
            '    picture = PROJECT_ROOT / "paper_output/figures/verified.png"\n'
            '    picture.parent.mkdir(exist_ok=True)\n' + create + '\n'
            '    write_json(PROJECT_ROOT / "paper_output/figure_index.json", {"figures": [\n'
            '        {"figure_id": "f1", "question_id": qid, "status": "computed",\n'
            '         "path": "paper_output/figures/verified.png", "exists": True, "ok": True}]})\n'
            '    data = load_json(RESULTS_DIR / "model_results.json", {})\n'
            '    result = next(r for r in data["questions"] if r["question_id"] == qid)\n'
            '    result["execution_provenance"]["output_artifacts"].append("paper_output/figures/verified.png")\n'
            '    write_json(RESULTS_DIR / "model_results.json", data)')

    def test_corrupt_image_rejected_even_with_fresh_hash(self):
        self.figure_producer(invalid=True)
        self.invoke(self.runner)
        report = self.gate(False)
        self.assertTrue(any('f1 无法读取' in e for e in report['failures']))

    def test_bound_image_passes_and_subsequent_edits_invalidate_writer(self):
        self.figure_producer()
        self.invoke(self.runner)
        report = self.gate(True)
        self.assertIn('paper_output/figures/verified.png', report['input_hashes'])
        self.assertEqual(fresh_evidence_gate(self.root)[1], [])
        (self.output / 'figures/verified.png').write_bytes(b'corrupt after audit')
        self.assertTrue(fresh_evidence_gate(self.root)[1])
        with patch.object(guard, 'BASE_DIR', self.root), patch.object(guard, 'OUTPUT_DIR', self.output):
            self.assertEqual(guard.check_s6()['status'], 'FAIL')
        self.gate(False)

    def test_unbound_and_unknown_question_figures_are_rejected(self):
        self.invoke(self.runner)
        self.gate(True)
        from PIL import Image
        path = self.output / 'unbound.png'
        Image.new('RGB', (20, 20), 'white').save(path)
        for qid in ('Q1', 'ALL', 'Q999', ''):
            write_json(self.output / 'figure_index.json', {'figures': [
                {'figure_id': 'f1', 'question_id': qid, 'status': 'computed', 'path': 'paper_output/unbound.png'}]})
            with self.subTest(qid=qid):
                report = self.gate(False)
                self.assertTrue(any('未绑定' in e or 'unknown question_id' in e for e in report['failures']))

    def test_changed_code_invalidates_previous_pass(self):
        self.invoke(self.runner)
        self.gate(True)
        script = self.output / 'code/modeling/q1_model.py'
        script.write_text(script.read_text(encoding='utf-8') + '\n# changed\n', encoding='utf-8')
        self.assertTrue(fresh_evidence_gate(self.root)[1])


if __name__ == '__main__':
    unittest.main()

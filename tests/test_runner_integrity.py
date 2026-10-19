"""Real subprocess regressions for runner receipts, without model/API calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / 'skills'
SCRIPTS = SKILLS / 'model-code-and-result-generator/scripts'

# A small real producer: its sentinel deliberately does not modify code or inputs.
PRODUCER = '''from pathlib import Path
import hashlib
import json
import os

root = Path(__file__).resolve().parents[3]
if (root / "skip").exists():
    raise SystemExit(0)
output = root / "paper_output"
def write(name, value):
    (output / name).write_text(json.dumps(value), encoding="utf-8")
(output / "tables/q1.csv").write_text("metric,value\\nscore,7\\n", encoding="utf-8")
write("results/model_results.json", {"questions": [{"question_id": "Q1", "status": "computed",
    "result_summary": "score is seven", "execution_provenance": {
        "execution_schema_version": "1.1", "run_id": os.environ.get("MATHMODEL_RUN_ID", ""),
        "source_code_path": "paper_output/code/modeling/q1_model.py",
        "source_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "run_command": "python paper_output/code/modeling/q1_model.py", "run_exit_code": 0,
        "output_artifacts": ["paper_output/tables/q1.csv"]}}]})
write("results/metrics.json", {"items": [{"question_id": "Q1", "status": "computed", "metric_name": "score", "value": 7}]})
write("results/conclusions.json", {"items": [{"question_id": "Q1", "status": "computed", "conclusion_text": "score is seven"}]})
write("tables/table_index.json", {"tables": [{"question_id": "Q1", "status": "computed", "table_id": "T1", "path": "paper_output/tables/q1.csv"}]})
'''


class RunnerIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='runner-integrity-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'paper_output'
        self.code = self.output / 'code/modeling'
        for directory in ('code/modeling', 'results', 'tables', 'plan', 'data_cleaned'):
            (self.output / directory).mkdir(parents=True, exist_ok=True)
        with patch.object(sys, 'path', [str(SCRIPTS), *sys.path]):
            generator = runpy.run_path(str(SCRIPTS / 'build_result_contracts.py'))
        self.runner = self.code / 'run_modeling.py'
        self.runner.write_text(generator['RUN_MODELING_CODE'], encoding='utf-8')
        shutil.copyfile(SKILLS / 'data-cleaning-and-visualization/scripts/data_inputs.py', self.code / 'data_inputs.py')
        # Empty approved data set is valid for this constant-calculation fixture.
        self.write('input_manifest.json', {'entries': []})
        import hashlib
        digest = hashlib.sha256((self.output / 'input_manifest.json').read_bytes()).hexdigest()
        self.write('data_cleaned/cleaning_report.json', {'status': 'PASS', 'datasets': [],
                   'input_hashes': {'paper_output/input_manifest.json': digest}})
        self.write('plan/model_route.json', {'questions': [{'question_id': 'Q1'}]})
        self.write('figure_index.json', {'figures': []})
        self.question = self.code / 'q1_model.py'
        self.question.write_text(PRODUCER, encoding='utf-8')

    def write(self, name, value):
        (self.output / name).write_text(json.dumps(value), encoding='utf-8')

    def load(self, name):
        return json.loads((self.output / name).read_text(encoding='utf-8'))

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(self.runner), *args], cwd=self.root,
                              capture_output=True, text=True, encoding='utf-8', timeout=30,
                              env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})

    def success(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.load('results/run_manifest.json')

    def receipt_failures(self, receipt=None):
        with patch.object(Path, 'cwd', return_value=self.root):
            gate = runpy.run_path(str(SKILLS / 'quality-assurance-auditor/scripts/evidence_gate.py'))
        return gate['run_manifest_failures'](self.load('results/model_results.json')['questions'][0],
                                           receipt or self.load('results/run_manifest.json'))

    def test_noop_rerun_cannot_bless_old_results(self):
        self.success()
        (self.root / 'skip').touch()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0, 'same code returned zero without producing new evidence')
        self.assertEqual(self.load('results/run_manifest.json')['status'], 'FAIL')
        self.assertTrue((self.output / 'tables/q1.csv').is_file(), 'old data must not be deleted')

    def test_result_contract_edit_invalidates_execution(self):
        self.success()
        self.assertEqual(self.receipt_failures(), [])
        for name in ('results/metrics.json', 'results/conclusions.json', 'results/model_results.json', 'tables/table_index.json'):
            with self.subTest(contract=name):
                original = (self.output / name).read_bytes()
                data = self.load(name)
                data['changed_after_execution'] = True
                self.write(name, data)
                self.assertTrue(self.receipt_failures(), 'post-run edit must fail already at S6')
                (self.output / name).write_bytes(original)

    def test_repeatable_result_gets_unique_invocation(self):
        first = self.success()
        second = self.success()
        self.assertEqual(second['schema_version'], '1.1')
        self.assertEqual(len(second['contract_files']), 4)
        self.assertNotEqual(first['runs'][0]['run_id'], second['runs'][0]['run_id'])
        self.assertEqual(self.receipt_failures(second), [])
        self.assertTrue(self.receipt_failures(first))

    def test_missing_snapshot_or_mismatched_invocation_rejected(self):
        manifest = self.success()
        manifest['contract_files'].pop()
        self.assertTrue(self.receipt_failures(manifest))
        manifest = self.load('results/run_manifest.json')
        manifest['runs'][0]['run_id'] = 'not-this-run'
        self.assertTrue(self.receipt_failures(manifest))

    def test_new_provenance_cannot_downgrade_to_legacy_receipt(self):
        receipt = self.success()
        receipt['schema_version'] = '1.0'
        self.assertTrue(self.receipt_failures(receipt))

    def test_nonzero_exit_invalidates_old_pass(self):
        self.success()
        self.question.write_text('raise SystemExit(7)\n', encoding='utf-8')
        self.assertNotEqual(self.invoke().returncode, 0)
        receipt = self.load('results/run_manifest.json')
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['runs'][0]['returncode'], 7)

    def test_running_state_visible_before_question_starts(self):
        self.success()
        self.question.write_text(PRODUCER + '\nwrite("observed_state.json", json.loads((output / "results/run_manifest.json").read_text())["status"])\n', encoding='utf-8')
        self.success()
        self.assertEqual(self.load('observed_state.json'), 'RUNNING')

    def test_timeout_kills_descendants_and_keeps_failure(self):
        self.success()
        child = "import time; from pathlib import Path; time.sleep(2); Path('orphan-output').touch()"
        self.question.write_text('import subprocess, sys, time\n'
                                 f'subprocess.Popen([sys.executable, "-c", {child!r}])\n'
                                 'print("before timeout", flush=True)\ntime.sleep(60)\n', encoding='utf-8')
        result = self.invoke('--timeout-seconds', '0.7')
        self.assertNotEqual(result.returncode, 0)
        receipt = self.load('results/run_manifest.json')
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertTrue(receipt['runs'][0]['timed_out'])
        self.assertEqual(receipt['runs'][0]['returncode'], 124)
        self.assertIn('before timeout', receipt['runs'][0]['stdout_tail'])
        time.sleep(2.2)
        self.assertFalse((self.code / 'orphan-output').exists())

    def test_invalid_timeout_is_rejected(self):
        for value in ('0', '-1', 'nan', 'inf'):
            with self.subTest(value=value):
                self.assertEqual(self.invoke('--timeout-seconds', value).returncode, 2)

    def test_large_stdout_uses_file_and_bounded_tail(self):
        self.question.write_text(PRODUCER + '\nprint("x" * 100_000)\n', encoding='utf-8')
        receipt = self.success()['runs'][0]
        self.assertLessEqual(len(receipt['stdout_tail']), 4000)
        self.assertGreater((self.root / receipt['log_path']).stat().st_size, 100_000)

    def test_output_path_escape_rejected(self):
        for path in ('../outside.csv', '/tmp/outside.csv', 'C:\\outside.csv'):
            with self.subTest(path=path):
                self.question.write_text(PRODUCER.replace('["paper_output/tables/q1.csv"]', repr([path])), encoding='utf-8')
                self.assertNotEqual(self.invoke().returncode, 0)
                self.assertEqual(self.load('results/run_manifest.json')['status'], 'FAIL')

    def test_windows_style_relative_paths_are_normalized(self):
        producer = PRODUCER.replace('"paper_output/code/modeling/q1_model.py"',
                                    repr('paper_output\\code/modeling\\q1_model.py'))
        producer = producer.replace('["paper_output/tables/q1.csv"]', repr(['paper_output\\tables/q1.csv']))
        self.question.write_text(producer, encoding='utf-8')
        self.success()
        self.assertEqual(self.receipt_failures(), [])

    def test_missing_output_and_corrupt_contract_rejected(self):
        for suffix in ('(output / "tables/q1.csv").unlink()',
                       '(output / "results/metrics.json").write_text("{")',
                       '(output / "results/conclusions.json").unlink()'):
            with self.subTest(suffix=suffix):
                self.question.write_text(PRODUCER + '\n' + suffix + '\n', encoding='utf-8')
                self.assertNotEqual(self.invoke().returncode, 0)
                self.assertEqual(self.load('results/run_manifest.json')['status'], 'FAIL')

    def test_concurrent_runner_is_rejected_without_overwriting_active_receipt(self):
        prefix = ('from pathlib import Path\nimport time\n'
                  'root = Path(__file__).resolve().parents[3]\n(root / "entered").touch()\n'
                  'while not (root / "release").exists(): time.sleep(0.02)\n')
        self.question.write_text(prefix + PRODUCER, encoding='utf-8')
        process = subprocess.Popen([sys.executable, str(self.runner), '--timeout-seconds', '15'],
                                   cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not (self.root / 'entered').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.root / 'entered').exists())
            before = (self.output / 'results/run_manifest.json').read_bytes()
            result = self.invoke()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Another modeling run', result.stdout)
            self.assertEqual((self.output / 'results/run_manifest.json').read_bytes(), before)
        finally:
            (self.root / 'release').touch()
            stdout, stderr = process.communicate(timeout=25)
        self.assertEqual(process.returncode, 0, repr((stdout, stderr)))
        self.assertEqual(self.receipt_failures(), [])
        # The leftover lock file is harmless after the process releases its OS lock.
        self.success()

    def test_later_question_cannot_overwrite_previous_artifact(self):
        self.write('plan/model_route.json', {'questions': [{'question_id': 'Q1'}, {'question_id': 'Q2'}]})
        second = PRODUCER.replace('q1', 'q2').replace('Q1', 'Q2')
        second += '\n(output / "tables/q1.csv").write_text("changed")\n'
        (self.code / 'q2_model.py').write_text(second, encoding='utf-8')
        self.assertNotEqual(self.invoke().returncode, 0)
        receipt = self.load('results/run_manifest.json')
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertIn('earlier run', receipt['failure'])


if __name__ == '__main__':
    unittest.main()

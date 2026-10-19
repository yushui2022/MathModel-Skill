"""Real gate invocations against disposable, explicitly synthetic evidence."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "packages/claude/.claude/skills"
GATE = SKILLS / "quality-assurance-auditor/scripts/evidence_gate.py"
sys.path.insert(0, str(SKILLS / "paper-formal-writer/scripts"))
from artifact_checks import artifact_errors


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mathmodel-latex-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "paper_output"
        for folder in ("plan", "results", "tables", "figures", "code"):
            (self.out / folder).mkdir(parents=True)
        (self.out / "code/model.py").write_text("# synthetic test source\n", encoding="utf-8")
        (self.out / "tables/q1.csv").write_text("metric,value\ncost,2\n", encoding="utf-8")
        self.write("plan/model_route.json", {"questions": [{"question_id": "Q1"}]})
        self.write("results/model_results.json", {"questions": [{
            "question_id": "Q1", "status": "computed",
            "execution_provenance": {"source_code_path": "paper_output/code/model.py", "run_exit_code": 0,
                                     "run_command": "python model.py", "output_artifacts": ["paper_output/tables/q1.csv"]}
        }]})
        self.write("results/metrics.json", {"items": [{"question_id": "Q1", "status": "computed", "value": 2}]})
        self.write("results/conclusions.json", {"items": [{"question_id": "Q1", "status": "computed", "conclusion_text": "cost is 2"}]})
        self.write("figure_index.json", {"figures": []})
        self.write("tables/table_index.json", {"tables": [{"question_id": "Q1", "status": "computed", "path": "paper_output/tables/q1.csv"}]})
        self.write("tasks.json", [])

    def write(self, name, data):
        (self.out / name).write_text(json.dumps(data), encoding="utf-8")

    def change(self, name, key, fields):
        data = json.loads((self.out / name).read_text(encoding="utf-8"))
        data[key][0].update(fields)
        self.write(name, data)

    def gate(self):
        result = subprocess.run([sys.executable, str(GATE)], cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        report = json.loads((self.out / "qa/evidence_gate_report.json").read_text(encoding="utf-8"))
        self.assertEqual(result.returncode == 0, report["status"] == "PASS", result.stdout + result.stderr)
        return report

    def test_valid_and_policy_version(self):
        report = self.gate()
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["policy_version"], 2)
        self.assertIn("paper_output/tables/q1.csv", report["input_hashes"])

    def test_failed_unknown_empty_and_conflicting_status(self):
        for fields in ({"status": "FAIL"}, {"status": "unknown"}, {"status": ""},
                       {"status": "computed", "evidence_status": "FAIL"}):
            with self.subTest(fields=fields):
                self.change("results/model_results.json", "questions", fields)
                self.assertEqual(self.gate()["status"], "FAIL")

    def test_nonnumeric_metric(self):
        for value in ("2", True, None, float("nan")):
            self.change("results/metrics.json", "items", {"value": value})
            self.assertEqual(self.gate()["status"], "FAIL")

    def test_duplicate_and_unknown_question(self):
        data = json.loads((self.out / "results/model_results.json").read_text())
        data["questions"].append(dict(data["questions"][0]))
        self.write("results/model_results.json", data)
        self.assertEqual(self.gate()["status"], "FAIL")
        self.change("results/metrics.json", "items", {"question_id": "Q999"})
        self.assertEqual(self.gate()["status"], "FAIL")

    def test_corrupt_table_is_not_evidence(self):
        (self.out / "tables/q1.csv").write_text("a,b\n1,2,3\n", encoding="utf-8")
        report = self.gate()
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("row width", str(report["failures"]))

    def test_corrupt_figure_cannot_pass_by_existing(self):
        image = self.out / "figures/corrupt.png"
        image.write_bytes(b"not a PNG")
        self.write("figure_index.json", {"figures": [{"question_id": "Q1", "status": "computed",
                                                     "path": "paper_output/figures/corrupt.png"}]})
        report = self.gate()
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("invalid artifact", str(report["failures"]))

    def test_unregistered_and_exploratory_table(self):
        (self.out / "tables/other.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        self.change("tables/table_index.json", "tables", {"path": "paper_output/tables/other.csv"})
        self.assertIn("execution outputs", str(self.gate()["failures"]))
        self.change("tables/table_index.json", "tables", {"path": "paper_output/tables/q1.csv", "evidence_role": "exploratory"})
        self.assertEqual(self.gate()["status"], "FAIL")

    def test_absolute_and_escaping_paths_fail(self):
        for name in ("../outside.csv", str(self.out / "tables/q1.csv"), "C:\\private.csv"):
            self.change("tables/table_index.json", "tables", {"path": name})
            self.assertEqual(self.gate()["status"], "FAIL")

    def test_table_header_empty_duplicate_and_no_data(self):
        path = self.out / "tables/q1.csv"
        for text in ("a,a\n1,2\n", ",b\n1,2\n", "a,b\n"):
            path.write_text(text, encoding="utf-8")
            self.assertTrue(artifact_errors(path))

    def test_xlsx_all_sheets_are_checked(self):
        from openpyxl import Workbook
        path = self.out / "tables/multi.xlsx"
        workbook = Workbook()
        workbook.active.append(["metric", "value"])
        workbook.active.append(["cost", 2])
        workbook.create_sheet("broken").append(["header only"])
        workbook.save(path)
        self.assertTrue(artifact_errors(path))
        workbook["broken"].append(["real data"])
        workbook.save(path)
        self.assertEqual(artifact_errors(path), [])


if __name__ == "__main__":
    unittest.main()

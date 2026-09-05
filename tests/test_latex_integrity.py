"""Fault-injection tests; these do not substitute for a real XeLaTeX render."""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "packages/claude/.claude/skills/paper-formal-writer/scripts"
sys.path.insert(0, str(SCRIPTS))
import format_formal_latex as exporter
import check_latex_format as checker
from latex_integrity import evidence_snapshot, safe_path, sha256


class LatexIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "paper_output"
        (self.output / "plan").mkdir(parents=True)
        (self.output / "qa").mkdir()
        (self.root / "problem_files").mkdir()
        (self.root / "problem_files/input.txt").write_text("actual input", encoding="utf-8")
        self.tex = self.output / "final_paper.tex"
        text = "\\documentclass{ctexart}\n\\usepackage{amsmath}\n\\begin{document}\n"
        text += "\n".join("\\section{" + s + "}" for s in checker.REQUIRED_TEXT)
        text += "\n\\subsection{model}\n\\[x=\\frac{1}{\\sqrt{2}}\\]\n\\end{document}"
        self.tex.write_text(text, encoding="utf-8")
        self.pdf = self.tex.with_suffix(".pdf")
        self.source = self.output / "final_paper_source.md"
        self.source.write_text("# Paper\n" + "explanation " * 900, encoding="utf-8")
        self.outline = self.output / "plan/paper_outline.json"
        self.outline.write_text(json.dumps({"delivery": {"mode": "smoke-test", "reason": "Synthetic integrity fixture"}}), encoding="utf-8")
        for module in (exporter, checker):
            replacements = {}
            for key, value in vars(module).items():
                if isinstance(value, Path) and value.is_relative_to(module.BASE_DIR):
                    replacements[key] = self.root / value.relative_to(module.BASE_DIR)
            context = patch.multiple(module, **replacements)
            context.start()
            self.addCleanup(context.stop)
        self.gate = self.output / "qa/evidence_gate_report.json"
        self.gate.write_text(json.dumps({"status": "PASS", "input_hashes": evidence_snapshot(self.root)}), encoding="utf-8")

    def receipt(self):
        self.pdf.write_bytes(b"%PDF-1.7 synthetic bytes; reader is mocked in positive receipt tests")
        report = {"source": "paper_output/final_paper_source.md", "tex_sha256": sha256(self.tex),
                  "compile": {"status": "PASS", "tex_sha256": sha256(self.tex), "pdf_sha256": sha256(self.pdf)},
                  "input_hashes": {p.relative_to(self.root).as_posix(): sha256(p) for p in (self.source, self.outline, self.gate)}}
        (self.output / "latex_build_report.json").write_text(json.dumps(report), encoding="utf-8")

    def fake_reader(self, count=1):
        return patch("pypdf.PdfReader", return_value=SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: "real text " * 30)] * count))

    def test_source_only_is_not_pdf_acceptance(self):
        report = checker.evaluate(self.tex, False)
        self.assertEqual(report["status"], "SOURCE_ONLY", report)
        self.assertEqual(report["acceptance_scope"], "NOT_ACCEPTED")

    def test_nested_formula_braces_are_valid(self):
        self.assertNotIn("占位", "".join(checker.evaluate(self.tex, False)["failures"]))

    def test_empty_source_fails(self):
        self.tex.write_text("", encoding="utf-8")
        self.assertEqual(checker.evaluate(self.tex, False)["status"], "FAIL")

    def test_missing_compiler_is_failure(self):
        with patch.object(exporter.shutil, "which", return_value=None):
            self.assertEqual(exporter.compile_pdf(self.tex, self.pdf)["status"], "FAIL")

    def test_noop_compiler_cannot_reuse_old_pdf(self):
        self.pdf.write_bytes(b"old PDF")
        with patch.object(exporter.shutil, "which", return_value="xelatex"), patch.object(exporter.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="")) as run:
            report = exporter.compile_pdf(self.tex, self.pdf)
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(self.pdf.exists())
            self.assertIn("-no-shell-escape", run.call_args.args[0])

    def test_compiler_timeout_is_failure(self):
        with patch.object(exporter.shutil, "which", return_value="xelatex"), patch.object(exporter.subprocess, "run", side_effect=subprocess.TimeoutExpired("xelatex", 300)):
            self.assertEqual(exporter.compile_pdf(self.tex, self.pdf)["status"], "FAIL")

    def test_fresh_receipt_contract(self):
        self.receipt()
        with self.fake_reader():
            report = checker.evaluate(self.tex, True)
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["acceptance_scope"], "LEGACY_LATEX_EXPORT_ONLY")

    def test_modified_pdf_fails(self):
        self.receipt()
        self.pdf.write_bytes(b"replacement")
        with self.fake_reader():
            self.assertEqual(checker.evaluate(self.tex, True)["status"], "FAIL")

    def test_modified_source_fails(self):
        self.receipt()
        self.source.write_text("changed", encoding="utf-8")
        with self.fake_reader():
            self.assertEqual(checker.evaluate(self.tex, True)["status"], "FAIL")

    def test_corrupt_pdf_records_failure(self):
        self.receipt()
        self.assertEqual(checker.evaluate(self.tex, True)["status"], "FAIL")

    def test_empty_pdf_pages_fail(self):
        self.receipt()
        with self.fake_reader(0):
            self.assertEqual(checker.evaluate(self.tex, True)["status"], "FAIL")

    def test_default_scope_rejects_short_pdf(self):
        self.outline.write_text("{}", encoding="utf-8")
        self.receipt()
        with self.fake_reader():
            report = checker.evaluate(self.tex, True)
        self.assertTrue(any("18-page" in f for f in report["failures"]), report)

    def test_modified_input_invalidates_evidence(self):
        self.assertTrue(exporter.check_evidence_gate()[0])
        (self.root / "problem_files/input.txt").write_text("changed", encoding="utf-8")
        self.assertFalse(exporter.check_evidence_gate()[0])

    def test_added_input_invalidates_evidence(self):
        (self.root / "problem_files/extra.txt").write_text("new", encoding="utf-8")
        self.assertFalse(exporter.check_evidence_gate()[0])

    def test_paths_stay_inside_project(self):
        for name in ("../escape", "/tmp/escape", "C:escape", "C:/escape", "a\\..\\escape"):
            with self.assertRaises(ValueError):
                safe_path(self.root, name)

    def test_tracked_packages_are_deterministic_and_preserve_user_config(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_release_packages as builder
        for directory in (self.root / "build-a", self.root / "build-b"):
            with patch.object(builder, "DIST_DIR", directory):
                for spec in builder.PACKAGE_SPECS:
                    output, _ = builder.build_package(spec)
                    self.assertEqual(output.read_bytes(), (ROOT / "dist" / output.name).read_bytes())
                    with zipfile.ZipFile(output) as archive:
                        self.assertNotIn("AGENTS.md", archive.namelist())
                        self.assertNotIn("CLAUDE.md", archive.namelist())


if __name__ == "__main__":
    unittest.main(verbosity=2)

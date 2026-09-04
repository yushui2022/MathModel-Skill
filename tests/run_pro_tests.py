from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import base64
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = REPO_ROOT / "packages" / "claude" / ".claude" / "skills"
ORCHESTRATOR_SCRIPTS = CLAUDE_SKILLS / "pro-workflow-orchestrator" / "scripts"
TOURNAMENT_SCRIPT = CLAUDE_SKILLS / "pro-model-tournament" / "scripts" / "validate_tournament.py"
SOURCE_SCRIPT = CLAUDE_SKILLS / "authoritative-data-harvester" / "scripts" / "validate_source_ledger.py"
REVIEW_SCRIPT = CLAUDE_SKILLS / "pro-review-board" / "scripts" / "validate_review_board.py"
PREFLIGHT_SCRIPT = ORCHESTRATOR_SCRIPTS / "pro_preflight.py"
CHECKPOINT_SCRIPT = ORCHESTRATOR_SCRIPTS / "pro_checkpoint.py"
MODEL_PROFILES = CLAUDE_SKILLS / "pro-workflow-orchestrator" / "references" / "model-profiles.json"
RENDER_SCRIPT = ORCHESTRATOR_SCRIPTS / "pro_render_pdf.py"
FREEZE_SCRIPT = ORCHESTRATOR_SCRIPTS / "pro_freeze_evidence.py"
FORMAT_SCRIPT = ORCHESTRATOR_SCRIPTS / "pro_format_check.py"
GATE_SCRIPT = ORCHESTRATOR_SCRIPTS / "pro_gate.py"

sys.path.insert(0, str(ORCHESTRATOR_SCRIPTS))
from pro_contracts import contract, sha256_file, write_json  # noqa: E402


def run(*args: str | Path, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(item) for item in args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def envelope(role: str, **payload):
    return contract(producer_role=role, status="PASS", input_hashes={}, **payload)


def write_valid_consensus(root: Path) -> None:
    manifest = json.loads((root / "instruction_manifest.json").read_text(encoding="utf-8"))
    write_json(root / "instruction_audit.json", envelope(
        "p0-instruction-auditor",
        instruction_manifest_sha256=sha256_file(root / "instruction_manifest.json"),
        reviewed_files=[
            {"locator": item["locator"], "sha256": item["sha256"]}
            for item in manifest["files"]
        ],
        conflicts=[],
        unresolved_conflicts=[],
        active_execution_contract=manifest["required_execution_contract"],
    ))
    analyses = []
    for index in range(1, 4):
        path = root / "analysis" / "independent" / f"analysis_{index}.json"
        write_json(path, envelope(f"p1-reader-{index}", isolated_context=True, summary=f"view {index}"))
        analyses.append({"role_id": f"reader-{index}", "path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
    write_json(root / "problem_consensus.json", envelope(
        "p1-consensus",
        independent_analyses=analyses,
        consensus=["well-defined"],
        disagreements=["none after adjudication"],
        assumptions=["declared assumption"],
        subproblems=[{"subproblem_id": "q1"}],
        attachment_roles=[{"path": "problem_files/赛题.pdf", "role": "problem_statement"}],
    ))


def valid_candidates() -> dict:
    dimensions = {
        "task_fit": 8,
        "data_feasibility": 8,
        "validation_strength": 8,
        "robustness": 8,
        "interpretability": 8,
        "innovation_value": 7,
        "implementation_risk": 7,
    }
    routes = [
        {
            "route_id": f"r{i}",
            "model_family": f"family-{i}",
            "is_interpretable_baseline": i == 1,
            "experiment_plan": "run, compare, and falsify",
            "expected_evidence": "metrics and diagnostic figures",
            "scores": dimensions,
        }
        for i in range(1, 5)
    ]
    return envelope("p2-route-generator", subproblems=[{"subproblem_id": "q1", "routes": routes}])


def valid_tournament() -> dict:
    return envelope(
        "p2-route-judge",
        decisions=[{
            "subproblem_id": "q1",
            "selected_route_id": "r2",
            "backup_route_id": "r3",
            "rejected_routes": [
                {"route_id": "r1", "reason": "baseline is weaker"},
                {"route_id": "r4", "reason": "higher identifiability risk"},
            ],
            "recommended_experiment_plan": "preregistered comparison",
            "implementation_risks": ["numerical instability"],
        }],
    )


class ProSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        preferred_value = os.environ.get("MATHMODEL_TEST_TEMP")
        if preferred_value:
            preferred = Path(preferred_value).resolve()
            preferred.mkdir(parents=True, exist_ok=True)
            self.temp = Path(tempfile.mkdtemp(prefix="pro-test-", dir=preferred)).resolve()
        else:
            self.temp = Path(tempfile.mkdtemp(prefix="pro-test-")).resolve()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def preflight(self, model: str = "ordinary-model", reasoning: str = "ultra") -> Path:
        (self.temp / "problem_files").mkdir(parents=True, exist_ok=True)
        (self.temp / "problem_files" / "赛题.pdf").write_bytes(b"fixture-problem")
        completed = run(
            sys.executable,
            PREFLIGHT_SCRIPT,
            "--project-root", self.temp,
            "--platform", "codex",
            "--model", model,
            "--reasoning", reasoning,
            "--multi-agent", "available",
            "--network", "available",
            "--parallel-tools", "available",
            "--async-tools", "available",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return self.temp / "paper_output_pro"

    def test_skill_surface_is_pro_only(self) -> None:
        names = sorted(path.name for path in CLAUDE_SKILLS.iterdir() if (path / "SKILL.md").is_file())
        self.assertEqual(len(names), 10)
        self.assertIn("pro-workflow-orchestrator", names)
        self.assertIn("pro-model-tournament", names)
        self.assertIn("pro-review-board", names)
        self.assertNotIn("paper-micro-unit-generator", names)
        self.assertNotIn("paper-workflow-orchestrator", names)
        self.assertFalse((REPO_ROOT / "packages" / "trae").exists())

    def test_forward_evaluation_has_four_required_case_types(self) -> None:
        fixtures = REPO_ROOT / "tests" / "fixtures" / "forward"
        cases = [json.loads(path.read_text(encoding="utf-8")) for path in fixtures.glob("*/case.json")]
        self.assertEqual({item["category"] for item in cases}, {"prediction", "optimization", "graph", "open_data"})
        self.assertTrue(all(len(item.get("required_evidence", [])) >= 5 for item in cases))

    def test_latest_frontier_model_profiles_are_selected(self) -> None:
        cases = [
            ("GPT-6 Astra", "openai-gpt-6-astra", "gpt-6-astra", "PREFERRED"),
            ("Claude Fable 5.1", "anthropic-claude-fable-5-1", "claude-fable-5-1", "PREFERRED"),
            ("claude-opus-5", "anthropic-claude-opus-5", "claude-opus-5", "SUPPORTED"),
            ("Claude Sonnet 5", "anthropic-claude-sonnet-5", "claude-sonnet-5", "SUPPORTED"),
            ("Claude Fable 5", "anthropic-claude-fable-5", "claude-fable-5", "SUPPORTED"),
            ("gpt-5.6-sol ultra", "openai-gpt-5-6-sol", "gpt-5.6-sol", "SUPPORTED"),
        ]
        for declared, profile_id, canonical_id, status in cases:
            with self.subTest(model=declared):
                root = self.preflight(declared)
                config = json.loads((root / "pro_config.json").read_text(encoding="utf-8"))
                self.assertTrue(config["recommended_model"])
                self.assertEqual(config["model_support_status"], status)
                self.assertEqual(config["model_profile"]["profile_id"], profile_id)
                self.assertEqual(config["model_profile"]["canonical_model_id"], canonical_id)
                self.assertEqual(config["reasoning_profile"]["normalized_effort"], "max")
                self.assertTrue(config["reasoning_profile"]["compatible"])

        catalog = json.loads(MODEL_PROFILES.read_text(encoding="utf-8"))
        self.assertEqual(len(catalog["profiles"]), 6)
        self.assertEqual(
            {item["canonical_model_id"] for item in catalog["profiles"] if item["support_tier"] == "preferred"},
            {"gpt-6-astra", "claude-fable-5-1"},
        )

    def test_preflight_warns_ordinary_model_and_blocks_mixed_install(self) -> None:
        root = self.preflight()
        config = json.loads((root / "pro_config.json").read_text(encoding="utf-8"))
        self.assertFalse(config["recommended_model"])
        self.assertTrue(config["warnings"])
        self.assertEqual(config["version"], "3.1.0-pro.1")
        self.assertEqual(config["model_support_status"], "UNVERIFIED")
        cases = [
            ("skills", "paper-workflow-orchestrator", None),
            (".agents/skills", "mathmodel-lite", None),
            (".codex/skills", "custom-standard", "standard"),
            (".claude/skills", "custom-lite", "lite"),
            (".trae/skills", "paper-workflow-orchestrator", None),
        ]
        for root_text, entry_name, marker_edition in cases:
            mixed = self.temp / Path(root_text) / entry_name
            mixed.mkdir(parents=True)
            if marker_edition:
                (mixed / "MATHMODEL_EDITION.json").write_text(json.dumps({
                    "product": "MathModel-Skill",
                    "edition": marker_edition,
                    "version": "test",
                    "entry_skill": entry_name,
                }), encoding="utf-8")
            else:
                (mixed / "SKILL.md").write_text(f"---\nname: {entry_name}\n---\n", encoding="utf-8")
            completed = run(
                sys.executable, PREFLIGHT_SCRIPT,
                "--project-root", self.temp,
                "--platform", "codex",
                "--model", "gpt-5.6-sol",
            )
            self.assertNotEqual(completed.returncode, 0, root_text)
            self.assertIn("mixed MathModel editions", completed.stdout)
            shutil.rmtree(mixed)

    def test_checkpoints_cannot_skip_and_hash_change_invalidates_downstream(self) -> None:
        root = self.preflight("gpt-5.6-sol")
        write_valid_consensus(root)
        skipped = run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "2", "--project-root", self.temp)
        self.assertNotEqual(skipped.returncode, 0)
        approved = run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "1", "--project-root", self.temp)
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        original = json.loads((root / "problem_consensus.json").read_text(encoding="utf-8"))
        original["consensus"].append("changed")
        write_json(root / "problem_consensus.json", original)
        stale = run(sys.executable, CHECKPOINT_SCRIPT, "validate", "--project-root", self.temp)
        self.assertNotEqual(stale.returncode, 0)
        ledger = json.loads((root / "checkpoint_ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["checkpoints"]["1"]["status"], "PENDING")

    def test_instruction_audit_is_required_and_new_instruction_invalidates_checkpoint(self) -> None:
        checkpoint = load_module("checkpoint_path_test", CHECKPOINT_SCRIPT)
        self.assertIsNone(checkpoint.instruction_source_path(
            self.temp, {"scope": "project", "path": "../outside.md"},
        ))
        self.assertIsNone(checkpoint.instruction_source_path(
            self.temp, {"scope": "skill", "skill_name": "../outside"},
        ))
        root = self.preflight("gpt-6-astra")
        write_valid_consensus(root)
        audit = json.loads((root / "instruction_audit.json").read_text(encoding="utf-8"))
        audit["unresolved_conflicts"] = ["conflicting output root"]
        write_json(root / "instruction_audit.json", audit)
        blocked = run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "1", "--project-root", self.temp)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("unresolved conflicts", blocked.stdout)

        write_valid_consensus(root)
        approved = run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "1", "--project-root", self.temp)
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        (self.temp / "AGENTS.md").write_text("# Added after approval\n", encoding="utf-8")
        stale = run(sys.executable, CHECKPOINT_SCRIPT, "validate", "--project-root", self.temp)
        self.assertNotEqual(stale.returncode, 0)
        ledger = json.loads((root / "checkpoint_ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["checkpoints"]["1"]["status"], "PENDING")

    def test_checkpoint_rejection_invalidates_later_states(self) -> None:
        root = self.preflight("gpt-5.6-sol")
        write_valid_consensus(root)
        self.assertEqual(run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "1", "--project-root", self.temp).returncode, 0)
        write_json(root / "source_ledger.json", envelope("p2-source", sources=[]))
        write_json(root / "candidate_routes.json", valid_candidates())
        write_json(root / "tournament_report.json", valid_tournament())
        self.assertEqual(run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "2", "--project-root", self.temp).returncode, 0)
        rejected = run(sys.executable, CHECKPOINT_SCRIPT, "reject", "--checkpoint", "2", "--decision", "change route", "--project-root", self.temp)
        self.assertEqual(rejected.returncode, 0)
        ledger = json.loads((root / "checkpoint_ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["checkpoints"]["2"]["status"], "REJECTED")
        self.assertEqual(ledger["checkpoints"]["3"]["status"], "PENDING")

    def test_tournament_requires_four_quality_routes_by_default_contract(self) -> None:
        candidates = self.temp / "candidate_routes.json"
        report = self.temp / "tournament_report.json"
        write_json(candidates, valid_candidates())
        write_json(report, valid_tournament())
        passed = run(sys.executable, TOURNAMENT_SCRIPT, "--candidates", candidates, "--report", report)
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        broken = valid_candidates()
        broken["subproblems"][0]["routes"] = broken["subproblems"][0]["routes"][:2]
        write_json(candidates, broken)
        failed = run(sys.executable, TOURNAMENT_SCRIPT, "--candidates", candidates, "--report", report)
        self.assertNotEqual(failed.returncode, 0)

    def test_source_gate_rejects_invalid_and_single_publisher_critical_claim(self) -> None:
        ledger = self.temp / "source_ledger.json"
        write_json(ledger, envelope(
            "source-researcher",
            sources=[{
                "source_id": "s1", "url": "not-a-url", "title": "T", "publisher": "P",
                "accessed_at_utc": "2026-01-01T00:00:00Z", "content_sha256": "a" * 64,
                "purpose": "critical data", "claim_ids": ["c1"], "access_status": "PUBLIC_OK",
                "authorization_required": False,
            }],
            critical_claims=[{"claim_id": "c1", "source_ids": ["s1"], "cross_validation_required": True}],
        ))
        failed = run(sys.executable, SOURCE_SCRIPT, "--ledger", ledger)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("two independent publishers", failed.stdout)

    def test_replication_robustness_and_document_corruption_are_blocking(self) -> None:
        gate = load_module("pro_gate_for_test", ORCHESTRATOR_SCRIPTS / "pro_gate.py")
        replication_errors = gate.check_replication({
            "critical_results": [{"result_id": "x", "replication_paths": [{"implementation_id": "a"}], "agreement_status": "PASS", "comparison_rule": "exact"}]
        })
        self.assertTrue(replication_errors)
        robustness_errors = gate.check_robustness({
            "baseline_comparisons": [1], "sensitivity_tests": [1], "constraint_stress_tests": [1],
            "stochastic_methods": [{"method_id": "m", "seeds": list(range(9)), "mean": 1, "variance": 1, "confidence_interval": [0, 2], "interval_stable": True}],
        })
        self.assertTrue(any("10 unique seeds" in item for item in robustness_errors))
        (self.temp / "final_paper_source.md").write_text("x" * 300, encoding="utf-8")
        (self.temp / "final_paper.docx").write_bytes(b"broken")
        (self.temp / "final_paper.pdf").write_bytes(b"broken")
        document_errors = gate.check_documents(self.temp, {})
        self.assertTrue(any("damaged" in item for item in document_errors))

    def test_review_board_requires_all_roles_and_no_unresolved_major(self) -> None:
        report = self.temp / "review_board_report.json"
        roles = ["mathematical_correctness", "code_reproducibility", "source_provenance", "paper_expression", "adversarial_challenge"]
        write_json(report, envelope("review-chair", rounds=[{
            "round": 1,
            "reviews": [{"role": role, "isolated_context": True, "findings": []} for role in roles],
        }]))
        passed = run(sys.executable, REVIEW_SCRIPT, "--report", report)
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        broken = json.loads(report.read_text(encoding="utf-8"))
        broken["rounds"][0]["reviews"][0]["findings"] = [{"finding_id": "M1", "severity": "MAJOR", "evidence": "counterexample", "disposition": "OPEN"}]
        write_json(report, broken)
        self.assertNotEqual(run(sys.executable, REVIEW_SCRIPT, "--report", report).returncode, 0)

    def test_path_resolution_handles_posix_windows_mixed_and_chinese(self) -> None:
        script_dir = CLAUDE_SKILLS / "paper-formal-writer" / "scripts"
        sys.path.insert(0, str(script_dir))
        try:
            writer = load_module("format_writer_for_test", script_dir / "format_formal_docx.py")
        finally:
            sys.path.pop(0)
        writer.BASE_DIR = self.temp
        for value in ("paper_output_pro/figures/中文.png", "paper_output_pro\\figures\\中文.png", "paper_output_pro\\figures/中文.png"):
            self.assertEqual(writer.resolve_path(value), self.temp / "paper_output_pro" / "figures" / "中文.png")

    def test_missing_libreoffice_is_detected(self) -> None:
        renderer = load_module("renderer_for_test", RENDER_SCRIPT)
        with mock.patch.object(renderer.shutil, "which", return_value=None), mock.patch.object(renderer.Path, "is_file", return_value=False):
            self.assertIsNone(renderer.find_soffice(None))

    def test_libreoffice_renders_docx_when_required_by_ci(self) -> None:
        if os.environ.get("REQUIRE_LIBREOFFICE") != "1":
            self.skipTest("Set REQUIRE_LIBREOFFICE=1 for the CI renderer integration test")
        renderer = load_module("renderer_integration_test", RENDER_SCRIPT)
        soffice = renderer.find_soffice(None)
        self.assertIsNotNone(soffice, "LibreOffice is required in Pro CI")
        from docx import Document
        from pypdf import PdfReader

        docx_path = self.temp / "renderer-test.docx"
        document = Document()
        document.add_heading("MathModel Pro Renderer Test", level=1)
        document.add_paragraph("This deterministic paragraph verifies extractable PDF text. " * 12)
        document.save(docx_path)
        completed = run(
            sys.executable, RENDER_SCRIPT,
            "--docx", docx_path,
            "--output-dir", self.temp,
            "--soffice", soffice,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        pdf = self.temp / "renderer-test.pdf"
        reader = PdfReader(str(pdf))
        self.assertGreaterEqual(len(reader.pages), 1)
        self.assertIn("MathModel Pro Renderer Test", "".join(page.extract_text() or "" for page in reader.pages))

    def test_complete_synthetic_pro_pipeline_passes_final_gate(self) -> None:
        if os.environ.get("REQUIRE_LIBREOFFICE") != "1":
            self.skipTest("Set REQUIRE_LIBREOFFICE=1 for the full delivery integration test")
        root = self.preflight("gpt-5.6-sol ultra")
        write_valid_consensus(root)
        self.assertEqual(run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "1", "--project-root", self.temp).returncode, 0)
        write_json(root / "source_ledger.json", envelope("p2-source", sources=[], critical_claims=[]))
        write_json(root / "candidate_routes.json", valid_candidates())
        write_json(root / "tournament_report.json", valid_tournament())
        self.assertEqual(run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "2", "--project-root", self.temp).returncode, 0)

        code = root / "code" / "model.py"
        input_file = root / "experiments" / "input.txt"
        output_file = root / "experiments" / "result.txt"
        code.write_text("print(1)\n", encoding="utf-8")
        input_file.write_text("input\n", encoding="utf-8")
        output_file.write_text("result=1\n", encoding="utf-8")
        run_record = {
            "run_id": "run-1", "route_id": "r2", "command": "python code/model.py", "status": "PASS", "exit_code": 0,
            "script_hashes": {"code/model.py": sha256_file(code)},
            "input_hashes": {"experiments/input.txt": sha256_file(input_file)},
            "output_hashes": {"experiments/result.txt": sha256_file(output_file)},
            "seeds": list(range(10)),
        }
        write_json(root / "experiment_manifest.json", envelope("p5-runner", runs=[run_record], environment={"python": sys.version}))
        write_json(root / "replication_report.json", envelope("p5-replicator", critical_results=[{
            "result_id": "E1", "replication_paths": [{"implementation_id": "impl-a"}, {"implementation_id": "impl-b"}],
            "comparison_rule": "exact", "agreement_status": "PASS",
        }]))
        write_json(root / "robustness_report.json", envelope(
            "p5-robustness", baseline_comparisons=[{"status": "PASS"}], sensitivity_tests=[{"status": "PASS"}],
            constraint_stress_tests=[{"status": "PASS"}], stochastic_methods=[{
                "method_id": "m1", "seeds": list(range(10)), "mean": 1.0, "variance": 0.01,
                "confidence_interval": [0.9, 1.1], "interval_stable": True,
            }],
        ))
        write_json(root / "ablation_report.json", envelope("p5-ablation", ablations=[{"component": "feature-a", "effect": "metric decreases"}]))
        write_json(root / "claim_evidence_map.json", envelope("p5-claim-linker", claims=[{
            "claim_id": "C1", "evidence_ids": ["E1"], "source_ids": [], "external": False,
        }]))
        self.assertEqual(run(sys.executable, CHECKPOINT_SCRIPT, "approve", "--checkpoint", "3", "--project-root", self.temp).returncode, 0)
        frozen = run(sys.executable, FREEZE_SCRIPT, "--project-root", self.temp)
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)

        paragraph = "The verified model result is one under the declared assumptions and remains stable across independent replication, sensitivity analysis, and constraint stress testing. " * 8
        (root / "final_paper_source.md").write_text("# Synthetic Pro Paper\n\n" + paragraph, encoding="utf-8")
        from docx import Document
        from docx.oxml import OxmlElement

        png = root / "figures" / "result.png"
        png.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="))
        document = Document()
        document.add_heading("Synthetic Pro Paper", level=1)
        document.add_paragraph(paragraph)
        formula_paragraph = document.add_paragraph("Model equation: ")
        omath = OxmlElement("m:oMath")
        math_run = OxmlElement("m:r")
        math_text = OxmlElement("m:t")
        math_text.text = "x=1"
        math_run.append(math_text)
        omath.append(math_run)
        formula_paragraph._p.append(omath)
        document.add_picture(str(png))
        document.save(root / "final_paper.docx")
        renderer = load_module("renderer_full_pipeline", RENDER_SCRIPT)
        soffice = renderer.find_soffice(None)
        self.assertIsNotNone(soffice)
        rendered = run(sys.executable, RENDER_SCRIPT, "--docx", root / "final_paper.docx", "--output-dir", root, "--soffice", soffice)
        self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)

        roles = ["mathematical_correctness", "code_reproducibility", "source_provenance", "paper_expression", "adversarial_challenge"]
        write_json(root / "review_board_report.json", envelope("review-chair", rounds=[{
            "round": 1, "reviews": [{"role": role, "isolated_context": True, "findings": []} for role in roles],
        }]))
        formatted = run(sys.executable, FORMAT_SCRIPT, "--project-root", self.temp)
        self.assertEqual(formatted.returncode, 0, formatted.stdout + formatted.stderr)
        gated = run(sys.executable, GATE_SCRIPT, "--project-root", self.temp)
        self.assertEqual(gated.returncode, 0, gated.stdout + gated.stderr)
        report = json.loads((root / "pro_gate_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")

    def test_platform_sync_and_deterministic_two_package_build(self) -> None:
        synced = run(sys.executable, REPO_ROOT / "scripts" / "sync_platform_packages.py", "--check")
        self.assertEqual(synced.returncode, 0, synced.stdout + synced.stderr)
        first = self.temp / "first"
        second = self.temp / "second"
        for output in (first, second):
            built = run(sys.executable, REPO_ROOT / "scripts" / "build_release_packages.py", "--output-dir", output)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        archives = sorted(first.glob("*.zip"))
        self.assertEqual([item.name for item in archives], ["MathModel-Skill-Pro-Claude-Code.zip", "MathModel-Skill-Pro-Codex.zip"])
        for archive in archives:
            counterpart = second / archive.name
            self.assertEqual(hashlib.sha256(archive.read_bytes()).digest(), hashlib.sha256(counterpart.read_bytes()).digest())
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertIn("VERSION", names)
                self.assertIn("LICENSE", names)
                self.assertIn("MATHMODEL_BUILD.json", names)
                marker_name = next(name for name in names if name.endswith("pro-workflow-orchestrator/MATHMODEL_EDITION.json"))
                marker = json.loads(bundle.read(marker_name).decode("utf-8"))
                self.assertEqual(marker["edition"], "pro")
                self.assertEqual(marker["version"], "3.1.0-pro.1")
                self.assertTrue(any(name.endswith("references/model-profiles.json") for name in names))
                self.assertTrue(any(name.endswith("references/frontier-model-guidance.md") for name in names))
                self.assertNotIn("AGENTS.md", names)
                self.assertNotIn("CLAUDE.md", names)
                self.assertFalse(any(name.startswith(".trae/") or "mathmodel-lite" in name or "paper-workflow-orchestrator" in name for name in names))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProSkillTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if os.environ.get("GITHUB_ACTIONS") == "true" and not result.wasSuccessful():
        details = [f"{case}: {error}" for case, error in [*result.failures, *result.errors]]
        annotation = " | ".join(details).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error title=MathModel Pro tests failed::{annotation}")
    raise SystemExit(0 if result.wasSuccessful() else 1)

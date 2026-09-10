from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import venv

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO/"plugins/mathmodel/skills/pro-workflow-orchestrator/scripts"))
from plugins.mathmodel.scripts.runtime.replay import export_replay, run_replay
from plugins.mathmodel.scripts.runtime.safety import file_hash
from pro_contracts import canonical_json_hash, checkpoint_hashes, contract
from pro_validation import evidence_files


def transport_fixture_gate(root):
    """Isolate portable transport tests from P0-P6; full Pro gate tested below."""
    from pro_contracts import read_json, validate_envelope
    from pro_validation import check_freeze, receipts
    errors = validate_envelope(root/"evidence_freeze.json", {"PASS"})
    if not errors:
        errors += check_freeze(root, read_json(root/"evidence_freeze.json"))
        errors += receipts(root, read_json(root/"experiment_manifest.json"))[1]
    if errors:
        raise ValueError("; ".join(errors))


class ReplayTests(unittest.TestCase):
    def setUp(self):
        cache = Path(os.environ.get("MATHMODEL_TEST_TMP", "G:/DevCache/Temp/mathmodel-insert/replay-tests"))
        cache.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base/"原始比赛"
        self.root = self.project/"paper_output_pro"
        self.root.mkdir(parents=True)
        self.bundle = self.base/"replay-bundle"
        self.output = self.base/"new-replay"
        self.write("pro_config.json", {"project_root": self.project.as_posix()})
        self.write("data_cleaned/x.json", {"x": 7})
        script = self.root/"code/main.py"
        script.parent.mkdir()
        script.write_text("import json, os, sys\nfrom pathlib import Path\n"
                          "value=json.loads(Path('data_cleaned/x.json').read_text())['x']*2\n"
                          "if os.environ.get('MATHMODEL_TEST_REPLAY_MISMATCH')=='1': value+=1\n"
                          "out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)\n"
                          "(out/'metrics.json').write_text(json.dumps({'metrics':{'answer':value}}))\n", encoding="utf-8")
        self.spec = {"run_id": "run1", "route_id": "r1", "implementation_id": "actual-test-script",
                     "script": "code/main.py", "inputs": ["data_cleaned/x.json"], "dependencies": [],
                     "args": ["{run_dir}"], "seed": None, "timeout_seconds": 10}
        self.write("code/run1.json", self.spec)
        directory = self.root/"experiments/run1"
        directory.mkdir(parents=True)
        command = [sys.executable, str(script), str(directory)]
        actual = subprocess.run(command, cwd=self.root, capture_output=True, text=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.receipt = contract(producer_role="pro-experiment-runner", status="PASS", run_id="run1", route_id="r1",
            implementation_id="actual-test-script", input_hashes={"data_cleaned/x.json": file_hash(self.root/"data_cleaned/x.json")},
            script_hashes={"code/main.py": file_hash(script)}, output_hashes={"experiments/run1/metrics.json": file_hash(directory/"metrics.json")},
            spec_path="code/run1.json", spec_sha256=file_hash(self.root/"code/run1.json"), argv=command,
            environment={"python": platform.python_version(), "platform": platform.platform(), "packages": []},
            seed=None, exit_code=actual.returncode, started_at_utc="2026-09-10T00:00:00Z", finished_at_utc="2026-09-10T00:00:01Z",
            metrics_file="experiments/run1/metrics.json")
        self.write("experiments/run1/receipt.json", self.receipt)
        self.refresh_manifest()
        self.rule = {"kind": "numeric", "atol": 1e-10, "rtol": 1e-10}
        self.write("tournament_report.json", {"comparison_rules": {"answer": self.rule}})
        self.write("replication_report.json", {"critical_results": [{"result_id": "answer", "comparison_rule": self.rule,
            "replication_paths": [{"run_id": "run1", "metric": "answer"}]}]})
        self.write("robustness_report.json", {})
        self.write("ablation_report.json", {})
        self.write("claim_evidence_map.json", {"claims": []})
        self.freeze()
        # These thirteen transport cases execute real scripts but their short
        # source contracts deliberately are not complete modeling approvals.
        patcher = mock.patch("plugins.mathmodel.scripts.runtime.replay._validate_source", side_effect=transport_fixture_gate)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, name, value):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def refresh_manifest(self):
        self.write("experiment_manifest.json", {"runs": [{"run_id": "run1", "receipt_path": "experiments/run1/receipt.json",
            "receipt_sha256": file_hash(self.root/"experiments/run1/receipt.json")}]})

    def freeze(self):
        hashes = checkpoint_hashes(self.root, "3")
        approval = canonical_json_hash(hashes)
        self.write("checkpoint_ledger.json", {"checkpoints": {"3": {"status": "APPROVED", "artifact_hashes": hashes, "approval_hash": approval}}})
        content = {"checkpoint_3_approval_hash": approval, "file_hashes": evidence_files(self.root), "claims": [], "reverse_index": {}}
        self.write("evidence_freeze.json", contract(producer_role="pro-evidence-freezer", status="PASS",
            input_hashes=content["file_hashes"], **content, snapshot_sha256=canonical_json_hash(content)))

    def export(self):
        result = export_replay(self.project, self.bundle, ["data_cleaned/x.json"])
        self.assertEqual(result["status"], "EXPORTED", result)
        return result

    def test_real_script_replays_in_new_directory_and_preserves_bundle(self):
        self.export()
        before = {p.relative_to(self.bundle).as_posix(): file_hash(p) for p in self.bundle.rglob("*") if p.is_file()}
        result = run_replay(self.bundle, self.output)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["comparisons"][0]["actual"], 14)
        self.assertEqual(result["scope"], "REPLAY_CONSISTENCY_ONLY_NO_PROJECT_APPROVAL")
        self.assertTrue((self.output/"runs/run1/replay_receipt.json").is_file())
        self.assertFalse(any(self.output.rglob("checkpoint_ledger.json")))
        self.assertFalse(any(self.output.rglob("pro_config.json")))
        self.assertFalse(any(self.output.rglob("evidence_freeze.json")))
        after = {p.relative_to(self.bundle).as_posix(): file_hash(p) for p in self.bundle.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_replay_works_in_clean_venv_without_installing_dependencies(self):
        self.export()
        env_root = self.base/"clean-venv"
        venv.EnvBuilder(with_pip=False).create(env_root)
        python = env_root/("Scripts/python.exe" if os.name == "nt" else "bin/python")
        result = run_replay(self.bundle, self.output, python)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["environment"]["packages"], {})

    def test_exported_runner_works_without_plugin_in_clean_environment(self):
        self.export()
        env_root = self.base/"standalone-venv"
        venv.EnvBuilder(with_pip=False).create(env_root)
        python = env_root/("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
        env.pop("PYTHONPATH", None)
        result = subprocess.run([str(python), "-B", str(self.bundle/"runner/run_replay.py"), "--output-root", str(self.output)],
                                cwd=self.base, capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")
        self.assertTrue((self.output/"replay_report.json").exists())

    def test_cross_run_inputs_are_rejected_instead_of_reusing_old_outputs(self):
        self.spec["inputs"].append("experiments/old/metrics.json")
        self.write("experiments/old/metrics.json", {"metrics": {"old": 3}})
        self.write("code/run1.json", self.spec)
        self.receipt["spec_sha256"] = file_hash(self.root/"code/run1.json")
        self.receipt["input_hashes"]["experiments/old/metrics.json"] = file_hash(self.root/"experiments/old/metrics.json")
        self.write("experiments/run1/receipt.json", self.receipt)
        self.refresh_manifest()
        self.freeze()
        result = export_replay(self.project, self.bundle, ["data_cleaned/x.json", "experiments/old/metrics.json"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("cross-run", " ".join(result["errors"]))

    def test_input_export_requires_explicit_authorization(self):
        exported = export_replay(self.project, self.bundle)
        self.assertEqual(exported["status"], "EXPORTED", exported)
        self.assertEqual(exported["missing_inputs"], ["data_cleaned/x.json"])
        self.assertFalse((self.bundle/"files/data_cleaned/x.json").exists())
        replay = run_replay(self.bundle, self.output)
        self.assertEqual(replay["status"], "BLOCKED")
        self.assertTrue((self.output/"replay_report.json").is_file())

    def test_user_can_supply_excluded_input_with_exact_recorded_hash(self):
        exported = export_replay(self.project, self.bundle)
        self.assertEqual(exported["status"], "EXPORTED")
        target = self.bundle/"files/data_cleaned/x.json"
        target.parent.mkdir(parents=True)
        target.write_bytes((self.root/"data_cleaned/x.json").read_bytes())
        self.assertEqual(run_replay(self.bundle, self.output)["status"], "PASS")

    def test_changed_frozen_input_rejects_export(self):
        self.write("data_cleaned/x.json", {"x": 999})
        self.assertEqual(export_replay(self.project, self.bundle, ["data_cleaned/x.json"])["status"], "BLOCKED")

    def test_no_freeze_rejects_export(self):
        (self.root/"evidence_freeze.json").unlink()
        self.assertEqual(export_replay(self.project, self.bundle)["status"], "BLOCKED")

    def test_tampered_code_is_rejected_before_execution(self):
        self.export()
        (self.bundle/"files/code/main.py").write_text("raise SystemExit('tampered')", encoding="utf-8")
        result = run_replay(self.bundle, self.output)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["runs"], [])

    def test_unregistered_files_are_rejected(self):
        self.export()
        (self.bundle/"checkpoint_ledger.json").write_text("{}", encoding="utf-8")
        self.assertEqual(run_replay(self.bundle, self.output)["status"], "BLOCKED")

    def test_numeric_disagreement_is_reported_and_preserved(self):
        self.export()
        with mock.patch.dict(os.environ, {"MATHMODEL_TEST_REPLAY_MISMATCH": "1"}):
            result = run_replay(self.bundle, self.output)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["comparisons"][0]["status"], "FAIL")
        self.assertTrue((self.output/"replay_report.json").exists())

    def test_missing_dependency_blocks_without_installing(self):
        self.receipt["environment"]["packages"] = ["mathmodel-deliberately-absent-package==0.0.0"]
        self.write("experiments/run1/receipt.json", self.receipt)
        self.refresh_manifest()
        self.freeze()
        self.export()
        result = run_replay(self.bundle, self.output)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("no automatic installation", " ".join(result["errors"]))

    def test_unsupported_statistical_rule_cannot_report_pass(self):
        rule = {"kind": "statistical", "alpha": 0.05, "equivalence_margin": 0.1}
        self.write("tournament_report.json", {"comparison_rules": {"answer": rule}})
        self.write("replication_report.json", {"critical_results": [{"result_id": "answer", "comparison_rule": rule,
            "replication_paths": [{"run_id": "run1", "metric": "answer"}]}]})
        self.freeze()
        self.export()
        self.assertEqual(run_replay(self.bundle, self.output)["status"], "FAILED")

    def test_output_must_be_empty_and_outside_bundle(self):
        self.export()
        self.assertEqual(run_replay(self.bundle, self.bundle/"output")["status"], "BLOCKED")
        self.output.mkdir()
        sentinel = self.output/"keep.txt"
        sentinel.write_text("user data", encoding="utf-8")
        self.assertEqual(run_replay(self.bundle, self.output)["status"], "BLOCKED")
        self.assertEqual(sentinel.read_text(), "user data")

    def test_invalid_allowlist_fails_without_export(self):
        self.assertEqual(export_replay(self.project, self.bundle, ["../secret"])["status"], "BLOCKED")
        self.assertFalse(self.bundle.exists())


class FullProReplayGateTests(unittest.TestCase):
    def test_export_checks_real_p0_p6_and_rejects_changed_original_input(self):
        cache = Path(os.environ.get("MATHMODEL_TEST_TMP", "G:/DevCache/Temp/mathmodel-insert/replay-tests"))
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            base = Path(temporary)
            project = base/"真实合成门禁"
            project.mkdir()
            # Build through the actual plugin installation, whose Codex skill
            # instruction hashes correctly differ from canonical Claude prose.
            program = (
                "import sys; from pathlib import Path; repo=Path(sys.argv[1]); "
                "skills=repo/'plugins/mathmodel/skills'; scripts=skills/'pro-workflow-orchestrator/scripts'; "
                "sys.path.insert(0,str(scripts)); sys.path.insert(0,str(repo/'tests')); "
                "import pro_contracts,pro_validation; import pro_fixture as fixture; "
                "sys.path.insert(0,str(scripts)); fixture.SKILLS=skills; fixture.SCRIPTS=scripts; "
                "fixture.prepare_evidence(Path(sys.argv[2]))"
            )
            prepared = subprocess.run([sys.executable, "-B", "-c", program, str(REPO), str(project)],
                                      capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            before = {str(p): (file_hash(p), p.stat().st_mtime_ns) for p in project.rglob("*") if p.is_file()}
            result = export_replay(project, base/"valid-export")
            self.assertEqual(result["status"], "EXPORTED", result)
            self.assertEqual(before, {str(p): (file_hash(p), p.stat().st_mtime_ns) for p in project.rglob("*") if p.is_file()})
            (project/"problem_files/task.md").write_text("A changed unapproved question", encoding="utf-8")
            blocked = export_replay(project, base/"stale-export")
            self.assertEqual(blocked["status"], "BLOCKED", blocked)
            self.assertFalse((base/"stale-export").exists())


if __name__ == "__main__":
    unittest.main()

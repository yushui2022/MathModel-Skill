"""Read-only P0-P9 status derived from the installed Pro validators.

Unlike pro_checkpoint validate and pro_gate this command never updates a ledger,
QA report, memory or database. A process exit code of zero means the query ran;
consumers must inspect status/steps rather than treating it as workflow success.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

from pro_checkpoint import invalidate_stale, load_ledger, validate_checkpoint_artifacts, validate_instruction_audit
from pro_contracts import check_original_inputs, output_root, read_json, sha256_file, validate_envelope
from pro_preflight import VERSION

PHASES = (
    ("P0", "能力、输入与指令预检", "pro-workflow-orchestrator"),
    ("P1", "隔离审题与题意确认", "problem-doc-model-selector"),
    ("P2", "研究、路线比较与确认", "pro-model-tournament"),
    ("P3", "实际实验与运行回执", "model-code-and-result-generator"),
    ("P4", "独立复算", "model-code-and-result-generator"),
    ("P5", "稳健性、结论与数值确认", "quality-assurance-auditor"),
    ("P6", "证据冻结", "pro-workflow-orchestrator"),
    ("P7", "完整论文写作", "paper-formal-writer"),
    ("P8", "五角色同版评审", "pro-review-board"),
    ("P9", "Word、PDF 与最终交付检查", "paper-formal-writer"),
)


def evaluate_status(project_root: str | Path) -> dict:
    project = Path(project_root).expanduser().resolve()
    root = output_root(project)
    result = {
        "schema_version": "1.0", "edition": "pro", "core_version": VERSION,
        "project_root": str(project), "output_root": str(root),
        "status": "PENDING", "current_step": "P0", "next_step": "P0",
        "recommended_skill": "pro-workflow-orchestrator", "next_action": "运行 Pro 预检并审计当前指令。",
        "failures": [], "checkpoints": {}, "awaiting_checkpoint": None,
        "acceptance_scope": "NOT_ACCEPTED", "contract_hashes": {},
        "steps": [{"step": p, "name": n, "status": "PENDING", "failures": []} for p, n, _ in PHASES],
    }
    config = {}
    original_ledger = None
    ledger = None
    stale: list[str] = []

    def read(name: str) -> dict:
        value = read_json(root / name)
        result["contract_hashes"][name] = sha256_file(root / name)
        return value

    def required(names: tuple[str, ...]) -> list[str]:
        errors = []
        for name in names:
            errors.extend(validate_envelope(root / name, {"PASS"}))
            if (root / name).is_file():
                result["contract_hashes"][name] = sha256_file(root / name)
        return errors

    def checkpoint(number: str) -> list[str]:
        errors = validate_checkpoint_artifacts(project, root, number)
        entry = (ledger or {}).get("checkpoints", {}).get(number, {})
        if entry.get("status") != "APPROVED":
            result["awaiting_checkpoint"] = number if not errors else None
            errors.append(f"checkpoint {number} requires a fresh explicit user approval")
        return errors

    def optimization_check() -> list[str]:
        if config.get("optimization_check_profile"):
            from pro_optimization import validate_delivery
            return validate_delivery(root)
        return []

    def stage_check(phase: str) -> list[str]:
        nonlocal config, original_ledger, ledger, stale
        from pro_validation import receipts, check_replication, check_robustness, check_ablation, check_claims, check_freeze, check_review
        if phase == "P0":
            errors = required(("pro_config.json", "input_manifest.json", "instruction_manifest.json", "instruction_audit.json"))
            if errors:
                return errors
            config = read("pro_config.json")
            if config.get("version") != VERSION or config.get("output_root") != "paper_output_pro":
                errors.append("project core version/output edition differs from the active Pro installation")
            errors.extend(check_original_inputs(project, root))
            errors.extend(validate_instruction_audit(project, root))
            original_ledger = load_ledger(root)
            ledger = copy.deepcopy(original_ledger)
            # invalidate_stale mutates only the supplied dictionary; no write_json.
            stale = invalidate_stale(project, root, ledger)
            result["checkpoints"] = {
                str(i): {"status": ledger["checkpoints"].get(str(i), {}).get("status", "UNKNOWN"),
                         "recorded_status": original_ledger["checkpoints"].get(str(i), {}).get("status", "UNKNOWN"),
                         "fresh": ledger["checkpoints"].get(str(i), {}).get("status") == "APPROVED",
                         "stale": str(i) in stale}
                for i in range(1, 4)
            }
            return errors
        if phase in {"P1", "P2"}:
            return checkpoint("1" if phase == "P1" else "2")
        if phase == "P3":
            return required(("experiment_manifest.json",)) or receipts(root, read("experiment_manifest.json"))[1]
        if phase == "P4":
            errors = required(("replication_report.json",))
            if errors:
                return errors
            runs, errors = receipts(root, read("experiment_manifest.json"))
            return errors + check_replication(root, read("replication_report.json"), runs, read("tournament_report.json"))
        if phase == "P5":
            return checkpoint("3") + optimization_check()
        if phase == "P6":
            return required(("evidence_freeze.json",)) or check_freeze(root, read("evidence_freeze.json"))
        if phase == "P7":
            errors = required(("paper_plan.json",))
            if errors:
                return errors
            from pro_paper_audit import check_paper
            # Pro final formatting revalidates the manuscript directly and does
            # not require a saved paper_audit.json. Use that same pure checker.
            return check_paper(root)
        if phase == "P8":
            return required(("review_board_report.json",)) or check_review(root, read("review_board_report.json"))
        if phase == "P9":
            from pro_gate import CONTRACTS, check_documents
            errors = []
            for name in CONTRACTS:
                errors += validate_envelope(root / name, {"APPROVED"} if name == "checkpoint_ledger.json" else {"PASS"})
            if errors:
                return errors
            errors += check_documents(root, read("final_format_report.json"))
            errors += optimization_check()
            errors += required(("pro_gate_report.json",))
            if not errors:
                report = read("pro_gate_report.json")
                expected = {n: sha256_file(root / n) for n in CONTRACTS}
                if report.get("input_hashes") != expected:
                    errors.append("final Pro gate report is stale")
                mode = config.get("paper_delivery", {}).get("mode")
                expected_scope = {"competition": "COMPETITION_REPORT_CHECKED", "short-report": "SHORT_REPORT_ONLY", "smoke-test": "ENGINEERING_SMOKE_ONLY"}.get(mode)
                if not expected_scope or report.get("acceptance_scope") != expected_scope:
                    errors.append("final gate acceptance scope differs from the confirmed paper mode")
                if not errors:
                    result["acceptance_scope"] = expected_scope
            return errors
        return ["unknown Pro stage"]

    missing_roots = not (root / "pro_config.json").is_file()
    for index, (phase, _, skill) in enumerate(PHASES):
        try:
            errors = stage_check(phase)
        except (ImportError, ValueError, OSError, KeyError, TypeError, AttributeError, zipfile.BadZipFile) as exc:
            errors = [f"{phase}: cannot verify current contracts: {exc}"]
        if not errors:
            result["steps"][index]["status"] = "PASS"
            continue
        pending = all(str(e).startswith("missing contract:") for e in errors)
        if phase == "P0" and len(errors) == 1 and str(errors[0]).startswith("instruction_audit.json: status must"):
            pending = read_json(root / "instruction_audit.json").get("status") == "PENDING"
        outdated = bool(stale) or any("stale" in str(e).lower() for e in errors)
        status = "INVALID" if outdated else "PENDING" if pending or missing_roots or result["awaiting_checkpoint"] else "FAIL"
        result["steps"][index].update(status=status, failures=sorted(set(map(str, errors))))
        result.update(status="PENDING" if status == "PENDING" else "BLOCKED", current_step=phase, next_step=phase,
                      recommended_skill="pro-workflow-orchestrator" if result["awaiting_checkpoint"] else skill,
                      failures=result["steps"][index]["failures"],
                      next_action=f"检查点 {result['awaiting_checkpoint']} 等待对当前对象的真实用户确认。" if result["awaiting_checkpoint"] else f"处理 {phase} 的未完成或失效契约，再使用 {skill} 继续。")
        break
    else:
        result.update(status="COMPLETE", current_step="P9", next_step="P9", recommended_skill="", next_action="当前 Pro 交付检查通过；按 acceptance_scope 描述实际验收范围。")
    result["verified_count"] = sum(s["status"] == "PASS" for s in result["steps"])
    result["optimization_validation"] = {"profile": config.get("optimization_check_profile"),
                                         "status": "ENABLED" if config.get("optimization_check_profile") else "NOT_ENABLED"}
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--fail-if-blocked", action="store_true", help="Exit nonzero unless every required phase has passed; never writes reports or approvals")
    parser.add_argument("--require-through", choices=tuple(p[0] for p in PHASES), default="P9", help="Last phase required for --fail-if-blocked (P5 checks current evidence before freeze/writing)")
    args = parser.parse_args()
    try:
        status = evaluate_status(args.project_root)
    except Exception as exc:
        status = {"schema_version": "1.0", "edition": "pro", "status": "UNKNOWN", "steps": [],
                  "current_step": "P0", "next_step": "P0", "recommended_skill": "pro-workflow-orchestrator",
                  "next_action": "修复状态读取错误后重试。", "failures": [str(exc)]}
    if args.format == "json":
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    else:
        print(f"# MathModel Pro · {status['status']}\n\n{status['next_action']}")
        for phase in status["steps"]:
            print(f"- {phase['step']} {phase['name']}: {phase['status']}")
        for failure in status["failures"]:
            print(f"- {failure}")
    if status["status"] == "UNKNOWN":
        return 1
    if args.fail_if_blocked:
        required_index = next(i for i, p in enumerate(PHASES) if p[0] == args.require_through)
        if any(p["status"] != "PASS" for p in status["steps"][:required_index + 1]):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

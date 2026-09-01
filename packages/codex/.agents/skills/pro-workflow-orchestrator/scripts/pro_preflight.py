from __future__ import annotations

import argparse
import platform
import shutil
import sys
from pathlib import Path

from pro_contracts import contract, hash_paths, output_root, read_json, sha256_file, write_json


RECOMMENDED_MODELS = ("claude fable 5", "fable 5", "gpt-5.6-sol", "gpt 5.6 sol")
FORBIDDEN_SKILLS = {
    "paper-workflow-orchestrator",
    "paper-micro-unit-generator",
    "modeling-paper-rubric-and-model-selector",
    "mathmodel-lite",
}


def classify(path: Path) -> str:
    name = path.name.casefold()
    suffix = path.suffix.casefold()
    if any(token in name for token in ("result", "结果", "提交", "答题纸", "template", "模板")):
        return "result_template"
    if suffix in {".csv", ".xls", ".xlsx", ".xlsm", ".parquet", ".json", ".txt"}:
        return "raw_data"
    if suffix in {".pdf", ".doc", ".docx", ".md"}:
        if any(token in name for token in ("附件", "reference", "参考", "说明")):
            return "reference_material"
        return "problem_statement"
    return "unclassified_attachment"


def find_libreoffice() -> str | None:
    candidates = [
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return None


def mixed_installations(project_root: Path) -> list[str]:
    found: list[str] = []
    for skill_root in (project_root / ".claude" / "skills", project_root / ".agents" / "skills"):
        if not skill_root.is_dir():
            continue
        for child in skill_root.iterdir():
            if child.is_dir() and child.name in FORBIDDEN_SKILLS:
                found.append(child.relative_to(project_root).as_posix())
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the MathModel Skill Pro P0 contracts.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--platform", choices=("codex", "claude-code"), required=True)
    parser.add_argument("--model", required=True, help="User-declared model name.")
    parser.add_argument("--reasoning", default="unspecified")
    parser.add_argument("--multi-agent", choices=("available", "unavailable", "unknown"), default="unknown")
    parser.add_argument("--network", choices=("available", "unavailable", "unknown"), default="unknown")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    out = output_root(project_root, args.output_root)
    problem_root = project_root / "problem_files"
    files = sorted((path for path in problem_root.rglob("*") if path.is_file()), key=lambda p: p.as_posix()) if problem_root.is_dir() else []
    installed_conflicts = mixed_installations(project_root)
    model_recommended = any(token in args.model.casefold() for token in RECOMMENDED_MODELS)
    warnings = [] if model_recommended else [
        "The declared model is outside the recommended Fable 5 / GPT-5.6 Sol Ultra profile; Pro will continue without reducing its gates."
    ]
    errors: list[str] = []
    if not files:
        errors.append("problem_files/ has no readable task or attachment files")
    if installed_conflicts:
        errors.append("mixed MathModel editions detected: " + ", ".join(installed_conflicts))

    out.mkdir(parents=True, exist_ok=True)
    for relative in (
        "analysis/independent", "research", "experiments", "evidence", "reviews", "paper",
        "qa", "code", "context", "data_cleaned", "figures", "tables",
    ):
        (out / relative).mkdir(parents=True, exist_ok=True)

    manifest_files = [
        {
            "path": path.relative_to(project_root).as_posix(),
            "role": classify(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    input_hashes = hash_paths(files, project_root)
    write_json(out / "input_manifest.json", contract(
        producer_role="p0-input-preflight",
        status="PASS" if not errors else "BLOCKED",
        input_hashes=input_hashes,
        files=manifest_files,
        classification_counts={role: sum(item["role"] == role for item in manifest_files) for role in sorted({item["role"] for item in manifest_files})},
        errors=errors,
    ))
    config = contract(
        producer_role="p0-capability-preflight",
        status="PASS" if not errors else "BLOCKED",
        input_hashes={"input_manifest.json": sha256_file(out / "input_manifest.json")},
        version="3.0.0-pro.1",
        platform=args.platform,
        declared_model=args.model,
        recommended_model=model_recommended,
        reasoning_effort=args.reasoning,
        checkpoint_mode="required",
        research_policy="public_sources_only_without_explicit_authorization",
        delivery_formats=["docx", "pdf"],
        output_root="paper_output_pro",
        capabilities={
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "libreoffice": find_libreoffice(),
            "multi_agent": args.multi_agent,
            "network": args.network,
        },
        warnings=warnings,
        errors=errors,
    )
    write_json(out / "pro_config.json", config)
    ledger_path = out / "checkpoint_ledger.json"
    if not ledger_path.exists():
        write_json(ledger_path, contract(
            producer_role="pro-workflow-orchestrator",
            status="PENDING",
            input_hashes={"pro_config.json": sha256_file(out / "pro_config.json")},
            checkpoints={str(i): {"status": "PENDING", "decision": None, "decided_at_utc": None, "artifact_hashes": {}, "approval_hash": None} for i in range(1, 4)},
        ))
    print(f"[{'PASS' if not errors else 'BLOCKED'}] Pro preflight: {out}")
    for warning in warnings:
        print(f"[WARNING] {warning}")
    for error in errors:
        print(f"[ERROR] {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

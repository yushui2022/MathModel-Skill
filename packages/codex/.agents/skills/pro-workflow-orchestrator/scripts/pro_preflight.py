from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from pro_contracts import contract, hash_paths, output_root, read_json, sha256_file, write_json


VERSION = "3.2.0-pro.1"
MODEL_CATALOG_PATH = Path(__file__).resolve().parents[1] / "references" / "model-profiles.json"
MODEL_SUFFIXES = {"low", "medium", "high", "xhigh", "max", "ultra", "preview", "latest"}
EXPECTED_EDITION = "pro"
SKILL_ROOTS = ("skills", ".agents/skills", ".codex/skills", ".agents/skills", ".trae/skills")
LEGACY_ENTRY_EDITIONS = {
    "paper-workflow-orchestrator": "standard",
    "mathmodel-lite": "lite",
    "pro-workflow-orchestrator": "pro",
}


def normalize_model_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def normalize_effort(value: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "", value.casefold())
    return None if normalized in {"", "auto", "default", "unspecified", "unknown"} else normalized


def load_model_catalog(path: Path = MODEL_CATALOG_PATH) -> dict:
    catalog = read_json(path)
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("model profile catalog must contain profiles")
    profile_ids: set[str] = set()
    aliases: dict[str, str] = {}
    required = {
        "profile_id", "vendor", "display_name", "canonical_model_id", "aliases",
        "support_tier", "supported_efforts", "phase_effort", "behavior_flags", "official_sources",
    }
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("every model profile must be an object")
        missing = required - set(profile)
        if missing:
            raise ValueError(f"invalid model profile: missing {sorted(missing)}")
        if profile["support_tier"] not in {"preferred", "supported"}:
            raise ValueError(f"invalid support tier for {profile['profile_id']}")
        if not isinstance(profile["aliases"], list) or not isinstance(profile["supported_efforts"], list):
            raise ValueError(f"aliases and supported_efforts must be arrays for {profile['profile_id']}")
        profile_id = str(profile["profile_id"])
        if profile_id in profile_ids:
            raise ValueError(f"duplicate model profile_id: {profile_id}")
        profile_ids.add(profile_id)
        for alias in [profile["canonical_model_id"], *profile["aliases"]]:
            normalized = normalize_model_name(str(alias))
            owner = aliases.get(normalized)
            if owner and owner != profile_id:
                raise ValueError(f"model alias {alias!r} belongs to both {owner} and {profile_id}")
            aliases[normalized] = profile_id
    return catalog


def match_model_profile(declared_model: str, catalog: dict) -> tuple[dict | None, str | None]:
    normalized = normalize_model_name(declared_model)
    candidates: list[tuple[int, dict, str]] = []
    for profile in catalog["profiles"]:
        for alias in [profile["canonical_model_id"], *profile["aliases"]]:
            normalized_alias = normalize_model_name(str(alias))
            if normalized == normalized_alias:
                candidates.append((len(normalized_alias), profile, str(alias)))
                continue
            prefix = normalized_alias + "-"
            if normalized.startswith(prefix):
                suffix = normalized[len(prefix):]
                if suffix and all(part in MODEL_SUFFIXES or part.isdigit() for part in suffix.split("-")):
                    candidates.append((len(normalized_alias), profile, str(alias)))
    if not candidates:
        return None, None
    _, profile, matched_alias = max(candidates, key=lambda item: item[0])
    return profile, matched_alias


def reasoning_profile(profile: dict | None, declared_effort: str) -> dict:
    normalized = normalize_effort(declared_effort)
    if profile is None:
        return {
            "declared_effort": declared_effort,
            "normalized_effort": normalized,
            "compatible": None,
            "profile_recommended_effort": None,
            "phase_effort": {},
            "alias_applied": False,
        }
    aliases = {normalize_effort(key): value for key, value in profile.get("effort_aliases", {}).items()}
    canonical = aliases.get(normalized, normalized)
    supported = set(profile["supported_efforts"])
    phase_effort = profile["phase_effort"]
    return {
        "declared_effort": declared_effort,
        "normalized_effort": canonical,
        "compatible": None if canonical is None else canonical in supported,
        "profile_recommended_effort": phase_effort.get("problem_and_research"),
        "phase_effort": phase_effort,
        "alias_applied": canonical != normalized,
    }


def catalog_is_stale(catalog: dict) -> bool:
    try:
        verified = date.fromisoformat(str(catalog["verified_on"]))
        freshness_days = int(catalog.get("catalog_freshness_days", 90))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid model catalog freshness metadata: {exc}") from exc
    return (date.today() - verified).days > freshness_days


def instruction_sources(project_root: Path) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = project_root / name
        if path.is_file():
            sources.append({
                "locator": f"project://{name}",
                "scope": "project",
                "path": name,
                "sha256": sha256_file(path),
            })
    skill_root = Path(__file__).resolve().parents[2]
    for path in sorted(skill_root.glob("*/SKILL.md"), key=lambda item: item.as_posix()):
        skill_name = path.parent.name
        sources.append({
            "locator": f"skill://{skill_name}/SKILL.md",
            "scope": "skill",
            "path": f"{skill_name}/SKILL.md",
            "skill_name": skill_name,
            "sha256": sha256_file(path),
        })
    return sources


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
        os.environ.get("LIBREOFFICE_PATH"),
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


def mathmodel_installations(project_root: Path) -> list[dict[str, str | None]]:
    found: list[dict[str, str | None]] = []
    for root_text in SKILL_ROOTS:
        skill_root = project_root / Path(root_text)
        if not skill_root.is_dir():
            continue
        for child in sorted(path for path in skill_root.iterdir() if path.is_dir()):
            marker_path = child / "MATHMODEL_EDITION.json"
            marker: dict[str, object] = {}
            marker_error: str | None = None
            if marker_path.is_file():
                try:
                    value = json.loads(marker_path.read_text(encoding="utf-8"))
                    marker = value if isinstance(value, dict) else {}
                    if marker.get("product") not in (None, "", "MathModel-Skill"):
                        continue
                except Exception as exc:
                    marker_error = f"{type(exc).__name__}: {exc}"
            legacy_edition = LEGACY_ENTRY_EDITIONS.get(child.name)
            edition = str(marker.get("edition") or legacy_edition or "").strip().lower()
            if edition not in {"standard", "lite", "pro"}:
                continue
            found.append({
                "edition": edition,
                "version": str(marker.get("version") or "legacy-unmarked"),
                "entry_skill": str(marker.get("entry_skill") or child.name),
                "skill_root": root_text,
                "path": child.relative_to(project_root).as_posix(),
                "marker": marker_path.relative_to(project_root).as_posix() if marker_path.is_file() else None,
                "marker_error": marker_error,
            })
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the MathModel Skill Pro P0 contracts.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--platform", choices=("codex", "claude-code"), required=True)
    parser.add_argument("--model", required=True, help="User-declared model name.")
    parser.add_argument("--reasoning", default="unspecified")
    parser.add_argument("--multi-agent", choices=("available", "unavailable", "unknown"), default="unknown")
    parser.add_argument("--network", choices=("available", "unavailable", "unknown"), default="unknown")
    parser.add_argument("--parallel-tools", choices=("available", "unavailable", "unknown"), default="unknown")
    parser.add_argument("--async-tools", choices=("available", "unavailable", "unknown"), default="unknown")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    out = output_root(project_root, args.output_root)
    problem_root = project_root / "problem_files"
    files = sorted((path for path in problem_root.rglob("*") if path.is_file()), key=lambda p: p.as_posix()) if problem_root.is_dir() else []
    installations = mathmodel_installations(project_root)
    editions = sorted({str(item["edition"]) for item in installations})
    installed_conflicts = [item for item in installations if item["edition"] != EXPECTED_EDITION]
    catalog = load_model_catalog()
    profile, matched_alias = match_model_profile(args.model, catalog)
    support_tier = str(profile.get("support_tier")) if profile else "unverified"
    model_recommended = support_tier in {"preferred", "supported"}
    model_preferred = support_tier == "preferred"
    effort = reasoning_profile(profile, args.reasoning)
    warnings: list[str] = []
    if not model_recommended:
        warnings.append(
            "The declared model is outside the verified Pro profiles; Pro will continue without reducing its gates."
        )
    if effort["compatible"] is False:
        warnings.append(
            f"Reasoning effort {args.reasoning!r} is not listed for {profile['display_name']}; verify the host setting before P1."
        )
    stale_catalog = catalog_is_stale(catalog)
    if stale_catalog:
        warnings.append("The bundled frontier-model catalog is stale; verify the declared model against current official vendor documentation.")
    versions = sorted({str(item["version"]) for item in installations if item["edition"] == EXPECTED_EDITION})
    if len(versions) > 1:
        warnings.append("Multiple Pro versions are installed: " + ", ".join(versions))
    errors: list[str] = []
    if any(version != VERSION for version in versions) or len([i for i in installations if i['edition'] == 'pro']) > 1:
        errors.append("old or duplicate Pro installations detected; install one current Pro payload")
    if any(not path.resolve().is_relative_to(project_root) for path in files):
        errors.append("original input symlink escapes project root")
        files = [path for path in files if path.resolve().is_relative_to(project_root)]
    if not files:
        errors.append("problem_files/ has no readable task or attachment files")
    if installed_conflicts:
        errors.append("mixed MathModel editions detected: " + ", ".join(str(item["path"]) for item in installed_conflicts))
    for item in installations:
        if item.get("marker_error"):
            errors.append(f"unreadable edition marker {item['marker']}: {item['marker_error']}")

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
    execution_policy = {
        "required_user_stops": ["checkpoint_1", "checkpoint_2", "checkpoint_3"],
        "continue_between_checkpoints": True,
        "additional_stop_reasons": [
            "missing_user_owned_data_or_authorization",
            "irreversible_external_action_outside_approved_scope",
            "same_normalized_failure_three_consecutive_times",
        ],
        "output_root": "paper_output_pro",
        "parallel_role_requirements": {
            "independent_problem_readers_minimum": 3,
            "candidate_routes_per_subproblem_default": 4,
            "independent_replication_paths_minimum": 2,
            "review_board_roles": 5,
        },
    }
    instruction_files = instruction_sources(project_root)
    instruction_manifest_path = out / "instruction_manifest.json"
    write_json(instruction_manifest_path, contract(
        producer_role="p0-instruction-inventory",
        status="PASS",
        input_hashes={item["locator"]: item["sha256"] for item in instruction_files},
        files=instruction_files,
        precedence=[
            "platform_system_and_safety",
            "explicit_user_scope_and_checkpoint_decisions",
            "host_applied_project_instructions",
            "pro_workflow_orchestrator",
            "phase_specific_pro_skills",
        ],
        required_execution_contract=execution_policy,
    ))
    audit_path = out / "instruction_audit.json"
    manifest_hash = sha256_file(instruction_manifest_path)
    existing_audit = read_json(audit_path) if audit_path.is_file() else {}
    if existing_audit.get("instruction_manifest_sha256") != manifest_hash:
        write_json(audit_path, contract(
            producer_role="p0-instruction-auditor",
            status="PENDING",
            input_hashes={"instruction_manifest.json": manifest_hash},
            instruction_manifest_sha256=manifest_hash,
            reviewed_files=[],
            conflicts=[],
            unresolved_conflicts=["instruction audit not completed"],
            active_execution_contract=execution_policy,
        ))
    profile_public = None
    if profile:
        profile_public = {key: value for key, value in profile.items() if key not in {"aliases", "effort_aliases"}}
        profile_public.update({"match_status": "MATCHED", "matched_alias": matched_alias})
    else:
        profile_public = {
            "match_status": "UNVERIFIED",
            "profile_id": None,
            "vendor": None,
            "display_name": args.model,
            "canonical_model_id": None,
            "support_tier": "unverified",
            "behavior_flags": [],
            "official_sources": [],
        }
    config = contract(
        producer_role="p0-capability-preflight",
        status="PASS" if not errors else "BLOCKED",
        input_hashes={
            "input_manifest.json": sha256_file(out / "input_manifest.json"),
            "instruction_manifest.json": manifest_hash,
            "model-profiles.json": sha256_file(MODEL_CATALOG_PATH),
        },
        version=VERSION,
        project_root=project_root.as_posix(),
        platform=args.platform,
        declared_model=args.model,
        recommended_model=model_recommended,
        preferred_model=model_preferred,
        model_support_status=support_tier.upper(),
        model_profile=profile_public,
        model_profile_catalog={
            "catalog_version": catalog["catalog_version"],
            "verified_on": catalog["verified_on"],
            "sha256": sha256_file(MODEL_CATALOG_PATH),
            "stale": stale_catalog,
        },
        reasoning_effort=args.reasoning,
        reasoning_profile=effort,
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
            "parallel_tools": args.parallel_tools,
            "async_tools": args.async_tools,
        },
        execution_policy=execution_policy,
        mathmodel_installation={
            "expected_edition": EXPECTED_EDITION,
            "detected_editions": editions,
            "installations": installations,
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
    print(f"[MODEL] {profile_public['display_name']} ({support_tier.upper()})")
    for warning in warnings:
        print(f"[WARNING] {warning}")
    for error in errors:
        print(f"[ERROR] {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Install an extracted LaTeX universal bundle into one existing project."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE / "skills/paper-workflow-orchestrator/scripts"))
import installation as installer


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--platform", choices=tuple(installer.PLATFORMS))
    parser.add_argument("--check", action="store_true", help="Read-only validation and change summary")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade unchanged managed files within this major version")
    parser.add_argument("--recover", action="store_true", help="Roll back an interrupted installation")
    args = parser.parse_args(argv)
    if args.recover and (args.check or args.upgrade or args.platform):
        parser.error("--recover only takes --project-root")
    if not args.recover and not args.platform:
        parser.error("--platform is required; the installer does not guess the host")
    try:
        installer.no_links(args.project_root.absolute())
        project = args.project_root.resolve()
        if not project.is_dir():
            raise installer.InstallError("--project-root must be an existing directory")
        home = Path.home().resolve()
        global_roots = [home / name for name in (".agents", ".codex", ".claude", ".trae")]
        if os.environ.get("CODEX_HOME"):
            global_roots.append(Path(os.environ["CODEX_HOME"]).resolve())
        if project == home or any(project.is_relative_to(path) for path in global_roots):
            raise installer.InstallError("Only contest projects are supported; home/global agent directories are forbidden")
        if project == SOURCE or project.is_relative_to(SOURCE / "skills") or SOURCE.is_relative_to(project / ".mathmodel"):
            raise installer.InstallError("Keep the distribution source separate from the contest project")
        if args.recover:
            if not installer.inside(project, installer.JOURNAL).is_file():
                raise installer.InstallError("No interrupted installation to recover")
            with installer.installation_lock(project):
                installer.recover(project)
            print("[PASS] Installation rolled back. Project evidence was not changed.")
            return 0
        manifest = installer.validate_source(SOURCE)
        incoming = installer.new_record(manifest, installer.PLATFORMS[args.platform])
        action, old = installer.installation_plan(project, incoming, args.upgrade)
        print(f"{action}: LaTeX {incoming['version']} -> {project / incoming['target']}")
        if args.check or action == "unchanged":
            return 0
        with installer.installation_lock(project):
            action, old = installer.installation_plan(project, incoming, args.upgrade)
            if action != "unchanged":
                installer.apply_install(project, SOURCE, incoming, old)
        print("[PASS] Installed. Restart/refresh your agent's skill discovery.")
        print(f"Entry: {project / incoming['target'] / installer.ENTRY / 'SKILL.md'}")
        print("Run preflight from the contest project; existing evidence was not modified or re-approved.")
        return 0
    except (installer.InstallError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

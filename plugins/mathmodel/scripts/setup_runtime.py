#!/usr/bin/env python3
"""Prepare a writable runtime and a machine-resolved MCP launch configuration."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[1]


def doctor(project_root: str | Path | None = None) -> dict:
    manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    lock = json.loads((PLUGIN / "core.lock.json").read_text(encoding="utf-8"))
    dependencies = {}
    for name in ("mcp", "numpy", "pandas", "scipy", "python-docx", "PyMuPDF"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    collisions = []
    if project_root is not None:
        root = Path(project_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("contest directory does not exist")
        for parent in ("skills", ".agents/skills", ".codex/skills", ".claude/skills", ".trae/skills"):
            directory = root / parent
            for name in ("pro-workflow-orchestrator", "paper-workflow-orchestrator", "mathmodel-lite"):
                if (directory / name / "SKILL.md").is_file():
                    collisions.append(str(directory / name))
    missing = [name for name, version in dependencies.items() if version is None]
    return {"status": "BLOCKED" if collisions else "NEEDS_DEPENDENCIES" if missing else "READY",
            "plugin_root": str(PLUGIN), "plugin_version": manifest["version"], "core": lock,
            "python": sys.executable, "dependencies": dependencies, "missing_dependencies": missing,
            "project_install_conflicts": collisions,
            "next_action": "Resolve the duplicate project installation; the active plugin is explicit." if collisions else
                           "Run setup_runtime.py --runtime-root <writable-directory> --install-deps if dependencies are missing." if missing else
                           "Use the generated absolute MCP configuration or the Skill entry."}


def resolved_config(python: Path) -> dict:
    if not python.is_file():
        raise ValueError("Python executable does not exist")
    return {"mcpServers": {"mathmodel": {"command": str(python.resolve()),
        "args": ["-B", str(PLUGIN / "scripts/mcp_server.py")], "cwd": str(PLUGIN),
        "env": {"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}, "startup_timeout_sec": 30}}}


def prepare(runtime_root: Path, *, install_deps: bool = False, python: Path | None = None) -> Path:
    runtime_root = runtime_root.expanduser().resolve()
    if runtime_root == PLUGIN or runtime_root.is_relative_to(PLUGIN):
        raise ValueError("Runtime must be outside the installed plugin cache")
    runtime_root.mkdir(parents=True, exist_ok=True)
    environment = runtime_root / ".venv"
    existing_python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = (python or (existing_python if not install_deps and existing_python.is_file() else Path(sys.executable))).resolve()
    if install_deps:
        if shutil.disk_usage(runtime_root).free < 2 * 1024**3:
            raise ValueError("At least 2 GiB free space is required before installing modeling dependencies")
        if not (environment / "pyvenv.cfg").exists():
            subprocess.run([str(python), "-m", "venv", str(environment)], check=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        temp = runtime_root / "temp"
        temp.mkdir(exist_ok=True)
        env = {**os.environ, "PIP_CACHE_DIR": str(runtime_root / "pip-cache"), "UV_CACHE_DIR": str(runtime_root / "uv-cache"),
               "TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp), "PYTHONDONTWRITEBYTECODE": "1"}
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(PLUGIN / "requirements.txt"), "-r", str(PLUGIN / "core-requirements.txt")], env=env, check=True)
    config = resolved_config(python)
    destination = runtime_root / "mcp.local.json"
    destination.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run([str(python), "-B", str(PLUGIN / "scripts/mcp_probe.py"), "--config", str(destination)], check=True)
    return destination


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--install-deps", action="store_true")
    parser.add_argument("--register-codex", action="store_true", help="Register the tested absolute command with codex mcp add")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--server-name", default="mathmodel", help="Name updated by codex mcp add; defaults to the existing MathModel server")
    args = parser.parse_args()
    try:
        if args.runtime_root is None:
            if args.install_deps or args.register_codex:
                parser.error("--runtime-root is required for setup")
            print(json.dumps(doctor(args.project_root), ensure_ascii=False, indent=2))
            return 0
        path = prepare(args.runtime_root, install_deps=args.install_deps, python=args.python)
        if args.register_codex:
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", args.server_name):
                raise ValueError("Invalid MCP server name")
            configuration = json.loads(path.read_text(encoding="utf-8"))["mcpServers"]["mathmodel"]
            subprocess.run([args.codex, "mcp", "add", args.server_name, "--env", "PYTHONUTF8=1", "--env", "PYTHONDONTWRITEBYTECODE=1", "--", configuration["command"], *configuration["args"]], check=True)
        print(json.dumps({"status": "PROTOCOL_VERIFIED", "config": str(path), "registered": args.register_codex}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

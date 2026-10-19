"""Install the tracked public ZIP; never copy repository payloads directly."""
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install_bundle(project: Path, platform: str) -> Path:
    archives = sorted((ROOT / "dist").glob("*.zip"))
    if len(archives) != 1:
        raise AssertionError("Expected exactly one universal archive")
    with tempfile.TemporaryDirectory(prefix="mathmodel-bundle-") as temporary:
        source = Path(temporary)
        with zipfile.ZipFile(archives[0]) as archive:
            archive.extractall(source)
        result = subprocess.run([sys.executable, "-S", str(source / "install.py"),
            "--project-root", str(project), "--platform", platform],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"})
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
    return project / {"codex": ".agents/skills", "claude": ".claude/skills", "trae": ".trae/skills"}[platform]

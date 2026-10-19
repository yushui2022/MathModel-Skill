"""Exercise the public ZIP and installer, not a copy of the repository payload."""
import io
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_release_packages as builder


def install_bundle(project: Path, platform: str) -> Path:
    with tempfile.TemporaryDirectory(prefix="mathmodel-bundle-") as temporary:
        source = Path(temporary)
        with zipfile.ZipFile(io.BytesIO(builder.package_bytes(builder.PACKAGE_SPECS[0]))) as archive:
            archive.extractall(source)
        result = subprocess.run([sys.executable, "-S", str(source / "install.py"), "--project-root",
            str(project), "--platform", platform], capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"})
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
    return project / {"codex": ".agents/skills", "claude": ".claude/skills", "trae": ".trae/skills"}[platform]

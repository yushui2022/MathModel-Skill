"""Run preserved Standard or current Pro core in an isolated baseline layout.

Legacy assertions are never removed to accommodate two product histories. The
Standard job checks its fixed published source and tracked ZIPs. The Pro job
overlays CURRENT canonical and generated code on the fixed Pro test layout, so
its original ten-skill/two-platform and mathematical gate assertions still run.
Requires the pinned git objects (CI should checkout with fetch-depth: 0).
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINES = {"standard": "0cc261d90d21e4ed540b02b0c71018cdcd47af58", "pro": "da520d49c62c8f5dc3755eb16bedefd78e77b466"}


def extract_snapshot(commit: str, destination: Path) -> None:
    data = subprocess.run(["git", "archive", "--format=tar", commit], cwd=REPO, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination.resolve()) or member.issym() or member.islnk():
                raise ValueError(f"Unsafe git archive member: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                stream = archive.extractfile(member)
                assert stream is not None
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stream.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=tuple(BASELINES), required=True)
    parser.add_argument("--temp-root", type=Path)
    parser.add_argument("--packages-only", action="store_true")
    parser.add_argument("--keep", action="store_true", help="Keep the isolated tree for diagnosis")
    args = parser.parse_args()
    temp = (args.temp_root or Path(os.environ.get("MATHMODEL_TEST_TEMP", "G:/DevCache/Temp/mathmodel-plugin" if os.name == "nt" else tempfile.gettempdir()))).resolve()
    temp.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix=f"baseline-{args.edition}-", dir=temp)).resolve()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "MATHMODEL_TEST_TEMP": str(sandbox / "test-temp"), "TEMP": str(sandbox / "test-temp"), "TMP": str(sandbox / "test-temp")}
    (sandbox / "test-temp").mkdir()
    try:
        extract_snapshot(BASELINES[args.edition], sandbox)
        if args.edition == "pro":
            for relative in ("packages/claude", "packages/codex"):
                destination = (sandbox / relative).resolve()
                if not destination.is_relative_to(sandbox):
                    raise ValueError("Unsafe baseline overlay destination")
                shutil.rmtree(destination)
                shutil.copytree(REPO / relative, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for relative in ("requirements.txt", "scripts/sync_platform_packages.py"):
                shutil.copyfile(REPO / relative, sandbox / relative)
        commands = [[sys.executable, "-B", "scripts/sync_platform_packages.py", "--check"]]
        if args.packages_only:
            if args.edition == "pro":
                # The sandbox contains current core code, so build its two
                # temporary ZIPs before verifying; historical repo ZIPs stay put.
                commands += [[sys.executable, "-B", "scripts/build_release_packages.py"]]
            commands += [[sys.executable, "-B", "scripts/build_release_packages.py", "--verify"]]
        elif args.edition == "pro":
            commands += [[sys.executable, "-B", "tests/run_pro_tests.py"]]
        else:
            commands += [[sys.executable, "-B", "tests/run_tests.py"], [sys.executable, "-B", "tests/test_paper_scope.py"], [sys.executable, "-B", "scripts/build_release_packages.py", "--verify"]]
        print(f"Baseline {args.edition} {BASELINES[args.edition]} in {sandbox}", flush=True)
        for command in commands:
            completed = subprocess.run(command, cwd=sandbox, env=env)
            if completed.returncode:
                print(f"[FAIL] Preserved baseline command: {' '.join(command)}", flush=True)
                return completed.returncode
        return 0
    finally:
        if not args.keep:
            if sandbox.parent != temp or not sandbox.name.startswith(f"baseline-{args.edition}-"):
                raise ValueError("Refusing unsafe baseline cleanup")
            shutil.rmtree(sandbox)


if __name__ == "__main__":
    raise SystemExit(main())

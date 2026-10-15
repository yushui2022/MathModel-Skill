import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    parser = argparse.ArgumentParser(description="Manifest-bound data import and plotting.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.project_root.resolve()
    scripts = Path(__file__).resolve().parent
    # Plans must use the actual current sheet outputs, not guessed first-sheet paths.
    for name in ("robust_loader.py", "clean_data.py", "build_data_visualization_plan.py",
                 "visualize_data.py", "generate_paper_figures_from_plan.py"):
        print(f"=== {name} ===", flush=True)
        completed = subprocess.run([sys.executable, str(scripts / name)], cwd=root, check=False)
        if completed.returncode:
            print(f"[FAIL] {name}; downstream steps were not run.")
            return completed.returncode
    print("[PASS] Data helper pipeline; confirm field semantics before modeling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

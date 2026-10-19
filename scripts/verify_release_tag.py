"""Reject mismatched, other-edition and development release tags."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text(encoding="utf-8").strip()
if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", version) or sys.argv[1] != "v" + version:
    raise SystemExit("Release tag must exactly match a stable Standard VERSION; dev builds are not released")

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def find_soffice(explicit: str | None) -> Path | None:
    candidates = [
        explicit,
        os.environ.get("LIBREOFFICE_PATH"),
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Pro DOCX to PDF with LibreOffice.")
    parser.add_argument("--docx", type=Path, default=Path("paper_output_pro/final_paper.docx"))
    parser.add_argument("--output-dir", type=Path, default=Path("paper_output_pro"))
    parser.add_argument("--soffice")
    args = parser.parse_args()
    docx = args.docx.resolve()
    output_dir = args.output_dir.resolve()
    soffice = find_soffice(args.soffice)
    if not docx.is_file() or docx.stat().st_size == 0:
        print(f"[BLOCKED] DOCX is missing or empty: {docx}")
        return 1
    if soffice is None:
        print("[BLOCKED] LibreOffice is required to produce and verify the final PDF")
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf = output_dir / f"{docx.stem}.pdf"
    if pdf.exists():
        pdf.unlink()
    temp_parent = os.environ.get("MATHMODEL_TEMP_DIR")
    if temp_parent:
        Path(temp_parent).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mathmodel-pro-lo-", dir=temp_parent) as profile_dir:
        profile_uri = Path(profile_dir).resolve().as_uri()
        completed = subprocess.run(
            [
                str(soffice),
                "--headless",
                f"-env:UserInstallation={profile_uri}",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(docx),
            ],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=180,
        )
    for _ in range(20):
        if pdf.is_file() and pdf.stat().st_size > 0:
            break
        time.sleep(0.25)
    if completed.returncode != 0 or not pdf.is_file() or pdf.stat().st_size == 0:
        print(completed.stdout)
        print(completed.stderr)
        print("[BLOCKED] LibreOffice did not create a non-empty PDF")
        return 1
    print(f"[PASS] Rendered {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

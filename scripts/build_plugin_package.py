"""Build a deterministic MathModel Codex plugin archive."""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "mathmodel"

def files() -> list[Path]:
    return sorted((p for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}), key=lambda p: p.relative_to(PLUGIN).as_posix())

def build(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = {p.relative_to(PLUGIN).as_posix(): p.read_bytes() for p in files()}
    digest = hashlib.sha256()
    for name, data in entries.items(): digest.update(name.encode()); digest.update(b"\0"); digest.update(hashlib.sha256(data).hexdigest().encode()); digest.update(b"\n")
    manifest = {"schema_version":"1.0", "plugin":"mathmodel", "version":json.loads((PLUGIN/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version'], "payload_sha256":digest.hexdigest(), "file_count":len(entries)}
    entries["MATHMODEL_PLUGIN_BUILD.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2020,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16; z.writestr(info, data)
    return output

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--output', default=str(ROOT/'dist'/'MathModel-Codex-Plugin.zip')); p.add_argument('--verify', action='store_true'); a=p.parse_args(); out=Path(a.output)
    if a.verify:
        if not out.exists(): raise SystemExit(f'Missing archive: {out}')
        with zipfile.ZipFile(out) as z:
            names=[n for n in z.namelist() if n != 'MATHMODEL_PLUGIN_BUILD.json']
            expected=[p.relative_to(PLUGIN).as_posix() for p in files()]
            if names != expected: raise SystemExit('Plugin archive entries differ from source')
        print(f'Plugin archive verified: {out}'); return 0
    print(f'Built {build(out)}'); return 0
if __name__ == '__main__': raise SystemExit(main())

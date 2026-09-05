from __future__ import annotations

import argparse
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from pro_checkpoint import require_checkpoints
from pro_contracts import contract, output_root, safe_path, sha256_file, utc_now, write_json


def public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("only public HTTP(S) URLs without credentials are allowed")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("source URL resolves to a non-public address")


def capture(root: Path, url: str, source_id: str) -> Path:
    if not source_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in source_id):
        raise ValueError("source_id must be a simple identifier")
    directory = safe_path(root, "research/" + source_id)
    if directory.exists():
        raise ValueError("source ID already exists; preserve the original retrieval")
    target = url
    with requests.Session() as session:
        # Public retrieval must not inherit .netrc credentials or authenticated proxies.
        session.trust_env = False
        for _ in range(6):
            public_url(target)
            response = session.get(target, allow_redirects=False, stream=True, timeout=(15, 60))
            if response.status_code in {301, 302, 303, 307, 308}:
                target = urljoin(target, response.headers.get("Location", ""))
                response.close()
                continue
            response.raise_for_status()
            if response.status_code != 200:
                response.close()
                raise ValueError("source did not return a complete HTTP 200 response")
            directory.mkdir(parents=True)
            snapshot = directory / "content.bin"
            total = 0
            try:
                with snapshot.open("wb") as stream:
                    for chunk in response.iter_content(65536):
                        total += len(chunk)
                        if total > 50 * 1024 * 1024:
                            raise ValueError("source exceeds the 50 MB retrieval limit; use an explicitly scoped dataset downloader")
                        stream.write(chunk)
                if not total:
                    raise ValueError("source response is empty")
                accessed = utc_now()
                path = directory / "retrieval.json"
                write_json(path, contract(
                    producer_role="pro-public-source-capture", status="PASS", url=url, final_url=target,
                    accessed_at_utc=accessed, http_status=200, content_type=response.headers.get("Content-Type", ""),
                    snapshot_path=snapshot.relative_to(root).as_posix(), content_sha256=sha256_file(snapshot),
                    input_hashes={snapshot.relative_to(root).as_posix(): sha256_file(snapshot)},
                ))
                return path
            finally:
                response.close()
    raise ValueError("too many public-source redirects")


def main() -> int:
    parser = argparse.ArgumentParser(description="Save a public source and its actual retrieval receipt.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    project = args.project_root.resolve()
    root = output_root(project)
    try:
        errors = require_checkpoints(project, root, 1)
        if errors:
            raise ValueError("; ".join(errors))
        print(f"[PASS] {capture(root, args.url, args.source_id)}")
        return 0
    except (ValueError, OSError, requests.RequestException) as exc:
        print(f"[BLOCKED] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

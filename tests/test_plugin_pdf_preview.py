"""Real PDF rasterization and authenticated artifact-only HTTP boundaries."""
from __future__ import annotations

import hashlib
import http.client
import json
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import pymupdf as fitz

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plugins/mathmodel/scripts"))
from serve_dashboard import ProjectServer
from runtime import pdf_preview

TEMP = REPO / "tests/.runtime-tmp"
TEMP.mkdir(exist_ok=True)


class PDFPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="PDF 中文 比赛 ", dir=TEMP)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "problem_files"
        self.inputs.mkdir()
        self.server = ProjectServer(self.root, REPO / "plugins/mathmodel/dashboard")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        self.temp.cleanup()

    def pdf(self, name="真实 题目.pdf", pages=2, encrypted=False, large=False):
        target = self.inputs / name
        with fitz.open() as document:
            for number in range(pages):
                page = document.new_page(width=8000 if large else 595, height=8000 if large else 842)
                page.insert_text((40, 60), f"Actual modeling problem: page {number + 1}")
            options = {"encryption": fitz.PDF_ENCRYPT_AES_256, "owner_pw": "owner-test", "user_pw": "user-test"} if encrypted else {}
            document.save(target, **options)
        artifact = next(x for x in self.server.state.artifacts() if x["path"] == target.relative_to(self.root).as_posix())
        return target, artifact["id"]

    def request(self, path, *, headers=None, token=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=20)
        actual = {"X-MathModel-Token": self.server.token} if token else {}
        actual.update(headers or {})
        connection.request("GET", path, headers=actual)
        response = connection.getresponse()
        result = response.status, dict(response.headers), response.read()
        connection.close()
        return result

    def test_real_pdf_info_png_mime_and_read_only_sources(self):
        target, artifact = self.pdf()
        before = target.read_bytes(), target.stat().st_mtime_ns
        status, headers, data = self.request(f"/api/artifacts/{artifact}/pdf-info")
        self.assertEqual(status, 200, data)
        info = json.loads(data)
        self.assertEqual(info["artifact_id"], artifact)
        self.assertEqual(info["page_count"], 2)
        self.assertEqual(info["preview_page_count"], 2)
        self.assertFalse(info["needs_password"])
        status, headers, image = self.request(f"/api/artifacts/{artifact}/pdf-page?page=1")
        self.assertEqual(status, 200, image[:100])
        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(before, (target.read_bytes(), target.stat().st_mtime_ns))
        self.assertFalse((self.root / "paper_output_pro").exists())

    def test_page_boundaries_and_non_pdf_mime(self):
        _, artifact = self.pdf()
        for page in ("-1", "2", "500", "1000000"):
            status, _, data = self.request(f"/api/artifacts/{artifact}/pdf-page?page={page}")
            self.assertEqual(status, 416, data)
        self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-page?page=nope")[0], 400)
        (self.inputs / "code.py").write_text("print(1)")
        code = next(x["id"] for x in self.server.state.artifacts() if x["path"].endswith(".py"))
        self.assertEqual(self.request(f"/api/artifacts/{code}/pdf-info")[0], 415)

    def test_preview_page_count_and_render_pixel_limits(self):
        _, artifact = self.pdf("many.pdf", pages=501)
        info = json.loads(self.request(f"/api/artifacts/{artifact}/pdf-info")[2])
        self.assertEqual(info["page_count"], 501)
        self.assertEqual(info["preview_page_count"], 500)
        self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-page?page=500")[0], 416)
        _, large = self.pdf("large-page.pdf", pages=1, large=True)
        status, _, png = self.request(f"/api/artifacts/{large}/pdf-page")
        self.assertEqual(status, 200, png[:100])
        width, height = struct.unpack(">II", png[16:24])
        self.assertLessEqual(width * height, pdf_preview.MAX_RENDER_PIXELS)
        self.assertLessEqual(len(png), pdf_preview.MAX_PNG_BYTES)

    def test_encrypted_and_invalid_pdf_are_explicit(self):
        _, artifact = self.pdf(encrypted=True)
        status, _, data = self.request(f"/api/artifacts/{artifact}/pdf-info")
        self.assertEqual(status, 200, data)
        self.assertTrue(json.loads(data)["needs_password"])
        self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-page")[0], 422)
        (self.inputs / "invalid.pdf").write_bytes(b"This is not a PDF")
        invalid = next(x["id"] for x in self.server.state.artifacts() if x["path"].endswith("invalid.pdf"))
        self.assertEqual(self.request(f"/api/artifacts/{invalid}/pdf-info")[0], 422)

    def test_auth_origin_registry_and_cross_path(self):
        _, artifact = self.pdf()
        path = f"/api/artifacts/{artifact}/pdf-page"
        self.assertEqual(self.request(path, token=False)[0], 401)
        self.assertEqual(self.request(path, headers={"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.request(path, headers={"Host": "example.com"})[0], 403)
        for route in ("/api/artifacts/%2e%2e/private.pdf/pdf-info", "/api/artifacts/..%5cprivate.pdf/pdf-page"):
            self.assertEqual(self.request(route)[0], 403)
        private = self.root / "private.pdf"
        private.write_bytes(b"not registered")
        guessed = hashlib.sha256(b"private.pdf").hexdigest()[:20]
        self.assertEqual(self.request(f"/api/artifacts/{guessed}/pdf-info")[0], 404)
        self.assertEqual(self.request(f"/api/artifacts/{artifact}/extra/pdf-info")[0], 404)

    def test_size_limit_timeout_and_busy_recovery(self):
        target, artifact = self.pdf()
        with mock.patch.object(pdf_preview.subprocess, "run", side_effect=subprocess.TimeoutExpired("render", 12)):
            self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-page")[0], 504)
        with mock.patch.object(pdf_preview, "_slots") as slots:
            slots.acquire.return_value = False
            self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-page")[0], 503)
        oversized = b"\x89PNG\r\n\x1a\n" + bytes(pdf_preview.MAX_PNG_BYTES)
        with mock.patch.object(pdf_preview.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, oversized, b"")):
            self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-page")[0], 413)
        self.assertEqual(self.request(f"/api/artifacts/{artifact}/pdf-info")[0], 200)
        with target.open("ab") as file:
            file.truncate(25 * 1024 * 1024 + 1)
        self.assertIn(self.request(f"/api/artifacts/{artifact}/pdf-info")[0], {403, 404})

    def test_linked_pdf_directory_cannot_be_registered(self):
        target, _ = self.pdf()
        external = self.root / "private-files"
        external.mkdir()
        (external / "private.pdf").write_bytes(target.read_bytes())
        link = self.inputs / "linked"
        try:
            link.symlink_to(external, target_is_directory=True)
        except OSError:
            if sys.platform != "win32":
                self.skipTest("symlinks unavailable")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(external)], capture_output=True)
            if result.returncode:
                self.skipTest("junctions unavailable")
        try:
            relative = "problem_files/linked/private.pdf"
            self.assertFalse(any(x["path"] == relative for x in self.server.state.artifacts()))
            guessed = hashlib.sha256(relative.encode()).hexdigest()[:20]
            self.assertEqual(self.request(f"/api/artifacts/{guessed}/pdf-info")[0], 404)
        finally:
            if link.is_symlink():
                link.unlink()
            else:
                link.rmdir()


if __name__ == "__main__":
    unittest.main()

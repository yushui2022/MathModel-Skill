"""Bounded PDF raster previews, isolated from the project HTTP process."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import threading
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.safety import MAX_ARTIFACT_BYTES, contained_file, execution_environment, spawn_options

MAX_PREVIEW_PAGES = 500
MAX_RENDER_PIXELS = 2_500_000
MAX_PNG_BYTES = 8 * 1024 * 1024
RENDER_TIMEOUT = 12
_slots = threading.BoundedSemaphore(2)


class PDFPreviewError(ValueError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def preview_pdf(project_root: Path, relative: str, *, page: int | None = None) -> dict | bytes:
    """The caller supplies an already registered artifact; recheck its path here."""
    target = contained_file(project_root, relative, limit=MAX_ARTIFACT_BYTES)
    if target.suffix.lower() != ".pdf":
        raise PDFPreviewError("所选产物不是 PDF 文件。", 415)
    if page is not None and (type(page) is not int or not 0 <= page < MAX_PREVIEW_PAGES):
        raise PDFPreviewError(f"页码必须在 0..{MAX_PREVIEW_PAGES - 1} 范围内。", 416)
    if not _slots.acquire(blocking=False):
        raise PDFPreviewError("PDF 预览正在处理其他页面，请稍后重试。", 503)
    try:
        command = [sys.executable, "-B", str(Path(__file__).resolve()), str(project_root), relative,
                   "info" if page is None else str(page)]
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=RENDER_TIMEOUT, cwd=project_root, env=execution_environment(), **spawn_options())
        except subprocess.TimeoutExpired as exc:
            raise PDFPreviewError("PDF 页面渲染超时，请下载原文件查看。", 504) from exc
        if result.returncode:
            try:
                error = json.loads(result.stderr[:4096].decode("utf-8"))
                code = error.get("status", 422)
                if code not in {403, 404, 413, 415, 416, 422, 503}:
                    code = 422
                raise PDFPreviewError(str(error.get("error", "PDF 预览失败。"))[:1000], code)
            except (UnicodeError, json.JSONDecodeError):
                raise PDFPreviewError("PDF 预览进程失败，请检查文件或下载原文件查看。") from None
        if page is None:
            if len(result.stdout) > 4096:
                raise PDFPreviewError("PDF 元数据超过预览限制。", 413)
            return json.loads(result.stdout.decode("utf-8"))
        if len(result.stdout) > MAX_PNG_BYTES or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
            raise PDFPreviewError("PDF 页面图片超过预览限制或无法渲染。", 413)
        return result.stdout
    finally:
        _slots.release()


def _render(project_root: Path, relative: str, page: int | None) -> dict | bytes:
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise PDFPreviewError("PDF 预览缺少 PyMuPDF，请运行插件环境安装。", 503) from exc
    target = contained_file(project_root, relative, limit=MAX_ARTIFACT_BYTES)
    if target.suffix.lower() != ".pdf":
        raise PDFPreviewError("所选产物不是 PDF 文件。", 415)
    # Freeze a bounded byte snapshot: page parsing cannot follow a swapped link.
    with target.open("rb") as source:
        data = source.read(MAX_ARTIFACT_BYTES + 1)
    if len(data) > MAX_ARTIFACT_BYTES:
        raise PDFPreviewError("PDF 超过 25 MiB 预览限制。", 413)
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    with fitz.open(stream=data, filetype="pdf") as document:
        count = document.page_count
        info = {"page_count": count, "encrypted": bool(document.is_encrypted), "needs_password": bool(document.needs_pass),
                "preview_page_count": min(count, MAX_PREVIEW_PAGES), "max_preview_pages": MAX_PREVIEW_PAGES,
                "max_render_pixels": MAX_RENDER_PIXELS, "max_png_bytes": MAX_PNG_BYTES}
        if page is None:
            return info
        if document.needs_pass:
            raise PDFPreviewError("此 PDF 需要密码，请下载后使用 PDF 阅读器打开。")
        if not 0 <= page < min(count, MAX_PREVIEW_PAGES):
            raise PDFPreviewError("请求的 PDF 页码超出可预览范围。", 416)
        sheet = document.load_page(page)
        width, height = sheet.rect.width, sheet.rect.height
        if not all(math.isfinite(x) and x > 0 for x in (width, height)):
            raise PDFPreviewError("PDF 页面尺寸无效。")
        scale = min(2.0, 1400 / width, 2400 / max(width, height), math.sqrt(MAX_RENDER_PIXELS / (width * height))) * 0.999
        if math.ceil(width * scale) * math.ceil(height * scale) > MAX_RENDER_PIXELS:
            scale *= 0.99
        pixels = sheet.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
        if pixels.width * pixels.height > MAX_RENDER_PIXELS:
            raise PDFPreviewError("PDF 页面像素超过预览限制。", 413)
        png = pixels.tobytes("png")
        if len(png) > MAX_PNG_BYTES:
            raise PDFPreviewError("PDF 页面图片超过 8 MiB 预览限制。", 413)
        return png


def main() -> int:
    try:
        result = _render(Path(sys.argv[1]), sys.argv[2], None if sys.argv[3] == "info" else int(sys.argv[3]))
        sys.stdout.buffer.write(result if isinstance(result, bytes) else json.dumps(result).encode("utf-8"))
        return 0
    except Exception as exc:
        status = getattr(exc, "status", 403 if isinstance(exc, PermissionError) else 404 if isinstance(exc, FileNotFoundError) else 422)
        sys.stderr.buffer.write(json.dumps({"error": str(exc)[:1000] or "PDF 文件无效。", "status": status}, ensure_ascii=False).encode("utf-8"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

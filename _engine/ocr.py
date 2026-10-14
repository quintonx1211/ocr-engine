"""High-level OCR interface -- the main public API."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from ._dll import _EngineDll
from ._protobuf import LineResult, parse_visual_annotation
from .models import OcrBlock, OcrLine, OcrPage, OcrResult

log = logging.getLogger(__name__)


class OcrEngine:
    """Direct interface to the native OCR engine -- loads the shared
    library via ctypes, no browser needed.

    >>> ai = OcrEngine(model_dir=...)
    >>> result = ai.ocr("scan.pdf")
    """

    def __init__(self, model_dir: Path, *, light_mode: bool = False):
        self._dll = _EngineDll(model_dir)
        if light_mode:
            self._dll.set_light_mode(True)
        if not self._dll.init_ocr():
            raise RuntimeError("Failed to initialize OCR pipeline")
        self._max_dim = self._dll.get_max_image_dimension()
        log.info("OCR ready (max dimension: %d)", self._max_dim)

    def ocr(self, file: str | Path, *, pages: Iterable[int] | None = None) -> OcrResult:
        """OCR a PDF or image file. `pages` (1-based) limits which PDF
        pages are processed; ignored for images."""
        path = Path(file)
        if path.suffix.lower() == ".pdf":
            return self._ocr_pdf(path, pages=pages)
        return self._ocr_image_file(path)

    # -- Internals ------------------------------------------------------

    def _perform_ocr(self, img: Image.Image) -> list[LineResult]:
        w, h = img.size
        if max(w, h) > self._max_dim:
            scale = self._max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        img = img.convert("RGBA")
        width, height = img.size
        raw = self._dll.perform_ocr(img.tobytes("raw", "BGRA"), width, height)
        return parse_visual_annotation(raw) if raw is not None else []

    def _ocr_image_file(self, path: Path) -> OcrResult:
        lines = self._perform_ocr(Image.open(path))
        return OcrResult(pages=[_lines_to_page(lines, page_number=1)])

    def _ocr_pdf(self, path: Path, *, pages: Iterable[int] | None = None) -> OcrResult:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF OCR: pip install PyMuPDF"
            ) from exc

        doc = fitz.open(path)
        page_set = set(pages) if pages is not None else None
        ocr_pages: list[OcrPage] = []

        for i in range(len(doc)):
            page_num = i + 1
            if page_set is not None and page_num not in page_set:
                continue

            pg = doc[i]
            scale = min(1.0, self._max_dim / max(pg.rect.width, pg.rect.height))
            pix = pg.get_pixmap(dpi=int(72 * scale * 2))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            lines = self._perform_ocr(img)
            ocr_page = _lines_to_page(lines, page_number=page_num)
            ocr_pages.append(ocr_page)
            log.info("Page %d: %d blocks", page_num, len(ocr_page.blocks))

        return OcrResult(pages=ocr_pages)


def _lines_to_page(lines: list[LineResult], page_number: int) -> OcrPage:
    blocks_map: dict[int, list[LineResult]] = defaultdict(list)
    for ln in lines:
        blocks_map[ln.block_id].append(ln)

    blocks = [
        OcrBlock(lines=[OcrLine(text=ln.text) for ln in blocks_map[block_id]])
        for block_id in sorted(blocks_map)
    ]
    return OcrPage(page_number=page_number, blocks=blocks)

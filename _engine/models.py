"""Public data model for OCR results -- trimmed to what ocr_module.py
actually reads (page.text); the engine's own per-word/bounding-box output
is decoded no further than that."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OcrLine:
    text: str


@dataclass
class OcrBlock:
    lines: list[OcrLine] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(ln.text for ln in self.lines)


@dataclass
class OcrPage:
    page_number: int
    blocks: list[OcrBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(blk.text for blk in self.blocks if blk.text.strip())


@dataclass
class OcrResult:
    pages: list[OcrPage] = field(default_factory=list)

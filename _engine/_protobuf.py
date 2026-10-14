"""Wire-format protobuf decoder for VisualAnnotation.

Decodes the binary protobuf returned by PerformOCR without needing
compiled .proto files. Only the fields ocr_module.py actually reads
(line text and block grouping) are decoded -- the message also carries
per-word text/confidence/bounding-box data that this pipeline never
uses, so it's skipped rather than parsed and discarded.
"""

from __future__ import annotations

import struct


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _decode_raw(data: bytes) -> list[tuple[int, int, object]]:
    pos = 0
    items: list[tuple[int, int, object]] = []
    while pos < len(data):
        try:
            tag, pos = _decode_varint(data, pos)
        except (IndexError, ValueError):
            break
        fn, wt = tag >> 3, tag & 7
        if wt == 0:
            val, pos = _decode_varint(data, pos)
        elif wt == 1:
            val = struct.unpack("<d", data[pos:pos + 8])[0]; pos += 8
        elif wt == 2:
            length, pos = _decode_varint(data, pos)
            val = data[pos:pos + length]; pos += length
        elif wt == 5:
            val = struct.unpack("<f", data[pos:pos + 4])[0]; pos += 4
        else:
            break
        items.append((fn, wt, val))
    return items


class LineResult:
    """One line from the VisualAnnotation protobuf: its text and which
    block it belongs to."""
    __slots__ = ("text", "block_id")

    def __init__(self):
        self.text = ""
        self.block_id = 0


def _parse_line(data: bytes) -> LineResult:
    ln = LineResult()
    for fn, wt, val in _decode_raw(data):
        if fn == 3 and wt == 2:
            ln.text = val.decode("utf-8", errors="replace")
        elif fn == 5 and wt == 0:
            ln.block_id = val
    return ln


def parse_visual_annotation(data: bytes) -> list[LineResult]:
    """Parse a serialised VisualAnnotation protobuf message."""
    return [_parse_line(val) for fn, wt, val in _decode_raw(data) if fn == 2 and wt == 2]

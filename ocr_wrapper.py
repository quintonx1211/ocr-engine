"""Easy-to-use wrapper around the local OCR engine (ctypes, no network
call) -- see _engine/ for the low-level ctypes binding.

The containing folder is named "ocr-engine" (a hyphen, not valid in a
Python module name), so it can't be imported directly as a package --
add it to sys.path and import this module by its own name instead:

    import sys
    sys.path.insert(0, "/path/to/ocr-engine")
    import ocr_wrapper

    text = ocr_wrapper.extract_text("invoice.pdf")   # plain text, pages joined
    result = ocr_wrapper.ocr("invoice.pdf")           # structured OcrResult

Auto-selects the right platform+arch resource folder under platforms/
(linux, mac-amd64, mac-arm64, windows-386, windows-amd64) via
_engine._platform.variant_dir_name(). No update-checking or download
logic: re-provisioning a newer engine version is a manual, offline step
(re-run the fetch script and replace these folders)."""
from pathlib import Path

from _engine.ocr import OcrEngine
from _engine.models import OcrResult
from _engine._platform import variant_dir_name

_PLATFORMS_DIR = Path(__file__).parent / "platforms"
_engine = None


def _model_dir() -> Path:
    d = _PLATFORMS_DIR / variant_dir_name()
    if not d.exists():
        raise FileNotFoundError(
            f"OCR engine data not found: {d}\n"
            "Expected one folder per platform under platforms/ "
            "(linux, mac-amd64, mac-arm64, windows-386, windows-amd64)."
        )
    return d


def get_engine() -> OcrEngine:
    """Lazy singleton -- loading the native library and initializing the
    OCR pipeline is expensive enough to do once per process, not per call."""
    global _engine
    if _engine is None:
        _engine = OcrEngine(model_dir=_model_dir())
    return _engine


def ocr(file_path, pages=None) -> OcrResult:
    """OCRs a PDF or image file (dispatched by extension). Returns the
    full structured result -- one OcrPage per page, each with its own
    .text and the blocks/lines under it. `pages` (1-based) limits which
    PDF pages are processed."""
    return get_engine().ocr(str(file_path), pages=pages)


def extract_text(file_path, pages=None) -> str:
    """OCRs a PDF or image file and returns the full text, pages joined
    with a blank line -- the common case when you just want the text."""
    result = ocr(file_path, pages=pages)
    return "\n\n".join(page.text for page in result.pages)

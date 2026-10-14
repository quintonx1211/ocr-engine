"""Native library filename and data-folder name per platform+arch variant.

The downloaded resource bundles are laid out one folder per variant under
platforms/ (see ocr_wrapper.py's _model_dir): linux, mac-amd64,
mac-arm64, windows-386, windows-amd64. Only the library filename differs
within each OS; the model/data files are identical across variants for
that OS.
"""
import platform
import sys


def variant_dir_name() -> str:
    machine = platform.machine().lower()
    # The DLL must match the interpreter, not the OS: 32-bit Python on
    # 64-bit Windows still reports machine() == "AMD64".
    is_64 = sys.maxsize > 2**32

    if sys.platform == "win32":
        return "windows-amd64" if is_64 else "windows-386"
    if sys.platform == "darwin":
        return "mac-arm64" if machine in ("arm64", "aarch64") else "mac-amd64"
    if sys.platform == "linux":
        return "linux"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def lib_name() -> str:
    return "ocr_core.dll" if sys.platform == "win32" else "libocrcore.so"


LIB_NAME = lib_name()

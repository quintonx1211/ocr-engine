# ocr-engine

Local OCR engine (ctypes, no network call, no browser) bundled for 5
platform+arch variants in one place.

## Layout

```
ocr-engine/
  platforms/        one folder per platform+arch variant
    linux/          libocrcore.so + resources (Linux x86_64)
    mac-amd64/      libocrcore.so + resources (macOS Intel)
    mac-arm64/      libocrcore.so + resources (macOS Apple Silicon)
    windows-386/    ocr_core.dll + resources (Windows 32-bit)
    windows-amd64/  ocr_core.dll + resources (Windows x64)
  _engine/          low-level ctypes binding (the actual Python/C interface)
  ocr_wrapper.py     <-- the module you import
  ocr_cli.py         command-line front end
```

No Linux ARM64 variant is available.

## Usage

The folder name has a hyphen, so it can't be `import`ed as a package --
add it to `sys.path` and import the wrapper module by its own name:

```python
import sys
sys.path.insert(0, "/path/to/ocr-engine")
import ocr_wrapper

text = ocr_wrapper.extract_text("invoice.pdf")    # plain text, pages joined
result = ocr_wrapper.ocr("invoice.pdf")            # structured OcrResult (pages -> blocks -> lines)
```

`ocr_wrapper` auto-detects the current platform+arch and loads the
matching variant folder under `platforms/` (see `_engine/_platform.py`). A PDF or a plain
image file (jpg/png/...) both work -- dispatched by file extension.

### Command line

```
python ocr_cli.py invoice.pdf                     # text to stdout
python ocr_cli.py *.pdf -o out/                   # one .txt per input into out/
python ocr_cli.py scan.pdf -p 1,3-5 -f json       # selected pages as JSON
python ocr_cli.py scan.png -o scan.txt            # single output file
```

Options: `-o/--output` (file, or directory for several inputs),
`-f/--format text|json`, `-p/--pages` (1-based, PDF only),
`-v/--verbose` (engine logs). Exits with 1 if any input failed.

Only dependency beyond the stdlib: `Pillow` (and `PyMuPDF` if OCRing a
PDF, not just images).

## Updating the engine

No update-checking or auto-download logic is included on purpose --
re-provisioning the engine is a deliberate, manual, offline step.

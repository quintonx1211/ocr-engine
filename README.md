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

### Which `platforms/` folder do I need?

`ocr_wrapper` picks the folder automatically -- this only matters when
shipping a single variant to save space (the full `platforms/` is ~600 MB).

| Machine | Folder |
|---|---|
| Windows, 64-bit Python (almost all Windows PCs) | `windows-amd64` |
| Windows, 32-bit Python | `windows-386` |
| macOS, Apple Silicon (M1/M2/M3/M4...) | `mac-arm64` |
| macOS, Intel | `mac-amd64` |
| Linux x86_64 | `linux` |

It follows the **Python interpreter**, not just the OS: 32-bit Python on
64-bit Windows needs `windows-386`, and x86 Python under Rosetta on an
Apple Silicon Mac needs `mac-amd64`. To check on the target machine:

```
python ocr_cli.py --platform
```

prints the folder name and whether it is present.

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
python ocr_cli.py invoice.pdf                     # -> ocr_output/invoice.txt
python ocr_cli.py *.pdf -o out/                   # one .txt per input into out/
python ocr_cli.py invoice.pdf --stdout            # print instead of writing files
python ocr_cli.py scan.pdf -p 1,3-5 -f json       # selected pages as JSON
python ocr_cli.py scan.png -o scan.txt            # single output file
```

Results go to `ocr_output/` in the current directory by default (created
if needed, one `<input name>.txt`/`.json` per input).

Options: `-o/--output` (file, or directory for several inputs),
`--stdout` (print instead of writing files),
`-f/--format text|json`, `-p/--pages` (1-based, PDF only),
`-v/--verbose` (engine logs). Exits with 1 if any input failed.

Only dependency beyond the stdlib: `Pillow` (and `PyMuPDF` if OCRing a
PDF, not just images).

## Updating the engine

No update-checking or auto-download logic is included on purpose --
re-provisioning the engine is a deliberate, manual, offline step.

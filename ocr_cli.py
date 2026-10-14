"""Command-line front end for ocr_wrapper.

    python ocr_cli.py invoice.pdf                     # -> ocr_output/invoice.txt
    python ocr_cli.py *.pdf -o out/                   # one .txt per input into out/
    python ocr_cli.py invoice.pdf --stdout            # print instead of writing files
    python ocr_cli.py scan.pdf --pages 1,3-5 -f json  # selected pages as JSON
    python ocr_cli.py --platform                      # which platforms/ folder this machine needs
"""
import argparse
import glob
import json
import logging
import sys
from pathlib import Path

import ocr_wrapper
from _engine._platform import variant_dir_name

DEFAULT_OUTPUT_DIR = "ocr_output"


def _parse_pages(spec: str) -> set[int]:
    """'1,3-5' -> {1, 3, 4, 5}"""
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        elif part:
            pages.add(int(part))
    return pages


def _expand_inputs(patterns: list[str]) -> list[Path]:
    # Windows shells don't expand wildcards, so do it here.
    files = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern)) if glob.has_magic(pattern) else [pattern]
        files.extend(Path(m) for m in matches)
    return files


def _render(path: Path, result, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(
            {
                "file": str(path),
                "pages": [
                    {
                        "page_number": p.page_number,
                        "text": p.text,
                        "blocks": [[ln.text for ln in b.lines] for b in p.blocks],
                    }
                    for p in result.pages
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    return "\n\n".join(page.text for page in result.pages)


def _print_platform() -> int:
    try:
        name = variant_dir_name()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    folder = ocr_wrapper._PLATFORMS_DIR / name
    status = "found" if folder.is_dir() else "MISSING"
    print(f"platform: {name}")
    print(f"folder:   {folder} ({status})")
    return 0 if folder.is_dir() else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ocr_cli", description="OCR PDF or image files with the local engine."
    )
    parser.add_argument("inputs", nargs="*", help="PDF/image files (wildcards allowed)")
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument("-o", "--output",
                      help="output file (single input) or directory (one file per input); "
                           f"default: ./{DEFAULT_OUTPUT_DIR}/")
    dest.add_argument("--stdout", action="store_true",
                      help="print results instead of writing files")
    parser.add_argument("-f", "--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("-p", "--pages", type=_parse_pages,
                        help="PDF pages to process, 1-based, e.g. 1,3-5 (default: all)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show engine logs")
    parser.add_argument("--platform", action="store_true",
                        help="print which platforms/ folder this machine needs, then exit")
    args = parser.parse_args(argv)

    if args.platform:
        return _print_platform()
    if not args.inputs:
        parser.error("the following arguments are required: inputs")

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s: %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    files = _expand_inputs(args.inputs)
    if args.stdout:
        out, out_is_dir = None, False
    elif args.output:
        out = Path(args.output)
        out_is_dir = len(files) > 1 or out.is_dir() or args.output.endswith(("/", "\\"))
    else:
        out, out_is_dir = Path(DEFAULT_OUTPUT_DIR), True
    if out_is_dir:
        out.mkdir(parents=True, exist_ok=True)
    ext = ".json" if args.format == "json" else ".txt"

    failed = 0
    for path in files:
        if not path.is_file():
            print(f"error: {path}: file not found", file=sys.stderr)
            failed += 1
            continue
        try:
            result = ocr_wrapper.ocr(path, pages=args.pages)
        except Exception as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            failed += 1
            continue

        rendered = _render(path, result, args.format)
        if out_is_dir:
            target = out / (path.stem + ext)
            target.write_text(rendered + "\n", encoding="utf-8")
            print(f"{path} -> {target}", file=sys.stderr)
        elif out is not None:
            out.write_text(rendered + "\n", encoding="utf-8")
        else:
            if len(files) > 1:
                print(f"==> {path} <==")
            print(rendered)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""Command-line front end for ocr_wrapper.

    python ocr_cli.py invoice.pdf                     # text to stdout
    python ocr_cli.py *.pdf -o out/                   # one .txt per input
    python ocr_cli.py scan.pdf --pages 1,3-5 -f json  # selected pages as JSON
"""
import argparse
import glob
import json
import logging
import sys
from pathlib import Path

import ocr_wrapper


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ocr_cli", description="OCR PDF or image files with the local engine."
    )
    parser.add_argument("inputs", nargs="+", help="PDF/image files (wildcards allowed)")
    parser.add_argument("-o", "--output",
                        help="output file (single input) or directory (one file per input); "
                             "default: stdout")
    parser.add_argument("-f", "--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    parser.add_argument("-p", "--pages", type=_parse_pages,
                        help="PDF pages to process, 1-based, e.g. 1,3-5 (default: all)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show engine logs")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s: %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    files = _expand_inputs(args.inputs)
    out = Path(args.output) if args.output else None
    out_is_dir = out is not None and (len(files) > 1 or out.is_dir() or args.output.endswith(("/", "\\")))
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

"""Command line: anonymise FILE_OR_DIR... [-o OUTDIR]"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

from .image import IMAGE_EXTS, process_image
from .model import mask
from .ocr import resolve_lang
from .pdf import process_pdf

VARIANT = "variant 2 · OCR + rules (no NER)"
SUPPORTED = IMAGE_EXTS | {".pdf"}


def collect(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED and ".anonymised" not in f.name)
        elif p.suffix.lower() in SUPPORTED:
            files.append(p)
        else:
            print(f"⚠️  skipping unsupported file: {p}", file=sys.stderr)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="anonymise", description=f"Black out personal data in PDFs and images ({VARIANT}).")
    ap.add_argument("inputs", nargs="+", help="files or folders")
    ap.add_argument("-o", "--out", help="output folder (default: next to each input, *.anonymised.*)")
    ap.add_argument("--lang", default="eng+ukr+rus", help="Tesseract languages (default: eng+ukr+rus)")
    ap.add_argument("--no-faces", dest="faces", action="store_false", help="do not black out faces")
    ap.add_argument("--no-codes", dest="codes", action="store_false", help="do not black out QR codes / barcodes")
    ap.add_argument("--skip", nargs="*", default=[], metavar="KIND", help="finding kinds to leave alone, e.g. url ip-address")
    ap.add_argument("--pad", type=float, default=3, help="extra pixels around each box (default 3)")
    ap.add_argument("--report", action="store_true", help="list every finding (values are partly masked)")
    ap.add_argument("--dry-run", action="store_true", help="detect only, write nothing")
    opts = ap.parse_args(argv)
    opts.skip = set(opts.skip)
    opts.lang = resolve_lang(opts.lang)

    files = collect(opts.inputs)
    if not files:
        ap.error("no supported files found")
    out_dir = Path(opts.out) if opts.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🤖 {VARIANT} · OCR langs: {opts.lang}")
    for src in files:
        dst = (out_dir or src.parent) / f"{src.stem}.anonymised{src.suffix}"
        t0 = time.perf_counter()
        try:
            findings = (process_pdf if src.suffix.lower() == ".pdf" else process_image)(src, dst, opts)
        except Exception as exc:  # noqa: BLE001 - keep going with the other files
            print(f"❌ {src}: {exc}")
            continue
        counts = Counter(f.kind for f in findings)
        summary = ", ".join(f"{k}×{n}" for k, n in counts.most_common()) or "nothing found"
        target = "(dry run)" if opts.dry_run else f"→ {dst}"
        print(f"✅ {src.name} {target}  [{time.perf_counter() - t0:.1f}s]  {summary}")
        if opts.report:
            for f in findings:
                print(f"     p{f.page + 1:<3} {f.kind:<12} {f.source:<7} {mask(f.text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

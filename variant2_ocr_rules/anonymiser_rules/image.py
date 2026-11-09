"""Image input (photos, screenshots): OCR -> rules -> black boxes."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .model import Finding
from .ocr import ocr_words
from .rules import find_sensitive
from .visual import detect_visual

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}


def analyse_image(img: Image.Image, opts, page: int = 0) -> list[Finding]:
    findings = find_sensitive(ocr_words(img, opts.lang), page, opts.skip)
    findings += [f for f in detect_visual(img, opts.faces, opts.codes) if f.kind not in opts.skip]
    for f in findings:
        f.page = page
    return findings


def process_image(src: Path, dst: Path, opts) -> list[Finding]:
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")  # also drops EXIF/GPS on save
    findings = analyse_image(img, opts)
    draw = ImageDraw.Draw(img)
    for f in findings:
        for b in f.boxes:
            b = b.pad(opts.pad).clip(img.width, img.height)
            draw.rectangle([b.x0, b.y0, b.x1, b.y1], fill="black")
    if not opts.dry_run:
        fmt = "JPEG" if dst.suffix.lower() in {".jpg", ".jpeg"} else None
        img.save(dst, fmt, **({"quality": 95} if fmt == "JPEG" else {}))
    return findings

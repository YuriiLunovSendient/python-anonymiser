"""Image input without OCR: every text-like region, face-like blob and code is blacked out."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .heuristics import skin_faces, text_regions
from .model import Finding
from .visual import detect_codes

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}


def analyse_image(img: Image.Image, opts, page: int = 0) -> list[Finding]:
    findings = text_regions(img) if "text-region" not in opts.skip else []
    if opts.faces:
        findings += skin_faces(img)
    if opts.codes:
        findings += detect_codes(img)
    findings = [f for f in findings if f.kind not in opts.skip]
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

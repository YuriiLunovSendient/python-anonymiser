"""PDF input. Digital text comes straight from the PDF; scanned pages and
embedded pictures go through OCR. Redaction is real: the text and image
pixels under each box are removed from the file, not just covered up."""

from __future__ import annotations

from pathlib import Path

import pymupdf
from PIL import Image

from .image import analyse_image
from .model import Box, Finding, Word
from .rules import find_sensitive

DPI = 300
ZOOM = DPI / 72
SCANNED_BELOW_CHARS = 20  # fewer text-layer chars than this -> treat page as a scan
MIN_IMAGE_PT = 40  # ignore tiny embedded images (icons, bullets)


def _render(page: pymupdf.Page) -> Image.Image:
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def analyse_page(page: pymupdf.Page, opts) -> list[Finding]:
    words = [Word(w[4], Box(*w[:4]), ("text", w[5], w[6])) for w in page.get_text("words")]
    findings = find_sensitive(words, page.number, opts.skip)

    scanned = sum(len(w.text) for w in words) < SCANNED_BELOW_CHARS
    if scanned:
        regions = [page.rect]
    else:
        regions = [
            pymupdf.Rect(i["bbox"]) & page.rect
            for i in page.get_image_info()
            if min(pymupdf.Rect(i["bbox"]).width, pymupdf.Rect(i["bbox"]).height) >= MIN_IMAGE_PT
        ]
    full = _render(page) if regions else None
    for r in regions:
        if r.is_empty:
            continue
        crop = full.crop(tuple(int(v * ZOOM) for v in (r.x0, r.y0, r.x1, r.y1)))
        for f in analyse_image(crop, opts, page.number):  # OCR + faces + codes inside the picture
            f.boxes = [b.scale(1 / ZOOM).shift(r.x0, r.y0) for b in f.boxes]
            findings.append(f)
    return findings


def process_pdf(src: Path, dst: Path, opts) -> list[Finding]:
    doc = pymupdf.open(src)
    all_findings: list[Finding] = []
    for page in doc:
        for annot in list(page.annots() or []):  # comments/notes can hold personal data
            page.delete_annot(annot)
        findings = analyse_page(page, opts)
        all_findings += findings
        for f in findings:
            for b in f.boxes:
                b = b.pad(opts.pad / 2)
                page.add_redact_annot(pymupdf.Rect(b.x0, b.y0, b.x1, b.y1), fill=(0, 0, 0))
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_PIXELS,
            graphics=getattr(pymupdf, "PDF_REDACT_LINE_ART_NONE", 0),
        )
    if not opts.dry_run:
        doc.scrub()  # metadata, XMP, attachments, JavaScript, hidden text, links
        doc.save(dst, garbage=4, deflate=True, clean=True)
    doc.close()
    return all_findings

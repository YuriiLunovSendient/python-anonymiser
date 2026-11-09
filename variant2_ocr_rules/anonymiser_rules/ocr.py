"""Local OCR with Tesseract: image -> words with boxes (in the input image's pixels)."""

from __future__ import annotations

import sys
from functools import lru_cache

import pytesseract
from PIL import Image, ImageOps, ImageStat

from .model import Box, Word


@lru_cache(maxsize=1)
def available_langs() -> set[str]:
    try:
        return set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError:
        sys.exit("Tesseract is not installed. On macOS: brew install tesseract tesseract-lang")


def resolve_lang(requested: str) -> str:
    have = available_langs()
    langs = [lang for lang in requested.split("+") if lang in have]
    missing = [lang for lang in requested.split("+") if lang not in have]
    if missing:
        print(f"  ⚠️  Tesseract language pack(s) missing: {', '.join(missing)}", file=sys.stderr)
    return "+".join(langs) or "eng"


def ocr_words(img: Image.Image, lang: str) -> list[Word]:
    """Run Tesseract. Small images (screenshots) are upscaled; dark ones inverted."""
    scale = 2 if max(img.size) < 1600 else 1
    gray = img.convert("L")
    if ImageStat.Stat(gray).mean[0] < 110:  # dark-mode screenshot
        gray = ImageOps.invert(gray)
    if scale != 1:
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.LANCZOS)
    data = pytesseract.image_to_data(gray, lang=lang, config="--psm 3", output_type=pytesseract.Output.DICT)
    words = []
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        if not text or float(data["conf"][i]) < 0:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        box = Box(x, y, x + w, y + h).scale(1 / scale)
        words.append(Word(text, box, (data["block_num"][i], data["par_num"][i], data["line_num"][i])))
    return words

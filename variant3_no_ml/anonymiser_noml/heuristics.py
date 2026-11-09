"""Pure pixel heuristics: no OCR, no trained model of any kind.

Without OCR the program cannot *read* an image, so it cannot tell an email
from a shopping list. The only safe choice is to black out everything that
looks like text. Expect heavy over-redaction; that is the price of zero ML.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from .model import Box, Finding

MAX_DIM = 2000


def _prep(img: Image.Image) -> tuple[np.ndarray, float]:
    arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    s = min(1.0, MAX_DIM / max(arr.shape[:2]))
    if s < 1.0:
        arr = cv2.resize(arr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return arr, s


def text_regions(img: Image.Image) -> list[Finding]:
    """Find text lines: small strokes darker (or lighter) than their surroundings,
    packed into horizontal strips."""
    bgr, s = _prep(img)
    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (3, 3), 0)  # tame camera noise
    h_img, w_img = gray.shape
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    # black-hat = dark text on light background, top-hat = light text on dark (dark mode)
    strokes = cv2.max(cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k), cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k))
    _, edges = cv2.threshold(strokes, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kw = max(9, w_img // 120)  # join letters of a word and words of a line
    joined = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 3)))
    contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if h < 6 or w < 8 or h > max(80, 0.08 * h_img) or w < 0.8 * h:
            continue
        density = cv2.countNonZero(edges[y : y + h, x : x + w]) / float(w * h)
        if density < 0.12:  # sparse = noise/texture, not letters
            continue
        out.append(Finding("text-region", "", [Box(x, y, x + w, y + h).scale(1 / s)], "heuristic"))
    return out


def skin_faces(img: Image.Image) -> list[Finding]:
    """Face-like blobs: skin-coloured, roughly oval, with darker holes (eyes, mouth)."""
    bgr, s = _prep(img)
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 135, 85), (255, 173, 127))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    img_area = mask.shape[0] * mask.shape[1]
    out = []
    for i, c in enumerate(contours):
        if hierarchy[0][i][3] != -1:  # only outer contours
            continue
        area = cv2.contourArea(c)
        x, y, w, h = cv2.boundingRect(c)
        if area < 0.002 * img_area or not 0.8 <= h / w <= 2.2 or area / (w * h) < 0.45:
            continue
        holes, child = 0, hierarchy[0][i][2]
        while child != -1:
            if cv2.contourArea(contours[child]) > 0.002 * area:
                holes += 1
            child = hierarchy[0][child][0]
        if holes >= 1:
            m = 0.2 * w
            out.append(Finding("face?", "", [Box(x - m, y - m * 1.5, x + w + m, y + h + m).scale(1 / s)], "heuristic"))
    return out

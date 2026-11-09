"""Non-text redaction: faces (Haar cascade) and QR codes / barcodes (OpenCV)."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from .model import Box, Finding

MAX_DIM = 1600  # detect on a downscaled copy for speed, then scale boxes back


def _to_bgr(img: Image.Image) -> tuple[np.ndarray, float]:
    arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    s = min(1.0, MAX_DIM / max(arr.shape[:2]))
    if s < 1.0:
        arr = cv2.resize(arr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return arr, s


def _points_box(pts: np.ndarray, s: float) -> Box:
    pts = np.asarray(pts).reshape(-1, 2)
    return Box(*pts.min(axis=0), *pts.max(axis=0)).scale(1 / s)


def detect_faces(img: Image.Image) -> list[Finding]:
    bgr, s = _to_bgr(img)
    gray = cv2.equalizeHist(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    out = []
    for name in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        for x, y, w, h in cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(24, 24)):
            m = 0.15 * w  # grow a little to cover hair / chin
            out.append(Finding("face", "", [Box(x - m, y - m * 1.5, x + w + m, y + h + m).scale(1 / s)], "visual"))
    return out


def detect_codes(img: Image.Image) -> list[Finding]:
    bgr, s = _to_bgr(img)
    out = []
    qr = cv2.QRCodeDetectorAruco() if hasattr(cv2, "QRCodeDetectorAruco") else cv2.QRCodeDetector()
    ok, pts = qr.detectMulti(bgr)
    if ok and pts is not None:
        out += [Finding("qr-code", "", [_points_box(p, s).pad(6)], "visual") for p in pts]
    if hasattr(cv2, "barcode"):
        ok, pts = cv2.barcode.BarcodeDetector().detect(bgr)[:2]
        if ok and pts is not None:
            out += [Finding("barcode", "", [_points_box(p, s).pad(6)], "visual") for p in pts]
    return out


def detect_visual(img: Image.Image, faces: bool, codes: bool) -> list[Finding]:
    return (detect_faces(img) if faces else []) + (detect_codes(img) if codes else [])

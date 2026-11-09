"""QR codes / barcodes with OpenCV's classical (geometry/gradient) detectors.

None of these detectors uses a trained model: the QR detectors look for the
square finder patterns, the barcode detector for regions of parallel gradients.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from .model import Box, Finding

MAX_DIM = 1600


def _to_bgr(img: Image.Image) -> tuple[np.ndarray, float]:
    arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    s = min(1.0, MAX_DIM / max(arr.shape[:2]))
    if s < 1.0:
        arr = cv2.resize(arr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return arr, s


def _points_box(pts: np.ndarray, s: float) -> Box:
    pts = np.asarray(pts).reshape(-1, 2)
    return Box(*pts.min(axis=0), *pts.max(axis=0)).scale(1 / s)


def detect_codes(img: Image.Image) -> list[Finding]:
    bgr, s = _to_bgr(img)
    out = []
    # Two classical QR detectors: finder-pattern scan, and the ArUco-style contour
    # detector, which copes much better with tilted / noisy phone photos.
    for det in (cv2.QRCodeDetector(), cv2.QRCodeDetectorAruco()):
        ok, pts = det.detectMulti(bgr)
        if ok and pts is not None:
            out += [Finding("qr-code", "", [_points_box(p, s).pad(6)], "visual") for p in pts]
    if hasattr(cv2, "barcode"):
        ok, pts = cv2.barcode.BarcodeDetector().detect(bgr)[:2]  # no super-resolution model loaded
        if ok and pts is not None:
            out += [Finding("barcode", "", [_points_box(p, s).pad(6)], "visual") for p in pts]
    return out

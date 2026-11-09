# /// script
# requires-python = ">=3.12"
# dependencies = ["pymupdf>=1.24.10", "pillow>=10.4", "opencv-python-headless>=4.10,<5", "numpy>=1.26"]
# ///
"""Generate test files full of FAKE personal data (EN-UK, EN-US, UK, RU).

    uv run samples/make_samples.py

Writes into samples/input/: digital.pdf, screenshot.png, screenshot_dark.png,
photo.jpg (screenshot made to look like a phone photo) and scanned.pdf.
Faces are not generated — drop your own photos into samples/input/ to test that.
"""

from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "input"
FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def ua_rnokpp(nine: str) -> str:
    w = [-1, 5, 7, 9, 4, 6, 10, 5, 7]
    return nine + str((sum(int(nine[i]) * w[i] for i in range(9)) % 11) % 10)


def ru_inn12(ten: str) -> str:
    n = [int(c) for c in ten]
    n.append(sum(a * b for a, b in zip(n, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])) % 11 % 10)
    n.append(sum(a * b for a, b in zip(n, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])) % 11 % 10)
    return "".join(map(str, n))


EN = [
    "Customer record — CONFIDENTIAL",
    "Full name: Jonathan Smith",
    "Email: jonathan.smith@example.co.uk",
    "Phone: +44 20 7946 0958",
    "Address: 221B Baker Street, London NW1 6XE",
    "Date of birth: 14/03/1985",
    "NI number: AB 12 34 56 C",
    "Card: 4111 1111 1111 1111",
    "IBAN: GB82 WEST 1234 5698 7654 32",
    "Password: Tr0ub4dor&3",
    "Dear Emily Johnson, thank you for your order.",
    "US office: 1600 Pennsylvania Avenue NW, Washington, DC 20500",
    "SSN 123-45-6789, call +1 415 555 2671",
    "Server 192.168.1.24, deploy key ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8",
    "The quarterly report covers sales in March and April.",
]
UK = [
    "Анкета клієнта",
    "ПІБ: Шевченко Тарас Григорович",
    "Ел. пошта: taras.shevchenko@ukr.net",
    "Телефон: +380 67 123 4567",
    "Адреса: м. Київ, вул. Хрещатик, буд. 22, кв. 15",
    f"РНОКПП: {ua_rnokpp('312456789')}",
    "Паспорт: АА 123456",
    "IBAN: UA21 3223 1300 0002 6007 2335 6600 1",
    "Пароль: Kyiv2024!",
    "Дякуємо, Олена Коваленко, за ваше звернення.",
    "Звіт про продажі за березень готовий.",
]
RU = [
    "Карточка клиента",
    "ФИО: Иванов Иван Иванович",
    "Эл. почта: ivanov@mail.ru",
    "Телефон: +7 916 123-45-67",
    "Адрес: г. Москва, ул. Тверская, д. 7, кв. 12",
    f"ИНН: {ru_inn12('7707083893')}",
    "СНИЛС: 112-233-445 95",
    "Паспорт: 45 06 123456",
    "Логин: ivanov_i",
    "С уважением, Мария Петрова",
    "Отчёт о продажах готов.",
]
SCREEN = [
    "Inbox — Sign-in alert",
    "From: Olivia Brown <olivia.brown@gmail.com>",
    "To: James Wilson <j.wilson@outlook.com>",
    "Username: jwilson88",
    "Password: S3cr3t-Pa55!",
    "Mobile: +44 7700 900123",
    "Ship to: 42 Oak Lane, Manchester M1 2AB",
    "Привіт, Андрій Мельник! Ваш номер: +380 50 765 4321",
    "Meeting notes are attached for next week.",
]


def qr_image(text: str, size: int) -> Image.Image:
    qr = cv2.QRCodeEncoder.create().encode(text)
    qr = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    return Image.fromarray(cv2.resize(qr, (size, size), interpolation=cv2.INTER_NEAREST)).convert("RGB")


def draw_screen(lines: list[str], dark: bool) -> Image.Image:
    bg, fg = ((30, 30, 34), (230, 230, 230)) if dark else ((255, 255, 255), (20, 20, 20))
    img = Image.new("RGB", (1280, 120 + 44 * len(lines)), bg)
    d, font = ImageDraw.Draw(img), ImageFont.truetype(FONT, 24)
    d.rectangle([0, 0, img.width, 56], fill=(60, 90, 200))
    d.text((24, 14), "Mail", font=font, fill="white")
    for i, line in enumerate(lines):
        d.text((32, 80 + 44 * i), line, font=font, fill=fg)
    img.paste(qr_image("otpauth://totp/jwilson88?secret=JBSWY3DPEHPK3PXP", 160), (img.width - 200, 70))
    return img


def fake_photo(img: Image.Image) -> Image.Image:
    """Tilt, warp, blur and add noise + uneven light, like a phone photo of a screen."""
    w, h = img.size
    canvas = Image.new("RGB", (w + 200, h + 200), (90, 80, 70))
    canvas.paste(img, (100, 100))
    arr = np.array(canvas.rotate(3, expand=False, fillcolor=(90, 80, 70)))
    src = np.float32([[0, 0], [arr.shape[1], 0], [arr.shape[1], arr.shape[0]], [0, arr.shape[0]]])
    dst = src + np.float32([[30, 10], [-10, 25], [-25, -5], [5, -20]])
    arr = cv2.warpPerspective(arr, cv2.getPerspectiveTransform(src, dst), (arr.shape[1], arr.shape[0]))
    light = np.linspace(0.75, 1.05, arr.shape[1])[None, :, None]
    arr = np.clip(arr * light + np.random.default_rng(1).normal(0, 7, arr.shape), 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.8))


def write_pdf(path: Path, screenshot: Path) -> None:
    doc = pymupdf.open()
    for title, lines in (("English (UK / US)", EN), ("Українська", UK), ("Русский", RU)):
        page = doc.new_page()
        page.insert_font(fontname="arialu", fontfile=FONT)
        page.insert_text((50, 60), title, fontname="arialu", fontsize=16)
        for i, line in enumerate(lines):
            page.insert_text((50, 95 + 20 * i), line, fontname="arialu", fontsize=11)
        if lines is EN:  # a screenshot pasted into the PDF -> needs OCR
            page.insert_image(pymupdf.Rect(50, 430, 545, 430 + 495 * 0.42), filename=str(screenshot))
    doc.set_metadata({"author": "Jonathan Smith", "title": "Customer record"})
    doc.save(path)


def write_scanned_pdf(path: Path, photo: Path) -> None:
    doc = pymupdf.open()
    img = Image.open(photo)
    page = doc.new_page(width=img.width * 0.5, height=img.height * 0.5)
    page.insert_image(page.rect, filename=str(photo))
    doc.save(path)


def main() -> None:
    random.seed(0)
    OUT.mkdir(parents=True, exist_ok=True)
    draw_screen(SCREEN, dark=False).save(OUT / "screenshot.png")
    draw_screen(SCREEN, dark=True).save(OUT / "screenshot_dark.png")
    fake_photo(draw_screen(SCREEN, dark=False)).save(OUT / "photo.jpg", quality=88)
    write_pdf(OUT / "digital.pdf", OUT / "screenshot.png")
    write_scanned_pdf(OUT / "scanned.pdf", OUT / "photo.jpg")
    print("✅ samples written to", OUT)
    for f in sorted(OUT.iterdir()):
        print("   ", f.name)


if __name__ == "__main__":
    main()

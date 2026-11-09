# python-anonymiser

Black out personal data (emails, phones, passwords, names, addresses, IDs,
cards, IBANs, faces, QR codes…) in **PDFs and images**, fully **offline**.
No cloud, no LLM.

Three independent implementations of the same CLI, so the approaches can be
compared side by side:

| | `variant1_local_ml` | `variant2_ocr_rules` | `variant3_no_ml` |
|---|---|---|---|
| "AI" used | Small local models only (Tesseract OCR, spaCy NER, YuNet faces) | Tesseract OCR only | **None** |
| PDF text | PyMuPDF text layer | PyMuPDF text layer | PyMuPDF text layer |
| Image text | Tesseract OCR (eng+ukr+rus) | Tesseract OCR (eng+ukr+rus) | ❌ cannot read. **Every text-like region is blacked out** |
| Detection | Rules + spaCy NER (en/uk/ru) | Rules only | Rules on PDF text; blanket on images |
| Faces | YuNet DNN (Haar fallback) | Haar cascade | Skin-colour + shape heuristic (`face?`) |
| QR / barcodes | OpenCV | OpenCV | OpenCV (classical detectors) |

**Rules** are regexes with checksums (Luhn, IBAN mod-97, UA РНОКПП, RU ИНН,
СНИЛС), `phonenumbers` (GB/US/UA/RU), UK NI / US SSN / postcodes / ZIP+state,
`Label: value` pairs in EN/UK/RU (`Password:`, `ПІБ:`, `ФИО:`, `Адреса:`…),
first-name lists plus neighbouring capitalised words, patronymics, initials,
honorifics, street patterns, and high-entropy tokens (API keys, JWTs).

## Setup

```bash
brew install tesseract tesseract-lang   # OCR engine + language packs (V1, V2)
cd variant2_ocr_rules && uv sync        # likewise for the other variants
```

V1 downloads the 230 KB YuNet face model on first run into
`variant1_local_ml/models/`. Its spaCy models install with `uv sync`.

## Usage

```bash
uv run --project variant2_ocr_rules anonymise invoice.pdf photo.jpg -o out/
uv run --project variant1_local_ml anonymise ~/Desktop/scans --report
uv run --project variant3_no_ml anonymise screenshot.png --dry-run
```

| Option | Meaning |
|---|---|
| `-o DIR` | output folder (default: `<name>.anonymised.<ext>` next to the input) |
| `--report` | list each finding, value partly masked (`j*******m`) |
| `--dry-run` | detect only, write nothing |
| `--skip url ip-address …` | leave these kinds alone |
| `--no-faces`, `--no-codes` | turn off face / QR-barcode redaction |
| `--lang eng+ukr+rus` | Tesseract languages (V1, V2) |
| `--no-ner` | rules only (V1) |
| `--pad 3` | extra margin around each box |

## Compare all three

```bash
uv run samples/make_samples.py   # fake EN/UK/RU documents → samples/input/
./compare.sh                     # or ./compare.sh ~/path/to/your/files
```

## What "redacted" means here

- **PDF**: real redaction. The text under each box is deleted from the file,
  and image pixels under it are wiped. Comments/annotations, metadata, XMP,
  attachments, JavaScript and links are removed too.
- **Images**: black boxes are drawn into the pixels, and the image is saved
  without EXIF (no GPS / camera info).

## Known limits

- No tool finds 100%. A word OCR misses can't be redacted, so always look at the output.
- Names and addresses are the weakest category for V2 (word lists + patterns).
- `Label: value` and postcode rules black out the whole value / line on purpose. Over-redacting is safer than missing something.
- V3 on images removes **all** text. That is the cost of having no OCR.
- Multi-page TIFF/GIF: only the first frame is processed.

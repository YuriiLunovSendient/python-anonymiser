"""Rule-based sensitive-data detection: regexes, checksums, word lists, labels.

No machine learning here. Every detector looks at one line of text at a time
and returns (kind, start, end) character spans; `find_sensitive` maps those
spans back onto the words (and therefore the boxes) they came from.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Callable, Iterable

import phonenumbers

from .model import Box, Finding, Word
from .names_data import AMBIGUOUS_NAMES, FIRST_NAMES, HONORIFICS, STOP_WORDS

Span = tuple[str, int, int]

UP = "A-ZА-ЯІЇЄҐЁ"  # upper-case letters, Latin + Cyrillic
LO = "a-zа-яіїєґёʼ'’\\-"  # lower-case letters + apostrophes/hyphen in names

# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------


def luhn_ok(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def iban_ok(raw: str) -> bool:
    s = raw.replace(" ", "").upper()
    if not 15 <= len(s) <= 34:
        return False
    s = s[4:] + s[:4]
    try:
        return int("".join(str(int(c, 36)) for c in s)) % 97 == 1
    except ValueError:
        return False


def ua_rnokpp_ok(d: str) -> bool:
    """Ukrainian individual tax number (РНОКПП / ІПН), 10 digits."""
    w = [-1, 5, 7, 9, 4, 6, 10, 5, 7]
    return (sum(int(d[i]) * w[i] for i in range(9)) % 11) % 10 == int(d[9])


def ru_inn_ok(d: str) -> bool:
    """Russian INN, 10 (company) or 12 (person) digits."""
    n = [int(c) for c in d]

    def chk(weights: list[int]) -> int:
        return sum(a * b for a, b in zip(n, weights)) % 11 % 10

    if len(n) == 10:
        return chk([2, 4, 10, 3, 5, 9, 4, 6, 8]) == n[9]
    if len(n) == 12:
        return (
            chk([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == n[10]
            and chk([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == n[11]
        )
    return False


def snils_ok(raw: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", raw)]
    if len(d) != 11:
        return False
    s = sum(d[i] * (9 - i) for i in range(9))
    c = s if s < 100 else 0 if s in (100, 101) else s % 101
    return (0 if c == 100 else c) == d[9] * 10 + d[10]


def entropy(s: str) -> float:
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())


# ---------------------------------------------------------------------------
# Plain regex detectors (pattern, kind, optional validator on the match text)
# ---------------------------------------------------------------------------

US_STATES = (
    "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    "MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC"
)

REGEXES: list[tuple[str, re.Pattern, Callable[[str], bool] | None]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), None),
    ("url", re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.I), None),
    (
        "ip-address",
        re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])"),
        None,
    ),
    (
        "card-number",
        re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)"),
        lambda m: 13 <= len(re.sub(r"\D", "", m)) <= 19 and luhn_ok(re.sub(r"\D", "", m)),
    ),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b"), iban_ok),
    ("ssn", re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"), None),
    (
        "ni-number",
        re.compile(r"\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z] ?\d{2} ?\d{2} ?\d{2} ?[A-D]\b"),
        None,
    ),
    (
        "tax-id",
        re.compile(r"(?<!\d)\d{10}(?!\d)|(?<!\d)\d{12}(?!\d)"),
        lambda m: (len(m) == 10 and (ua_rnokpp_ok(m) or ru_inn_ok(m))) or (len(m) == 12 and ru_inn_ok(m)),
    ),
    ("snils", re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}[ \-]\d{2}(?!\d)"), snils_ok),
    ("passport", re.compile(rf"(?<![\w])[{UP}]{{2}} ?\d{{6}}(?!\d)"), None),  # UA booklet "АА 123456"
    ("passport", re.compile(r"(?<!\d)\d{2} \d{2} \d{6}(?!\d)"), None),  # RU "45 06 123456"
    ("jwt", re.compile(r"eyJ[\w\-]+\.[\w\-]+\.[\w\-]+"), None),
    ("secret", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), None),
    ("secret", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), None),
    ("secret", re.compile(r"\bxox[abprs]-[\w\-]{10,}"), None),
    ("secret", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), None),
]

# ---------------------------------------------------------------------------
# Addresses (whole rest-of-line once something address-like starts)
# ---------------------------------------------------------------------------

EN_STREET = re.compile(
    r"(?<![\w])\d{1,5}[A-Za-z]?,?[ ]+(?:[A-Z][\w'.\-]*[ ]+){0,4}"
    r"(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Drive|Dr|Boulevard|Blvd|Close|Court|Ct|"
    r"Way|Place|Pl|Square|Sq|Terrace|Crescent|Cres|Gardens|Grove|Hill|Park|Row|Mews|"
    r"Parkway|Pkwy|Highway|Hwy|Circle|Cir)\b\.?"
)
EN_UNIT = re.compile(r"\b(?:Flat|Apt|Apartment|Suite|Unit|Floor|PO Box|P\.O\. Box)[ ]+\w+", re.I)
CYR_STREET = re.compile(
    r"(?<![\w])(?:вул|вулиця|ул|улица|просп|проспект|пров|провулок|пер|переулок|бул|"
    r"бульвар|пл|площа|площадь|шосе|шоссе|наб|набережна|набережная|мкр|мікрорайон|"
    r"микрорайон)\.?[ ]+\S+",
    re.I,
)
CYR_HOUSE = re.compile(r"(?<![\w])(?:буд|будинок|дом|д|кв|квартира|корп|корпус)\.?[ ]*\d+\w*", re.I)
CYR_CITY = re.compile(rf"(?<![\w])(?:м|г|с|смт|пгт)\.[ ]?[{UP}][{LO}]+")
UK_POSTCODE = re.compile(r"\b(?:GIR ?0AA|[A-PR-UWYZ][A-HK-Y]?\d[A-Z\d]? ?\d[ABD-HJLNP-UW-Z]{2})\b")
US_ZIP = re.compile(rf"\b(?:{US_STATES}),?[ ]+\d{{5}}(?:-\d{{4}})?\b")


def detect_addresses(line: str) -> list[Span]:
    spans: list[Span] = []
    # A street, city or postcode means the rest of the line is address.
    for rx in (EN_STREET, CYR_STREET, CYR_CITY, EN_UNIT):
        for m in rx.finditer(line):
            spans.append(("address", m.start(), len(line)))
    for m in CYR_HOUSE.finditer(line):
        spans.append(("address", m.start(), m.end()))
    for rx in (UK_POSTCODE, US_ZIP):
        if rx.search(line):  # postcode -> this is an address line, take all of it
            spans.append(("address", 0, len(line)))
    return spans


# ---------------------------------------------------------------------------
# "Label: value" pairs (password: ..., Ім'я: ..., ФИО: ...)
# ---------------------------------------------------------------------------

LABELS: dict[str, list[str]] = {
    "password": [
        "password", "passwd", "pwd", "pass", "passcode", "pin", "pin code", "secret",
        "token", "api key", "api_key", "apikey", "access key", "private key",
        "client secret", "secret key", "пароль", "пін", "пін-код", "пин", "пин-код",
        "секрет", "токен", "ключ",
    ],
    "username": ["username", "user name", "user id", "userid", "login", "логін", "логин", "користувач", "пользователь"],
    "name": [
        "name", "full name", "first name", "last name", "surname", "given name",
        "family name", "middle name", "patronymic", "ім'я", "ім’я", "імʼя", "імя",
        "прізвище", "по батькові", "піб", "имя", "фамилия", "отчество", "фио",
    ],
    "address": [
        "address", "home address", "residential address", "street", "адреса",
        "адреса проживання", "місце проживання", "адрес", "место жительства",
    ],
    "dob": ["date of birth", "dob", "birth date", "birthday", "дата народження", "дата рождения"],
    "id-number": [
        "passport", "passport no", "passport number", "id number", "id no",
        "licence number", "license number", "driver's license", "driving licence",
        "ssn", "social security number", "ni number", "national insurance number",
        "nino", "tax id", "tin", "ipn", "рнокпп", "іпн", "інн", "инн", "снилс",
        "паспорт", "номер паспорта", "номер паспорту", "серія", "серия",
    ],
    "phone": ["phone", "tel", "telephone", "mobile", "cell", "телефон", "тел", "моб"],
    "account": [
        "account number", "account no", "sort code", "card number", "cvv", "cvc",
        "expiry", "номер картки", "номер карты", "рахунок", "счет", "счёт",
    ],
}


def _label_alt(words: Iterable[str]) -> str:
    return "|".join(re.escape(w).replace(r"\ ", r"[ _]?") for w in sorted(words, key=len, reverse=True))


LABEL_VALUE = {
    kind: re.compile(rf"(?<![\w])(?:{_label_alt(ws)})[ ]*(?:\([^)]*\))?[ ]*[:=：][ ]*(\S.*)$", re.I)
    for kind, ws in LABELS.items()
}
LABEL_ONLY = {
    kind: re.compile(rf"^[ ]*(?:{_label_alt(ws)})[ ]*[:=：]?[ ]*$", re.I) for kind, ws in LABELS.items()
}


def detect_labels(line: str) -> list[Span]:
    spans = []
    for kind, rx in LABEL_VALUE.items():
        for m in rx.finditer(line):
            spans.append((kind, m.start(1), m.end(1)))
    return spans


def label_only_kind(line: str) -> str | None:
    for kind, rx in LABEL_ONLY.items():
        if rx.match(line):
            return kind
    return None


# ---------------------------------------------------------------------------
# Names (word lists + neighbours, patronymics, initials, honorifics)
# ---------------------------------------------------------------------------

PATRONYMIC = re.compile(rf"^[{UP}][{LO}]+(?:ович|евич|ьович|йович|івна|ївна|овна|евна|ична)$")
INITIALS_FIRST = re.compile(rf"(?<![\w.])[{UP}]\.[ ]?(?:[{UP}]\.[ ]?)?[{UP}][{LO}]+")  # J. Smith / Т.Г. Шевченко
INITIALS_AFTER = re.compile(rf"(?<![\w])[{UP}][{LO}]+[ ][{UP}]\.[ ]?(?:[{UP}]\.)?")  # Шевченко Т.Г.


def _clean(tok: str) -> str:
    return tok.strip(".,;:!?()[]{}\"«»“”")


def _is_cap_word(tok: str) -> bool:
    t = _clean(tok)
    return (
        len(t) >= 2
        and t[0].isupper()
        and all(c.isalpha() or c in "'’ʼ-" for c in t)
        and t.lower().strip("'’ʼ") not in STOP_WORDS
    )


def _ends_phrase(tok: str) -> bool:
    return tok[-1:] in ",:;.!?" and not re.fullmatch(rf"[{UP}]\.", tok)  # "J." is an initial, not an end


def detect_names(tokens: list[str]) -> list[tuple[int, int]]:
    """Return inclusive token ranges (first, last) that look like a person's name."""
    hits: list[tuple[int, int]] = []
    n = len(tokens)
    for i, tok in enumerate(tokens):
        t = _clean(tok)
        low = t.lower()
        anchor = False
        if t and t[0].isupper() and low in FIRST_NAMES:
            anchor = True
            if low in AMBIGUOUS_NAMES:
                anchor = (i + 1 < n and _is_cap_word(tokens[i + 1])) or (i > 0 and _is_cap_word(tokens[i - 1]))
        elif PATRONYMIC.match(t):
            anchor = True
        elif low.rstrip(".") in HONORIFICS and i + 1 < n and _is_cap_word(tokens[i + 1]):
            hits.append((i + 1, i + 2 if i + 2 < n and _is_cap_word(tokens[i + 2]) else i + 1))
            continue
        if not anchor:
            continue
        lo, hi = i, i
        # Grow to capitalised neighbours (surname, patronymic), never across punctuation.
        while hi + 1 < n and hi - i < 2 and not _ends_phrase(tokens[hi]) and _is_cap_word(tokens[hi + 1]):
            hi += 1
        while lo - 1 >= 0 and i - lo < 2 and not _ends_phrase(tokens[lo - 1]) and _is_cap_word(tokens[lo - 1]):
            lo -= 1
        hits.append((lo, hi))
    return hits


# ---------------------------------------------------------------------------
# Line indexing + the main entry point
# ---------------------------------------------------------------------------


def group_lines(words: list[Word]) -> list[list[Word]]:
    lines: dict[tuple, list[Word]] = {}
    for w in words:
        lines.setdefault(w.line, []).append(w)
    return list(lines.values())


def _offsets(tokens: list[str]) -> tuple[str, list[tuple[int, int]]]:
    pos, spans = 0, []
    for t in tokens:
        spans.append((pos, pos + len(t)))
        pos += len(t) + 1
    return " ".join(tokens), spans


PHONE_REGIONS = ("GB", "US", "UA", "RU")


def detect_line(line: str, tokens: list[str], offsets: list[tuple[int, int]]) -> list[Span]:
    spans: list[Span] = []
    for kind, rx, valid in REGEXES:
        for m in rx.finditer(line):
            if valid is None or valid(m.group(0)):
                spans.append((kind, m.start(), m.end()))
    for region in PHONE_REGIONS:
        try:
            for m in phonenumbers.PhoneNumberMatcher(line, region):
                spans.append(("phone", m.start, m.end))
        except Exception:  # noqa: BLE001 - library can choke on odd OCR text
            pass
    spans += detect_addresses(line)
    spans += detect_labels(line)
    for rx in (INITIALS_FIRST, INITIALS_AFTER):
        for m in rx.finditer(line):
            spans.append(("name", m.start(), m.end()))
    for lo, hi in detect_names(tokens):
        spans.append(("name", offsets[lo][0], offsets[hi][1]))
    for (s, e), tok in zip(offsets, tokens):  # long random-looking strings = keys/tokens
        t = _clean(tok)
        if (
            len(t) >= 24
            and "@" not in t
            and not t.lower().startswith(("http", "www"))
            and any(c.isdigit() for c in t)
            and any(c.isalpha() for c in t)
            and entropy(t) >= 3.5
        ):
            spans.append(("secret", s, e))
    return spans


def find_sensitive(words: list[Word], page: int = 0, skip: set[str] | None = None) -> list[Finding]:
    skip = skip or set()
    findings: list[Finding] = []
    lines = group_lines(words)
    pending_kind: str | None = None  # set when a line is just a label like "Password:"
    for line_words in lines:
        tokens = [w.text for w in line_words]
        text, offsets = _offsets(tokens)
        spans = detect_line(text, tokens, offsets)
        if pending_kind:
            spans.append((pending_kind, 0, len(text)))
        pending_kind = label_only_kind(text)
        for kind, s, e in spans:
            if kind in skip or e <= s:
                continue
            hit = [w for w, (ws, we) in zip(line_words, offsets) if ws < e and we > s]
            if not hit:
                continue
            box = hit[0].box
            for w in hit[1:]:
                box = box.union(w.box)
            findings.append(Finding(kind, text[s:e], [box], "rule", page))
    return dedupe(findings)


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    for f in findings:
        key = (f.kind, f.page, tuple((round(b.x0), round(b.y0), round(b.x1), round(b.y1)) for b in f.boxes))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def boxes_of(findings: list[Finding]) -> list[Box]:
    return [b for f in findings for b in f.boxes]

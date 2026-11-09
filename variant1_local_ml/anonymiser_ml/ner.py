"""Local named-entity recognition with spaCy (EN / UK / RU small models).

Runs fully offline once the models are installed. Adds what rules are bad
at: names that aren't in the word lists, and street / place names.
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache

from .model import Finding, Word
from .rules import group_lines

MODELS = {"en": "en_core_web_sm", "uk": "uk_core_news_sm", "ru": "ru_core_news_sm"}
NAME_LABELS = {"PERSON", "PER"}
PLACE_LABELS = {"FAC", "GPE", "LOC"}
EXCLUDE = ["parser", "lemmatizer", "attribute_ruler", "morphologizer", "tagger", "senter"]

LATIN = re.compile(r"[A-Za-z]")
CYRILLIC = re.compile(r"[А-Яа-яІіЇїЄєҐґЁё]")
UK_ONLY = re.compile(r"[ІіЇїЄєҐґ]")
RU_ONLY = re.compile(r"[ЫыЭэЪъЁё]")


@lru_cache(maxsize=None)
def load(lang: str):
    import spacy

    try:
        return spacy.load(MODELS[lang], exclude=EXCLUDE)
    except OSError:
        print(f"  ⚠️  spaCy model {MODELS[lang]} not installed; NER skipped for '{lang}'", file=sys.stderr)
        return None


def line_lang(text: str, cyr_default: str) -> str | None:
    lat, cyr = len(LATIN.findall(text)), len(CYRILLIC.findall(text))
    if lat + cyr < 3:
        return None
    if lat >= cyr:
        return "en"
    uk, ru = len(UK_ONLY.findall(text)), len(RU_ONLY.findall(text))
    return "uk" if uk > ru else "ru" if ru > uk else cyr_default


def find_entities(words: list[Word], page: int = 0, skip: set[str] | None = None) -> list[Finding]:
    """Group lines by language, run that language's model, map entities back to word boxes."""
    skip = skip or set()
    lines = group_lines(words)
    all_text = " ".join(w.text for w in words)
    cyr_default = "uk" if len(UK_ONLY.findall(all_text)) >= len(RU_ONLY.findall(all_text)) else "ru"

    by_lang: dict[str, list[list[Word]]] = {}
    for line in lines:
        lang = line_lang(" ".join(w.text for w in line), cyr_default)
        if lang:
            by_lang.setdefault(lang, []).append(line)

    findings: list[Finding] = []
    for lang, lang_lines in by_lang.items():
        nlp = load(lang)
        if nlp is None:
            continue
        # One text per language: lines separated by "\n", each word's char span remembered.
        parts, index, pos = [], [], 0
        for li, line in enumerate(lang_lines):
            for w in line:
                index.append((pos, pos + len(w.text), li, w))
                parts.append(w.text + " ")
                pos += len(w.text) + 1
            parts.append("\n")
            pos += 1
        doc = nlp("".join(parts))
        for ent in doc.ents:
            if ent.label_ in NAME_LABELS:
                kind = "name"
            elif ent.label_ in PLACE_LABELS:
                kind = "address"
            else:
                continue
            if kind in skip:
                continue
            script = LATIN if lang == "en" else CYRILLIC
            if not script.search(ent.text):  # e.g. the EN model tagging a Cyrillic word
                continue
            per_line: dict[int, list[Word]] = {}
            for s, e, li, w in index:
                if s < ent.end_char and e > ent.start_char:
                    per_line.setdefault(li, []).append(w)
            for li, hit in per_line.items():
                line_text = " ".join(w.text for w in lang_lines[li])
                if ent.label_ in {"GPE", "LOC"} and not any(c.isdigit() for c in line_text):
                    continue  # a city/country on its own isn't an address; one next to numbers is
                box = hit[0].box
                for w in hit[1:]:
                    box = box.union(w.box)
                findings.append(Finding(kind, ent.text, [box], f"ner:{lang}", page))
    return findings

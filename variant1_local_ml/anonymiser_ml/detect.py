"""Variant 1 text detection = rules + local NER, merged."""

from __future__ import annotations

from .model import Finding, Word
from .ner import find_entities
from .rules import dedupe, find_sensitive


def detect_text(words: list[Word], page: int, skip: set[str], use_ner: bool = True) -> list[Finding]:
    findings = find_sensitive(words, page, skip)
    if use_ner and words:
        findings += find_entities(words, page, skip)
    return dedupe(findings)

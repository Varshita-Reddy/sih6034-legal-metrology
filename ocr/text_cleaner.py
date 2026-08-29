"""
text_cleaner.py
----------------
Context-aware cleanup of raw OCR text for packaged-commodity labels.

Important design rule (per project notes, section 18):
    We must NOT blindly replace look-alike characters everywhere.
    "FOOD" must stay "FOOD" — we only correct O/0, I/1, S/5, B/8 style
    confusions *inside* fields where we have strong contextual evidence,
    such as currency amounts, quantities, and dates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


# --------------------------------------------------------------------------- #
# Character-confusion maps, applied only within a matched numeric context
# --------------------------------------------------------------------------- #

_LETTER_TO_DIGIT = {
    "O": "0", "o": "0",
    "I": "1", "l": "1", "|": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
    "G": "6",
    "T": "7",
}


def _fix_digits_in_number(match: re.Match) -> str:
    """Replace letter-lookalikes with digits inside a matched numeric token only."""
    token = match.group(0)
    fixed = "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in token)
    return fixed


# --------------------------------------------------------------------------- #
# Field-specific cleaners
# --------------------------------------------------------------------------- #

# Currency: ₹ or "Rs" / "Rs." followed by a number that may contain OCR noise.
# \b before Rs/INR is required — without it, "Rs" matches the "rs" hiding
# inside ordinary words like "characters", producing corrupted output.
# Found via real-world testing on a Lay's chips label.
_CURRENCY_PATTERN = re.compile(
    r"(?:₹|\bRs\b\.?|\bINR\b)\s*([0-9OoIlSBZGT|.,]+)", re.IGNORECASE
)

# Quantity: a number followed by a unit (g, kg, ml, l, gm, gms).
_QUANTITY_PATTERN = re.compile(
    r"([0-9OoIlSBZGT|.,]+)\s*(g|gm|gms|kg|ml|l|litre|liter|litres)\b",
    re.IGNORECASE,
)

# Dates: dd/mm/yyyy, mm/yyyy, or dd-mm-yyyy style, allowing OCR noise on digits.
_DATE_PATTERN = re.compile(
    r"\b([0-9OoIlSBZGT|]{1,2}[/\-][0-9OoIlSBZGT|]{1,2}(?:[/\-][0-9OoIlSBZGT|]{2,4})?)\b"
)


def _has_real_digit(s: str) -> bool:
    """
    True if `s` contains at least one genuine 0-9 digit.

    This is the key safety check: a real OCR misread of a number always
    keeps SOME actual digit characters mixed in with the misread letters
    (e.g. "5OO" from "500"). A plain English word never does. Without this
    check, words built entirely from digit-lookalike letters — "tool",
    "cool", "bolt", "silt" (O/I/L/S/B/Z/G/T, matched case-insensitively)
    — get swallowed whole and corrupted. Found via real-world testing on
    a spice-packet label where "cool" was corrupted into "c00l".
    """
    return any(ch.isdigit() for ch in s)


def clean_currency(text: str) -> str:
    def repl(m: re.Match) -> str:
        full = m.group(0)
        amount = m.group(1)
        if not _has_real_digit(amount):
            return full
        fixed_amount = "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in amount)
        return full.replace(amount, fixed_amount)

    return _CURRENCY_PATTERN.sub(repl, text)


def clean_quantity(text: str) -> str:
    def repl(m: re.Match) -> str:
        full = m.group(0)
        number = m.group(1)
        if not _has_real_digit(number):
            return full
        fixed_number = "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in number)
        return full.replace(number, fixed_number)

    return _QUANTITY_PATTERN.sub(repl, text)


def clean_dates(text: str) -> str:
    def repl(m: re.Match) -> str:
        token = m.group(1)
        fixed = "".join(_LETTER_TO_DIGIT.get(ch, ch) for ch in token)
        return m.group(0).replace(token, fixed)

    return _DATE_PATTERN.sub(repl, text)


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- #
# Master cleaning function
# --------------------------------------------------------------------------- #

@dataclass
class CleanResult:
    original: str
    cleaned: str
    changed: bool


def clean_text(raw_text: str) -> CleanResult:
    """
    Apply context-aware corrections to a block of raw OCR text.
    Plain words (e.g. "FOOD", "BRAND") are left untouched because none of
    the field-specific patterns match them.
    """
    text = raw_text
    text = clean_currency(text)
    text = clean_quantity(text)
    text = clean_dates(text)
    text = normalize_whitespace(text)

    return CleanResult(original=raw_text, cleaned=text, changed=(text != raw_text.strip()))


def clean_detections(detections: List[dict]) -> List[dict]:
    """
    Apply clean_text() to each individual OCR detection's "text" field
    (as produced by ocr_engine.OCREngine.run), preserving bbox/confidence.
    """
    cleaned = []
    for det in detections:
        result = clean_text(det["text"])
        new_det = dict(det)
        new_det["text"] = result.cleaned
        new_det["was_corrected"] = result.changed
        cleaned.append(new_det)
    return cleaned


if __name__ == "__main__":
    samples = [
        "MRP ₹5O",
        "NET QUANTlTY 1OO g",
        "MFG O6/2O26",
        "FOOD PRODUCTS OF INDIA",  # should remain unchanged
        "BEST BEFORE 12 MONTHS",
    ]
    for s in samples:
        r = clean_text(s)
        marker = "changed" if r.changed else "unchanged"
        print(f"{s!r:35} -> {r.cleaned!r:35} [{marker}]")

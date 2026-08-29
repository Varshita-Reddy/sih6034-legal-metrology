"""
field_extractor.py
------------------

Extracts fields required by the Legal Metrology compliance pipeline.

Required fields:
    - mrp
    - net_quantity
    - manufacturing_date
    - best_before
    - manufacturer

Optional metadata:
    - product_name
    - packaging_date

IMPORTANT DESIGN RULES
----------------------

1. This module NEVER decides compliance.
2. OCR confidence != field correctness.
3. Product name is NEVER inferred merely from large/first OCR text.
4. Packaging date is NEVER treated as manufacturing date.
5. Missing values remain missing instead of being guessed.
6. Manufacturer/Marketer values may span multiple OCR detections.
7. Cropped "BEFORE 11 MONTHS..." can be recognized as best-before,
   but with lower reliability than an explicit "BEST BEFORE" label.
8. A value belonging to another field must NEVER be stolen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import List, Optional, Dict, Any


# ============================================================================
# FIELD RESULT CONTRACT
# ============================================================================

VALID_STATES = (
    "present",
    "partial",
    "uncertain",
    "missing",
)


@dataclass
class FieldResult:
    field_name: str
    value: Optional[str]
    state: str
    reliability: float
    source_detections: List[Dict[str, Any]] = dc_field(
        default_factory=list
    )
    note: str = ""
    parsed: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            "field": self.field_name,
            "value": self.value,
            "parsed": self.parsed,
            "state": self.state,
            "reliability": round(
                max(0.0, min(1.0, self.reliability)),
                3,
            ),
            "note": self.note,
            "source_text": [
                d.get("text")
                for d in self.source_detections
            ],
        }


# ============================================================================
# REGEX HELPERS
# ============================================================================

# ---------------------------------------------------------------------------
# MRP
# ---------------------------------------------------------------------------

# Supports:
#   MRP
#   M.R.P.
#   M R P
#   MRP (incl. of all taxes)
#
MRP_KEYWORD = re.compile(
    r"\bM\s*\.?\s*R\s*\.?\s*P\s*\.?\b",
    re.IGNORECASE,
)

MRP_VALUE = re.compile(
    r"(?:₹|Rs\.?|INR)"
    r"\s*"
    r"([0-9]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# NET QUANTITY
# ---------------------------------------------------------------------------

NET_QUANTITY_KEYWORD = re.compile(
    r"\b("
    r"net\s*(?:qty|quantity|weight)"
    r"|n\s*\.?\s*qty"
    r")\b",
    re.IGNORECASE,
)

NET_QUANTITY_VALUE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)"
    r"\s*"
    r"(g|gm|gms|kg|ml|l|litre|liter|litres)"
    r"\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# MANUFACTURING DATE
# ---------------------------------------------------------------------------

MANUFACTURING_KEYWORD = re.compile(
    r"\b("
    r"mfg"
    r"|mfd"
    r"|manufacturing"
    r"|manufactured"
    r")"
    r"(?:\s*date)?"
    r"\b",
    re.IGNORECASE,
)

DATE_VALUE = re.compile(
    r"("
    r"[0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}"
    r"|"
    r"[0-9]{1,2}[\/\-\.][0-9]{4}"
    r")"
)


# ---------------------------------------------------------------------------
# PACKAGING DATE
# ---------------------------------------------------------------------------

PACKAGING_DATE_KEYWORD = re.compile(
    r"\b("
    r"pkd"
    r"|packed"
    r"|packaging"
    r"|packing"
    r")"
    r"(?:\s*date)?"
    r"\b",
    re.IGNORECASE,
)

PACKAGING_DATE_VALUE = re.compile(
    r"\b("
    r"january|february|march|april|may|june|"
    r"july|august|september|october|november|december"
    r"|"
    r"[0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}"
    r"|"
    r"[0-9]{1,2}[\/\-\.][0-9]{4}"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# BEST BEFORE
# ---------------------------------------------------------------------------

BEST_BEFORE_KEYWORD = re.compile(
    r"\bbest\s*before\b",
    re.IGNORECASE,
)

BEST_BEFORE_VALUE = re.compile(
    r"("
    # Numeric duration
    r"[0-9]+\s*(?:months?|years?|days?)"
    r"(?:\s*from\s*"
    r"(?:mfg|manufactur\w*|packing|packaging|"
    r"date\s+of\s+packing))?"
    r"|"
    # Spelled-out duration
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve)"
    r"\s*(?:months?|years?|days?)"
    r"(?:\s*from\s*"
    r"(?:mfg|manufactur\w*|packing|packaging|"
    r"date\s+of\s+packing))?"
    r"|"
    # Full date
    r"[0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}"
    r"|"
    # Month/year
    r"[0-9]{1,2}[\/\-\.][0-9]{4}"
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# CROPPED BEST-BEFORE FALLBACK
# ---------------------------------------------------------------------------

# Example:
#   BEFORE 11 MONTHS FROM THE DATE OF PACKING
#
# We require a duration after "BEFORE".
#
CROPPED_BEST_BEFORE_VALUE = re.compile(
    r"\bbefore\b"
    r"\s+"
    r"("
    r"[0-9]+\s*(?:months?|years?|days?)"
    r"|"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve)"
    r"\s*(?:months?|years?|days?)"
    r")"
    r"(?:\s+from\s+"
    r"(?:the\s+)?"
    r"(?:date\s+of\s+)?"
    r"(?:mfg|manufactur\w*|packing|packaging)"
    r")?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# MANUFACTURER / MARKETER
# ---------------------------------------------------------------------------

MANUFACTURER_KEYWORD = re.compile(
    r"\b("
    r"packed\s*by"
    r"|mfd\s*\.?\s*by"
    r"|manufactured\s*by"
    r"|manufactured\s*for"
    r"|marketed\s*by"
    r"|marketed\s*for"
    r"|manufactured\s*&\s*marketed\s*by"
    r")\b",
    re.IGNORECASE,
)

MANUFACTURER_VALUE = re.compile(
    r"(?:"
    r"packed\s*by"
    r"|mfd\s*\.?\s*by"
    r"|manufactured\s*by"
    r"|manufactured\s*for"
    r"|marketed\s*by"
    r"|marketed\s*for"
    r"|manufactured\s*&\s*marketed\s*by"
    r")"
    r"\s*[:\-]?\s*"
    r"(.+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# PRODUCT NAME
# ---------------------------------------------------------------------------

PRODUCT_NAME_KEYWORD = re.compile(
    r"\b("
    r"product\s*name"
    r"|product"
    r")"
    r"\s*[:\-]",
    re.IGNORECASE,
)

PRODUCT_NAME_VALUE = re.compile(
    r"\b(?:product\s*name|product)"
    r"\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)


# ============================================================================
# FIELD PATTERNS
# ============================================================================

FIELD_PATTERNS = {
    "mrp": {
        "keyword": MRP_KEYWORD,
        "value": MRP_VALUE,
    },
    "net_quantity": {
        "keyword": NET_QUANTITY_KEYWORD,
        "value": NET_QUANTITY_VALUE,
    },
    "manufacturing_date": {
        "keyword": MANUFACTURING_KEYWORD,
        "value": DATE_VALUE,
    },
    "best_before": {
        "keyword": BEST_BEFORE_KEYWORD,
        "value": BEST_BEFORE_VALUE,
    },
    "manufacturer": {
        "keyword": MANUFACTURER_KEYWORD,
        "value": MANUFACTURER_VALUE,
    },
}


# ============================================================================
# STRUCTURED VALUE PARSERS
# ============================================================================

_UNIT_ALIASES = {
    "g": "g",
    "gm": "g",
    "gms": "g",
    "kg": "kg",
    "ml": "ml",
    "l": "l",
    "litre": "l",
    "liter": "l",
    "litres": "l",
}


_WORD_TO_NUMBER = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


_DURATION_RE = re.compile(
    r"(?P<amount>"
    r"[0-9]+|one|two|three|four|five|six|seven|eight|nine|"
    r"ten|eleven|twelve"
    r")"
    r"\s*"
    r"(?P<unit>months?|years?|days?)"
    r"(?:\s*from\s*"
    r"(?P<ref>"
    r"mfg"
    r"|manufactur\w*"
    r"|packing"
    r"|packaging"
    r"|date\s+of\s+packing"
    r"))?",
    re.IGNORECASE,
)


_DATE_RE = re.compile(
    r"(?P<a>[0-9]{1,2})"
    r"[\/\-\.]"
    r"(?P<b>[0-9]{1,2})"
    r"[\/\-\.]"
    r"(?P<c>[0-9]{2,4})"
    r"|"
    r"(?P<mm>[0-9]{1,2})"
    r"[\/\-\.]"
    r"(?P<yyyy>[0-9]{4})",
)


def _parse_quantity(
    raw_value: str,
    source_text: str,
) -> Optional[Dict[str, Any]]:
    match = re.search(
        re.escape(raw_value)
        + r"\s*"
        + r"(g|gm|gms|kg|ml|l|litre|liter|litres)\b",
        source_text,
        re.IGNORECASE,
    )

    if not match:
        return None

    try:
        amount = float(raw_value)
    except ValueError:
        return None

    unit = _UNIT_ALIASES.get(
        match.group(1).lower()
    )

    return {
        "amount": amount,
        "unit": unit,
    }


def _parse_currency(
    raw_value: str,
) -> Optional[Dict[str, Any]]:
    try:
        amount = float(raw_value)
    except ValueError:
        return None

    return {
        "amount": amount,
        "currency": "INR",
    }


def _parse_date(
    raw_value: str,
) -> Optional[Dict[str, Any]]:
    match = _DATE_RE.fullmatch(
        raw_value.strip()
    )

    if not match:
        return None

    # DD/MM/YYYY
    if match.group("c"):
        day = int(match.group("a"))
        month = int(match.group("b"))
        year = int(match.group("c"))

        if year < 100:
            year += 2000

        try:
            datetime(
                year,
                month,
                day,
            )
        except ValueError:
            return None

        return {
            "day": day,
            "month": month,
            "year": year,
        }

    # MM/YYYY
    if match.group("yyyy"):
        month = int(match.group("mm"))
        year = int(match.group("yyyy"))

        if not (1 <= month <= 12):
            return None

        return {
            "month": month,
            "year": year,
        }

    return None


def _parse_duration_or_date(
    raw_value: str,
) -> Optional[Dict[str, Any]]:
    match = _DURATION_RE.search(
        raw_value
    )

    if match:
        amount_raw = match.group(
            "amount"
        ).lower()

        amount = _WORD_TO_NUMBER.get(
            amount_raw
        )

        if amount is None:
            try:
                amount = int(amount_raw)
            except ValueError:
                return None

        unit = (
            match.group("unit")
            .lower()
            .rstrip("s")
            + "s"
        )

        ref_raw = (
            match.group("ref")
            or ""
        ).lower()

        reference = None

        if ref_raw.startswith(
            (
                "mfg",
                "manufactur",
            )
        ):
            reference = "manufacturing"

        elif ref_raw.startswith(
            (
                "packing",
                "packaging",
            )
        ):
            reference = "packing"

        elif "date of packing" in ref_raw:
            reference = "packing"

        result = {
            "amount": amount,
            "unit": unit,
        }

        if reference:
            result["reference"] = reference

        return result

    return _parse_date(
        raw_value
    )


# ============================================================================
# PARSER MAP
# ============================================================================

_PARSERS = {
    "mrp": lambda value, source_text:
        _parse_currency(value),

    "net_quantity": lambda value, source_text:
        _parse_quantity(
            value,
            source_text,
        ),

    "manufacturing_date": lambda value, source_text:
        _parse_date(value),

    "best_before": lambda value, source_text:
        _parse_duration_or_date(value),

    "manufacturer": lambda value, source_text:
        None,

    "product_name": lambda value, source_text:
        None,

    "packaging_date": lambda value, source_text:
        _parse_date(value),
}


def _parse_field_value(
    field_name: str,
    value: Optional[str],
    source_text: str,
) -> Optional[Dict[str, Any]]:
    if value is None:
        return None

    parser = _PARSERS.get(
        field_name
    )

    if parser is None:
        return None

    try:
        return parser(
            value,
            source_text,
        )
    except Exception:
        return None


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _clean_text(
    text: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def _find_value(
    text: str,
    pattern: re.Pattern,
    search_from: int = 0,
) -> Optional[str]:
    match = pattern.search(
        text,
        search_from,
    )

    if match:
        return match.group(1).strip()

    return None


def _ocr_confidence(
    detection: Dict[str, Any],
) -> float:
    try:
        value = float(
            detection.get(
                "confidence",
                0.0,
            )
        )
    except Exception:
        value = 0.0

    return max(
        0.0,
        min(1.0, value),
    )


# ============================================================================
# STRONG CROSS-FIELD PROTECTION
# ============================================================================

# These patterns identify text that should not be interpreted as another
# field's value when the text clearly belongs to a different field.

OTHER_FIELD_KEYWORDS = {
    "mrp": re.compile(
        r"\b("
        r"net\s*(?:qty|quantity|weight)"
        r"|n\s*\.?\s*qty"
        r"|mfg"
        r"|mfd"
        r"|manufactur\w*"
        r"|best\s*before"
        r"|pkd"
        r"|packed"
        r"|packing"
        r"|packaging"
        r"|marketed\s*by"
        r"|marketed\s*for"
        r"|packed\s*by"
        r"|manufactured\s*by"
        r"|manufactured\s*for"
        r")\b",
        re.IGNORECASE,
    ),

    "net_quantity": re.compile(
        r"\b("
        r"m\.?\s*r\.?\s*p\.?"
        r"|rs\.?"
        r"|inr"
        r"|mfg"
        r"|mfd"
        r"|manufactur\w*"
        r"|best\s*before"
        r"|pkd"
        r"|packed"
        r"|packing"
        r"|packaging"
        r"|marketed\s*by"
        r"|marketed\s*for"
        r"|packed\s*by"
        r"|manufactured\s*by"
        r"|manufactured\s*for"
        r")\b",
        re.IGNORECASE,
    ),

    "manufacturing_date": re.compile(
        r"\b("
        r"m\.?\s*r\.?\s*p\.?"
        r"|rs\.?"
        r"|inr"
        r"|net\s*(?:qty|quantity|weight)"
        r"|best\s*before"
        r"|pkd"
        r"|packed"
        r"|packing"
        r"|packaging"
        r"|marketed\s*by"
        r"|marketed\s*for"
        r"|packed\s*by"
        r"|manufactured\s*by"
        r"|manufactured\s*for"
        r")\b",
        re.IGNORECASE,
    ),

    "best_before": re.compile(
        r"\b("
        r"m\.?\s*r\.?\s*p\.?"
        r"|rs\.?"
        r"|inr"
        r"|net\s*(?:qty|quantity|weight)"
        r"|mfg"
        r"|mfd"
        r"|pkd"
        r"|packed"
        r"|packing"
        r"|packaging"
        r"|marketed\s*by"
        r"|marketed\s*for"
        r"|packed\s*by"
        r"|manufactured\s*by"
        r"|manufactured\s*for"
        r")\b",
        re.IGNORECASE,
    ),

    "manufacturer": re.compile(
        r"\b("
        r"m\.?\s*r\.?\s*p\.?"
        r"|rs\.?"
        r"|inr"
        r"|net\s*(?:qty|quantity|weight)"
        r"|mfg"
        r"|mfd"
        r"|manufactur\w*"
        r"|best\s*before"
        r"|pkd"
        r"|packed"
        r"|packing"
        r"|packaging"
        r"|fssai"
        r"|lic(?:ence|ense)?\s*(?:no|number)"
        r"|batch\s*(?:no|number)?"
        r"|ingredients"
        r"|nutrition"
        r"|product\s*name"
        r")\b",
        re.IGNORECASE,
    ),
}


def _line_belongs_to_other_field(
    text: str,
    this_field: str,
) -> bool:
    """
    Strong protection against assigning a value from one field to another.

    Example:
        Mfg Date: 06/2026 Best Before: 11 months

    Manufacturing date must get 06/2026.
    Best-before must get 11 months.

    A bare numeric/date value from a line containing another field label
    is therefore rejected.
    """

    text = _clean_text(text)

    if not text:
        return False

    # Explicit packaging information must NEVER become manufacturing date.
    if this_field == "manufacturing_date":
        if PACKAGING_DATE_KEYWORD.search(text):
            return True

    # Explicit manufacturing information must NEVER become packaging date.
    if this_field == "packaging_date":
        if MANUFACTURING_KEYWORD.search(text):
            return True

    pattern = OTHER_FIELD_KEYWORDS.get(
        this_field
    )

    if pattern and pattern.search(text):
        return True

    return False


def _has_explicit_field_label(
    text: str,
    field_name: str,
) -> bool:
    """
    Determines whether a line explicitly labels the requested field.
    """

    if field_name == "mrp":
        return bool(
            MRP_KEYWORD.search(text)
        )

    if field_name == "net_quantity":
        return bool(
            NET_QUANTITY_KEYWORD.search(text)
        )

    if field_name == "manufacturing_date":
        return bool(
            MANUFACTURING_KEYWORD.search(text)
        )

    if field_name == "best_before":
        return bool(
            BEST_BEFORE_KEYWORD.search(text)
        )

    if field_name == "manufacturer":
        return bool(
            MANUFACTURER_KEYWORD.search(text)
        )

    if field_name == "product_name":
        return bool(
            PRODUCT_NAME_KEYWORD.search(text)
        )

    if field_name == "packaging_date":
        return bool(
            PACKAGING_DATE_KEYWORD.search(text)
        )

    return False


# ============================================================================
# RELIABILITY
# ============================================================================

def _reliability(
    ocr_confidence: float,
    context_score: float,
) -> float:
    """
    Reliability is a combined signal.

    IMPORTANT:
        This does NOT determine whether the field is legally compliant.
    """

    score = (
        0.5 * ocr_confidence
        + 0.5 * context_score
    )

    return round(
        max(
            0.0,
            min(1.0, score),
        ),
        4,
    )


# ============================================================================
# MANUFACTURER / MARKETER EXTRACTION
# ============================================================================

def _extract_manufacturer(
    detections: List[Dict[str, Any]],
) -> FieldResult:

    keyword_hits = []

    for index, detection in enumerate(detections):

        text = _clean_text(
            detection.get("text", "")
        )

        keyword_match = (
            MANUFACTURER_KEYWORD.search(text)
        )

        if not keyword_match:
            continue

        keyword_hits.append(
            (index, detection)
        )

        # -------------------------------------------------------------------
        # SAME-LINE VALUE
        # -------------------------------------------------------------------

        same_line = _find_value(
            text,
            MANUFACTURER_VALUE,
            keyword_match.start(),
        )

        if same_line:
            same_line = _clean_text(
                same_line
            )

            if same_line:

                return FieldResult(
                    field_name="manufacturer",
                    value=same_line,
                    state="present",
                    reliability=_reliability(
                        _ocr_confidence(detection),
                        1.0,
                    ),
                    source_detections=[
                        detection
                    ],
                    note=(
                        "Manufacturer/marketer label "
                        "and value found together."
                    ),
                )

        # -------------------------------------------------------------------
        # NEXT FEW OCR DETECTIONS
        # -------------------------------------------------------------------

        collected_lines = []

        source_detections = [
            detection
        ]

        for neighbor_index in range(
            index + 1,
            min(
                len(detections),
                index + 5,
            ),
        ):

            neighbor = detections[
                neighbor_index
            ]

            neighbor_text = _clean_text(
                neighbor.get(
                    "text",
                    "",
                )
            )

            if not neighbor_text:
                continue

            # Stop at another tracked field.
            if _line_belongs_to_other_field(
                neighbor_text,
                "manufacturer",
            ):
                break

            # Additional unrelated metadata protection.
            if re.search(
                r"\b("
                r"fssai"
                r"|lic(?:ence|ense)?\s*(?:no|number)"
                r"|batch\s*(?:no|number)?"
                r"|mrp"
                r"|net\s*(?:qty|quantity|weight)"
                r"|best\s*before"
                r"|mfg"
                r"|mfd"
                r"|ingredients"
                r"|nutrition"
                r"|product\s*name"
                r")\b",
                neighbor_text,
                re.IGNORECASE,
            ):
                break

            collected_lines.append(
                neighbor_text
            )

            source_detections.append(
                neighbor
            )

            if len(collected_lines) >= 3:
                break

        if collected_lines:

            # First meaningful adjacent line is treated as company value.
            value = collected_lines[0]

            combined_confidences = [
                _ocr_confidence(d)
                for d in source_detections
            ]

            confidence = min(
                combined_confidences
            )

            return FieldResult(
                field_name="manufacturer",
                value=value,
                state="present",
                reliability=_reliability(
                    confidence,
                    0.9,
                ),
                source_detections=source_detections,
                note=(
                    "Manufacturer/marketer label found; "
                    "company value extracted from adjacent OCR line."
                ),
            )

    # -----------------------------------------------------------------------
    # KEYWORD FOUND BUT NO VALUE
    # -----------------------------------------------------------------------

    if keyword_hits:

        best_detection = max(
            keyword_hits,
            key=lambda pair:
                _ocr_confidence(pair[1]),
        )[1]

        return FieldResult(
            field_name="manufacturer",
            value=None,
            state="partial",
            reliability=_reliability(
                _ocr_confidence(
                    best_detection
                ),
                0.3,
            ),
            source_detections=[
                pair[1]
                for pair in keyword_hits
            ],
            note=(
                "Manufacturer/marketer label detected, "
                "but its value could not be read."
            ),
        )

    return FieldResult(
        field_name="manufacturer",
        value=None,
        state="missing",
        reliability=0.0,
        source_detections=[],
        note=(
            "No manufacturer/marketer label was detected."
        ),
    )


# ============================================================================
# BEST-BEFORE EXTRACTION
# ============================================================================

def _extract_best_before(
    detections: List[Dict[str, Any]],
) -> FieldResult:

    # -----------------------------------------------------------------------
    # FIRST: EXPLICIT "BEST BEFORE"
    # -----------------------------------------------------------------------

    for detection in detections:

        text = _clean_text(
            detection.get(
                "text",
                "",
            )
        )

        keyword = BEST_BEFORE_KEYWORD.search(
            text
        )

        if not keyword:
            continue

        value = _find_value(
            text,
            BEST_BEFORE_VALUE,
            keyword.end(),
        )

        if value:

            return FieldResult(
                field_name="best_before",
                value=value,
                state="present",
                reliability=_reliability(
                    _ocr_confidence(
                        detection
                    ),
                    1.0,
                ),
                source_detections=[
                    detection
                ],
                note=(
                    "Explicit Best Before label "
                    "and value found together."
                ),
                parsed=_parse_field_value(
                    "best_before",
                    value,
                    text,
                ),
            )

    # -----------------------------------------------------------------------
    # SECOND: CROPPED OCR FALLBACK
    # -----------------------------------------------------------------------

    for detection in detections:

        text = _clean_text(
            detection.get(
                "text",
                "",
            )
        )

        match = CROPPED_BEST_BEFORE_VALUE.search(
            text
        )

        if not match:
            continue

        full_match = match.group(0)

        duration_match = re.search(
            r"("
            r"[0-9]+\s*(?:months?|years?|days?)"
            r"|"
            r"(?:one|two|three|four|five|six|seven|eight|nine|"
            r"ten|eleven|twelve)"
            r"\s*(?:months?|years?|days?)"
            r")",
            full_match,
            re.IGNORECASE,
        )

        if not duration_match:
            continue

        value = duration_match.group(1).strip()

        if re.search(
            r"from\s+(?:the\s+)?(?:date\s+of\s+)?packing",
            full_match,
            re.IGNORECASE,
        ):
            value = (
                value
                + " from packing"
            )

        return FieldResult(
            field_name="best_before",
            value=value,
            state="uncertain",
            reliability=_reliability(
                _ocr_confidence(
                    detection
                ),
                0.65,
            ),
            source_detections=[
                detection
            ],
            note=(
                "Best-before duration inferred from "
                "a cropped/partial 'BEFORE ...' OCR line. "
                "Treat as lower-confidence than an explicit "
                "'BEST BEFORE' label."
            ),
            parsed=_parse_duration_or_date(
                value
            ),
        )

    # -----------------------------------------------------------------------
    # NO BEST-BEFORE INFORMATION
    # -----------------------------------------------------------------------

    return FieldResult(
        field_name="best_before",
        value=None,
        state="missing",
        reliability=0.0,
        source_detections=[],
        note=(
            "No Best Before information was detected."
        ),
    )


# ============================================================================
# GENERIC FIELD EXTRACTION
# ============================================================================

def _extract_one_field(
    field_name: str,
    patterns: dict,
    detections: List[Dict[str, Any]],
) -> FieldResult:

    keyword_pattern = patterns[
        "keyword"
    ]

    value_pattern = patterns[
        "value"
    ]

    keyword_hits = []
    value_only_hits = []

    for detection in detections:

        text = _clean_text(
            detection.get(
                "text",
                "",
            )
        )

        if not text:
            continue

        keyword_match = keyword_pattern.search(
            text
        )

        has_keyword = (
            keyword_match is not None
        )

        search_start = (
            keyword_match.end()
            if keyword_match
            else 0
        )

        # -------------------------------------------------------------------
        # SEARCH AFTER KEYWORD FIRST
        # -------------------------------------------------------------------

        value = _find_value(
            text,
            value_pattern,
            search_from=search_start,
        )

        # -------------------------------------------------------------------
        # SAME-LINE LABEL + VALUE
        # -------------------------------------------------------------------

        if has_keyword and value:

            # For manufacturing date, reject lines where packaging date
            # is explicitly the actual label.
            if (
                field_name == "manufacturing_date"
                and PACKAGING_DATE_KEYWORD.search(text)
                and not MANUFACTURING_KEYWORD.search(text)
            ):
                value = None

            if value:

                parsed = _parse_field_value(
                    field_name,
                    value,
                    text,
                )

                # A syntactically matching value which fails parsing should
                # not be treated as a valid present field.
                if parsed is not None:

                    return FieldResult(
                        field_name=field_name,
                        value=value,
                        state="present",
                        reliability=_reliability(
                            _ocr_confidence(
                                detection
                            ),
                            1.0,
                        ),
                        source_detections=[
                            detection
                        ],
                        note=(
                            "Keyword and value found together."
                        ),
                        parsed=parsed,
                    )

        # -------------------------------------------------------------------
        # KEYWORD FOUND BUT VALUE NOT FOUND
        # -------------------------------------------------------------------

        if has_keyword:
            keyword_hits.append(
                detection
            )

        # -------------------------------------------------------------------
        # BARE VALUE
        # -------------------------------------------------------------------

        elif value:

            # Strong cross-field protection.
            if not _line_belongs_to_other_field(
                text,
                field_name,
            ):
                value_only_hits.append(
                    (
                        detection,
                        value,
                        text,
                    )
                )

    # =========================================================================
    # ADJACENT LINE SEARCH
    # =========================================================================

    if keyword_hits:

        for keyword_detection in keyword_hits:

            try:
                index = detections.index(
                    keyword_detection
                )
            except ValueError:
                continue

            # Check up to 2 lines forward and 1 line backward.
            neighbors = []

            neighbors.extend(
                detections[
                    index + 1:
                    min(
                        len(detections),
                        index + 3,
                    )
                ]
            )

            if index > 0:
                neighbors.append(
                    detections[
                        index - 1
                    ]
                )

            for neighbor in neighbors:

                neighbor_text = _clean_text(
                    neighbor.get(
                        "text",
                        "",
                    )
                )

                if not neighbor_text:
                    continue

                # Never steal another field's value.
                if _line_belongs_to_other_field(
                    neighbor_text,
                    field_name,
                ):
                    continue

                value = _find_value(
                    neighbor_text,
                    value_pattern,
                )

                if not value:
                    continue

                parsed = _parse_field_value(
                    field_name,
                    value,
                    neighbor_text,
                )

                if parsed is None:
                    continue

                combined_confidence = min(
                    _ocr_confidence(
                        keyword_detection
                    ),
                    _ocr_confidence(
                        neighbor
                    ),
                )

                return FieldResult(
                    field_name=field_name,
                    value=value,
                    state="present",
                    reliability=_reliability(
                        combined_confidence,
                        0.85,
                    ),
                    source_detections=[
                        keyword_detection,
                        neighbor,
                    ],
                    note=(
                        "Keyword and value found on "
                        "adjacent OCR lines."
                    ),
                    parsed=parsed,
                )

        # ---------------------------------------------------------------------
        # KEYWORD EXISTS BUT NO VALUE
        # ---------------------------------------------------------------------

        best_keyword = max(
            keyword_hits,
            key=_ocr_confidence,
        )

        return FieldResult(
            field_name=field_name,
            value=None,
            state="partial",
            reliability=_reliability(
                _ocr_confidence(
                    best_keyword
                ),
                0.3,
            ),
            source_detections=keyword_hits,
            note=(
                "Field label found but no usable "
                "value could be extracted nearby."
            ),
        )

    # =========================================================================
    # BARE VALUE ONLY
    # =========================================================================

    if value_only_hits:

        best_detection, best_value, best_text = max(
            value_only_hits,
            key=lambda item:
                _ocr_confidence(
                    item[0]
                ),
        )

        parsed = _parse_field_value(
            field_name,
            best_value,
            best_text,
        )

        if parsed is not None:

            return FieldResult(
                field_name=field_name,
                value=best_value,
                state="uncertain",
                reliability=_reliability(
                    _ocr_confidence(
                        best_detection
                    ),
                    0.4,
                ),
                source_detections=[
                    best_detection
                ],
                note=(
                    "A matching value was found without "
                    "a nearby field label."
                ),
                parsed=parsed,
            )

    # =========================================================================
    # COMPLETELY MISSING
    # =========================================================================

    return FieldResult(
        field_name=field_name,
        value=None,
        state="missing",
        reliability=0.0,
        source_detections=[],
        note=(
            "Neither the field label nor a matching "
            "value was detected."
        ),
    )


# ============================================================================
# PRODUCT NAME
# ============================================================================

def _extract_product_name(
    detections: List[Dict[str, Any]],
) -> FieldResult:
    """
    Product name is ONLY extracted when explicitly labelled.

    We intentionally DO NOT do this:

        first OCR line -> product name
        largest OCR text -> product name
        logo -> product name
        brand -> product name

    Therefore "ANSHRI" will NOT automatically become product_name.
    """

    for detection in detections:

        text = _clean_text(
            detection.get(
                "text",
                "",
            )
        )

        keyword = PRODUCT_NAME_KEYWORD.search(
            text
        )

        if not keyword:
            continue

        value = _find_value(
            text,
            PRODUCT_NAME_VALUE,
            keyword.start(),
        )

        if not value:
            continue

        value = _clean_text(
            value
        )

        if not value:
            continue

        return FieldResult(
            field_name="product_name",
            value=value,
            state="present",
            reliability=_reliability(
                _ocr_confidence(
                    detection
                ),
                1.0,
            ),
            source_detections=[
                detection
            ],
            note=(
                "Product name explicitly labelled "
                "in the OCR text."
            ),
        )

    return FieldResult(
        field_name="product_name",
        value=None,
        state="missing",
        reliability=0.0,
        source_detections=[],
        note=(
            "No explicitly labelled product name was detected. "
            "Brand/logo text was intentionally NOT treated "
            "as the product name."
        ),
    )


# ============================================================================
# OPTIONAL PACKAGING DATE
# ============================================================================

def _extract_packaging_date(
    detections: List[Dict[str, Any]],
) -> FieldResult:
    """
    Extracts packaging/packed date separately.

    IMPORTANT:
        This does NOT modify manufacturing_date.
    """

    for detection in detections:

        text = _clean_text(
            detection.get(
                "text",
                "",
            )
        )

        keyword = PACKAGING_DATE_KEYWORD.search(
            text
        )

        if not keyword:
            continue

        value = _find_value(
            text,
            PACKAGING_DATE_VALUE,
            keyword.end(),
        )

        if value:

            parsed = _parse_packaging_date(
                value
            )

            if parsed is None:
                continue

            return FieldResult(
                field_name="packaging_date",
                value=value,
                state="present",
                reliability=_reliability(
                    _ocr_confidence(
                        detection
                    ),
                    1.0,
                ),
                source_detections=[
                    detection
                ],
                note=(
                    "Packaging/packing date detected separately "
                    "from manufacturing date."
                ),
                parsed=parsed,
            )

    return FieldResult(
        field_name="packaging_date",
        value=None,
        state="missing",
        reliability=0.0,
        source_detections=[],
        note=(
            "No packaging date was detected."
        ),
    )


def _parse_packaging_date(
    raw_value: str,
) -> Optional[Dict[str, Any]]:
    """
    Packaging dates may include month names, unlike the stricter
    manufacturing-date parser.

    Examples:
        July
        July 2026
        07/2026
        07/07/2026
    """

    raw_value = _clean_text(
        raw_value
    )

    # Numeric date/month.
    parsed = _parse_date(
        raw_value
    )

    if parsed is not None:
        return parsed

    # Month name only.
    month_match = re.fullmatch(
        r"(january|february|march|april|may|june|"
        r"july|august|september|october|november|december)",
        raw_value,
        re.IGNORECASE,
    )

    if month_match:

        month_names = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }

        return {
            "month": month_names[
                month_match.group(1).lower()
            ]
        }

    # Month + year.
    month_year_match = re.fullmatch(
        r"(january|february|march|april|may|june|"
        r"july|august|september|october|november|december)"
        r"\s+"
        r"([0-9]{4})",
        raw_value,
        re.IGNORECASE,
    )

    if month_year_match:

        month_names = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }

        return {
            "month": month_names[
                month_year_match.group(1).lower()
            ],
            "year": int(
                month_year_match.group(2)
            ),
        }

    return None


# ============================================================================
# MAIN EXTRACTION FUNCTION
# ============================================================================

def extract_fields(
    detections: List[Dict[str, Any]],
) -> Dict[str, dict]:
    """
    Extract all required fields plus safe optional metadata.

    Returns:
        {
            "mrp": {...},
            "net_quantity": {...},
            "manufacturing_date": {...},
            "best_before": {...},
            "manufacturer": {...},
            "product_name": {...},
            "packaging_date": {...}
        }

    IMPORTANT:
        Only the first five are required compliance fields.

        product_name and packaging_date are metadata and must
        NOT increase the required-field count.
    """

    # -----------------------------------------------------------------------
    # CLEAN MALFORMED DETECTIONS
    # -----------------------------------------------------------------------

    cleaned_detections = []

    for detection in detections or []:

        if not isinstance(
            detection,
            dict,
        ):
            continue

        text = _clean_text(
            detection.get(
                "text",
                "",
            )
        )

        if not text:
            continue

        cleaned = dict(
            detection
        )

        cleaned["text"] = text

        cleaned_detections.append(
            cleaned
        )

    results = {}

    # -----------------------------------------------------------------------
    # REQUIRED FIELDS
    # -----------------------------------------------------------------------

    for field_name, patterns in FIELD_PATTERNS.items():

        if field_name == "manufacturer":

            result = _extract_manufacturer(
                cleaned_detections
            )

        elif field_name == "best_before":

            result = _extract_best_before(
                cleaned_detections
            )

        else:

            result = _extract_one_field(
                field_name,
                patterns,
                cleaned_detections,
            )

        results[
            field_name
        ] = result.to_dict()

    # -----------------------------------------------------------------------
    # OPTIONAL METADATA
    # -----------------------------------------------------------------------

    results[
        "product_name"
    ] = _extract_product_name(
        cleaned_detections
    ).to_dict()

    results[
        "packaging_date"
    ] = _extract_packaging_date(
        cleaned_detections
    ).to_dict()

    return results


# ============================================================================
# READABILITY SUMMARY
# ============================================================================

def summarize_readability(
    field_results: Dict[str, dict],
) -> dict:
    """
    Summarizes ONLY the five required compliance fields.

    product_name and packaging_date are deliberately excluded.
    """

    required_fields = [
        "mrp",
        "net_quantity",
        "manufacturing_date",
        "best_before",
        "manufacturer",
    ]

    states = []

    for field_name in required_fields:

        result = field_results.get(
            field_name,
            {},
        )

        states.append(
            result.get(
                "state",
                "missing",
            )
        )

    total = len(states)

    present = states.count(
        "present"
    )

    partial = states.count(
        "partial"
    )

    uncertain = states.count(
        "uncertain"
    )

    missing = states.count(
        "missing"
    )

    if present == total:

        overall = "fully_readable"

    elif (
        present + uncertain
        >= total * 0.6
    ):

        overall = "mostly_readable"

    elif missing == total:

        overall = "unreadable"

    else:

        overall = "partially_readable"

    return {
        "overall": overall,
        "fields_present": present,
        "fields_partial": partial,
        "fields_uncertain": uncertain,
        "fields_missing": missing,
        "total_fields_checked": total,
        "required_fields": required_fields,

        # Informational only.
        "product_name_extracted": (
            field_results
            .get("product_name", {})
            .get("value")
        ),

        # Informational only.
        "packaging_date_extracted": (
            field_results
            .get("packaging_date", {})
            .get("value")
        ),
    }


# ============================================================================
# MANUAL TEST
# ============================================================================

if __name__ == "__main__":

    import json

    sample_detections = [

        {
            "text": "Anshri",
            "confidence": 0.99,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "M.R.P. Rs 50",
            "confidence": 0.98,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "Net Weight",
            "confidence": 0.96,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "32 g",
            "confidence": 0.97,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "Mfg. Date: 06/2026",
            "confidence": 0.95,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "BEFORE 11 MONTHS FROM THE DATE OF PACKING",
            "confidence": 0.92,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "Marketed By:",
            "confidence": 0.94,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "ANSHRI OVERSEAS",
            "confidence": 0.96,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "Laxminagar Main Road",
            "confidence": 0.90,
            "bbox": [0, 0, 0, 0],
        },

        {
            "text": "Pkd. Date: July",
            "confidence": 0.94,
            "bbox": [0, 0, 0, 0],
        },
    ]

    fields = extract_fields(
        sample_detections
    )

    readability = summarize_readability(
        fields
    )

    print("\n" + "=" * 70)
    print("FIELD EXTRACTION TEST")
    print("=" * 70)

    print(
        json.dumps(
            fields,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("\n" + "=" * 70)
    print("READABILITY")
    print("=" * 70)

    print(
        json.dumps(
            readability,
            indent=2,
            ensure_ascii=False,
        )
    )
"""
value_validator.py
------------------

Stage 11.2: Validation of extracted compliance field values.

Validates the five required packaged-commodity fields:

1. MRP
2. Net Quantity
3. Manufacturing Date
4. Best Before
5. Manufacturer

This module does NOT perform OCR.

It works on the output produced by field_extractor.py.

Validation states:

    valid       -> value looks structurally valid
    suspicious  -> value exists but may need review
    invalid     -> value is clearly invalid
    missing     -> no value was extracted
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_VALID_YEAR = 2000
MAX_VALID_YEAR = 2100

MAX_REASONABLE_MRP = 1_000_000

MAX_BEST_BEFORE_MONTHS = 120

VALID_QUANTITY_UNITS = {
    "mg",
    "g",
    "kg",
    "ml",
    "l",
}

QUANTITY_UNIT_MAP = {
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",

    "g": "g",
    "gram": "g",
    "grams": "g",

    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",

    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",

    "l": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
}

DURATION_UNIT_MAP = {
    "day": "days",
    "days": "days",

    "month": "months",
    "months": "months",

    "yr": "years",
    "yrs": "years",
    "year": "years",
    "years": "years",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> float | None:
    """Convert a value to float safely."""
    try:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        result = float(value)

        if result != result:  # NaN
            return None

        if result in (float("inf"), float("-inf")):
            return None

        return result

    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    """Convert a value to int safely."""
    try:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        # Handle values such as "6.0" safely.
        numeric = float(value)

        if not numeric.is_integer():
            return None

        return int(numeric)

    except (TypeError, ValueError):
        return None


def _normalise_text(value: Any) -> str:
    """Return a clean string representation."""
    if value is None:
        return ""

    return str(value).strip()


def _missing_field_result(message: str) -> dict[str, Any]:
    """Standard missing-field response."""
    return {
        "state": "missing",
        "valid": False,
        "message": message,
        "reason": "missing_value",
    }


def _invalid_result(
    message: str,
    reason: str,
    **extra: Any,
) -> dict[str, Any]:
    """Create a standard invalid result."""
    return {
        "state": "invalid",
        "valid": False,
        "message": message,
        "reason": reason,
        **extra,
    }


def _suspicious_result(
    message: str,
    reason: str,
    **extra: Any,
) -> dict[str, Any]:
    """Create a standard suspicious result."""
    return {
        "state": "suspicious",
        "valid": False,
        "message": message,
        "reason": reason,
        **extra,
    }


def _valid_result(
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    """Create a standard valid result."""
    return {
        "state": "valid",
        "valid": True,
        "message": message,
        "reason": None,
        **extra,
    }


# ---------------------------------------------------------------------------
# MRP validation
# ---------------------------------------------------------------------------

def validate_mrp(field: dict[str, Any]) -> dict[str, Any]:
    """
    Validate MRP.

    Expected examples:

        50
        Rs 50
        Rs. 50
        ₹50
        ₹ 50
        50.00
        MRP: ₹50
    """

    value = field.get("value")
    parsed = field.get("parsed")

    if value is None and parsed is None:
        return _missing_field_result("MRP value was not detected.")

    amount: float | None = None
    currency = "INR"

    # Prefer already-parsed value from field_extractor.py.
    if isinstance(parsed, dict):
        amount = _safe_float(parsed.get("amount"))

        if parsed.get("currency"):
            currency = str(parsed["currency"]).strip().upper()

    # Fallback: parse numeric value from raw field value.
    if amount is None:
        text = _normalise_text(value)

        # Supports:
        # 50
        # 50.00
        # Rs 50
        # Rs. 50
        # ₹50
        # ₹ 50
        match = re.search(
            r"(?<!\d)(\d+(?:\.\d{1,2})?)(?!\d)",
            text,
        )

        if match:
            amount = _safe_float(match.group(1))

    if amount is None:
        return _invalid_result(
            "MRP could not be interpreted as a numeric value.",
            "invalid_numeric_value",
        )

    if amount <= 0:
        return _invalid_result(
            "MRP must be greater than zero.",
            "non_positive_mrp",
            value=amount,
        )

    if amount > MAX_REASONABLE_MRP:
        return _suspicious_result(
            "MRP is unusually high. Please verify the extracted value.",
            "unusually_high_mrp",
            value=amount,
            currency=currency,
        )

    return _valid_result(
        "MRP value is valid.",
        value=amount,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Net quantity validation
# ---------------------------------------------------------------------------

def _normalise_quantity_unit(unit: Any) -> str | None:
    """Normalize a quantity unit."""
    if unit is None:
        return None

    normalized = str(unit).strip().lower()

    return QUANTITY_UNIT_MAP.get(normalized)


def validate_net_quantity(field: dict[str, Any]) -> dict[str, Any]:
    """
    Validate net quantity.

    Expected examples:

        100 g
        500 g
        1 kg
        250 ml
        2 L
        1 litre
    """

    value = field.get("value")
    parsed = field.get("parsed")

    if value is None and parsed is None:
        return _missing_field_result("Net quantity was not detected.")

    amount: float | None = None
    unit: str | None = None

    # Prefer parsed value from field_extractor.py.
    if isinstance(parsed, dict):
        amount = _safe_float(parsed.get("amount"))
        unit = _normalise_quantity_unit(parsed.get("unit"))

    # Fallback: parse raw value.
    if amount is None:
        text = _normalise_text(value)

        match = re.search(
            r"(?<!\d)"
            r"(\d+(?:\.\d+)?)"
            r"\s*"
            r"(kg|g|mg|l|ml|litre|litres|liter|liters|"
            r"kilogram|kilograms|gram|grams|milligram|milligrams|"
            r"millilitre|millilitres|milliliter|milliliters)"
            r"\b",
            text,
            re.IGNORECASE,
        )

        if match:
            amount = _safe_float(match.group(1))
            unit = _normalise_quantity_unit(match.group(2))

    if amount is None:
        return _invalid_result(
            "Net quantity could not be interpreted.",
            "invalid_quantity",
        )

    if amount <= 0:
        return _invalid_result(
            "Net quantity must be greater than zero.",
            "non_positive_quantity",
            value=amount,
            unit=unit,
        )

    if unit is None:
        return _suspicious_result(
            "Net quantity was detected but its unit is missing or unrecognised.",
            "missing_or_invalid_quantity_unit",
            value=amount,
        )

    return _valid_result(
        "Net quantity is valid.",
        value=amount,
        unit=unit,
    )


# ---------------------------------------------------------------------------
# Date helper
# ---------------------------------------------------------------------------

def _validate_date_parts(
    day: int | None,
    month: int | None,
    year: int | None,
    field_name: str,
) -> dict[str, Any] | None:
    """
    Validate date components.

    Returns a validation result if invalid/suspicious.
    Returns None if valid.
    """

    if month is not None and not 1 <= month <= 12:
        return _invalid_result(
            f"{field_name} month must be between 1 and 12.",
            "invalid_month",
            month=month,
            year=year,
        )

    if day is not None and not 1 <= day <= 31:
        return _invalid_result(
            f"{field_name} day is invalid.",
            "invalid_day",
            day=day,
            month=month,
            year=year,
        )

    if year is not None and not MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
        return _suspicious_result(
            f"{field_name} year is outside the expected range.",
            "unusual_year",
            day=day,
            month=month,
            year=year,
        )

    # If full date exists, verify actual calendar validity.
    if day is not None and month is not None and year is not None:
        try:
            date(year, month, day)
        except ValueError:
            return _invalid_result(
                f"{field_name} date is not a valid calendar date.",
                "invalid_calendar_date",
                day=day,
                month=month,
                year=year,
            )

    return None


# ---------------------------------------------------------------------------
# Manufacturing date validation
# ---------------------------------------------------------------------------

def validate_manufacturing_date(
    field: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate manufacturing date.

    Supported forms include:

        06/2026
        03/2025
        15/06/2026
        15-06-2026
        15.06.2026
        2026-06-15

    The current extractor commonly returns:

        {
            "month": 6,
            "year": 2026
        }
    """

    value = field.get("value")
    parsed = field.get("parsed")

    if value is None and parsed is None:
        return _missing_field_result(
            "Manufacturing date was not detected."
        )

    # ---------------------------------------------------------
    # If field_extractor already parsed month/year
    # ---------------------------------------------------------

    if isinstance(parsed, dict):
        month = _safe_int(parsed.get("month"))
        year = _safe_int(parsed.get("year"))
        day = _safe_int(parsed.get("day"))

        if month is not None and year is not None:
            validation_error = _validate_date_parts(
                day,
                month,
                year,
                "Manufacturing",
            )

            if validation_error:
                return validation_error

            result = _valid_result(
                "Manufacturing date is valid.",
                month=month,
                year=year,
            )

            if day is not None:
                result["day"] = day

            return result

    # ---------------------------------------------------------
    # Try extracting from raw value
    # ---------------------------------------------------------

    text = _normalise_text(value)

    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    match = re.search(
        r"\b"
        r"(\d{1,2})"
        r"\s*[/.\-]\s*"
        r"(\d{1,2})"
        r"\s*[/.\-]\s*"
        r"(20\d{2})"
        r"\b",
        text,
    )

    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        validation_error = _validate_date_parts(
            day,
            month,
            year,
            "Manufacturing",
        )

        if validation_error:
            return validation_error

        return _valid_result(
            "Manufacturing date is valid.",
            day=day,
            month=month,
            year=year,
        )

    # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    match = re.search(
        r"\b"
        r"(20\d{2})"
        r"\s*[/.\-]\s*"
        r"(\d{1,2})"
        r"\s*[/.\-]\s*"
        r"(\d{1,2})"
        r"\b",
        text,
    )

    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        validation_error = _validate_date_parts(
            day,
            month,
            year,
            "Manufacturing",
        )

        if validation_error:
            return validation_error

        return _valid_result(
            "Manufacturing date is valid.",
            day=day,
            month=month,
            year=year,
        )

    # MM/YYYY, MM-YYYY, MM.YYYY
    match = re.search(
        r"\b"
        r"(0?[1-9]|1[0-2])"
        r"\s*[/.\-]\s*"
        r"(20\d{2})"
        r"\b",
        text,
    )

    if match:
        month = int(match.group(1))
        year = int(match.group(2))

        validation_error = _validate_date_parts(
            None,
            month,
            year,
            "Manufacturing",
        )

        if validation_error:
            return validation_error

        return _valid_result(
            "Manufacturing date is valid.",
            month=month,
            year=year,
        )

    return _suspicious_result(
        "Manufacturing date was detected but could not be validated.",
        "unrecognised_date_format",
        raw_value=text,
    )


# ---------------------------------------------------------------------------
# Best-before validation
# ---------------------------------------------------------------------------

def _normalise_duration_unit(unit: Any) -> str | None:
    """Normalize best-before duration units."""
    if unit is None:
        return None

    normalized = str(unit).strip().lower()

    return DURATION_UNIT_MAP.get(normalized)


def _duration_months_equivalent(
    amount: float,
    unit: str,
) -> float:
    """Convert duration into an approximate month equivalent."""
    if unit == "years":
        return amount * 12

    if unit == "days":
        return amount / 30

    return amount


def validate_best_before(
    field: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate best-before information.

    Expected examples:

        12 months
        9 months from Mfg
        6 months
        1 year
        30 days
    """

    value = field.get("value")
    parsed = field.get("parsed")

    if value is None and parsed is None:
        return _missing_field_result(
            "Best-before information was not detected."
        )

    amount: float | None = None
    unit: str | None = None
    reference = None

    # ---------------------------------------------------------
    # Parsed value from field_extractor.py
    # ---------------------------------------------------------

    if isinstance(parsed, dict):
        amount = _safe_float(parsed.get("amount"))
        unit = _normalise_duration_unit(parsed.get("unit"))
        reference = parsed.get("reference")

    if amount is not None:

        if amount <= 0:
            return _invalid_result(
                "Best-before duration must be greater than zero.",
                "non_positive_duration",
                value=amount,
                unit=unit,
            )

        if unit is None:
            return _suspicious_result(
                "Best-before duration was detected but its unit is missing or unrecognised.",
                "missing_or_invalid_duration_unit",
                value=amount,
            )

        months_equivalent = _duration_months_equivalent(
            amount,
            unit,
        )

        if months_equivalent > MAX_BEST_BEFORE_MONTHS:
            return _suspicious_result(
                "Best-before duration is unusually long. Please verify.",
                "unusually_long_duration",
                value=amount,
                unit=unit,
            )

        return _valid_result(
            "Best-before information is valid.",
            value=amount,
            unit=unit,
            reference=reference,
        )

    # ---------------------------------------------------------
    # Try parsing raw value
    # ---------------------------------------------------------

    text = _normalise_text(value)

    match = re.search(
        r"\b"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(months?|yrs?|years?|days?)"
        r"\b",
        text,
        re.IGNORECASE,
    )

    if match:
        amount = _safe_float(match.group(1))
        unit = _normalise_duration_unit(match.group(2))

        if amount is None:
            return _invalid_result(
                "Best-before duration could not be interpreted.",
                "invalid_duration",
            )

        if amount <= 0:
            return _invalid_result(
                "Best-before duration must be greater than zero.",
                "non_positive_duration",
                value=amount,
            )

        if unit is None:
            return _suspicious_result(
                "Best-before duration unit could not be recognised.",
                "invalid_duration_unit",
                value=amount,
            )

        months_equivalent = _duration_months_equivalent(
            amount,
            unit,
        )

        if months_equivalent > MAX_BEST_BEFORE_MONTHS:
            return _suspicious_result(
                "Best-before duration is unusually long. Please verify.",
                "unusually_long_duration",
                value=amount,
                unit=unit,
            )

        return _valid_result(
            "Best-before information is valid.",
            value=amount,
            unit=unit,
        )

    return _suspicious_result(
        "Best-before value was detected but could not be validated.",
        "unrecognised_best_before_format",
        raw_value=text,
    )


# ---------------------------------------------------------------------------
# Manufacturer validation
# ---------------------------------------------------------------------------

def validate_manufacturer(
    field: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate manufacturer / packed-by text.

    Checks:

        - existence
        - minimum meaningful alphabetic content
        - excessive digits
        - obviously malformed values
    """

    value = field.get("value")

    if value is None:
        return _missing_field_result(
            "Manufacturer information was not detected."
        )

    text = _normalise_text(value)

    if not text:
        return _missing_field_result(
            "Manufacturer information is empty."
        )

    # Remove punctuation and spaces to inspect actual alphabetic content.
    alpha_chars = re.sub(
        r"[^A-Za-z]",
        "",
        text,
    )

    if len(alpha_chars) < 3:
        return _invalid_result(
            "Manufacturer name is too short to be reliable.",
            "manufacturer_too_short",
            raw_value=text,
        )

    digit_count = sum(
        ch.isdigit()
        for ch in text
    )

    non_space_length = len(
        re.sub(r"\s", "", text)
    )

    if (
        non_space_length > 0
        and digit_count / non_space_length > 0.5
    ):
        return _suspicious_result(
            "Manufacturer value contains unusually many digits.",
            "digit_heavy_manufacturer",
            raw_value=text,
        )

    # Reject values that are almost entirely punctuation.
    meaningful_chars = re.sub(
        r"[^A-Za-z0-9\s]",
        "",
        text,
    )

    if len(meaningful_chars.strip()) < 3:
        return _invalid_result(
            "Manufacturer value does not contain enough meaningful text.",
            "insufficient_meaningful_text",
            raw_value=text,
        )

    return _valid_result(
        "Manufacturer information is valid.",
        value=text,
    )


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------

def validate_fields(
    fields: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Validate all five extracted compliance fields.

    Input:

        fields = output from extract_fields()

    Output:

        {
            "mrp": {...},
            "net_quantity": {...},
            "manufacturing_date": {...},
            "best_before": {...},
            "manufacturer": {...},
            "summary": {...}
        }
    """

    if not isinstance(fields, dict):
        fields = {}

    validators = {
        "mrp": validate_mrp,
        "net_quantity": validate_net_quantity,
        "manufacturing_date": validate_manufacturing_date,
        "best_before": validate_best_before,
        "manufacturer": validate_manufacturer,
    }

    results: dict[str, Any] = {}

    valid_count = 0
    suspicious_count = 0
    invalid_count = 0
    missing_count = 0

    for field_name, validator in validators.items():

        field_data = fields.get(field_name, {})

        if not isinstance(field_data, dict):
            field_data = {}

        result = validator(field_data)

        results[field_name] = result

        state = result.get("state")

        if state == "valid":
            valid_count += 1

        elif state == "suspicious":
            suspicious_count += 1

        elif state == "invalid":
            invalid_count += 1

        elif state == "missing":
            missing_count += 1

    total_fields = len(validators)

    # ---------------------------------------------------------
    # Overall validation verdict
    # ---------------------------------------------------------

    if valid_count == total_fields:
        overall = "valid"

    elif missing_count == total_fields:
        overall = "missing"

    elif valid_count == 0 and invalid_count > 0:
        overall = "invalid"

    else:
        overall = "needs_review"

    results["summary"] = {
        "overall": overall,
        "total_fields": total_fields,
        "valid": valid_count,
        "suspicious": suspicious_count,
        "invalid": invalid_count,
        "missing": missing_count,
    }

    return results


# ---------------------------------------------------------------------------
# Convenience function used by run_pipeline.py
# ---------------------------------------------------------------------------

def validate_extracted_fields(
    fields: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Public function used by run_pipeline.py.

    This wrapper keeps Stage 11.2 integration simple.
    """
    return validate_fields(fields)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    test_fields = {
        "mrp": {
            "field": "mrp",
            "value": "50",
            "parsed": {
                "amount": 50.0,
                "currency": "INR",
            },
            "state": "present",
            "reliability": 0.988,
        },

        "net_quantity": {
            "field": "net_quantity",
            "value": "100 g",
            "parsed": {
                "amount": 100.0,
                "unit": "g",
            },
            "state": "present",
            "reliability": 0.988,
        },

        "manufacturing_date": {
            "field": "manufacturing_date",
            "value": "06/2026",
            "parsed": {
                "month": 6,
                "year": 2026,
            },
            "state": "present",
            "reliability": 0.997,
        },

        "best_before": {
            "field": "best_before",
            "value": "12 Months from Mfg",
            "parsed": {
                "amount": 12,
                "unit": "months",
                "reference": "manufacturing",
            },
            "state": "present",
            "reliability": 0.995,
        },

        "manufacturer": {
            "field": "manufacturer",
            "value": "XYZ Foods Pvt. Ltd.",
            "parsed": None,
            "state": "present",
            "reliability": 0.996,
        },
    }

    result = validate_fields(test_fields)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
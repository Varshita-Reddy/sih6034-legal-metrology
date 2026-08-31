"""
compliance_decision.py
----------------------
Stage 12: Compliance Decision Engine

Converts OCR field validation results into one final compliance decision.

Possible decisions:

    compliant
    needs_review
    non_compliant
    extraction_failed

The module does NOT perform OCR or field extraction.
It only evaluates the results produced by the previous stages.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Required compliance fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = (
    "mrp",
    "net_quantity",
    "manufacturing_date",
    "best_before",
    "manufacturer",
)


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------

def decide_compliance(
    validation: dict[str, Any],
    readability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Decide the final compliance status.

    Rules
    -----

    1. All five fields valid
        -> COMPLIANT

    2. Any field invalid
        -> NON-COMPLIANT

    3. Any field missing
        -> NON-COMPLIANT

    4. Any field suspicious
        -> NEEDS REVIEW

    5. No usable fields / extraction failure
        -> EXTRACTION FAILED

    Parameters
    ----------
    validation:
        Output of validate_extracted_fields().

    readability:
        Output of summarize_readability().
        Used as an additional signal when available.
    """

    if not isinstance(validation, dict):
        return _extraction_failed(
            "Validation results are unavailable or invalid."
        )

    # -----------------------------------------------------------------------
    # Count validation states
    # -----------------------------------------------------------------------

    valid_count = 0
    suspicious_count = 0
    invalid_count = 0
    missing_count = 0

    field_results: dict[str, Any] = {}

    for field_name in REQUIRED_FIELDS:
        result = validation.get(field_name, {})

        if not isinstance(result, dict):
            result = {}

        field_results[field_name] = result

        state = result.get("state")

        if state == "valid":
            valid_count += 1

        elif state == "suspicious":
            suspicious_count += 1

        elif state == "invalid":
            invalid_count += 1

        elif state == "missing":
            missing_count += 1

        else:
            # Unknown / malformed state is treated as suspicious
            # rather than silently accepting it.
            suspicious_count += 1

    total_fields = len(REQUIRED_FIELDS)

    # -----------------------------------------------------------------------
    # Optional readability information
    # -----------------------------------------------------------------------

    fields_present = None

    if isinstance(readability, dict):
        try:
            fields_present = int(
                readability.get("fields_present", 0)
            )
        except (TypeError, ValueError):
            fields_present = None

    # -----------------------------------------------------------------------
    # Decision 1 — All fields valid
    # -----------------------------------------------------------------------

    if valid_count == total_fields:
        return {
            "decision": "compliant",
            "label": "🟢 Compliant",
            "reason": (
                "All 5 required compliance fields are present "
                "and their extracted values are valid."
            ),
            "fields_required": total_fields,
            "fields_present": (
                valid_count
                if fields_present is None
                else fields_present
            ),
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # -----------------------------------------------------------------------
    # Decision 2 — Invalid value detected
    # -----------------------------------------------------------------------

    if invalid_count > 0:
        return {
            "decision": "non_compliant",
            "label": "🔴 Non-compliant",
            "reason": (
                f"{invalid_count} required field(s) contain "
                "clearly invalid extracted values."
            ),
            "fields_required": total_fields,
            "fields_present": (
                total_fields - missing_count
                if fields_present is None
                else fields_present
            ),
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # -----------------------------------------------------------------------
    # Decision 3 — Missing fields
    # -----------------------------------------------------------------------

    if missing_count > 0:
        return {
            "decision": "non_compliant",
            "label": "🔴 Non-compliant",
            "reason": (
                f"{missing_count} required compliance field(s) "
                "were not detected."
            ),
            "fields_required": total_fields,
            "fields_present": (
                total_fields - missing_count
                if fields_present is None
                else fields_present
            ),
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # -----------------------------------------------------------------------
    # Decision 4 — Suspicious values
    # -----------------------------------------------------------------------

    if suspicious_count > 0:
        return {
            "decision": "needs_review",
            "label": "🟡 Needs review",
            "reason": (
                f"{suspicious_count} required field(s) contain "
                "values that could not be confidently validated."
            ),
            "fields_required": total_fields,
            "fields_present": (
                total_fields
                if fields_present is None
                else fields_present
            ),
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # -----------------------------------------------------------------------
    # Decision 5 — Nothing usable
    # -----------------------------------------------------------------------

    return _extraction_failed(
        "No usable compliance field information was available."
    )


# ---------------------------------------------------------------------------
# Extraction failure helper
# ---------------------------------------------------------------------------

def _extraction_failed(reason: str) -> dict[str, Any]:
    """Return a standard extraction-failure response."""

    total_fields = len(REQUIRED_FIELDS)

    return {
        "decision": "extraction_failed",
        "label": "🔴 Extraction failed",
        "reason": reason,
        "fields_required": total_fields,
        "fields_present": 0,
        "fields_valid": 0,
        "fields_invalid": 0,
        "fields_suspicious": 0,
        "fields_missing": total_fields,
    }


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def build_compliance_decision(
    validation: dict[str, Any],
    readability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Public wrapper used by run_pipeline.py.

    Keeping this wrapper allows the decision engine to be changed later
    without changing the pipeline integration.
    """

    return decide_compliance(
        validation=validation,
        readability=readability,
    )


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    test_validation = {
        "mrp": {
            "state": "valid",
            "valid": True,
        },
        "net_quantity": {
            "state": "valid",
            "valid": True,
        },
        "manufacturing_date": {
            "state": "valid",
            "valid": True,
        },
        "best_before": {
            "state": "valid",
            "valid": True,
        },
        "manufacturer": {
            "state": "valid",
            "valid": True,
        },
        "summary": {
            "overall": "valid",
            "total_fields": 5,
            "valid": 5,
            "suspicious": 0,
            "invalid": 0,
            "missing": 0,
        },
    }

    test_readability = {
        "overall": "fully_readable",
        "fields_present": 5,
        "fields_partial": 0,
        "fields_uncertain": 0,
        "fields_missing": 0,
        "total_fields_checked": 5,
    }

    result = build_compliance_decision(
        validation=test_validation,
        readability=test_readability,
    )

    import json

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
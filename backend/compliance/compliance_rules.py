"""
compliance_rules.py
-------------------

Stage 12 — Compliance Decision Layer

This module receives the output of:

    field_extractor.py
            ↓
    value_validator.py
            ↓
    compliance_rules.py

It does NOT perform OCR.

It does NOT perform image processing.

It does NOT replace value validation.

Its responsibility is to convert the extracted/validated field
information into a clear compliance decision.

Required packaged-commodity fields currently checked:

    1. MRP
    2. Net Quantity
    3. Manufacturing Date
    4. Best Before
    5. Manufacturer

Decision states:

    compliant
    non_compliant
    needs_review

Important:
This first version intentionally does NOT invent specific Legal
Metrology numerical/business rules. It evaluates whether the five
required fields were successfully extracted and whether their
values passed Stage 11.2 validation.

Actual Legal Metrology rule checks can be added later without
changing the OCR pipeline.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = (
    "mrp",
    "net_quantity",
    "manufacturing_date",
    "best_before",
    "manufacturer",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_dict(value: Any) -> dict[str, Any]:
    """
    Return value as a dictionary when possible.
    Otherwise return an empty dictionary.
    """
    if isinstance(value, dict):
        return value

    return {}


def _field_state(
    validation: dict[str, Any],
    field_name: str,
) -> str:
    """
    Safely obtain the validation state of a field.
    """
    field_result = _safe_dict(
        validation.get(field_name)
    )

    state = field_result.get("state")

    if not isinstance(state, str):
        return "missing"

    return state.lower().strip()


# ---------------------------------------------------------------------------
# Field counting
# ---------------------------------------------------------------------------

def count_field_states(
    validation: dict[str, Any],
) -> dict[str, int]:
    """
    Count the validation states of the five required fields.

    Returns:

        {
            "valid": 5,
            "suspicious": 0,
            "invalid": 0,
            "missing": 0
        }
    """

    valid_count = 0
    suspicious_count = 0
    invalid_count = 0
    missing_count = 0

    for field_name in REQUIRED_FIELDS:

        state = _field_state(
            validation,
            field_name,
        )

        if state == "valid":
            valid_count += 1

        elif state == "suspicious":
            suspicious_count += 1

        elif state == "invalid":
            invalid_count += 1

        elif state == "missing":
            missing_count += 1

        else:
            # Unknown state should never silently become valid.
            # Treat it as needing review.
            suspicious_count += 1

    return {
        "valid": valid_count,
        "suspicious": suspicious_count,
        "invalid": invalid_count,
        "missing": missing_count,
    }


# ---------------------------------------------------------------------------
# Compliance decision
# ---------------------------------------------------------------------------

def determine_compliance(
    validation: dict[str, Any],
) -> dict[str, Any]:
    """
    Determine the overall compliance decision from Stage 11.2
    validation results.

    Decision logic:

        ALL 5 valid
            ↓
        compliant

        Any invalid field
            ↓
        non_compliant

        Any suspicious field
            ↓
        needs_review

        Any missing field
            ↓
        non_compliant

    Note:
    A missing required field is treated as non-compliant at this
    current Stage 12 level because the required information could
    not be verified.

    More detailed Legal Metrology rules can be added later.
    """

    counts = count_field_states(validation)

    valid_count = counts["valid"]
    suspicious_count = counts["suspicious"]
    invalid_count = counts["invalid"]
    missing_count = counts["missing"]

    total_required = len(REQUIRED_FIELDS)

    # ------------------------------------------------------------------
    # Case 1 — Everything is valid
    # ------------------------------------------------------------------

    if valid_count == total_required:
        return {
            "decision": "compliant",
            "label": "🟢 Compliant",
            "reason": (
                "All 5 required compliance fields are present "
                "and their extracted values are valid."
            ),
            "fields_required": total_required,
            "fields_present": valid_count,
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # ------------------------------------------------------------------
    # Case 2 — Clearly invalid or missing information
    # ------------------------------------------------------------------

    if invalid_count > 0 or missing_count > 0:

        reasons = []

        if invalid_count > 0:
            reasons.append(
                f"{invalid_count} field(s) contain invalid values"
            )

        if missing_count > 0:
            reasons.append(
                f"{missing_count} required field(s) are missing"
            )

        reason = (
            "The product label could not be considered compliant "
            "because " + " and ".join(reasons) + "."
        )

        return {
            "decision": "non_compliant",
            "label": "🔴 Non-compliant",
            "reason": reason,
            "fields_required": total_required,
            "fields_present": (
                total_required - missing_count
            ),
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # ------------------------------------------------------------------
    # Case 3 — Suspicious values
    # ------------------------------------------------------------------

    if suspicious_count > 0:

        return {
            "decision": "needs_review",
            "label": "🟠 Needs Review",
            "reason": (
                f"{suspicious_count} extracted field(s) "
                "are suspicious and require manual verification."
            ),
            "fields_required": total_required,
            "fields_present": (
                valid_count + suspicious_count
            ),
            "fields_valid": valid_count,
            "fields_invalid": invalid_count,
            "fields_suspicious": suspicious_count,
            "fields_missing": missing_count,
        }

    # ------------------------------------------------------------------
    # Safety fallback
    # ------------------------------------------------------------------

    return {
        "decision": "needs_review",
        "label": "🟠 Needs Review",
        "reason": (
            "The extracted compliance fields could not be "
            "classified with sufficient confidence."
        ),
        "fields_required": total_required,
        "fields_present": valid_count,
        "fields_valid": valid_count,
        "fields_invalid": invalid_count,
        "fields_suspicious": suspicious_count,
        "fields_missing": missing_count,
    }


# ---------------------------------------------------------------------------
# Detailed field-level compliance information
# ---------------------------------------------------------------------------

def build_field_summary(
    validation: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a compact field-by-field summary.

    This is useful for the frontend because the frontend does not
    need to understand the internal validator implementation.

    Example:

        {
            "mrp": {
                "state": "valid",
                "valid": True
            },
            ...
        }
    """

    summary: dict[str, Any] = {}

    for field_name in REQUIRED_FIELDS:

        result = _safe_dict(
            validation.get(field_name)
        )

        state = _field_state(
            validation,
            field_name,
        )

        summary[field_name] = {
            "state": state,
            "valid": state == "valid",
        }

        # Preserve useful validation message if available.
        if "message" in result:
            summary[field_name]["message"] = result["message"]

        # Preserve validation reason if available.
        if "reason" in result:
            summary[field_name]["reason"] = result["reason"]

    return summary


# ---------------------------------------------------------------------------
# Complete Stage 12 function
# ---------------------------------------------------------------------------

def evaluate_compliance(
    validation: dict[str, Any],
    product_category: str = None,
    product_subcategory: str = None,
) -> dict[str, Any]:
    """
    Main public Stage 12 function.

    Input:
        validation
        └── output from validate_extracted_fields()

    Output:

        {
            "decision": "compliant",
            "label": "🟢 Compliant",
            "reason": "...",
            "fields_required": 5,
            "fields_present": 5,
            "fields_valid": 5,
            "fields_invalid": 0,
            "fields_suspicious": 0,
            "fields_missing": 0,
            "field_summary": {...}
        }
    """

    if not isinstance(validation, dict):
        return {
            "decision": "needs_review",
            "label": "🟠 Needs Review",
            "reason": (
                "Validation output is missing or has an invalid format."
            ),
            "fields_required": len(REQUIRED_FIELDS),
            "fields_present": 0,
            "fields_valid": 0,
            "fields_invalid": 0,
            "fields_suspicious": 0,
            "fields_missing": len(REQUIRED_FIELDS),
            "field_summary": {},
        }

    decision = determine_compliance(
        validation
    )

    # Category-specific rules (from Mani's engine)
    violations = []
    if product_category:
        try:
            from compliance.rules import COMMON_RULES, CATEGORY_RULES, FSSAI_RULES
            
            selected_fields = CATEGORY_RULES.get(product_category, {}).get(product_subcategory)
            if selected_fields is None:
                selected_fields = list(COMMON_RULES.keys())
                
            All_RULESS = {**COMMON_RULES, **FSSAI_RULES}
            selected_rules = {
                field: All_RULESS[field]
                for field in selected_fields
                if field in All_RULESS
            }
            
            rule_to_validation_map = {
                "mrp": "mrp",
                "net_quantity": "net_quantity",
                "manufacturing_date": "manufacturing_date",
                "manufacturer_name": "manufacturer",
                "manufacturer_address": "manufacturer",
                "expiry_date": "best_before",
                "common_generic_name": "product_name"
            }
            
            for rule_field, rule_detail in selected_rules.items():
                val_field = rule_to_validation_map.get(rule_field)
                if not val_field:
                    continue
                    
                val_res = validation.get(val_field, {})
                val_state = val_res.get("state", "missing")
                
                if rule_detail.get("required") and val_state in ("missing", "invalid"):
                    violations.append({
                        "field": rule_field,
                        "message": f"{rule_detail['description']} is missing or invalid"
                    })
                    decision["decision"] = "non_compliant"
                    decision["label"] = "🔴 Non-compliant"
                    
            if violations:
                decision["reason"] = f"Category-specific compliance check failed: {len(violations)} violation(s) detected."
        except Exception as e:
            # Fallback if rules cannot be loaded
            pass

    decision["violations"] = violations
    decision["field_summary"] = build_field_summary(
        validation
    )

    return decision


# ---------------------------------------------------------------------------
# Convenience alias
# ---------------------------------------------------------------------------

def check_compliance(
    validation: dict[str, Any],
    product_category: str = None,
    product_subcategory: str = None,
) -> dict[str, Any]:
    """
    Convenience alias for evaluate_compliance().
    """

    return evaluate_compliance(validation, product_category, product_subcategory)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    import json

    # ---------------------------------------------------------------
    # Test 1 — Fully valid product
    # ---------------------------------------------------------------

    valid_test = {

        "mrp": {
            "state": "valid",
            "valid": True,
            "message": "MRP value is valid.",
            "reason": None,
            "value": 50.0,
            "currency": "INR",
        },

        "net_quantity": {
            "state": "valid",
            "valid": True,
            "message": "Net quantity is valid.",
            "reason": None,
            "value": 100.0,
            "unit": "g",
        },

        "manufacturing_date": {
            "state": "valid",
            "valid": True,
            "message": "Manufacturing date is valid.",
            "reason": None,
            "month": 6,
            "year": 2026,
        },

        "best_before": {
            "state": "valid",
            "valid": True,
            "message": "Best-before information is valid.",
            "reason": None,
            "value": 12.0,
            "unit": "months",
            "reference": "manufacturing",
        },

        "manufacturer": {
            "state": "valid",
            "valid": True,
            "message": "Manufacturer information is valid.",
            "reason": None,
            "value": "XYZ Foods Pvt. Ltd.",
        },
    }

    result = evaluate_compliance(
        valid_test
    )

    print("\n========================================")
    print("STAGE 12 — VALID TEST")
    print("========================================")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ---------------------------------------------------------------
    # Test 2 — Missing field
    # ---------------------------------------------------------------

    missing_test = dict(valid_test)

    missing_test["mrp"] = {
        "state": "missing",
        "valid": False,
        "message": "MRP value was not detected.",
        "reason": "missing_value",
    }

    result = evaluate_compliance(
        missing_test
    )

    print("\n========================================")
    print("STAGE 12 — MISSING FIELD TEST")
    print("========================================")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ---------------------------------------------------------------
    # Test 3 — Suspicious field
    # ---------------------------------------------------------------

    suspicious_test = dict(valid_test)

    suspicious_test["mrp"] = {
        "state": "suspicious",
        "valid": False,
        "message": (
            "MRP is unusually high. "
            "Please verify the extracted value."
        ),
        "reason": "unusually_high_mrp",
        "value": 1500000.0,
    }

    result = evaluate_compliance(
        suspicious_test
    )

    print("\n========================================")
    print("STAGE 12 — SUSPICIOUS FIELD TEST")
    print("========================================")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    # ---------------------------------------------------------------
    # Test 4 — Invalid field
    # ---------------------------------------------------------------

    invalid_test = dict(valid_test)

    invalid_test["net_quantity"] = {
        "state": "invalid",
        "valid": False,
        "message": (
            "Net quantity must be greater than zero."
        ),
        "reason": "non_positive_quantity",
        "value": 0,
        "unit": "g",
    }

    result = evaluate_compliance(
        invalid_test
    )

    print("\n========================================")
    print("STAGE 12 — INVALID FIELD TEST")
    print("========================================")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
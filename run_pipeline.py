"""
run_pipeline.py

Optimized end-to-end SIH packaged-commodity OCR pipeline.

Flow:
Image
  ↓
Quality Check
  ↓
Adaptive OCR
  ↓
Clean detections
  ↓
Field extraction + repair
  ↓
Optional alternate/recovery OCR
  ↓
Validation
  ↓
Compliance
  ↓
Frontend routing
  ↓
Feature-engineering handoff

IMPORTANT:
OCR confidence alone NEVER determines success.

Required fields:
    mrp
    net_quantity
    manufacturing_date
    best_before
    manufacturer

Decision:
    0 fields          -> RETAKE
    missing fields    -> RETAKE
    suspicious/invalid values -> REVIEW
    all 5 valid       -> ACCEPT
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2

from preprocessing.image_preprocess import (
    check_image_quality,
    adaptive_preprocess,
    alternate_preprocess,
)

from preprocessing.recovery_preprocess import (
    aggressive_recovery_preprocess,
)

from ocr.ocr_engine import OCREngine
from ocr.text_cleaner import clean_detections
from ocr.field_extractor import (
    extract_fields,
    summarize_readability,
)

from ocr.quality_scorer import (
    combined_quality_verdict,
    build_status_summary,
    score_attempt,
)

from ocr.value_validator import validate_extracted_fields
from compliance.compliance_rules import evaluate_compliance


# ============================================================================
# CONFIGURATION
# ============================================================================

REQUIRED_FIELDS = (
    "mrp",
    "net_quantity",
    "manufacturing_date",
    "best_before",
    "manufacturer",
)

REQUIRED_FIELD_COUNT = len(REQUIRED_FIELDS)

MIN_OCR_CONFIDENCE_FOR_ACCEPT = 0.50
MIN_STRONG_OCR_CONFIDENCE = 0.80

ENABLE_ALTERNATE_ATTEMPT = True
ENABLE_RECOVERY = True

MAX_IMAGE_FILE_SIZE_MB = 25

_ENGINE_CACHE: Dict[float, OCREngine] = {}


# ============================================================================
# BASIC HELPERS
# ============================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def get_detection_text(detection: Dict[str, Any]) -> str:
    return normalize_text(detection.get("text", ""))


# ============================================================================
# OCR ENGINE
# ============================================================================

def get_ocr_engine(confidence_threshold: float = 0.5) -> OCREngine:
    """
    Initialize the OCR engine once and reuse it.
    """

    threshold = float(confidence_threshold)

    if threshold not in _ENGINE_CACHE:
        print("🚀 Initializing OCR engine...")

        _ENGINE_CACHE[threshold] = OCREngine(
            confidence_threshold=threshold
        )

        print("✅ OCR engine initialized.")
    else:
        print("♻️ Reusing existing OCR engine...")

    return _ENGINE_CACHE[threshold]


# ============================================================================
# FIELD HELPERS
# ============================================================================

def field_is_usable(field: Any) -> bool:
    if not isinstance(field, dict):
        return False

    state = str(
        field.get("state", "")
    ).lower().strip()

    value = field.get("value")

    return (
        state == "present"
        and value is not None
        and normalize_text(value) != ""
    )


def count_usable_fields(fields: Dict[str, Any]) -> int:
    if not isinstance(fields, dict):
        return 0

    return sum(
        field_is_usable(fields.get(name))
        for name in REQUIRED_FIELDS
    )


def get_missing_required_fields(
    fields: Dict[str, Any],
) -> List[str]:

    return [
        name
        for name in REQUIRED_FIELDS
        if not field_is_usable(fields.get(name))
    ]


def get_attempt_average_confidence(
    ocr_result: Dict[str, Any],
) -> float:

    if not isinstance(ocr_result, dict):
        return 0.0

    detections = ocr_result.get("detections", [])

    if not isinstance(detections, list):
        return 0.0

    confidences = []

    for detection in detections:
        if not isinstance(detection, dict):
            continue

        confidence = safe_float(
            detection.get("confidence", 0.0)
        )

        if confidence > 0:
            confidences.append(confidence)

    if not confidences:
        return 0.0

    return sum(confidences) / len(confidences)


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def count_validation_states(
    validation: Dict[str, Any],
) -> Dict[str, int]:

    counts = {
        "valid": 0,
        "suspicious": 0,
        "invalid": 0,
        "missing": 0,
    }

    if not isinstance(validation, dict):
        return counts

    for field_name in REQUIRED_FIELDS:

        result = validation.get(field_name, {})

        if not isinstance(result, dict):
            counts["missing"] += 1
            continue

        state = str(
            result.get("state", "missing")
        ).lower().strip()

        if state in counts:
            counts[state] += 1
        else:
            counts["missing"] += 1

    return counts


# ============================================================================
# READABILITY
# ============================================================================

def is_readable(readability: Dict[str, Any]) -> bool:

    if not isinstance(readability, dict):
        return True

    if "readable" in readability:
        return bool(readability["readable"])

    if "is_readable" in readability:
        return bool(readability["is_readable"])

    overall = str(
        readability.get("overall", "")
    ).lower().strip()

    return overall != "unreadable"


# ============================================================================
# DETECTION CLEANING
# ============================================================================

def prepare_detections(
    ocr_result: Dict[str, Any],
) -> List[Dict[str, Any]]:

    if not isinstance(ocr_result, dict):
        return []

    detections = ocr_result.get("detections", [])

    if not isinstance(detections, list):
        return []

    try:
        cleaned = clean_detections(detections)
    except Exception as exc:
        print(f"⚠️ Text cleaning failed: {exc}")
        cleaned = detections

    return cleaned if isinstance(cleaned, list) else []


# ============================================================================
# SAFE FIELD REPAIR
# ============================================================================

def repair_known_cross_line_fields(
    fields: Dict[str, Any],
    detections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Repairs only values explicitly present in nearby OCR detections.

    Handles examples such as:

        MRP
        ₹99.00

    and:

        MANUFACTURED & MARKETED BY:
        Healthy Bites Foods Pvt. Ltd.

    No values are invented.
    """

    repaired = dict(fields or {})

    if not isinstance(detections, list):
        return repaired

    # ------------------------------------------------------------------------
    # MRP
    # ------------------------------------------------------------------------

    if not field_is_usable(repaired.get("mrp")):

        for index, detection in enumerate(detections):

            text = get_detection_text(detection)

            if not text:
                continue

            if not re.search(
                r"\bM\s*\.?\s*R\s*\.?\s*P\b",
                text,
                re.IGNORECASE,
            ):
                continue

            # Same-line MRP
            match = re.search(
                r"(?:₹|Rs\.?|INR)?\s*"
                r"([0-9]+(?:\.[0-9]{1,2})?)",
                text,
                re.IGNORECASE,
            )

            if match:

                amount = match.group(1)

                repaired["mrp"] = {
                    "field": "mrp",
                    "value": amount,
                    "parsed": {
                        "amount": float(amount),
                        "currency": "INR",
                    },
                    "state": "present",
                    "reliability": safe_float(
                        detection.get("confidence", 0)
                    ),
                    "note": "MRP extracted from the MRP OCR line.",
                    "source_text": [text],
                }

                break

            # Next OCR lines
            for neighbor in detections[
                index + 1 : min(index + 4, len(detections))
            ]:

                neighbor_text = get_detection_text(neighbor)

                if not neighbor_text:
                    continue

                # Do not cross into another known field.
                if re.search(
                    r"\b("
                    r"net\s*(?:qty|quantity|weight)"
                    r"|manufacturing\s*date"
                    r"|mfg"
                    r"|mfd"
                    r"|best\s*before"
                    r"|manufactured\s*&\s*marketed\s*by"
                    r"|ingredients"
                    r"|batch\s*(?:no|number)"
                    r")\b",
                    neighbor_text,
                    re.IGNORECASE,
                ):
                    break

                value_match = re.search(
                    r"(?:₹|Rs\.?|INR|:|：)?\s*"
                    r"([0-9]+(?:\.[0-9]{1,2})?)",
                    neighbor_text,
                    re.IGNORECASE,
                )

                if not value_match:
                    continue

                amount = value_match.group(1)

                confidences = [
                    safe_float(
                        detection.get("confidence", 0)
                    ),
                    safe_float(
                        neighbor.get("confidence", 0)
                    ),
                ]

                confidences = [
                    value for value in confidences
                    if value > 0
                ]

                reliability = (
                    min(confidences)
                    if confidences
                    else 0.0
                )

                repaired["mrp"] = {
                    "field": "mrp",
                    "value": amount,
                    "parsed": {
                        "amount": float(amount),
                        "currency": "INR",
                    },
                    "state": "present",
                    "reliability": round(
                        reliability,
                        3,
                    ),
                    "note": (
                        "MRP label and numeric value were "
                        "detected on adjacent OCR lines."
                    ),
                    "source_text": [
                        text,
                        neighbor_text,
                    ],
                }

                break

            if field_is_usable(repaired.get("mrp")):
                break

    # ------------------------------------------------------------------------
    # MANUFACTURER
    # ------------------------------------------------------------------------

    manufacturer = repaired.get("manufacturer")

    manufacturer_value = ""

    if isinstance(manufacturer, dict):
        manufacturer_value = normalize_text(
            manufacturer.get("value", "")
        )

    invalid_manufacturer_values = {
        "",
        ":",
        "：",
        "-",
        "_",
        "|",
    }

    if manufacturer_value in invalid_manufacturer_values:

        for index, detection in enumerate(detections):

            text = get_detection_text(detection)

            if not text:
                continue

            if not re.search(
                r"\b("
                r"manufactured\s*&\s*marketed\s*by"
                r"|manufactured\s*by"
                r"|marketed\s*by"
                r"|packed\s*by"
                r"|mfd\s*by"
                r")\b",
                text,
                re.IGNORECASE,
            ):
                continue

            # Same-line manufacturer
            same_line = re.search(
                r"\b("
                r"manufactured\s*&\s*marketed\s*by"
                r"|manufactured\s*by"
                r"|marketed\s*by"
                r"|packed\s*by"
                r"|mfd\s*by"
                r")\b"
                r"\s*[:\-]?\s*(.+)$",
                text,
                re.IGNORECASE,
            )

            if same_line:

                value = normalize_text(
                    same_line.group(2)
                )

                if value not in invalid_manufacturer_values:

                    repaired["manufacturer"] = {
                        "field": "manufacturer",
                        "value": value,
                        "parsed": None,
                        "state": "present",
                        "reliability": safe_float(
                            detection.get("confidence", 0)
                        ),
                        "note": (
                            "Manufacturer value found on "
                            "the same OCR line."
                        ),
                        "source_text": [text],
                    }

                    break

            # Adjacent manufacturer value
            for neighbor in detections[
                index + 1 : min(index + 5, len(detections))
            ]:

                neighbor_text = get_detection_text(neighbor)

                if not neighbor_text:
                    continue

                if re.search(
                    r"\b("
                    r"fssai"
                    r"|lic(?:ense)?\s*no"
                    r"|mrp"
                    r"|net\s*(?:qty|quantity|weight)"
                    r"|best\s*before"
                    r"|manufacturing\s*date"
                    r"|mfg"
                    r"|mfd"
                    r"|batch\s*(?:no|number)"
                    r"|ingredients"
                    r"|nutrition"
                    r")\b",
                    neighbor_text,
                    re.IGNORECASE,
                ):
                    break

                if neighbor_text in invalid_manufacturer_values:
                    continue

                # Avoid selecting pure numbers/dates.
                if re.fullmatch(
                    r"[\d\s/.\-]+",
                    neighbor_text,
                ):
                    continue

                confidences = [
                    safe_float(
                        detection.get("confidence", 0)
                    ),
                    safe_float(
                        neighbor.get("confidence", 0)
                    ),
                ]

                confidences = [
                    value for value in confidences
                    if value > 0
                ]

                reliability = (
                    min(confidences)
                    if confidences
                    else 0.0
                )

                repaired["manufacturer"] = {
                    "field": "manufacturer",
                    "value": neighbor_text,
                    "parsed": None,
                    "state": "present",
                    "reliability": round(
                        reliability * 0.95,
                        3,
                    ),
                    "note": (
                        "Manufacturer label and company name "
                        "were detected on adjacent OCR lines."
                    ),
                    "source_text": [
                        text,
                        neighbor_text,
                    ],
                }

                break

            if field_is_usable(
                repaired.get("manufacturer")
            ):
                break

    return repaired


# ============================================================================
# FIELD EXTRACTION
# ============================================================================

def extract_and_repair_fields(
    detections: List[Dict[str, Any]],
) -> Dict[str, Any]:

    try:
        fields = extract_fields(detections)
    except Exception as exc:
        print(f"⚠️ Field extraction failed: {exc}")
        fields = {}

    return repair_known_cross_line_fields(
        fields,
        detections,
    )


# ============================================================================
# SCORING
# ============================================================================

def calculate_attempt_score(
    fields: Dict[str, Any],
    ocr_result: Dict[str, Any],
) -> float:

    try:
        return float(
            score_attempt(
                fields,
                ocr_result,
            )
        )
    except Exception:

        # Fallback score.
        #
        # Field completeness dominates OCR confidence.
        field_score = (
            count_usable_fields(fields) * 10.0
        )

        confidence_score = (
            get_attempt_average_confidence(
                ocr_result
            )
        )

        return field_score + confidence_score


def result_rank(
    fields: Dict[str, Any],
    ocr_result: Dict[str, Any],
    score: float,
) -> Tuple[int, float, float]:

    """
    Result selection priority:

        1. Number of required fields
        2. Attempt score
        3. OCR confidence
    """

    return (
        count_usable_fields(fields),
        score,
        get_attempt_average_confidence(
            ocr_result
        ),
    )


# ============================================================================
# STRONG RESULT / EARLY STOP
# ============================================================================

def is_strong_result(
    fields: Dict[str, Any],
    ocr_result: Dict[str, Any],
    score: float,
) -> bool:

    del score

    if count_usable_fields(fields) != REQUIRED_FIELD_COUNT:
        return False

    return (
        get_attempt_average_confidence(ocr_result)
        >= MIN_STRONG_OCR_CONFIDENCE
    )


def should_stop_early(
    fields: Dict[str, Any],
    ocr_result: Dict[str, Any],
) -> bool:

    if count_usable_fields(fields) != REQUIRED_FIELD_COUNT:
        return False

    return (
        get_attempt_average_confidence(ocr_result)
        >= MIN_OCR_CONFIDENCE_FOR_ACCEPT
    )


# ============================================================================
# OCR ATTEMPT
# ============================================================================

def run_ocr_attempt(
    engine: OCREngine,
    image: Any,
    preprocessing_name: str,
    preprocessing_function: Any,
    quality: Any = None,
) -> Tuple[
    Dict[str, Any],
    List[Dict[str, Any]],
    Dict[str, Any],
    float,
]:

    print(f"🔎 {preprocessing_name}")

    start = time.perf_counter()

    # Preprocessing
    if quality is not None:
        processed_image = preprocessing_function(
            image,
            quality=quality,
        )
    else:
        processed_image = preprocessing_function(image)

    preprocessing_time = time.perf_counter() - start

    # OCR
    ocr_start = time.perf_counter()

    ocr_result = engine.run(
        processed_image
    )

    ocr_time = time.perf_counter() - ocr_start

    # Cleaning
    cleaned = prepare_detections(
        ocr_result
    )

    # Extraction
    fields = extract_and_repair_fields(
        cleaned
    )

    # Scoring
    score = calculate_attempt_score(
        fields,
        ocr_result,
    )

    total_time = time.perf_counter() - start

    print(
        f"   Preprocessing: {preprocessing_time:.3f}s"
    )

    print(
        f"   PaddleOCR: {ocr_time:.3f}s"
    )

    print(
        f"   Detections: {len(cleaned)}"
    )

    print(
        f"   Confidence: "
        f"{get_attempt_average_confidence(ocr_result):.3f}"
    )

    print(
        f"   Required fields: "
        f"{count_usable_fields(fields)}/"
        f"{REQUIRED_FIELD_COUNT}"
    )

    print(
        f"   Score: {score:.3f}"
    )

    return (
        ocr_result,
        cleaned,
        fields,
        score,
    )


# ============================================================================
# FRONTEND ROUTING
# ============================================================================

def frontend_result(
    action: str,
    reason: str,
    user_message: str,
    instruction: str,
    send: bool = False,
) -> Dict[str, Any]:

    labels = {
        "ACCEPT": "🟢 Image Accepted",
        "RETAKE": "📸 Retake Photo",
        "REVIEW": "🟡 Review Required",
    }

    next_steps = {
        "ACCEPT": "SEND_TO_FEATURE_ENGINEERING",
        "RETAKE": "REQUEST_RETAKE",
        "REVIEW": "REQUEST_MANUAL_REVIEW",
    }

    return {
        "action": action,
        "label": labels[action],
        "next_step": next_steps[action],
        "send_to_feature_engineering": send,
        "reason": reason,
        "user_message": user_message,
        "frontend_instruction": instruction,
    }


def determine_frontend_action(
    quality: Any,
    fields: Dict[str, Any],
    validation: Dict[str, Any],
    compliance: Dict[str, Any],
    readability: Dict[str, Any],
    ocr_quality: Dict[str, Any],
) -> Dict[str, Any]:

    del quality
    del readability

    usable_fields = count_usable_fields(fields)

    missing_required = get_missing_required_fields(
        fields
    )

    counts = count_validation_states(
        validation
    )

    valid_fields = counts["valid"]
    suspicious_fields = counts["suspicious"]
    invalid_fields = counts["invalid"]
    missing_fields = counts["missing"]

    avg_confidence = safe_float(
        ocr_quality.get(
            "avg_ocr_confidence",
            0.0,
        )
        if isinstance(oCR_quality := ocr_quality, dict)
        else 0.0
    )

    compliance_decision = str(
        compliance.get(
            "decision",
            "needs_review",
        )
    ).lower().strip()

    # ------------------------------------------------------------------------
    # 1. ACCEPT
    #
    # ALL FIVE must be:
    #   - extracted
    #   - valid
    #   - sufficiently readable
    #   - confidence acceptable
    # ------------------------------------------------------------------------

    if (
        usable_fields == REQUIRED_FIELD_COUNT
        and valid_fields == REQUIRED_FIELD_COUNT
        and suspicious_fields == 0
        and invalid_fields == 0
        and missing_fields == 0
        and avg_confidence >= MIN_OCR_CONFIDENCE_FOR_ACCEPT
    ):

        return frontend_result(
            action="ACCEPT",
            reason=(
                "All five required compliance fields were "
                "successfully extracted and passed validation."
            ),
            user_message=(
                "Product information was successfully "
                "extracted and verified."
            ),
            instruction=(
                "Display the extracted values and continue "
                "to Feature Engineering."
            ),
            send=True,
        )

    # ------------------------------------------------------------------------
    # 2. ZERO FIELDS
    # ------------------------------------------------------------------------

    if usable_fields == 0:

        return frontend_result(
            action="RETAKE",
            reason=(
                "No required compliance fields could be "
                "reliably extracted."
            ),
            user_message=(
                "Please retake the photo. Make sure the "
                "complete product label is visible, well lit, "
                "and in focus."
            ),
            instruction=(
                "Ask the user to capture another image."
            ),
        )

    # ------------------------------------------------------------------------
    # 3. MISSING FIELDS
    # ------------------------------------------------------------------------

    if missing_fields > 0 or missing_required:

        names = (
            ", ".join(missing_required)
            if missing_required
            else "one or more required fields"
        )

        return frontend_result(
            action="RETAKE",
            reason=(
                f"Required field(s) could not be reliably "
                f"extracted: {names}."
            ),
            user_message=(
                "Some required product information could "
                "not be read. Please retake the photo with "
                "the complete label clearly visible."
            ),
            instruction=(
                "Ask the user to capture another image."
            ),
        )

    # ------------------------------------------------------------------------
    # 4. INVALID / SUSPICIOUS VALUES
    #
    # Important:
    # All fields may be present but the values can still be
    # unreliable. That is REVIEW, not ACCEPT.
    # ------------------------------------------------------------------------

    if invalid_fields > 0 or suspicious_fields > 0:

        return frontend_result(
            action="REVIEW",
            reason=(
                f"All required fields were detected, but "
                f"{invalid_fields} invalid and "
                f"{suspicious_fields} suspicious value(s) "
                f"require verification."
            ),
            user_message=(
                "The product information was extracted, "
                "but some values need verification before "
                "a compliance decision can be made."
            ),
            instruction=(
                "Display the extracted values and request "
                "manual verification."
            ),
        )

    # ------------------------------------------------------------------------
    # 5. LOW CONFIDENCE
    # ------------------------------------------------------------------------

    if avg_confidence < MIN_OCR_CONFIDENCE_FOR_ACCEPT:

        return frontend_result(
            action="RETAKE",
            reason=(
                "OCR confidence is too low to safely "
                "pass the extracted information forward."
            ),
            user_message=(
                "The label text is difficult to read. "
                "Please retake the photo with better focus "
                "and lighting."
            ),
            instruction=(
                "Ask the user to capture another image."
            ),
        )

    # ------------------------------------------------------------------------
    # 6. COMPLIANCE REVIEW
    # ------------------------------------------------------------------------

    if compliance_decision in {
        "non_compliant",
        "needs_review",
        "review",
    }:

        return frontend_result(
            action="REVIEW",
            reason=(
                "The extracted information requires "
                "manual verification before forwarding."
            ),
            user_message=(
                "The product information was extracted, "
                "but manual verification is required."
            ),
            instruction=(
                "Display the extracted fields and "
                "request manual verification."
            ),
        )

    # ------------------------------------------------------------------------
    # 7. SAFE DEFAULT
    # ------------------------------------------------------------------------

    return frontend_result(
        action="REVIEW",
        reason=(
            "The OCR result could not be safely classified "
            "as fully verified."
        ),
        user_message=(
            "The product information requires manual "
            "verification."
        ),
        instruction=(
            "Display the extracted information for review."
        ),
    )


# ============================================================================
# IMAGE VALIDATION
# ============================================================================

def validate_image_path(image_path: str) -> Path:

    if not image_path:
        raise ValueError(
            "Image path cannot be empty."
        )

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Could not read image: {image_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Image path is not a file: {image_path}"
        )

    try:
        size_mb = (
            path.stat().st_size
            / (1024 * 1024)
        )
    except OSError:
        size_mb = 0.0

    if size_mb > MAX_IMAGE_FILE_SIZE_MB:
        raise ValueError(
            f"Image file is too large "
            f"({size_mb:.1f} MB). Maximum allowed is "
            f"{MAX_IMAGE_FILE_SIZE_MB} MB."
        )

    return path


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run(
    image_path: str,
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:

    pipeline_start = time.perf_counter()

    image_path_obj = validate_image_path(
        image_path
    )

    image_path = str(image_path_obj)

    print()
    print("=" * 72)
    print("🚀 SIH PACKAGED-COMMODITY OCR PIPELINE")
    print("=" * 72)
    print(f"📷 Image: {image_path}")

    # ------------------------------------------------------------------------
    # Load image
    # ------------------------------------------------------------------------

    load_start = time.perf_counter()

    image = cv2.imread(image_path)

    image_load_time = (
        time.perf_counter() - load_start
    )

    if image is None:
        raise FileNotFoundError(
            f"Could not read image: {image_path}"
        )

    height, width = image.shape[:2]

    print(
        f"📐 Resolution: {width} x {height}"
    )

    # ------------------------------------------------------------------------
    # Stage 9: Quality
    # ------------------------------------------------------------------------

    print()
    print("🔎 Stage 9: Checking image quality...")

    quality_start = time.perf_counter()

    quality = check_image_quality(
        image
    )

    quality_time = (
        time.perf_counter() - quality_start
    )

    print(
        f"   Quality check: {quality_time:.3f}s"
    )

    if quality.is_low_quality:

        print("⚠️ Image quality warnings:")

        for message in quality.messages or []:
            print(f"   • {message}")

    else:
        print("✅ Image quality checks passed.")

    # ------------------------------------------------------------------------
    # OCR engine
    # ------------------------------------------------------------------------

    engine = get_ocr_engine(
        confidence_threshold
    )

    # ------------------------------------------------------------------------
    # ATTEMPT 1
    # ------------------------------------------------------------------------

    print()
    print("🔎 Attempt 1: Adaptive preprocessing...")

    attempt1_start = time.perf_counter()

    (
        ocr_result,
        cleaned_detections,
        fields,
        best_score,
    ) = run_ocr_attempt(
        engine=engine,
        image=image,
        preprocessing_name="Adaptive preprocessing",
        preprocessing_function=adaptive_preprocess,
        quality=quality,
    )

    attempt1_time = (
        time.perf_counter() - attempt1_start
    )

    best_bundle = (
        ocr_result,
        cleaned_detections,
        fields,
        "adaptive",
    )

    # ------------------------------------------------------------------------
    # EARLY STOP AFTER ATTEMPT 1
    # ------------------------------------------------------------------------

    early_stop = False

    if is_strong_result(
        fields,
        ocr_result,
        best_score,
    ):

        early_stop = True

        print()
        print(
            "⚡ Stage 10 early-stop triggered."
        )

        print(
            "   All five fields are present with strong confidence."
        )

        print(
            "   Skipping alternate and recovery OCR."
        )

    elif should_stop_early(
        fields,
        ocr_result,
    ):

        early_stop = True

        print()
        print(
            "⚡ Stage 10 early-stop triggered."
        )

        print(
            "   All five required fields are available."
        )

    # ------------------------------------------------------------------------
    # ATTEMPT 2
    # ------------------------------------------------------------------------

    attempt2_time = 0.0

    if (
        not early_stop
        and ENABLE_ALTERNATE_ATTEMPT
    ):

        print()
        print(
            "🔄 Attempt 2: Alternate preprocessing..."
        )

        attempt2_start = time.perf_counter()

        (
            alt_ocr_result,
            alt_cleaned,
            alt_fields,
            alt_score,
        ) = run_ocr_attempt(
            engine=engine,
            image=image,
            preprocessing_name="Alternate preprocessing",
            preprocessing_function=alternate_preprocess,
        )

        attempt2_time = (
            time.perf_counter() - attempt2_start
        )

        current_rank = result_rank(
            fields,
            ocr_result,
            best_score,
        )

        alternate_rank = result_rank(
            alt_fields,
            alt_ocr_result,
            alt_score,
        )

        if alternate_rank > current_rank:

            best_bundle = (
                alt_ocr_result,
                alt_cleaned,
                alt_fields,
                "alternate",
            )

            ocr_result = alt_ocr_result
            cleaned_detections = alt_cleaned
            fields = alt_fields
            best_score = alt_score

            print(
                "   ✅ Alternate result selected."
            )

        else:

            print(
                "   ℹ️ Adaptive result retained."
            )

        if is_strong_result(
            fields,
            ocr_result,
            best_score,
        ):

            early_stop = True

            print(
                "⚡ Strong result found after Attempt 2."
            )

            print(
                "   Skipping recovery."
            )

    # ------------------------------------------------------------------------
    # RECOVERY
    # ------------------------------------------------------------------------

    recovery_time = 0.0
    recovery_attempts = 0

    if (
        not early_stop
        and ENABLE_RECOVERY
        and quality.is_low_quality
        and count_usable_fields(fields)
        < REQUIRED_FIELD_COUNT
    ):

        print()
        print(
            "🔄 Stage 9 recovery started..."
        )

        recovery_start = time.perf_counter()

        recovery_strategies = (
            aggressive_recovery_preprocess(
                image,
                quality,
            )
        )

        for strategy_name, recovered_image in (
            recovery_strategies
        ):

            recovery_attempts += 1

            print(
                f"\n   → Recovery: {strategy_name}"
            )

            recovery_ocr = engine.run(
                recovered_image
            )

            recovery_cleaned = (
                prepare_detections(
                    recovery_ocr
                )
            )

            recovery_fields = (
                extract_and_repair_fields(
                    recovery_cleaned
                )
            )

            recovery_score = calculate_attempt_score(
                recovery_fields,
                recovery_ocr,
            )

            print(
                f"      Score: {recovery_score:.3f}"
            )

            print(
                f"      Required fields: "
                f"{count_usable_fields(recovery_fields)}/"
                f"{REQUIRED_FIELD_COUNT}"
            )

            current_rank = result_rank(
                fields,
                ocr_result,
                best_score,
            )

            recovery_rank = result_rank(
                recovery_fields,
                recovery_ocr,
                recovery_score,
            )

            if recovery_rank > current_rank:

                best_bundle = (
                    recovery_ocr,
                    recovery_cleaned,
                    recovery_fields,
                    f"recovery_{strategy_name}",
                )

                ocr_result = recovery_ocr
                cleaned_detections = recovery_cleaned
                fields = recovery_fields
                best_score = recovery_score

                print(
                    "      ✅ Recovery result selected."
                )

            # Stop once 5/5 is found.
            if (
                count_usable_fields(fields)
                == REQUIRED_FIELD_COUNT
            ):

                print()
                print(
                    "✅ Recovery found all five required fields."
                )

                break

        recovery_time = (
            time.perf_counter() - recovery_start
        )

    # ------------------------------------------------------------------------
    # FINAL RESULT BUNDLE
    # ------------------------------------------------------------------------

    (
        ocr_result,
        cleaned_detections,
        fields,
        preprocessing_attempt_used,
    ) = best_bundle

    # Final safe repair.
    fields = repair_known_cross_line_fields(
        fields,
        cleaned_detections,
    )

    # ------------------------------------------------------------------------
    # FIELD COUNT
    # ------------------------------------------------------------------------

    fields_present = count_usable_fields(
        fields
    )

    field_count = {
        "found": fields_present,
        "present": fields_present,
        "required": REQUIRED_FIELD_COUNT,
        "complete": (
            fields_present
            == REQUIRED_FIELD_COUNT
        ),
    }

    print()
    print("=" * 72)
    print(
        f"📋 Final extracted fields: "
        f"{fields_present}/{REQUIRED_FIELD_COUNT}"
    )

    # ------------------------------------------------------------------------
    # Readability
    # ------------------------------------------------------------------------

    readability = summarize_readability(
        fields
    )

    # ------------------------------------------------------------------------
    # Stage 11.2: Validation
    # ------------------------------------------------------------------------

    print()
    print(
        "🔎 Stage 11.2: Validating extracted values..."
    )

    validation_start = time.perf_counter()

    validation = validate_extracted_fields(
        fields
    )

    validation_time = (
        time.perf_counter() - validation_start
    )

    validation_counts = count_validation_states(
        validation
    )

    print(
        f"   Valid: {validation_counts['valid']}"
    )

    print(
        f"   Suspicious: "
        f"{validation_counts['suspicious']}"
    )

    print(
        f"   Invalid: "
        f"{validation_counts['invalid']}"
    )

    print(
        f"   Missing: "
        f"{validation_counts['missing']}"
    )

    # ------------------------------------------------------------------------
    # Stage 12: Compliance
    # ------------------------------------------------------------------------

    print()
    print(
        "📋 Stage 12: Evaluating compliance..."
    )

    compliance_start = time.perf_counter()

    compliance = evaluate_compliance(
        validation
    )

    compliance_time = (
        time.perf_counter() - compliance_start
    )

    print(
        f"   Decision: "
        f"{compliance.get('decision', 'unknown')}"
    )

    # ------------------------------------------------------------------------
    # OCR quality
    # ------------------------------------------------------------------------

    combined_quality = combined_quality_verdict(
        image_is_low_quality=quality.is_low_quality,
        image_quality_messages=quality.messages,
        detections=cleaned_detections,
    )

    combined_quality_dict = (
        combined_quality.to_dict()
    )

    # ------------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------------

    status = build_status_summary(
        image_is_low_quality=quality.is_low_quality,
        image_quality_messages=quality.messages,
        ocr_quality=combined_quality,
        readability=readability,
    )

    # ------------------------------------------------------------------------
    # Stage 13: Frontend
    # ------------------------------------------------------------------------

    print()
    print(
        "📱 Stage 13: Determining frontend action..."
    )

    frontend_action = determine_frontend_action(
        quality=quality,
        fields=fields,
        validation=validation,
        compliance=compliance,
        readability=readability,
        ocr_quality=combined_quality_dict,
    )

    print(
        f"➡️ Frontend action: "
        f"{frontend_action['action']}"
    )

    # ------------------------------------------------------------------------
    # Feature-engineering handoff
    # ------------------------------------------------------------------------

    send_to_feature_engineering = bool(
        frontend_action[
            "send_to_feature_engineering"
        ]
    )

    raw_text = "\n".join(
        detection.get("text", "")
        for detection in cleaned_detections
    )

    feature_engineering_handoff = {
        "send": send_to_feature_engineering,
        "image_path": (
            image_path
            if send_to_feature_engineering
            else None
        ),
        "reason": frontend_action["reason"],
        "ocr_data": (
            {
                "raw_text": raw_text,
                "detections": cleaned_detections,
                "fields": fields,
                "field_count": field_count,
                "readability": readability,
                "validation": validation,
                "compliance": compliance,
            }
            if send_to_feature_engineering
            else None
        ),
    }

    # ------------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------------

    total_time = (
        time.perf_counter() - pipeline_start
    )

    performance = {
        "image_loading_seconds": round(
            image_load_time,
            3,
        ),
        "quality_check_seconds": round(
            quality_time,
            3,
        ),
        "attempt_1_seconds": round(
            attempt1_time,
            3,
        ),
        "attempt_2_seconds": round(
            attempt2_time,
            3,
        ),
        "recovery_seconds": round(
            recovery_time,
            3,
        ),
        "recovery_attempts": recovery_attempts,
        "validation_seconds": round(
            validation_time,
            3,
        ),
        "compliance_seconds": round(
            compliance_time,
            3,
        ),
        "total_seconds": round(
            total_time,
            3,
        ),
    }

    print()
    print("⏱️ PIPELINE TIMING")

    for name, value in performance.items():
        if name != "recovery_attempts":
            print(
                f"   {name}: {value}"
            )

    print(
        f"   recovery_attempts: "
        f"{recovery_attempts}"
    )

    # ------------------------------------------------------------------------
    # Final return
    # ------------------------------------------------------------------------

    return {
        "success": True,

        "image_path": image_path,

        # Frontend
        "action": frontend_action["action"],
        "label": frontend_action["label"],
        "next_step": frontend_action["next_step"],
        "user_message": frontend_action["user_message"],
        "frontend_instruction": (
            frontend_action[
                "frontend_instruction"
            ]
        ),
        "send_to_feature_engineering": (
            send_to_feature_engineering
        ),

        # Quality
        "quality": {
            "is_low_quality": quality.is_low_quality,
            "messages": quality.messages,
            "blur_score": quality.blur_score,
            "brightness": quality.brightness,
        },

        # OCR quality
        "ocr_quality": combined_quality_dict,

        # Status
        "status": status,

        # Preprocessing
        "preprocessing_attempt_used": (
            preprocessing_attempt_used
        ),

        "best_score": round(
            best_score,
            3,
        ),

        # Fields
        "field_count": field_count,

        # OCR
        "raw_text": raw_text,
        "detections": cleaned_detections,

        # Extracted fields
        "fields": fields,

        # Readability
        "readability": readability,

        # Validation
        "validation": validation,

        # Compliance
        "compliance": compliance,

        # Frontend routing
        "frontend_action": frontend_action,

        # Feature engineering
        "feature_engineering": (
            feature_engineering_handoff
        ),

        # Performance
        "performance": performance,
    }


# ============================================================================
# COMMAND LINE
# ============================================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "SIH packaged-commodity OCR pipeline."
        )
    )

    parser.add_argument(
        "image",
        help="Path to product/label image.",
    )

    parser.add_argument(
        "--out",
        default=None,
        help="Optional JSON output path.",
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="Minimum OCR confidence threshold.",
    )

    args = parser.parse_args()

    if not 0.0 <= args.confidence <= 1.0:
        parser.error(
            "--confidence must be between 0.0 and 1.0"
        )

    try:

        result = run(
            image_path=args.image,
            confidence_threshold=args.confidence,
        )

    except FileNotFoundError as exc:

        result = {
            "success": False,
            "image_path": args.image,
            "action": "RETAKE",
            "label": "📸 Retake Photo",
            "next_step": "REQUEST_RETAKE",
            "send_to_feature_engineering": False,
            "reason": str(exc),
            "user_message": (
                "The image could not be read. "
                "Please check the image path and try again."
            ),
            "frontend_instruction": (
                "Ask the user to provide a valid image."
            ),
            "error": {
                "type": "image_not_found",
                "message": str(exc),
            },
        }

    except ValueError as exc:

        result = {
            "success": False,
            "image_path": args.image,
            "action": "RETAKE",
            "label": "📸 Retake Photo",
            "next_step": "REQUEST_RETAKE",
            "send_to_feature_engineering": False,
            "reason": str(exc),
            "user_message": (
                "The image could not be processed correctly. "
                "Please provide a valid product image."
            ),
            "frontend_instruction": (
                "Ask the user to provide another image."
            ),
            "error": {
                "type": "invalid_image",
                "message": str(exc),
            },
        }

    except Exception as exc:

        print()
        print("❌ Pipeline failed:")
        print(
            f"   {type(exc).__name__}: {exc}"
        )

        result = {
            "success": False,
            "image_path": args.image,
            "action": "RETAKE",
            "label": "📸 Retake Photo",
            "next_step": "REQUEST_RETAKE",
            "send_to_feature_engineering": False,
            "reason": "Unexpected OCR pipeline error.",
            "user_message": (
                "The image could not be processed correctly. "
                "Please retake the photo and try again."
            ),
            "frontend_instruction": (
                "Ask the user to capture another image."
            ),
            "error": {
                "type": "pipeline_error",
                "message": str(exc),
            },
        }

    # ------------------------------------------------------------------------
    # Save JSON
    # ------------------------------------------------------------------------

    if args.out:

        output_path = Path(args.out)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                result,
                file,
                indent=2,
                ensure_ascii=False,
            )

        print()
        print(
            f"💾 JSON saved to: {output_path}"
        )

    # ------------------------------------------------------------------------
    # Console result
    # ------------------------------------------------------------------------

    print()
    print("=" * 72)
    print("📦 FINAL PIPELINE RESULT")
    print("=" * 72)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
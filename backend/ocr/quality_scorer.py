"""
quality_scorer.py
------------------

Combines:

    PRE-OCR:
        - blur
        - brightness
        - image-quality flags

    POST-OCR:
        - OCR confidence
        - number of detections

    POST-EXTRACTION:
        - required compliance fields
        - field readability

The required compliance fields are the PRIMARY signal for determining
whether extraction actually succeeded.

Required fields:

    1. MRP
    2. Net Quantity
    3. Manufacturing Date
    4. Best Before
    5. Manufacturer

Important principle:

    High OCR confidence != correct compliance extraction.

Therefore:

    5/5 usable fields -> success
    1-4 usable fields -> partial
    0 usable fields -> failed

Image-quality warnings are NON-BLOCKING when extraction succeeds.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# OCR confidence thresholds
# ---------------------------------------------------------------------------

GOOD_CONFIDENCE_THRESHOLD = 0.85
ACCEPTABLE_CONFIDENCE_THRESHOLD = 0.60


# ---------------------------------------------------------------------------
# Attempt scoring thresholds
# ---------------------------------------------------------------------------

RECOVERY_TRIGGER_SCORE = 35.0
RECOVERY_SUCCESS_SCORE = 45.0


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

TOTAL_REQUIRED_FIELDS = len(REQUIRED_FIELDS)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class CombinedQuality:
    """
    Combined OCR/image quality result.
    """

    avg_ocr_confidence: float
    num_detections: int

    image_flagged_low_quality: bool
    image_quality_messages: List[str]

    verdict: str  # "good" | "acceptable" | "poor"

    guidance: List[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dictionary."""
        return {
            "avg_ocr_confidence": round(
                self.avg_ocr_confidence,
                4,
            ),
            "num_detections": self.num_detections,
            "image_flagged_low_quality": self.image_flagged_low_quality,
            "image_quality_messages": list(
                self.image_quality_messages
            ),
            "verdict": self.verdict,
            "guidance": list(self.guidance),
        }


# ---------------------------------------------------------------------------
# OCR confidence
# ---------------------------------------------------------------------------

def _safe_confidence(value: Any) -> float:
    """
    Convert OCR confidence into a safe value between 0 and 1.

    PaddleOCR confidence should normally already be in [0, 1].
    Invalid values are treated as 0.
    """

    try:
        if value is None:
            return 0.0

        confidence = float(value)

        if confidence != confidence:  # NaN
            return 0.0

        if confidence < 0.0:
            return 0.0

        if confidence > 1.0:
            return 1.0

        return confidence

    except (TypeError, ValueError):
        return 0.0


def average_confidence(
    detections: List[Dict[str, Any]],
) -> float:
    """
    Calculate average OCR confidence safely.

    Empty detections return 0.0.
    """

    if not detections:
        return 0.0

    valid_confidences = [
        _safe_confidence(
            detection.get("confidence", 0.0)
        )
        for detection in detections
        if isinstance(detection, dict)
    ]

    if not valid_confidences:
        return 0.0

    return sum(valid_confidences) / len(valid_confidences)


# ---------------------------------------------------------------------------
# Combined image + OCR quality
# ---------------------------------------------------------------------------

def combined_quality_verdict(
    image_is_low_quality: bool,
    image_quality_messages: List[str],
    detections: List[Dict[str, Any]],
) -> CombinedQuality:
    """
    Combine image quality and OCR confidence.

    Important:

        OCR confidence is used to describe OCR quality.

        It is NOT used alone to determine compliance success.

    A flagged image can still receive "good" if OCR confidence is high.
    """

    if not isinstance(image_quality_messages, list):
        image_quality_messages = []

    if not isinstance(detections, list):
        detections = []

    avg_conf = average_confidence(detections)
    num_det = len(detections)

    # ---------------------------------------------------------
    # Determine OCR quality
    # ---------------------------------------------------------

    if num_det == 0:
        verdict = "poor"

    elif avg_conf >= GOOD_CONFIDENCE_THRESHOLD:
        verdict = "good"

    elif avg_conf >= ACCEPTABLE_CONFIDENCE_THRESHOLD:
        verdict = "acceptable"

    else:
        verdict = "poor"

    guidance: List[str] = []

    # ---------------------------------------------------------
    # Guidance
    # ---------------------------------------------------------

    if verdict == "poor":

        if num_det == 0:
            guidance.append(
                "No text could be detected. Make sure the product "
                "label is fully in frame, well-lit, focused, and unobstructed."
            )

        elif image_is_low_quality:
            # Image metrics and OCR both indicate a problem.
            guidance.extend(
                message
                for message in image_quality_messages
                if isinstance(message, str) and message.strip()
            )

            if not guidance:
                guidance.append(
                    "OCR confidence is low. Retake the image with "
                    "better focus, lighting, and framing."
                )

        else:
            # OCR struggled even though image heuristics passed.
            guidance.append(
                "Text recognition was unreliable even though the image "
                "quality checks passed. Try moving closer to the label, "
                "using better lighting, or holding the camera more steadily."
            )

    elif verdict == "acceptable" and image_is_low_quality:

        guidance.extend(
            message
            for message in image_quality_messages
            if isinstance(message, str) and message.strip()
        )

    return CombinedQuality(
        avg_ocr_confidence=avg_conf,
        num_detections=num_det,
        image_flagged_low_quality=bool(image_is_low_quality),
        image_quality_messages=image_quality_messages,
        verdict=verdict,
        guidance=guidance,
    )


# ---------------------------------------------------------------------------
# Image warning helper
# ---------------------------------------------------------------------------

def _issue_summary(messages: List[str]) -> str:
    """
    Convert detailed image-quality messages into a short diagnostic summary.

    Example:

        "Image is overexposed. Reduce glare/flash and retake."

    becomes:

        "Image is overexposed"
    """

    if not isinstance(messages, list):
        return "Image quality flagged"

    clauses: List[str] = []

    for message in messages:

        if not isinstance(message, str):
            continue

        message = message.strip()

        if not message:
            continue

        # Keep only the diagnostic sentence.
        first_clause = message.split(".", 1)[0].strip()

        if first_clause:
            clauses.append(first_clause)

    if not clauses:
        return "Image quality flagged"

    return "; ".join(clauses)


# ---------------------------------------------------------------------------
# Readability helpers
# ---------------------------------------------------------------------------

def _safe_count(
    readability: Dict[str, Any],
    key: str,
) -> int:
    """Safely extract a non-negative integer count."""

    try:
        value = int(
            readability.get(key, 0) or 0
        )

        return max(value, 0)

    except (TypeError, ValueError):
        return 0


def _normalise_total_fields(
    readability: Dict[str, Any],
) -> int:
    """
    Determine the total number of fields being checked.

    The pipeline normally reports 5.
    """

    try:
        total = int(
            readability.get(
                "total_fields_checked",
                TOTAL_REQUIRED_FIELDS,
            )
            or TOTAL_REQUIRED_FIELDS
        )

    except (TypeError, ValueError):
        total = TOTAL_REQUIRED_FIELDS

    return max(total, TOTAL_REQUIRED_FIELDS)


# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------

def build_status_summary(
    image_is_low_quality: bool,
    image_quality_messages: List[str],
    ocr_quality: CombinedQuality,
    readability: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compose:

        1. Image quality
        2. OCR quality
        3. Field readability

    into one frontend-ready status block.

    CRITICAL RULE:

        Required-field extraction determines success.

    Therefore:

        5/5 fields present
            -> success

        1-4 usable fields
            -> partial

        0 usable fields
            -> failed

    Image quality NEVER independently determines success.

    OCR confidence NEVER independently determines compliance success.
    """

    if not isinstance(readability, dict):
        readability = {}

    total_fields = _normalise_total_fields(
        readability
    )

    fields_present = min(
        _safe_count(readability, "fields_present"),
        total_fields,
    )

    fields_uncertain = _safe_count(
        readability,
        "fields_uncertain",
    )

    usable_fields = min(
        fields_present + fields_uncertain,
        total_fields,
    )

    # ---------------------------------------------------------
    # Determine extraction status
    # ---------------------------------------------------------

    if fields_present >= total_fields:

        ocr_status = "success"
        ocr_status_label = "🟢 Successfully extracted"

    elif usable_fields >= 1:

        ocr_status = "partial"
        ocr_status_label = "🟡 Partially extracted"

    else:

        ocr_status = "failed"
        ocr_status_label = "🔴 Extraction failed"

    # ---------------------------------------------------------
    # Determine retake requirement
    # ---------------------------------------------------------

    #
    # IMPORTANT:
    #
    # A successful 5/5 extraction should NOT trigger a retake simply
    # because the image-quality heuristic was flagged.
    #
    # Example:
    #
    #   overexposed image
    #   OCR confidence = 0.99
    #   5/5 fields extracted
    #
    # => success, no retake
    #

    needs_retake = (
        ocr_status == "failed"
        or (
            ocr_quality.verdict == "poor"
            and ocr_status != "success"
        )
    )

    # ---------------------------------------------------------
    # Readability labels
    # ---------------------------------------------------------

    readability_labels = {
        "fully_readable": "🟢 Fully readable",
        "mostly_readable": "🟡 Mostly readable",
        "partially_readable": "🟠 Partially readable",
        "unreadable": "🔴 Unreadable",
    }

    readability_overall = readability.get(
        "overall"
    )

    readability_label = readability_labels.get(
        readability_overall,
        readability_overall,
    )

    # ---------------------------------------------------------
    # User-facing messages
    # ---------------------------------------------------------

    retake_message: str | None = None
    image_warning: str | None = None

    if needs_retake:

        if ocr_quality.guidance:

            reason = " ".join(
                str(item).strip()
                for item in ocr_quality.guidance
                if str(item).strip()
            )

        else:

            reason = (
                "Please retake the photo with better focus, "
                "lighting, and framing."
            )

        retake_message = (
            "🔴 Unable to read the product label clearly. "
            + reason
        )

    elif (
        ocr_status == "success"
        and image_is_low_quality
    ):

        issue = _issue_summary(
            image_quality_messages
        )

        image_warning = (
            f"⚠️ {issue}, but all required fields were "
            "successfully extracted."
        )

    # ---------------------------------------------------------
    # Final frontend-ready object
    # ---------------------------------------------------------

    return {
        "ocr_status": ocr_status,
        "ocr_status_label": ocr_status_label,

        "readability_label": readability_label,

        "fields_present": fields_present,
        "fields_uncertain": fields_uncertain,
        "total_fields_checked": total_fields,

        "usable_fields": usable_fields,

        "needs_retake": needs_retake,

        "retake_message": retake_message,
        "image_warning": image_warning,

        # Useful for frontend/backend debugging.
        "ocr_quality_verdict": ocr_quality.verdict,
        "avg_ocr_confidence": round(
            ocr_quality.avg_ocr_confidence,
            4,
        ),
        "num_ocr_detections": ocr_quality.num_detections,
    }


# ---------------------------------------------------------------------------
# Stage 9 — Attempt scoring
# ---------------------------------------------------------------------------

def score_attempt(
    fields: Dict[str, Dict[str, Any]],
    ocr_result: Dict[str, Any],
) -> float:
    """
    Score an OCR attempt.

    Required-field extraction is the primary signal.
    OCR confidence is a secondary signal.

    Scoring:

        present   = 10 points
        uncertain = 3 points
        partial   = 1 point
        OCR confidence contributes up to 2 points

    Maximum theoretical score:

        5 * 10 + 2 = 52

    This score is intended for recovery/retry decisions and should NOT
    replace the final compliance validation result.
    """

    if not isinstance(fields, dict):
        fields = {}

    if not isinstance(ocr_result, dict):
        ocr_result = {}

    present = 0
    uncertain = 0
    partial = 0

    # Only score the five required compliance fields.
    for field_name in REQUIRED_FIELDS:

        field_data = fields.get(
            field_name,
            {},
        )

        if not isinstance(field_data, dict):
            continue

        state = str(
            field_data.get("state", "")
        ).strip().lower()

        if state == "present":
            present += 1

        elif state == "uncertain":
            uncertain += 1

        elif state == "partial":
            partial += 1

    detections = ocr_result.get(
        "detections",
        [],
    )

    if not isinstance(detections, list):
        detections = []

    avg_conf = average_confidence(
        detections
    )

    # Compliance fields are significantly more important than
    # raw OCR confidence.
    score = (
        present * 10.0
        + uncertain * 3.0
        + partial * 1.0
        + avg_conf * 2.0
    )

    return round(
        score,
        2,
    )


# ---------------------------------------------------------------------------
# Recovery decision helper
# ---------------------------------------------------------------------------

def should_trigger_recovery(
    fields: Dict[str, Dict[str, Any]],
    ocr_result: Dict[str, Any],
) -> bool:
    """
    Determine whether the OCR attempt should enter recovery/retry logic.

    A low attempt score indicates that another OCR/preprocessing strategy
    may be worthwhile.
    """

    score = score_attempt(
        fields,
        ocr_result,
    )

    return score < RECOVERY_TRIGGER_SCORE


def recovery_succeeded(
    fields: Dict[str, Dict[str, Any]],
    ocr_result: Dict[str, Any],
) -> bool:
    """
    Determine whether a recovery attempt produced a strong result.
    """

    score = score_attempt(
        fields,
        ocr_result,
    )

    return score >= RECOVERY_SUCCESS_SCORE


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # Example OCR detections.
    detections = [
        {
            "text": "MRP ₹50",
            "confidence": 0.99,
        },
        {
            "text": "Net Quantity 100 g",
            "confidence": 0.98,
        },
        {
            "text": "Mfg 06/2026",
            "confidence": 0.99,
        },
        {
            "text": "Best Before 12 Months",
            "confidence": 0.97,
        },
        {
            "text": "XYZ Foods Pvt Ltd",
            "confidence": 0.98,
        },
    ]

    # Image quality information.
    image_quality_messages = [
        "Image is overexposed. Reduce glare/flash and retake."
    ]

    # Calculate OCR quality.
    ocr_quality = combined_quality_verdict(
        image_is_low_quality=True,
        image_quality_messages=image_quality_messages,
        detections=detections,
    )

    # Example readability result.
    readability = {
        "overall": "fully_readable",
        "fields_present": 5,
        "fields_uncertain": 0,
        "total_fields_checked": 5,
    }

    status = build_status_summary(
        image_is_low_quality=True,
        image_quality_messages=image_quality_messages,
        ocr_quality=ocr_quality,
        readability=readability,
    )

    print("\nOCR QUALITY")
    print("=" * 60)
    print(
        ocr_quality.to_dict()
    )

    print("\nSTATUS SUMMARY")
    print("=" * 60)
    print(
        json.dumps(
            status,
            indent=2,
            ensure_ascii=False,
        )
    )

    # Example attempt score.
    fields = {
        "mrp": {"state": "present"},
        "net_quantity": {"state": "present"},
        "manufacturing_date": {"state": "present"},
        "best_before": {"state": "present"},
        "manufacturer": {"state": "present"},
    }

    ocr_result = {
        "detections": detections
    }

    print("\nATTEMPT SCORE")
    print("=" * 60)
    print(
        score_attempt(
            fields,
            ocr_result,
        )
    )

    print("\nRECOVERY REQUIRED")
    print("=" * 60)
    print(
        should_trigger_recovery(
            fields,
            ocr_result,
        )
    )
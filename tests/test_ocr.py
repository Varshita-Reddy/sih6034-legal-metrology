"""
test_ocr.py
-----------
Basic unit tests for the OCR module.

Run with:
    pytest tests/test_ocr.py -v

Note: tests for ocr_engine.OCREngine itself require paddleocr/paddlepaddle
to be installed and are skipped automatically if that dependency is
unavailable, so you can still test preprocessing + text_cleaner on their own.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from ocr.text_cleaner import clean_text, clean_currency, clean_quantity, clean_detections
from ocr.field_extractor import extract_fields, summarize_readability
from ocr.quality_scorer import combined_quality_verdict, average_confidence, build_status_summary
from ocr.accuracy_eval import character_error_rate, word_error_rate, evaluate_text, aggregate_results
from preprocessing.image_preprocess import (
    check_image_quality, resize_image, enhance_contrast, cap_max_dimension,
    alternate_preprocess,
)


# --------------------------------------------------------------------------- #
# text_cleaner tests
# --------------------------------------------------------------------------- #

def test_currency_correction():
    assert clean_currency("MRP ₹5O") == "MRP ₹50"
    assert clean_currency("Rs. 12O") == "Rs. 120"


def test_quantity_correction():
    assert clean_quantity("NET QUANTlTY 1OO g") == "NET QUANTlTY 100 g"
    assert clean_quantity("5OO ml") == "500 ml"


def test_plain_words_untouched():
    # "FOOD" contains an O but must NOT be numerically "corrected" — this
    # guards against the over-correction warned about in the project notes.
    result = clean_text("FOOD PRODUCTS OF INDIA")
    assert result.cleaned == "FOOD PRODUCTS OF INDIA"
    assert result.changed is False


def test_ordinary_words_ending_in_lookalike_unit_letters_untouched():
    # Regression test: found via a real spice-packet label. Words made
    # entirely of digit-lookalike letters (O/I/L/S/B/Z/G/T, matched
    # case-insensitively) — "cool", "tool", "bolt" — were getting
    # swallowed whole by the quantity pattern and corrupted (e.g.
    # "cool" -> "c00l") because they happened to end in a valid unit
    # letter like "l" for litres. A real OCR misread of a number always
    # keeps at least one genuine digit; a plain word never does.
    for phrase in [
        "Store in a cool, dry place away from direct sunlight.",
        "Use a tool to open this.",
        "Bolt the lid shut tightly.",
    ]:
        result = clean_text(phrase)
        assert result.cleaned == phrase, f"corrupted: {phrase!r} -> {result.cleaned!r}"
        assert result.changed is False


def test_combined_line():
    result = clean_text("MRP ₹5O NET QUANTITY 1OO g")
    assert "₹50" in result.cleaned
    assert "100 g" in result.cleaned


def test_clean_detections_preserves_bbox_and_confidence():
    detections = [
        {"text": "MRP ₹5O", "confidence": 0.97, "bbox": [10, 10, 100, 40]},
    ]
    cleaned = clean_detections(detections)
    assert cleaned[0]["text"] == "MRP ₹50"
    assert cleaned[0]["confidence"] == 0.97
    assert cleaned[0]["bbox"] == [10, 10, 100, 40]
    assert cleaned[0]["was_corrected"] is True


# --------------------------------------------------------------------------- #
# image_preprocess tests
# --------------------------------------------------------------------------- #

def _make_test_image(width=800, height=600, brightness=128, noise=False):
    img = np.full((height, width, 3), brightness, dtype=np.uint8)
    if noise:
        rng = np.random.default_rng(0)
        noise_arr = rng.integers(0, 255, img.shape, dtype=np.uint8)
        img = noise_arr
    return img


def test_quality_check_flags_dark_image():
    dark_img = _make_test_image(brightness=20)
    report = check_image_quality(dark_img)
    assert report.is_too_dark is True
    assert report.is_low_quality is True


def test_quality_check_flags_low_resolution():
    small_img = _make_test_image(width=100, height=80)
    report = check_image_quality(small_img)
    assert report.is_low_resolution is True


def test_quality_check_normal_image_not_flagged_dark_or_bright():
    normal_img = _make_test_image(brightness=140)
    report = check_image_quality(normal_img)
    assert report.is_too_dark is False
    assert report.is_too_bright is False


def test_resize_image_changes_width():
    img = _make_test_image(width=300, height=200)
    resized = resize_image(img, target_width=600)
    assert resized.shape[1] == 600


def test_cap_max_dimension_downscales_large_images():
    # Simulates a typical modern phone photo (e.g. 3000px wide).
    large_img = _make_test_image(width=3000, height=4000)
    capped = cap_max_dimension(large_img, max_dimension=1600)
    assert max(capped.shape[:2]) == 1600


def test_cap_max_dimension_leaves_small_images_untouched():
    small_img = _make_test_image(width=800, height=600)
    result = cap_max_dimension(small_img, max_dimension=1600)
    assert result.shape == small_img.shape


def test_enhance_contrast_runs_without_error():
    img = _make_test_image(width=200, height=200, noise=True)
    out = enhance_contrast(img)
    assert out.shape[:2] == img.shape[:2]


def test_alternate_preprocess_runs_without_error_and_preserves_size():
    img = _make_test_image(width=800, height=600)
    out = alternate_preprocess(img)
    assert out.shape[:2] == img.shape[:2]


# --------------------------------------------------------------------------- #
# field_extractor tests
# --------------------------------------------------------------------------- #

def _dets(*texts_with_conf):
    """Helper: build a minimal detections list from (text, confidence) pairs."""
    return [
        {"text": t, "confidence": c, "bbox": [0, 0, 0, 0]}
        for t, c in texts_with_conf
    ]


def test_two_fields_crammed_on_one_line_do_not_steal_each_others_value():
    # Regression test: real spice-packet label crammed both fields onto
    # one line: "Mfg Date: 03/2026 Best Before: 9 months from Mfg."
    # Searching the whole line for best_before's value pattern found the
    # earlier-appearing "03/2026" (the mfg date) instead of "9 months",
    # because the search wasn't scoped to start after the "Best Before"
    # keyword itself.
    detections = _dets(("Mfg Date: 03/2026 Best Before: 9 months from Mfg.", 0.99))
    fields = extract_fields(detections)
    assert fields["manufacturing_date"]["value"] == "03/2026"
    assert fields["best_before"]["value"] == "9 months from Mfg"


def test_field_present_when_keyword_and_value_together():
    detections = _dets(("MRP (incl. of all taxes): Rs 50", 0.98))
    fields = extract_fields(detections)
    assert fields["mrp"]["value"] == "50"
    assert fields["mrp"]["state"] == "present"


def test_manufacturing_date_full_year_not_truncated():
    # Regression test: an earlier version of the date regex matched only
    # "06/20" out of "06/2026" because the year group was capped at 2 digits.
    detections = _dets(("Mfg. Date: 06/2026", 0.91))
    fields = extract_fields(detections)
    assert fields["manufacturing_date"]["value"] == "06/2026"
    assert fields["manufacturing_date"]["state"] == "present"


def test_best_before_does_not_steal_neighboring_field_value():
    # Regression test: an earlier version's neighbor-search let "Best
    # Before:" (with no value of its own, e.g. due to occlusion) grab the
    # adjacent "Mfg. Date: 06/2026" line's value and misreport it as the
    # best-before date. It must instead report itself as "partial".
    detections = _dets(
        ("Mfg. Date: 06/2026", 0.91),
        ("Best Before:", 0.80),
        ("Packed by: XYZ Foods Pvt. Ltd.", 0.95),
    )
    fields = extract_fields(detections)
    assert fields["best_before"]["state"] == "partial"
    assert fields["best_before"]["value"] is None
    assert fields["manufacturing_date"]["value"] == "06/2026"


def test_field_partial_when_keyword_found_but_no_value_nearby():
    detections = _dets(("Best Before:", 0.80), ("BRAND XYZ FOODS", 0.99))
    fields = extract_fields(detections)
    assert fields["best_before"]["state"] == "partial"
    assert fields["best_before"]["reliability"] < 1.0


def test_field_missing_when_nothing_found():
    detections = _dets(("BRAND XYZ FOODS", 0.99), ("Crunchy Wheat Biscuits", 0.97))
    fields = extract_fields(detections)
    assert fields["mrp"]["state"] == "missing"
    assert fields["mrp"]["value"] is None
    assert fields["mrp"]["reliability"] == 0.0


def test_field_uncertain_when_value_found_without_label():
    # A currency-shaped value with no "MRP" keyword anywhere near it.
    detections = _dets(("Rs 50", 0.90), ("BRAND XYZ FOODS", 0.99))
    fields = extract_fields(detections)
    assert fields["mrp"]["state"] == "uncertain"
    assert fields["mrp"]["value"] == "50"


def test_mrp_does_not_false_positive_on_word_containing_rs():
    # Regression test: found via a real Lay's chips label. The unanchored
    # currency pattern matched the "rs" hiding inside "characters" and
    # fabricated a fake MRP of "0" from an unrelated batch-number sentence.
    detections = _dets(("characters 0f batch no. and sebelow.", 0.82))
    fields = extract_fields(detections)
    assert fields["mrp"]["state"] == "missing"
    assert fields["mrp"]["value"] is None


def test_best_before_recognizes_spelled_out_duration():
    # Regression test: real Indian packaged-food labels often spell out
    # the duration ("SIX MONTHS FROM MANUFACTURE") instead of using a
    # numeral. Found via a real Lay's chips label.
    detections = _dets(('"BEST BEFORE SIX MONTHS FROM MANUFACTURE"', 0.99))
    fields = extract_fields(detections)
    assert fields["best_before"]["state"] == "present"
    assert "SIX MONTHS" in fields["best_before"]["value"].upper()


def test_currency_cleaner_does_not_false_positive_on_word_containing_rs():
    # Same underlying bug as above, but in text_cleaner's independent
    # currency pattern.
    result = clean_text("characters 0f batch no. and sebelow.")
    assert result.cleaned == "characters 0f batch no. and sebelow."
    assert result.changed is False


def test_net_quantity_recognizes_net_weight_phrasing():
    # Regression test: real spice-packet label used "Net Weight:" instead
    # of "Net Qty"/"Net Quantity", which the original keyword pattern
    # didn't recognize at all.
    detections = _dets(("Net Weight: 50 g", 0.99))
    fields = extract_fields(detections)
    assert fields["net_quantity"]["state"] == "present"
    assert fields["net_quantity"]["value"] == "50"


def test_net_quantity_does_not_false_positive_on_cool_dry_place():
    # Full regression scenario from the real spice-packet test: with the
    # text_cleaner bug present, "cool" got corrupted to "c00l" upstream,
    # and net_quantity's value-only fallback then (wrongly) picked up
    # "00" from the corrupted word as an "uncertain" quantity value.
    detections = _dets(
        ("Net Weight: 50 g", 0.99),
        ("Store in a cool, dry place away from direct sunlight.", 0.99),
    )
    fields = extract_fields(detections)
    assert fields["net_quantity"]["value"] == "50"
    assert fields["net_quantity"]["state"] == "present"


def test_net_quantity_split_across_adjacent_lines():
    detections = _dets(("Net Quantity:", 0.9), ("100 g", 0.95))
    fields = extract_fields(detections)
    assert fields["net_quantity"]["state"] == "present"
    assert fields["net_quantity"]["value"] == "100"


def test_summarize_readability_fully_readable():
    detections = _dets(
        ("MRP (incl. of all taxes): Rs 50", 0.98),
        ("Net Quantity: 100 g", 0.97),
        ("Mfg. Date: 06/2026", 0.91),
        ("Best Before: 12 Months from Mfg.", 0.99),
        ("Packed by: XYZ Foods Pvt. Ltd.", 0.95),
    )
    fields = extract_fields(detections)
    summary = summarize_readability(fields)
    assert summary["overall"] == "fully_readable"
    assert summary["fields_present"] == 5
    assert summary["fields_missing"] == 0


def test_summarize_readability_unreadable_when_all_missing():
    detections = _dets(("some unrelated text", 0.9))
    fields = extract_fields(detections)
    summary = summarize_readability(fields)
    assert summary["overall"] == "unreadable"
    assert summary["fields_missing"] == 5


# --------------------------------------------------------------------------- #
# Structured "parsed" value tests
# --------------------------------------------------------------------------- #
# Downstream feature-extraction shouldn't have to re-parse "100 g" or
# "Rs 50" itself — these lock in the clean numeric/unit breakdown.

def test_parsed_mrp_is_numeric_with_currency():
    detections = _dets(("MRP (incl. of all taxes): Rs 50", 0.98))
    fields = extract_fields(detections)
    assert fields["mrp"]["parsed"] == {"amount": 50.0, "currency": "INR"}


def test_parsed_net_quantity_separates_amount_and_unit():
    detections = _dets(("Net Quantity: 100 g", 0.97))
    fields = extract_fields(detections)
    assert fields["net_quantity"]["parsed"] == {"amount": 100.0, "unit": "g"}


def test_parsed_net_quantity_normalizes_unit_aliases():
    # "kg", "ml", "litre" etc. should normalize consistently.
    detections = _dets(("Net Quantity: 2 litre", 0.97))
    fields = extract_fields(detections)
    assert fields["net_quantity"]["parsed"]["unit"] == "l"


def test_parsed_manufacturing_date_splits_month_and_year():
    detections = _dets(("Mfg. Date: 06/2026", 0.91))
    fields = extract_fields(detections)
    assert fields["manufacturing_date"]["parsed"] == {"month": 6, "year": 2026}


def test_parsed_best_before_duration_numeric():
    detections = _dets(("Best Before: 12 Months from Mfg.", 0.99))
    fields = extract_fields(detections)
    assert fields["best_before"]["parsed"] == {
        "amount": 12, "unit": "months", "reference": "manufacturing"
    }


def test_parsed_best_before_handles_spelled_out_numbers():
    # Regression coverage: real Indian labels spell out durations
    # ("SIX MONTHS FROM MANUFACTURE") instead of using digits.
    detections = _dets(('"BEST BEFORE SIX MONTHS FROM MANUFACTURE"', 0.99))
    fields = extract_fields(detections)
    assert fields["best_before"]["parsed"]["amount"] == 6
    assert fields["best_before"]["parsed"]["unit"] == "months"


def test_parsed_is_none_when_field_missing():
    detections = _dets(("BRAND XYZ FOODS", 0.99))
    fields = extract_fields(detections)
    assert fields["mrp"]["parsed"] is None


def test_parsed_manufacturer_stays_none_no_structure_expected():
    detections = _dets(("Packed by: XYZ Foods Pvt. Ltd.", 0.95))
    fields = extract_fields(detections)
    assert fields["manufacturer"]["parsed"] is None


def test_parsed_correctly_separated_on_combined_line():
    # Real spice-packet layout: two fields crammed onto one line. Confirms
    # the "parsed" values don't cross-contaminate any more than the raw
    # "value" strings already don't.
    detections = _dets(("Net Weight: 50 g MRP: Rs 35 (Incl. of all taxes)", 0.99))
    fields = extract_fields(detections)
    assert fields["net_quantity"]["parsed"] == {"amount": 50.0, "unit": "g"}
    assert fields["mrp"]["parsed"] == {"amount": 35.0, "currency": "INR"}


# --------------------------------------------------------------------------- #
# quality_scorer tests
# --------------------------------------------------------------------------- #
# OCR's own confidence is the real signal, not image metrics alone —
# these lock in the real scenarios found during Stage 7 testing.

def test_average_confidence_empty_detections():
    assert average_confidence([]) == 0.0


def test_average_confidence_computes_mean():
    dets = [{"confidence": 0.9}, {"confidence": 0.7}, {"confidence": 0.8}]
    assert abs(average_confidence(dets) - 0.8) < 1e-9


def test_flagged_bad_image_but_great_ocr_is_still_good():
    # Real scenario: 03_bright_overexposed.jpg was flagged overexposed by
    # image metrics, but OCR read every field perfectly. The image flag
    # must not override a demonstrably successful OCR result.
    dets = [{"text": "a", "confidence": 0.99}, {"text": "b", "confidence": 0.97}]
    result = combined_quality_verdict(
        image_is_low_quality=True,
        image_quality_messages=["Image is overexposed. Reduce glare/flash and retake."],
        detections=dets,
    )
    assert result.verdict == "good"
    assert result.guidance == []


def test_fine_looking_image_but_bad_ocr_is_poor_with_honest_guidance():
    # The inverse: image metrics passed, but OCR still failed. Guidance
    # must not blame blur/brightness when that's not what actually failed.
    dets = [{"text": "x", "confidence": 0.2}, {"text": "y", "confidence": 0.15}]
    result = combined_quality_verdict(
        image_is_low_quality=False, image_quality_messages=[], detections=dets
    )
    assert result.verdict == "poor"
    assert "quality checks passed" in result.guidance[0]


def test_no_detections_at_all_is_poor_with_specific_guidance():
    result = combined_quality_verdict(
        image_is_low_quality=False, image_quality_messages=[], detections=[]
    )
    assert result.verdict == "poor"
    assert result.num_detections == 0
    assert "No text could be detected" in result.guidance[0]


def test_poor_and_image_flagged_reuses_specific_image_messages():
    dets = [{"text": "x", "confidence": 0.1}]
    result = combined_quality_verdict(
        image_is_low_quality=True,
        image_quality_messages=["Image appears blurry. Hold the camera steady and refocus."],
        detections=dets,
    )
    assert result.verdict == "poor"
    assert "Hold the camera steady" in result.guidance[0]


def test_acceptable_verdict_band():
    dets = [{"text": "x", "confidence": 0.7}, {"text": "y", "confidence": 0.65}]
    result = combined_quality_verdict(
        image_is_low_quality=False, image_quality_messages=[], detections=dets
    )
    assert result.verdict == "acceptable"


# --------------------------------------------------------------------------- #
# build_status_summary tests — the frontend-facing status composer
# --------------------------------------------------------------------------- #
# These lock in real scenarios found during Stage 7 testing, including a
# genuine bug: status was originally decided from raw OCR confidence on
# whatever text was detected, NOT from whether the required compliance
# fields were actually extracted. Two confidently-read fragments of
# garbage text (avg confidence 0.61) on 06_very_blurry.jpg were wrongly
# reported as a successful extraction despite 0/5 fields being found.

def _readability(overall, present, uncertain=0, partial=0, missing=None, total=5):
    if missing is None:
        missing = total - present - uncertain - partial
    return {
        "overall": overall,
        "fields_present": present,
        "fields_partial": partial,
        "fields_uncertain": uncertain,
        "fields_missing": missing,
        "total_fields_checked": total,
    }


def test_status_flagged_image_but_successful_ocr_shows_info_only_warning():
    # Real scenario: 01_clean_normal.jpg, flagged overexposed, 5/5 fields
    # extracted at 99%+ confidence. Must show success with an
    # informational-only note, never a retake prompt.
    dets = [{"text": "a", "confidence": 0.995}, {"text": "b", "confidence": 0.993}]
    cq = combined_quality_verdict(
        True, ["Image is overexposed. Reduce glare/flash and retake."], dets
    )
    status = build_status_summary(
        True, ["Image is overexposed. Reduce glare/flash and retake."], cq,
        _readability("fully_readable", present=5),
    )
    assert status["ocr_status"] == "success"
    assert status["readability_label"] == "🟢 Fully readable"
    assert status["needs_retake"] is False
    assert status["retake_message"] is None
    assert status["image_warning"] == "⚠️ Image is overexposed, but extracted data is reliable."


def test_status_zero_fields_fails_even_with_acceptable_raw_confidence():
    # THE BUG, locked in as a regression test: 06_very_blurry.jpg had
    # avg OCR confidence of 0.6132 (technically "acceptable") from just 2
    # stray detections, but extracted 0/5 required fields. This must be
    # reported as failed + needs_retake, never as a success, regardless
    # of how confident PaddleOCR was about the wrong text.
    dets = [{"text": "garbled fragment", "confidence": 0.65}, {"text": "noise", "confidence": 0.58}]
    cq = combined_quality_verdict(
        True, ["Image appears blurry. Hold the camera steady and refocus."], dets
    )
    assert cq.verdict == "acceptable"  # confirms the trap: raw confidence alone looks fine
    status = build_status_summary(
        True, ["Image appears blurry. Hold the camera steady and refocus."], cq,
        _readability("unreadable", present=0),
    )
    assert status["ocr_status"] == "failed"
    assert status["ocr_status_label"] == "🔴 Extraction failed"
    assert status["needs_retake"] is True
    assert "Unable to read the product label clearly" in status["retake_message"]
    assert status["image_warning"] is None


def test_status_partial_extraction_gets_its_own_tier_not_success_or_failure():
    # Real scenario: 17_partial_occlusion.jpg — 4/5 fields present, 1
    # uncertain (MRP's label was occluded, only the value survived).
    # Must be reported as "partial", not lumped into success or failure.
    dets = [{"text": "(es): Rs 50", "confidence": 0.9876}]
    cq = combined_quality_verdict(False, [], dets)
    status = build_status_summary(
        False, [], cq, _readability("mostly_readable", present=4, uncertain=1),
    )
    assert status["ocr_status"] == "partial"
    assert status["ocr_status_label"] == "🟡 Partially extracted"
    assert status["needs_retake"] is False
    assert status["image_warning"] is None  # never say "reliable" on a partial result


def test_status_poor_quality_flagged_but_all_fields_still_extracted_is_success():
    # Real scenario: 18_mixed_dark_blur_tilt.jpg — flagged blurry, but
    # OCR still got all 5 fields at very high confidence. Success, with
    # only an informational note.
    dets = [{"text": f"line{i}", "confidence": 0.99} for i in range(5)]
    cq = combined_quality_verdict(
        True, ["Image appears blurry. Hold the camera steady and refocus."], dets
    )
    status = build_status_summary(
        True, ["Image appears blurry. Hold the camera steady and refocus."], cq,
        _readability("fully_readable", present=5),
    )
    assert status["ocr_status"] == "success"
    assert status["needs_retake"] is False
    assert status["image_warning"] == "⚠️ Image appears blurry, but extracted data is reliable."


def test_status_poor_ocr_with_no_image_flag_still_retakes_with_generic_reason():
    # Image metrics passed but OCR still failed (e.g. unusual font) —
    # must still trigger a retake, with an honest generic reason rather
    # than a false blur/brightness claim.
    dets = [{"text": "x", "confidence": 0.1}]
    cq = combined_quality_verdict(False, [], dets)
    status = build_status_summary(False, [], cq, _readability("unreadable", present=0))
    assert status["needs_retake"] is True
    assert status["retake_message"] is not None
    assert status["image_warning"] is None


def test_status_clean_image_and_good_ocr_has_no_warnings_at_all():
    dets = [{"text": "a", "confidence": 0.99}]
    cq = combined_quality_verdict(False, [], dets)
    status = build_status_summary(False, [], cq, _readability("fully_readable", present=5))
    assert status["ocr_status"] == "success"
    assert status["needs_retake"] is False
    assert status["retake_message"] is None
    assert status["image_warning"] is None


# --------------------------------------------------------------------------- #
# accuracy_eval tests (Stage 8 — CER/WER)
# --------------------------------------------------------------------------- #

def test_cer_perfect_match_is_zero():
    assert character_error_rate("MRP Rs 50", "MRP Rs 50") == 0.0


def test_cer_single_character_error():
    # "500 g" vs "5OO g": 2 of 5 characters differ (0->O twice).
    cer = character_error_rate("500 g", "5OO g")
    assert abs(cer - 0.4) < 1e-9


def test_cer_empty_reference_and_hypothesis_is_zero():
    assert character_error_rate("", "") == 0.0


def test_cer_empty_reference_nonempty_hypothesis_is_one():
    assert character_error_rate("", "some text") == 1.0


def test_wer_perfect_match_is_zero():
    assert word_error_rate("Hello world", "Hello world") == 0.0


def test_wer_one_wrong_word_out_of_two():
    assert abs(word_error_rate("Hello world", "Hello wrold") - 0.5) < 1e-9


def test_aggregate_results_macro_and_micro():
    results = [
        evaluate_text("a.jpg", "12345", "12345"),   # CER 0
        evaluate_text("b.jpg", "12345", "1234X"),    # CER 0.2
    ]
    agg = aggregate_results(results)
    assert agg["num_images"] == 2
    assert abs(agg["macro_cer"] - 0.1) < 1e-9  # (0 + 0.2) / 2


def test_aggregate_results_empty_list():
    agg = aggregate_results([])
    assert agg["num_images"] == 0
    assert agg["macro_cer"] == 0.0


# --------------------------------------------------------------------------- #
# ocr_engine tests (skipped if paddleocr isn't installed)
# --------------------------------------------------------------------------- #

def test_ocr_engine_importable_or_skips():
    pytest.importorskip("paddleocr", reason="paddleocr not installed in this environment")
    from ocr.ocr_engine import OCREngine  # noqa: F401
    # We don't instantiate here (model download required); import success is enough
    # to confirm the module is wired correctly.


# --------------------------------------------------------------------------- #
# Stage 9 — Recovery preprocessing tests
# --------------------------------------------------------------------------- #

def test_recovery_upscale_increases_small_image():
    from preprocessing.recovery_preprocess import recover_low_resolution
    img = _make_test_image(width=200, height=150)
    out = recover_low_resolution(img, target_min_dimension=1000)
    assert max(out.shape[:2]) >= 1000


def test_recovery_upscale_leaves_large_image_untouched():
    from preprocessing.recovery_preprocess import recover_low_resolution
    img = _make_test_image(width=2000, height=1500)
    out = recover_low_resolution(img, target_min_dimension=1000)
    assert out.shape == img.shape


def test_recovery_sharpen_preserves_dimensions():
    from preprocessing.recovery_preprocess import recover_blur
    img = _make_test_image(width=400, height=300)
    out = recover_blur(img)
    assert out.shape == img.shape


def test_recovery_strategies_run_without_error():
    from preprocessing.recovery_preprocess import aggressive_recovery_preprocess
    img = _make_test_image(width=300, height=200)
    quality = type("Q", (), {
        "is_low_quality": True,
        "blur_score": 30,
        "is_low_resolution": True,
    })()
    strategies = aggressive_recovery_preprocess(img, quality)
    assert len(strategies) >= 2
    for name, proc_img in strategies:
        assert proc_img.shape[0] >= img.shape[0]
        assert proc_img.shape[1] >= img.shape[1]


def test_score_attempt_prefers_fields_over_raw_confidence():
    # Stage 8 bug regression: 2 detections at 0.65 conf, 0 fields present
    # should score LOWER than 2 detections at 0.50 conf, 2 fields present
    from ocr.quality_scorer import score_attempt

    bad_ocr = {"detections": [{"confidence": 0.65}, {"confidence": 0.58}]}
    bad_fields = {
        "mrp": {"state": "missing"},
        "net_quantity": {"state": "missing"},
        "manufacturing_date": {"state": "missing"},
        "best_before": {"state": "missing"},
        "manufacturer": {"state": "missing"},
    }

    good_ocr = {"detections": [{"confidence": 0.50}, {"confidence": 0.48}]}
    good_fields = {
        "mrp": {"state": "present"},
        "net_quantity": {"state": "present"},
        "manufacturing_date": {"state": "missing"},
        "best_before": {"state": "missing"},
        "manufacturer": {"state": "missing"},
    }

    bad_score = score_attempt(bad_fields, bad_ocr)
    good_score = score_attempt(good_fields, good_ocr)
    assert good_score > bad_score


def test_score_attempt_uncertain_fields_contribute():
    from ocr.quality_scorer import score_attempt

    ocr = {"detections": [{"confidence": 0.80}]}
    fields = {
        "mrp": {"state": "uncertain"},
        "net_quantity": {"state": "uncertain"},
        "manufacturing_date": {"state": "missing"},
        "best_before": {"state": "missing"},
        "manufacturer": {"state": "missing"},
    }
    s = score_attempt(fields, ocr)
    # 2 uncertain = 6 pts + 0.8*5 = 4  => ~10
    assert s > 5.0

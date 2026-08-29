"""
evaluate_accuracy.py
---------------------
Stage 8: Accuracy evaluation.

Runs the full OCR pipeline against every test image we have known-correct
ground truth for, and reports real, measured CER/WER — plus field-level
accuracy (did we get the right MRP, quantity, dates, manufacturer), which
matters more for a Legal Metrology compliance tool than raw text accuracy
alone: a single stray character in a page of ingredients is a very
different problem from a wrong MRP.

Usage:
    python evaluate_accuracy.py
    python evaluate_accuracy.py --out output/accuracy_report.json
"""

from __future__ import annotations

import argparse
import json
import os

from run_pipeline import run
from ocr.accuracy_eval import evaluate_text, aggregate_results
from tests.ground_truth import GROUND_TRUTH


def _fields_match(expected: dict, actual_fields: dict) -> dict:
    """
    Compares expected structured field values against what the pipeline
    actually extracted. A field counts as correct only if it's in the
    "present" state AND its parsed value matches exactly — an "uncertain"
    or "partial" result is never counted as correct, even if the raw
    value happens to look right, since the whole point of those states is
    that they shouldn't be trusted at face value.
    """
    results = {}
    for field_name, expected_value in expected.items():
        actual = actual_fields.get(field_name, {})
        actual_state = actual.get("state")
        actual_parsed = actual.get("parsed")
        actual_value = actual.get("value")

        if expected_value is None:
            # We don't expect this field to be reliably present on this
            # label (e.g. no manufacturer info on the oil-bottle test).
            results[field_name] = {"expected": None, "skipped": True}
            continue

        if field_name == "manufacturer":
            correct = actual_state == "present" and actual_value == expected_value
        else:
            correct = actual_state == "present" and actual_parsed == expected_value

        results[field_name] = {
            "expected": expected_value,
            "actual_value": actual_value,
            "actual_parsed": actual_parsed,
            "actual_state": actual_state,
            "correct": correct,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description="Stage 8 accuracy evaluation")
    parser.add_argument(
        "--images-dir", default="images/test_set",
        help="Directory containing the ground-truth test images",
    )
    parser.add_argument("--out", default=None, help="Optional path to save JSON report")
    parser.add_argument(
        "--start-from", default=None,
        help="Resume from this image filename onward (inclusive), skipping "
             "everything before it — useful if a previous run got interrupted.",
    )
    args = parser.parse_args()

    text_results = []
    field_accuracy_by_image = {}
    per_field_correct_count = {}
    per_field_total_count = {}

    print(f"{'Image':<30} {'CER':>8} {'WER':>8}  Fields correct")
    print("-" * 70)

    started = args.start_from is None
    for image_name, (expected_text, expected_fields) in GROUND_TRUTH.items():
        if not started:
            if image_name == args.start_from:
                started = True
            else:
                continue
        image_path = os.path.join(args.images_dir, image_name)
        if not os.path.exists(image_path):
            print(f"{image_name:<30} SKIPPED (file not found)")
            continue

        result = run(image_path)
        actual_text = result["raw_text"]
        actual_fields = result["fields"]

        acc = evaluate_text(image_name, expected_text, actual_text)
        text_results.append(acc)

        field_check = _fields_match(expected_fields, actual_fields)
        field_accuracy_by_image[image_name] = field_check

        correct_fields = [f for f, r in field_check.items() if r.get("correct")]
        checked_fields = [f for f, r in field_check.items() if not r.get("skipped")]
        for f, r in field_check.items():
            if r.get("skipped"):
                continue
            per_field_total_count[f] = per_field_total_count.get(f, 0) + 1
            if r.get("correct"):
                per_field_correct_count[f] = per_field_correct_count.get(f, 0) + 1

        fields_summary = f"{len(correct_fields)}/{len(checked_fields)}"
        print(f"{image_name:<30} {acc.cer:>8.4f} {acc.wer:>8.4f}  {fields_summary}")

    print("-" * 70)
    agg = aggregate_results(text_results)
    print(f"\nOverall (macro-averaged across {agg['num_images']} images):")
    print(f"  CER: {agg['macro_cer']:.4f}   WER: {agg['macro_wer']:.4f}")
    print(f"Overall (micro, weighted by text length):")
    print(f"  CER: {agg['micro_cer']:.4f}")

    print("\nPer-field accuracy across all images:")
    for field_name in per_field_total_count:
        correct = per_field_correct_count.get(field_name, 0)
        total = per_field_total_count[field_name]
        pct = 100 * correct / total if total else 0.0
        print(f"  {field_name:<20} {correct}/{total}  ({pct:.1f}%)")

    report = {
        "per_image_text_accuracy": [r.to_dict() for r in text_results],
        "aggregate_text_accuracy": agg,
        "per_image_field_accuracy": field_accuracy_by_image,
        "per_field_summary": {
            f: {"correct": per_field_correct_count.get(f, 0), "total": per_field_total_count[f]}
            for f in per_field_total_count
        },
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fp:
            json.dump(report, fp, indent=2, ensure_ascii=False)
        print(f"\nSaved full report to {args.out}")


if __name__ == "__main__":
    main()

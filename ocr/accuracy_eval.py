"""
accuracy_eval.py
-----------------
Character Error Rate (CER) and Word Error Rate (WER) — the standard
metrics for measuring OCR accuracy against known ground truth.

    CER = edit_distance(reference_chars, hypothesis_chars) / len(reference_chars)
    WER = edit_distance(reference_words, hypothesis_words) / len(reference_words)

Lower is better. 0.0 = perfect match. Values above 1.0 are possible
(hypothesis much longer/more wrong than the reference) and are left
uncapped rather than artificially clamped, since capping would hide a
genuinely bad result.

Per the project notes: don't invent an accuracy percentage — measure it.
This module is what makes that possible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence


def _levenshtein(a: Sequence, b: Sequence) -> int:
    """Standard dynamic-programming edit distance between two sequences
    (works for both character sequences and word-token sequences)."""
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n

    prev = list(range(m + 1))
    curr = [0] * (m + 1)

    for i in range(1, n + 1):
        curr[0] = i
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,      # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution
            )
        prev, curr = curr, prev

    return prev[m]


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace, so line-break differences or case
    variance don't inflate error rates for comparisons that don't care
    about them. Used as the default; raw comparison is still available
    via normalize=False for callers that want exact-case sensitivity."""
    return re.sub(r"\s+", " ", text.strip().lower())


def character_error_rate(reference: str, hypothesis: str, normalize: bool = True) -> float:
    ref = _normalize(reference) if normalize else reference
    hyp = _normalize(hypothesis) if normalize else hypothesis
    if len(ref) == 0:
        return 0.0 if len(hyp) == 0 else 1.0
    return _levenshtein(list(ref), list(hyp)) / len(ref)


def word_error_rate(reference: str, hypothesis: str, normalize: bool = True) -> float:
    ref = _normalize(reference) if normalize else reference
    hyp = _normalize(hypothesis) if normalize else hypothesis
    ref_words = ref.split()
    hyp_words = hyp.split()
    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0
    return _levenshtein(ref_words, hyp_words) / len(ref_words)


@dataclass
class AccuracyResult:
    image_name: str
    cer: float
    wer: float
    reference_length_chars: int
    hypothesis_length_chars: int

    def to_dict(self) -> dict:
        return {
            "image": self.image_name,
            "cer": round(self.cer, 4),
            "wer": round(self.wer, 4),
            "reference_length_chars": self.reference_length_chars,
            "hypothesis_length_chars": self.hypothesis_length_chars,
        }


def evaluate_text(image_name: str, reference: str, hypothesis: str) -> AccuracyResult:
    return AccuracyResult(
        image_name=image_name,
        cer=character_error_rate(reference, hypothesis),
        wer=word_error_rate(reference, hypothesis),
        reference_length_chars=len(reference),
        hypothesis_length_chars=len(hypothesis),
    )


def aggregate_results(results: List[AccuracyResult]) -> dict:
    """
    Two ways to average, both reported since they answer different
    questions:
      - macro (mean of per-image CER/WER): "how well does it do on a
        typical image", each image weighted equally regardless of length
      - micro (total errors / total reference length across all images):
        "what fraction of all characters/words were wrong overall",
        weighted by how much text was actually in each image
    """
    if not results:
        return {"macro_cer": 0.0, "macro_wer": 0.0, "micro_cer": 0.0, "micro_wer": 0.0, "num_images": 0}

    macro_cer = sum(r.cer for r in results) / len(results)
    macro_wer = sum(r.wer for r in results) / len(results)

    total_ref_chars = sum(r.reference_length_chars for r in results)
    total_char_errors = sum(r.cer * r.reference_length_chars for r in results)
    micro_cer = total_char_errors / total_ref_chars if total_ref_chars else 0.0

    return {
        "macro_cer": round(macro_cer, 4),
        "macro_wer": round(macro_wer, 4),
        "micro_cer": round(micro_cer, 4),
        "num_images": len(results),
    }


if __name__ == "__main__":
    # Quick sanity check against known examples from the project notes.
    examples = [
        ("MRP ₹120", "MRP ₹12O"),   # one char wrong (O for 0)
        ("500 g", "5OO g"),          # two chars wrong
        ("Hello world", "Hello wrold"),  # one transposition-ish word
    ]
    for ref, hyp in examples:
        print(f"ref={ref!r} hyp={hyp!r} -> CER={character_error_rate(ref, hyp):.3f} "
              f"WER={word_error_rate(ref, hyp):.3f}")

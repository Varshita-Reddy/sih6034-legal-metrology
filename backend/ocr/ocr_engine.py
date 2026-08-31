"""
ocr_engine.py
-------------
Production-oriented PaddleOCR 3.x wrapper for the SIH
Packaged-Commodity OCR project.

Responsibilities:
    - Load and configure PaddleOCR
    - Load/validate images
    - Resize oversized images
    - Run OCR
    - Normalize PaddleOCR output
    - Filter low-confidence detections
    - Return JSON-compatible OCR data

This module DOES NOT:
    - Extract MRP
    - Extract net quantity
    - Extract manufacturing date
    - Extract best-before
    - Extract manufacturer
    - Decide compliance

Those responsibilities belong to the field extraction,
validation and compliance stages.

Expected usage:

    engine = OCREngine()

    result = engine.run(
        "images/test_set/normalimage.jpg"
    )

Returned structure:

    {
        "raw_text": "...",
        "detections": [
            {
                "text": "...",
                "confidence": 0.98,
                "bbox": [x1, y1, x2, y2]
            }
        ]
    }
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Union
import json
import os
import time

import cv2
import numpy as np


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_CONFIDENCE_THRESHOLD = 0.50

# ============================================================================
# OCR MODEL CONFIGURATION
# ============================================================================

# Lightweight detector.
TEXT_DETECTION_MODEL = "PP-OCRv5_mobile_det"

# Product-label photographs are normally upright.
USE_TEXTLINE_ORIENTATION = False

# Product packages are not document scans.
USE_DOC_ORIENTATION = False
USE_DOC_UNWARPING = False

# Detection image size.
#
# 960 gives a good balance between speed and small-text detection.
TEXT_DET_LIMIT_SIDE_LEN = 960
TEXT_DET_LIMIT_TYPE = "max"

# Do not feed unnecessarily huge camera images to OCR.
#
# IMPORTANT:
# This is deliberately kept at 1280 rather than 1600.
# Your input was already 1536x1024 and PaddleOCR internally
# limits detection to 960 anyway.
MAX_IMAGE_SIDE = 1280

# CPU optimization.
#
# Keep False initially because your environment previously showed
# Paddle/PIR/MKL-DNN compatibility concerns.
ENABLE_MKLDNN = False

# Number of CPU threads.
#
# 0 means let Paddle choose automatically.
# Explicitly forcing a number can actually make some machines slower.
CPU_THREADS = 0

# OCR confidence filtering.
DEFAULT_DROP_LOW_CONFIDENCE = True

# Logging.
SHOW_TIMING = True


# ============================================================================
# DATA CLASS
# ============================================================================

@dataclass
class Detection:
    """
    Represents one OCR text detection.
    """

    text: str
    confidence: float
    bbox: List[int]

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================================
# OCR ENGINE
# ============================================================================

class EasyOCRPredictorWrapper:
    def __init__(self, reader):
        self.reader = reader

    def predict(self, img):
        # easyocr readtext takes numpy array
        easyocr_results = self.reader.readtext(img)
        # Format to match what _extract_result expects
        # Each item in easyocr_results is (bbox, text, score)
        return [
            {
                "rec_texts": [item[1] for item in easyocr_results],
                "rec_scores": [item[2] for item in easyocr_results],
                "rec_boxes": [item[0] for item in easyocr_results]
            }
        ]


class OCREngine:
    """
    Production wrapper around PaddleOCR 3.x.

    Public interface intentionally remains:

        engine.run(image)

    so existing run_pipeline.py code does not need to change.
    """

    def __init__(
        self,
        lang: str = "en",
        use_textline_orientation: bool = USE_TEXTLINE_ORIENTATION,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        max_image_side: int = MAX_IMAGE_SIDE,
        enable_mkldnn: bool = ENABLE_MKLDNN,
        show_timing: bool = SHOW_TIMING,
    ):
        self.lang = lang

        self.confidence_threshold = float(
            confidence_threshold
        )

        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                "confidence_threshold must be between 0 and 1."
            )

        self.max_image_side = int(
            max_image_side
        )

        if self.max_image_side <= 0:
            raise ValueError(
                "max_image_side must be greater than zero."
            )

        self.enable_mkldnn = bool(
            enable_mkldnn
        )

        self.show_timing = bool(
            show_timing
        )

        self.use_textline_orientation = bool(
            use_textline_orientation
        )

        # Load OCR exactly once.
        self._ocr = self._load_paddleocr(
            lang=self.lang,
            use_textline_orientation=(
                self.use_textline_orientation
            ),
            enable_mkldnn=self.enable_mkldnn,
        )

    # ========================================================================
    # LOAD PADDLEOCR
    # ========================================================================

    @staticmethod
    def _load_paddleocr(
        lang: str,
        use_textline_orientation: bool,
        enable_mkldnn: bool,
    ):
        """
        Initialize PaddleOCR.

        The configuration intentionally avoids forcing a recognition
        model name because the installed PaddleOCR/PaddleX version
        determines which compatible recognition model is available.

        This prevents version-specific model-name failures.
        """

        try:
            from paddleocr import PaddleOCR

            print()
            print("🚀 Loading optimized PaddleOCR...")
            print(
                f"   Detection model: {TEXT_DETECTION_MODEL}"
            )
            print(
                f"   Text-line orientation: "
                f"{use_textline_orientation}"
            )
            print(
                f"   Detection limit: "
                f"{TEXT_DET_LIMIT_TYPE} "
                f"{TEXT_DET_LIMIT_SIDE_LEN}"
            )
            print(
                f"   Document orientation: "
                f"{USE_DOC_ORIENTATION}"
            )
            print(
                f"   Document unwarping: "
                f"{USE_DOC_UNWARPING}"
            )
            print(
                f"   MKL-DNN: "
                f"{enable_mkldnn}"
            )

            start = time.perf_counter()

            # ====================================================================
            # PRIMARY CONFIGURATION
            # ====================================================================

            try:

                ocr = PaddleOCR(

                    # Language
                    lang=lang,

                    # Lightweight detector
                    text_detection_model_name=(
                        TEXT_DETECTION_MODEL
                    ),

                    # Disable document pipeline
                    use_doc_orientation_classify=(
                        USE_DOC_ORIENTATION
                    ),

                    use_doc_unwarping=(
                        USE_DOC_UNWARPING
                    ),

                    # Disable unnecessary orientation stage
                    use_textline_orientation=(
                        use_textline_orientation
                    ),

                    # Detection size
                    text_det_limit_side_len=(
                        TEXT_DET_LIMIT_SIDE_LEN
                    ),

                    text_det_limit_type=(
                        TEXT_DET_LIMIT_TYPE
                    ),

                    # CPU configuration
                    enable_mkldnn=(
                        enable_mkldnn
                    ),
                )

            except TypeError as exc:

                print()
                print(
                    "⚠️ Extended PaddleOCR configuration "
                    "is not supported by this installation."
                )

                print(
                    f"   Reason: {exc}"
                )

                print(
                    "   Retrying with compatible configuration..."
                )

                # =================================================================
                # COMPATIBILITY FALLBACK
                # =================================================================

                try:

                    ocr = PaddleOCR(

                        lang=lang,

                        text_detection_model_name=(
                            TEXT_DETECTION_MODEL
                        ),

                        use_doc_orientation_classify=(
                            USE_DOC_ORIENTATION
                        ),

                        use_doc_unwarping=(
                            USE_DOC_UNWARPING
                        ),

                        use_textline_orientation=(
                            use_textline_orientation
                        ),

                    )

                except TypeError as exc2:

                    print()
                    print(
                        "⚠️ Model-specific configuration "
                        "is not supported."
                    )

                    print(
                        f"   Reason: {exc2}"
                    )

                    print(
                        "   Using basic PaddleOCR configuration."
                    )

                    # =============================================================
                    # FINAL FALLBACK
                    # =============================================================

                    ocr = PaddleOCR(

                        lang=lang,

                        use_textline_orientation=(
                            use_textline_orientation
                        ),

                        use_doc_orientation_classify=False,

                        use_doc_unwarping=False,

                    )

            load_time = (
                time.perf_counter()
                - start
            )

            print()
            print(
                f"✅ PaddleOCR loaded in "
                f"{load_time:.2f}s"
            )

            print(
                "   OCR engine ready."
            )

            return ocr
        except ImportError as exc:
            try:
                import easyocr
                print("⚠️ PaddleOCR not found. Initializing EasyOCR as fallback...")
                start = time.perf_counter()
                # Initialize EasyOCR Reader for english, without GPU
                reader = easyocr.Reader(['en'], gpu=False)
                load_time = time.perf_counter() - start
                print(f"✅ EasyOCR loaded in {load_time:.2f}s")
                print("   OCR engine ready.")
                return EasyOCRPredictorWrapper(reader)
            except ImportError:
                raise ImportError(
                    "\nNeither PaddleOCR nor EasyOCR is installed.\n\n"
                    "Install it inside your virtual environment with:\n"
                    "pip install paddleocr paddlepaddle\n"
                ) from exc

    # ========================================================================
    # LOAD IMAGE
    # ========================================================================

    @staticmethod
    def _load_image(
        image: Union[str, np.ndarray],
    ) -> np.ndarray:
        """
        Load image from:

            - filesystem path
            - numpy array

        Returns BGR numpy array.
        """

        # --------------------------------------------------------------------
        # Path
        # --------------------------------------------------------------------

        if isinstance(image, (str, os.PathLike)):

            image_path = os.fspath(
                image
            )

            if not os.path.isfile(
                image_path
            ):

                raise FileNotFoundError(
                    f"Could not read image: "
                    f"{image_path}"
                )

            img = cv2.imread(
                image_path,
                cv2.IMREAD_COLOR,
            )

            if img is None:

                raise ValueError(
                    f"Image exists but could not "
                    f"be decoded: {image_path}"
                )

            return img

        # --------------------------------------------------------------------
        # NumPy image
        # --------------------------------------------------------------------

        if isinstance(
            image,
            np.ndarray,
        ):

            if image.size == 0:

                raise ValueError(
                    "Received an empty image array."
                )

            if image.ndim not in (2, 3):

                raise ValueError(
                    "Image array must have 2 or 3 dimensions."
                )

            return image

        # --------------------------------------------------------------------
        # Invalid type
        # --------------------------------------------------------------------

        raise TypeError(
            "image must be either a file path "
            "or numpy.ndarray."
        )

    # ========================================================================
    # RESIZE IMAGE
    # ========================================================================

    def _resize_for_ocr(
        self,
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Resize oversized images while preserving aspect ratio.

        Smaller images are returned unchanged.
        """

        if image is None:

            raise ValueError(
                "Cannot resize a None image."
            )

        height, width = image.shape[:2]

        if height <= 0 or width <= 0:

            raise ValueError(
                "Image has invalid dimensions."
            )

        longest_side = max(
            height,
            width,
        )

        # Already small enough.
        if longest_side <= self.max_image_side:

            return image

        scale = (
            self.max_image_side
            / float(longest_side)
        )

        new_width = max(
            1,
            int(round(width * scale)),
        )

        new_height = max(
            1,
            int(round(height * scale)),
        )

        resized = cv2.resize(
            image,
            (
                new_width,
                new_height,
            ),
            interpolation=cv2.INTER_AREA,
        )

        if self.show_timing:

            print(
                "   ↳ Resized OCR input: "
                f"{width}x{height} "
                f"→ "
                f"{new_width}x{new_height}"
            )

        return resized

    # ========================================================================
    # NORMALIZE BOUNDING BOX
    # ========================================================================

    @staticmethod
    def _normalize_bbox(
        box,
    ) -> List[int]:
        """
        Convert PaddleOCR bounding-box formats into:

            [x1, y1, x2, y2]
        """

        if box is None:

            return [
                0,
                0,
                0,
                0,
            ]

        try:

            arr = np.asarray(
                box
            )

        except Exception:

            return [
                0,
                0,
                0,
                0,
            ]

        # --------------------------------------------------------------------
        # [x1,y1,x2,y2]
        # --------------------------------------------------------------------

        if (
            arr.ndim == 1
            and arr.size >= 4
        ):

            try:

                x1 = int(round(float(arr[0])))
                y1 = int(round(float(arr[1])))
                x2 = int(round(float(arr[2])))
                y2 = int(round(float(arr[3])))

                return [
                    x1,
                    y1,
                    x2,
                    y2,
                ]

            except (
                TypeError,
                ValueError,
            ):

                return [
                    0,
                    0,
                    0,
                    0,
                ]

        # --------------------------------------------------------------------
        # Polygon:
        #
        # [[x1,y1],
        #  [x2,y2],
        #  [x3,y3],
        #  [x4,y4]]
        # --------------------------------------------------------------------

        if (
            arr.ndim == 2
            and arr.shape[1] >= 2
            and arr.shape[0] >= 1
        ):

            try:

                x_values = (
                    arr[:, 0]
                    .astype(float)
                )

                y_values = (
                    arr[:, 1]
                    .astype(float)
                )

                return [
                    int(round(np.min(x_values))),
                    int(round(np.min(y_values))),
                    int(round(np.max(x_values))),
                    int(round(np.max(y_values))),
                ]

            except (
                TypeError,
                ValueError,
            ):

                return [
                    0,
                    0,
                    0,
                    0,
                ]

        return [
            0,
            0,
            0,
            0,
        ]

    # ========================================================================
    # CLEAN TEXT
    # ========================================================================

    @staticmethod
    def _clean_text(
        text,
    ) -> str:
        """
        Lightweight text cleanup.

        Do NOT perform aggressive OCR correction here.

        Field-specific corrections belong to field_extractor.py.
        """

        if text is None:

            return ""

        cleaned = str(
            text
        ).strip()

        # Normalize repeated whitespace without destroying
        # meaningful punctuation.
        cleaned = " ".join(
            cleaned.split()
        )

        return cleaned

    # ========================================================================
    # SAFE RESULT ACCESS
    # ========================================================================

    @staticmethod
    def _get_result_value(
        result,
        key: str,
    ):
        """
        Safely read a PaddleOCR result field.

        Supports dictionary-like PaddleOCR result objects.
        """

        try:

            return result[key]

        except (
            KeyError,
            TypeError,
            IndexError,
        ):

            pass

        try:

            return getattr(
                result,
                key,
            )

        except AttributeError:

            return None

    # ========================================================================
    # EXTRACT ONE PADDLE RESULT
    # ========================================================================

    def _extract_result(
        self,
        result,
    ) -> List[Detection]:
        """
        Convert one PaddleOCR result into Detection objects.
        """

        detections: List[Detection] = []

        texts = self._get_result_value(
            result,
            "rec_texts",
        )

        scores = self._get_result_value(
            result,
            "rec_scores",
        )

        boxes = self._get_result_value(
            result,
            "rec_boxes",
        )

        if texts is None:
            return detections

        if scores is None:
            return detections

        if boxes is None:
            return detections

        try:

            iterator = zip(
                texts,
                scores,
                boxes,
            )

        except TypeError:

            return detections

        for text, score, box in iterator:

            # ---------------------------------------------------------------
            # Confidence
            # ---------------------------------------------------------------

            try:

                confidence = float(
                    score
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            if not np.isfinite(
                confidence
            ):

                continue

            # ---------------------------------------------------------------
            # Confidence filter
            # ---------------------------------------------------------------

            if (
                confidence
                < self.confidence_threshold
            ):

                continue

            # ---------------------------------------------------------------
            # Text
            # ---------------------------------------------------------------

            clean_text = self._clean_text(
                text
            )

            if not clean_text:

                continue

            # ---------------------------------------------------------------
            # Bounding box
            # ---------------------------------------------------------------

            bbox = self._normalize_bbox(
                box
            )

            detections.append(
                Detection(

                    text=clean_text,

                    confidence=round(
                        confidence,
                        4,
                    ),

                    bbox=bbox,
                )
            )

        return detections

    # ========================================================================
    # SORT DETECTIONS
    # ========================================================================

    @staticmethod
    def _sort_detections(
        detections: List[Detection],
    ) -> List[Detection]:
        """
        Sort detections approximately top-to-bottom,
        then left-to-right.

        This makes raw_text more useful to the downstream
        field extractor.
        """

        if not detections:

            return []

        # Estimate line height from bounding box.
        def sort_key(
            detection: Detection,
        ):

            x1, y1, x2, y2 = (
                detection.bbox
            )

            height = max(
                1,
                y2 - y1,
            )

            # Group boxes into approximate rows.
            row = int(
                y1 / max(
                    10,
                    height,
                )
            )

            return (
                y1,
                x1,
            )

        return sorted(
            detections,
            key=sort_key,
        )

    # ========================================================================
    # MAIN OCR FUNCTION
    # ========================================================================

    def run(
        self,
        image: Union[str, np.ndarray],
    ) -> dict:
        """
        Run OCR.

        Compatible with existing run_pipeline.py.

        Returns:

            {
                "raw_text": "...",
                "detections": [...]
            }
        """

        total_start = time.perf_counter()

        # ====================================================================
        # LOAD
        # ====================================================================

        load_start = time.perf_counter()

        image_array = self._load_image(
            image
        )

        load_time = (
            time.perf_counter()
            - load_start
        )

        # ====================================================================
        # RESIZE
        # ====================================================================

        resize_start = time.perf_counter()

        ocr_image = self._resize_for_ocr(
            image_array
        )

        resize_time = (
            time.perf_counter()
            - resize_start
        )

        # ====================================================================
        # OCR
        # ====================================================================

        inference_start = time.perf_counter()

        try:

            results = self._ocr.predict(
                ocr_image
            )

        except Exception as exc:

            print()
            print(
                "❌ PaddleOCR inference failed:"
            )

            print(
                f"   {exc}"
            )

            raise RuntimeError(
                f"PaddleOCR inference failed: {exc}"
            ) from exc

        inference_time = (
            time.perf_counter()
            - inference_start
        )

        # ====================================================================
        # RESULT EXTRACTION
        # ====================================================================

        extraction_start = time.perf_counter()

        detections: List[Detection] = []

        try:

            for result in results:

                detections.extend(
                    self._extract_result(
                        result
                    )
                )

        except TypeError:

            # Some PaddleOCR versions return a generator/list-like
            # object that may not behave exactly as expected.
            detections = []

        # Sort for stable downstream extraction.
        detections = self._sort_detections(
            detections
        )

        extraction_time = (
            time.perf_counter()
            - extraction_start
        )

        # ====================================================================
        # RAW TEXT
        # ====================================================================

        raw_text = "\n".join(
            detection.text
            for detection in detections
        )

        # ====================================================================
        # TOTAL
        # ====================================================================

        total_time = (
            time.perf_counter()
            - total_start
        )

        # ====================================================================
        # PERFORMANCE LOG
        # ====================================================================

        if self.show_timing:

            print()
            print(
                "   ⏱️ OCR PERFORMANCE"
            )

            print(
                f"      Image loading: "
                f"{load_time:.3f}s"
            )

            print(
                f"      Image resize: "
                f"{resize_time:.3f}s"
            )

            print(
                f"      PaddleOCR inference: "
                f"{inference_time:.3f}s"
            )

            print(
                f"      Result extraction: "
                f"{extraction_time:.3f}s"
            )

            print(
                f"      Total OCR time: "
                f"{total_time:.3f}s"
            )

            print(
                f"      Detections kept: "
                f"{len(detections)}"
            )

            if detections:

                avg_confidence = (
                    sum(
                        d.confidence
                        for d in detections
                    )
                    / len(detections)
                )

                print(
                    f"      Average confidence: "
                    f"{avg_confidence:.3f}"
                )

        # ====================================================================
        # RETURN
        # ====================================================================

        return {
            "raw_text": raw_text,

            "detections": [
                detection.to_dict()
                for detection in detections
            ],
        }

    # ========================================================================
    # JSON OUTPUT
    # ========================================================================

    def run_to_json(
        self,
        image: Union[str, np.ndarray],
        out_path: str,
    ) -> dict:
        """
        Run OCR and save JSON result.
        """

        result = self.run(
            image
        )

        output_directory = os.path.dirname(
            os.path.abspath(
                out_path
            )
        )

        if output_directory:

            os.makedirs(
                output_directory,
                exist_ok=True,
            )

        with open(
            out_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                result,
                f,
                indent=2,
                ensure_ascii=False,
            )

        return result


# ============================================================================
# COMMAND-LINE TEST
# ============================================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print()
        print(
            "Usage:"
        )

        print(
            "python ocr_engine.py "
            "<path_to_image>"
        )

        print()

        sys.exit(1)

    image_path = sys.argv[1]

    print()
    print(
        "============================================================"
    )

    print(
        "             SIH OPTIMIZED OCR ENGINE TEST"
    )

    print(
        "============================================================"
    )

    print(
        f"Image: {image_path}"
    )

    print(
        f"Detection model: {TEXT_DETECTION_MODEL}"
    )

    print(
        f"Detection limit: "
        f"{TEXT_DET_LIMIT_TYPE} "
        f"{TEXT_DET_LIMIT_SIDE_LEN}"
    )

    print(
        f"Max image side: "
        f"{MAX_IMAGE_SIDE}"
    )

    print(
        f"Text orientation: "
        f"{USE_TEXTLINE_ORIENTATION}"
    )

    print(
        f"Document orientation: "
        f"{USE_DOC_ORIENTATION}"
    )

    print(
        f"Document unwarping: "
        f"{USE_DOC_UNWARPING}"
    )

    print(
        "============================================================"
    )

    try:

        engine = OCREngine()

        result = engine.run(
            image_path
        )

        print()
        print(
            "============================================================"
        )

        print(
            "OCR RESULT"
        )

        print(
            "============================================================"
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as exc:

        print()
        print(
            "❌ OCR test failed:"
        )

        print(
            str(exc)
        )

        sys.exit(1)
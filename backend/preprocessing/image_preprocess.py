"""
image_preprocess.py
--------------------
Image quality checking and preprocessing for packaged-commodity label images,
before they are sent to the OCR engine.

Pipeline this module implements:

    Input image
        -> Quality analysis (blur, brightness, resolution)
        -> Decide which operations are actually needed
        -> Apply: resize / denoise / contrast enhancement /
                  sharpening / rotation correction / perspective correction
        -> Preprocessed image ready for OCR

Design principle: we do NOT blindly apply every operation to every image.
We inspect the image first and only apply what it actually needs.
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Quality analysis
# --------------------------------------------------------------------------- #

@dataclass
class QualityReport:
    blur_score: float
    brightness: float
    width: int
    height: int
    is_blurry: bool
    is_too_dark: bool
    is_too_bright: bool
    is_low_resolution: bool
    is_low_quality: bool
    messages: list = field(default_factory=list)


# Thresholds — tuned for typical phone-camera product-label shots.
# These are starting points; adjust after running Stage 7 (real-world testing).
BLUR_THRESHOLD = 100.0          # Laplacian variance below this => blurry
DARK_THRESHOLD = 60.0           # mean brightness (0-255) below this => too dark
BRIGHT_THRESHOLD = 235.0        # mean brightness above this => overexposed
MIN_WIDTH = 400                 # px
MIN_HEIGHT = 300                # px


def _to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def check_image_quality(image: np.ndarray) -> QualityReport:
    """
    Analyze an image (BGR, as loaded by cv2.imread) and report whether it is
    good enough to send to OCR, and what's wrong with it if not.
    """
    gray = _to_gray(image)
    h, w = gray.shape[:2]

    # Blur: variance of the Laplacian. Sharp images have high variance.
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Brightness: mean pixel intensity.
    brightness = float(gray.mean())

    is_blurry = blur_score < BLUR_THRESHOLD
    is_too_dark = brightness < DARK_THRESHOLD
    is_too_bright = brightness > BRIGHT_THRESHOLD
    is_low_resolution = (w < MIN_WIDTH) or (h < MIN_HEIGHT)

    messages = []
    if is_blurry:
        messages.append("Image appears blurry. Hold the camera steady and refocus.")
    if is_too_dark:
        messages.append("Image is too dark. Retake in better lighting.")
    if is_too_bright:
        messages.append("Image is overexposed. Reduce glare/flash and retake.")
    if is_low_resolution:
        messages.append("Image resolution is too low. Move closer to the label.")

    is_low_quality = is_blurry or is_too_dark or is_too_bright or is_low_resolution

    return QualityReport(
        blur_score=blur_score,
        brightness=brightness,
        width=w,
        height=h,
        is_blurry=is_blurry,
        is_too_dark=is_too_dark,
        is_too_bright=is_too_bright,
        is_low_resolution=is_low_resolution,
        is_low_quality=is_low_quality,
        messages=messages,
    )


# --------------------------------------------------------------------------- #
# Individual preprocessing operations
# --------------------------------------------------------------------------- #

def resize_image(image: np.ndarray, target_width: int = 1200) -> np.ndarray:
    """Upscale/downscale so text is a usable size for OCR, preserving aspect ratio."""
    h, w = image.shape[:2]
    if w == target_width:
        return image
    scale = target_width / float(w)
    new_size = (target_width, int(h * scale))
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(image, new_size, interpolation=interp)


def cap_max_dimension(image: np.ndarray, max_dimension: int = 1600) -> np.ndarray:
    """
    Downscale very large images (typical of modern phone cameras, often
    3000-4000px wide) before OCR. Real product-label text is still plenty
    legible at ~1600px on the long side, and this cuts PaddleOCR inference
    time substantially on CPU-only setups. No-op if the image is already
    smaller than the cap.
    """
    h, w = image.shape[:2]
    longest_side = max(h, w)
    if longest_side <= max_dimension:
        return image
    scale = max_dimension / float(longest_side)
    new_size = (int(w * scale), int(h * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def denoise_image(image: np.ndarray) -> np.ndarray:
    """Remove noise while trying to keep text edges intact."""
    if len(image.shape) == 2:
        return cv2.fastNlMeansDenoising(image, h=10)
    return cv2.fastNlMeansDenoisingColored(image, h=10, hColor=10)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """CLAHE-based local contrast enhancement — helps faded/low-contrast labels."""
    gray = _to_gray(image)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    if len(image.shape) == 2:
        return enhanced
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def sharpen_image(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Mild unsharp-mask style sharpening. Keep `amount` small to avoid artifacts."""
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3)
    sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
    return sharpened


def correct_rotation(image: np.ndarray) -> np.ndarray:
    """
    Detect and correct small skew angles (label photographed slightly tilted).
    Uses the minimum-area bounding rectangle of thresholded text pixels.
    Good for +/-  a few tens of degrees of skew, not full 90/180 degree flips.
    """
    gray = _to_gray(image)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))

    if coords.shape[0] < 20:
        # Not enough foreground pixels to estimate a reliable angle.
        return image

    angle = cv2.minAreaRect(coords)[-1]

    # cv2.minAreaRect returns angle in [-90, 0); normalize to a small correction.
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Ignore near-zero corrections and implausibly large ones (likely noise).
    if abs(angle) < 0.5 or abs(angle) > 20:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, rot_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def correct_perspective(image: np.ndarray) -> np.ndarray:
    """
    Attempt to find the label's quadrilateral outline and warp it to a
    front-facing rectangle. Falls back to the original image if no
    confident 4-point contour is found (e.g. curved packaging, cluttered
    background).
    """
    gray = _to_gray(image)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    largest = max(contours, key=cv2.contourArea)
    image_area = image.shape[0] * image.shape[1]

    # Require the candidate label to cover a meaningful chunk of the frame.
    if cv2.contourArea(largest) < 0.2 * image_area:
        return image

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    if len(approx) != 4:
        return image

    pts = approx.reshape(4, 2).astype("float32")
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = max(int(height_a), int(height_b))

    if max_width < 10 or max_height < 10:
        return image

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
    return warped


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


# --------------------------------------------------------------------------- #
# Adaptive pipeline
# --------------------------------------------------------------------------- #

def adaptive_preprocess(
    image: np.ndarray,
    quality: Optional[QualityReport] = None,
    do_perspective: bool = True,
) -> np.ndarray:
    """
    Apply only the preprocessing steps the image actually needs, based on
    the QualityReport. This avoids degrading already-good images with
    unnecessary sharpening/denoising.
    """
    if quality is None:
        quality = check_image_quality(image)

    # Cap size first — real phone photos are often 3000-4000px wide, and
    # running perspective/rotation correction plus OCR at that size is
    # unnecessarily slow with no accuracy benefit.
    result = cap_max_dimension(image)

    if do_perspective:
        result = correct_perspective(result)

    result = correct_rotation(result)

    if quality.is_low_resolution:
        result = resize_image(result)

    if quality.is_too_dark or quality.blur_score < BLUR_THRESHOLD * 1.5:
        result = enhance_contrast(result)

    if quality.is_blurry:
        result = denoise_image(result)
        result = sharpen_image(result, amount=0.6)

    return result


def alternate_preprocess(image: np.ndarray) -> np.ndarray:
    """
    A deliberately DIFFERENT preprocessing strategy, used as a retry when
    the primary adaptive_preprocess() pipeline produces unreliable OCR
    (backlog roadmap item #3: conditional preprocessing + OCR retry).

    Key differences from adaptive_preprocess():
      - Skips perspective correction entirely. Perspective correction can
        make things WORSE when the quadrilateral detection picks the wrong
        contour (e.g. cluttered backgrounds, curved packaging) — trying
        without it is a genuinely different bet, not just "more of the
        same" preprocessing.
      - Forces contrast enhancement and mild sharpening unconditionally,
        rather than only when the quality report flags an issue — this
        covers cases where OCR struggled despite the image "looking" fine
        by blur/brightness metrics alone.
    """
    result = cap_max_dimension(image)
    result = correct_rotation(result)
    result = enhance_contrast(result)
    result = sharpen_image(result, amount=0.4)
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python image_preprocess.py <path_to_image>")
        sys.exit(1)

    img = cv2.imread(sys.argv[1])
    if img is None:
        print(f"Could not read image: {sys.argv[1]}")
        sys.exit(1)

    report = check_image_quality(img)
    print(report)

    if report.is_low_quality:
        for msg in report.messages:
            print("⚠️ ", msg)

    processed = adaptive_preprocess(img, quality=report)
    out_path = "preprocessed_output.jpg"
    cv2.imwrite(out_path, processed)
    print(f"Saved preprocessed image to {out_path}")

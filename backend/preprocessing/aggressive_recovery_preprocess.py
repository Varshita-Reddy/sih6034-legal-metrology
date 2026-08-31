import cv2
import numpy as np

def aggressive_recovery_preprocess(image, quality):
    """
    Stage 9 Recovery: Returns a list of (strategy_name, processed_image) tuples.
    Applies highly aggressive, specialized techniques to recover broken/faded text.
    """
    strategies = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # --- Strategy 1: Heavy Upscale + Unsharp Mask + Adaptive Threshold ---
    # Best for: Low resolution and slight blur. Forces text to be crisp and binary.
    upscaled = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(upscaled, (0, 0), 3)
    unsharp = cv2.addWeighted(upscaled, 1.5, blurred, -0.5, 0)
    thresh = cv2.adaptiveThreshold(unsharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4)
    strategies.append(("upscale_unsharp_adaptive", thresh))

    # --- Strategy 2: Morphological Top-Hat + CLAHE ---
    # Best for: Small text on uneven backgrounds or slight blur. Extracts fine details.
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    tophat = cv2.morphologyEx(cl, cv2.MORPH_TOPHAT, kernel)
    _, tophat_thresh = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("tophat_clahe_otsu", tophat_thresh))

    # --- Strategy 3: Bilateral Filter + Otsu Threshold ---
    # Best for: Blurry images with noise. Smooths noise while keeping text edges razor-sharp.
    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    _, bilat_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("bilateral_otsu", bilat_thresh))

    # --- Strategy 4: Denoise + High Laplacian Sharpening ---
    # Best for: Heavy blur. Aggressively enhances high-frequency edges (text strokes).
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    laplacian = cv2.Laplacian(denoised, cv2.CV_64F)
    laplacian = np.uint8(np.clip(laplacian, 0, 255))
    sharp = cv2.addWeighted(denoised, 1.0, laplacian, 0.5, 0)
    _, sharp_thresh = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("denoise_laplacian_otsu", sharp_thresh))

    # --- Strategy 5: Morphological Closing + Sharpen ---
    # Best for: Text where the strokes are physically broken/gapped due to extreme blur.
    upscaled2 = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
    # Horizontal bias kernel to connect broken horizontal text strokes
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 2)) 
    closed = cv2.morphologyEx(upscaled2, cv2.MORPH_CLOSE, kernel_close)
    kernel_sharp = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    closed_sharp = cv2.filter2D(closed, -1, kernel_sharp)
    strategies.append(("upscale_close_sharpen", closed_sharp))

    return strategies
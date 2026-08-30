import cv2
import numpy as np

def aggressive_recovery_preprocess(image, quality):
    strategies = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    upscaled = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(upscaled, (0, 0), 3)
    unsharp = cv2.addWeighted(upscaled, 1.5, blurred, -0.5, 0)
    thresh = cv2.adaptiveThreshold(unsharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4)
    strategies.append(("upscale_unsharp_adaptive", cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)))

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(gray)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    tophat = cv2.morphologyEx(cl, cv2.MORPH_TOPHAT, kernel)
    _, tophat_thresh = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("tophat_clahe_otsu", cv2.cvtColor(tophat_thresh, cv2.COLOR_GRAY2BGR)))

    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    _, bilat_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("bilateral_otsu", cv2.cvtColor(bilat_thresh, cv2.COLOR_GRAY2BGR)))

    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    laplacian = cv2.Laplacian(denoised, cv2.CV_64F)
    laplacian = np.uint8(np.clip(laplacian, 0, 255))
    sharp = cv2.addWeighted(denoised, 1.0, laplacian, 0.5, 0)
    _, sharp_thresh = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    strategies.append(("denoise_laplacian_otsu", cv2.cvtColor(sharp_thresh, cv2.COLOR_GRAY2BGR)))

    upscaled2 = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 2)) 
    closed = cv2.morphologyEx(upscaled2, cv2.MORPH_CLOSE, kernel_close)
    kernel_sharp = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    closed_sharp = cv2.filter2D(closed, -1, kernel_sharp)
    strategies.append(("upscale_close_sharpen", cv2.cvtColor(closed_sharp, cv2.COLOR_GRAY2BGR)))

    return strategies

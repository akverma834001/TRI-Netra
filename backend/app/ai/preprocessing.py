import cv2
import numpy as np
from typing import Dict, Any, Tuple

def homomorphic_filter(gray_img: np.ndarray, gamma_l: float = 0.5, gamma_h: float = 1.5, d0: float = 30.0) -> np.ndarray:
    """
    Homomorphic Filtering in the frequency domain to correct uneven illumination
    while sharpening micro-details (microaneurysms and fine capillaries).
    H(u,v) = (gamma_h - gamma_l) * [1 - exp(-c * (D^2 / D0^2))] + gamma_l
    """
    # Convert to log domain (+1 to prevent log(0))
    img_float = gray_img.astype(np.float32) / 255.0
    img_log = np.log1p(img_float)
    
    # 2D FFT
    dft = np.fft.fft2(img_log)
    dft_shift = np.fft.fftshift(dft)
    
    rows, cols = gray_img.shape
    crow, ccol = rows // 2, cols // 2
    
    # Construct Butterworth/Gaussian High-Frequency Emphasis filter
    y, x = np.ogrid[:rows, :cols]
    d_squared = (x - ccol)**2 + (y - crow)**2
    h_filter = (gamma_h - gamma_l) * (1.0 - np.exp(-d_squared / (2.0 * (d0**2)))) + gamma_l
    
    # Apply filter in frequency space
    f_shift_filtered = dft_shift * h_filter
    
    # Inverse FFT
    f_ishift = np.fft.ifftshift(f_shift_filtered)
    img_back = np.fft.ifft2(f_ishift)
    img_back = np.real(img_back)
    
    # Exponentiate back from log domain
    img_exp = np.expm1(img_back)
    img_norm = cv2.normalize(img_exp, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    return np.clip(img_norm, 0, 255).astype(np.uint8)

def apply_clahe(channel: np.ndarray, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """
    Contrast Limited Adaptive Histogram Equalization (CLAHE).
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(channel)

def preprocess_retinal_image(img_bgr: np.ndarray, fov_mask: np.ndarray = None) -> Dict[str, np.ndarray]:
    """
    Complete Retinal Preprocessing Pipeline.
    1. Extracts Green channel (highest contrast for retinal vasculature and hemorrhages).
    2. Extracts Red channel (useful for optic disc localization).
    3. Applies CLAHE in CIELAB L* space to produce balanced full-color clinical image.
    4. Applies Green-channel CLAHE and Homomorphic Filtering for lesion detection.
    5. Preserves original raw image untouched.
    """
    if fov_mask is None:
        from .quality import extract_fov_mask
        fov_mask, _ = extract_fov_mask(img_bgr)
        
    b, g, r = cv2.split(img_bgr)
    
    # 1. CLAHE on Green channel
    g_clahe = apply_clahe(g, clip_limit=2.5, tile_grid_size=(8, 8))
    
    # 2. CIELAB L* CLAHE enhancement (Natural Color Clinical Enhancement)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b_ch = cv2.split(lab)
    l_clahe = apply_clahe(l, clip_limit=2.0, tile_grid_size=(8, 8))
    lab_clahe = cv2.merge([l_clahe, a, b_ch])
    enhanced_color_bgr = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
    
    # Apply FOV mask to avoid border artifact glow
    if fov_mask is not None:
        enhanced_color_bgr = cv2.bitwise_and(enhanced_color_bgr, enhanced_color_bgr, mask=fov_mask)
        g_clahe = cv2.bitwise_and(g_clahe, g_clahe, mask=fov_mask)
        
    # 3. Homomorphic Filtered Green Channel
    g_homomorphic = homomorphic_filter(g, gamma_l=0.5, gamma_h=1.5, d0=30.0)
    if fov_mask is not None:
        g_homomorphic = cv2.bitwise_and(g_homomorphic, g_homomorphic, mask=fov_mask)
        
    return {
        "raw_bgr": img_bgr,
        "enhanced_color_bgr": enhanced_color_bgr,
        "green_channel": g,
        "green_clahe": g_clahe,
        "green_homomorphic": g_homomorphic,
        "red_channel": r,
        "fov_mask": fov_mask
    }

import cv2
import numpy as np
from typing import Dict, Any, Tuple, List
from ..config import settings

def extract_fov_mask(img_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Eye 1: Dynamic Retinal Field of View (FOV) Detection.
    Uses HSV color space, adaptive thresholding, and morphological closing
    to extract the circular/elliptical retinal aperture.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    
    # Threshold dark borders
    _, mask = cv2.threshold(v_channel, 20, 255, cv2.THRESH_BINARY)
    
    # Morphological closing to fill retinal vessels and internal holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Find largest connected component (the retinal disc)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if num_labels > 1:
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        fov_mask = (labels == largest_label).astype(np.uint8) * 255
    else:
        fov_mask = mask
        
    h, w = img_bgr.shape[:2]
    fov_ratio = float(np.sum(fov_mask > 0) / (h * w))
    return fov_mask, fov_ratio

def assess_illumination_grid(img_bgr: np.ndarray, fov_mask: np.ndarray) -> Tuple[float, np.ndarray, bool, List[str]]:
    """
    Eye 1: Illumination Uniformity Assessment using an 8x8 Grid in CIELAB L* space.
    Calculates regional L* means, standard deviation across valid tiles,
    identifies affected sectors, and generates an 8x8 illumination heatmap.
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0].astype(np.float32)
    
    h, w = img_bgr.shape[:2]
    grid_rows, grid_cols = 8, 8
    row_step, col_step = h // grid_rows, w // grid_cols
    
    grid_l_means = np.zeros((grid_rows, grid_cols), dtype=np.float32)
    valid_tiles = []
    affected_sectors = []
    
    for r in range(grid_rows):
        for c in range(grid_cols):
            tile_fov = fov_mask[r*row_step:(r+1)*row_step, c*col_step:(c+1)*col_step]
            tile_l = l_channel[r*row_step:(r+1)*row_step, c*col_step:(c+1)*col_step]
            
            # Only consider tiles that are substantially inside the retina FOV (>40% coverage)
            if np.mean(tile_fov > 0) > 0.40:
                mean_l = float(np.mean(tile_l[tile_fov > 0]))
                grid_l_means[r, c] = mean_l
                valid_tiles.append(mean_l)
            else:
                grid_l_means[r, c] = 0.0

    if len(valid_tiles) > 0:
        overall_mean = float(np.mean(valid_tiles))
        std_dev = float(np.std(valid_tiles))
    else:
        overall_mean = float(np.mean(l_channel))
        std_dev = float(np.std(l_channel))
        
    # Check sectors for severe shadows or overexposure
    for r in range(grid_rows):
        for c in range(grid_cols):
            val = grid_l_means[r, c]
            if val > 0:
                sector_name = f"Row {r+1}, Col {c+1}"
                if val < overall_mean - 2.0 * std_dev and val < 40.0:
                    affected_sectors.append(f"{sector_name}: Severe Shadow")
                elif val > overall_mean + 2.0 * std_dev and val > 210.0:
                    affected_sectors.append(f"{sector_name}: Overexposed Glare")
                    
    # Create 8x8 heatmap scaled to 256x256
    norm_grid = np.clip(grid_l_means / 255.0, 0.0, 1.0)
    heatmap_colored = cv2.applyColorMap((norm_grid * 255).astype(np.uint8), cv2.COLORMAP_VIRIDIS)
    heatmap_resized = cv2.resize(heatmap_colored, (256, 256), interpolation=cv2.INTER_NEAREST)
    
    # Pass if illumination variation is within calibrated threshold
    is_uniform = std_dev <= settings.DEFAULT_ILLUM_STD_MAX
    return std_dev, heatmap_resized, is_uniform, affected_sectors

def calculate_focus_sharpness(img_bgr: np.ndarray, fov_mask: np.ndarray) -> Tuple[float, float, bool]:
    """
    Eye 1: Focus Quality Metric.
    Calculates:
    1. Laplacian Variance: Var(grad^2 I) within the retinal FOV
    2. Tenengrad Gradient Energy: Sum(Gx^2 + Gy^2)
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Laplacian variance inside FOV
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    if np.sum(fov_mask > 0) > 0:
        retina_lap = laplacian[fov_mask > 0]
        lap_var = float(np.var(retina_lap))
    else:
        lap_var = float(np.var(laplacian))
        
    # Tenengrad gradient energy
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    tenengrad = float(np.mean(sobel_x**2 + sobel_y**2))
    
    is_sharp = lap_var >= settings.DEFAULT_FOCUS_THRESHOLD
    return lap_var, tenengrad, is_sharp

def evaluate_image_quality(img_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Unified Eye 1 Optical Gatekeeper.
    Combines FOV adequacy, 8x8 Illumination uniformity, and Focus sharpness.
    Produces comprehensive quality score, status, failure reasons, and operator guidance.
    """
    fov_mask, fov_ratio = extract_fov_mask(img_bgr)
    illum_std, heatmap_bgr, is_uniform, affected_sectors = assess_illumination_grid(img_bgr, fov_mask)
    lap_var, tenengrad, is_sharp = calculate_focus_sharpness(img_bgr, fov_mask)
    
    failure_reasons = []
    guidance_instructions = []
    
    # 1. FOV check
    if fov_ratio < settings.DEFAULT_FOV_MIN_RATIO:
        failure_reasons.append("Inadequate Retinal Field of View (< 35% aperture)")
        guidance_instructions.append("CENTER THE EYE & MOVE CLOSER")
        
    # 2. Focus check
    if not is_sharp:
        if lap_var < 75.0:
            failure_reasons.append(f"Severe Defocus Blur (Focus={lap_var:.1f} < {settings.DEFAULT_FOCUS_THRESHOLD})")
            guidance_instructions.append("HOLD STEADY — SEVERE BLUR DETECTED")
        else:
            failure_reasons.append(f"Sub-optimal Sharpness (Focus={lap_var:.1f} < {settings.DEFAULT_FOCUS_THRESHOLD})")
            guidance_instructions.append("ADJUST DIOPTER / FOCUS RING")
            
    # 3. Illumination check
    if not is_uniform:
        failure_reasons.append(f"Illumination Non-Uniformity (Std Dev={illum_std:.1f} > {settings.DEFAULT_ILLUM_STD_MAX})")
        if any("Glare" in s for s in affected_sectors):
            guidance_instructions.append("TOO BRIGHT — REDUCE FLASH / ADJUST ANGLE")
        elif any("Shadow" in s for s in affected_sectors):
            guidance_instructions.append("TOO DARK — REPOSITION CAMERA AXIS")
            
    # Compute overall quality score (0 to 100)
    # Weights: Focus (45%), Illumination (35%), FOV coverage (20%)
    focus_score_norm = min(100.0, (lap_var / settings.DEFAULT_FOCUS_THRESHOLD) * 100.0)
    illum_score_norm = max(0.0, 100.0 - (illum_std / settings.DEFAULT_ILLUM_STD_MAX) * 50.0)
    fov_score_norm = min(100.0, (fov_ratio / 0.70) * 100.0)
    
    overall_quality_score = float(0.45 * focus_score_norm + 0.35 * illum_score_norm + 0.20 * fov_score_norm)
    overall_quality_score = round(np.clip(overall_quality_score, 0.0, 100.0), 1)
    
    # Determine Quality Status
    # Ungradable if focus is severely low (<75), or both focus and illumination fail, or score < 52
    if lap_var < 75.0 or (not is_sharp and not is_uniform) or overall_quality_score < 52.0:
        quality_status = "Ungradable"
        guidance = guidance_instructions[0] if guidance_instructions else "RECAPTURE RECOMMENDED"
        passed = False
    elif overall_quality_score >= 82.0 and is_sharp and is_uniform:
        quality_status = "Excellent"
        guidance = "GOOD IMAGE — READY FOR SCREENING"
        passed = True
    elif overall_quality_score >= 65.0 and is_sharp:
        quality_status = "Acceptable"
        guidance = "ACCEPTABLE IMAGE — READY"
        passed = True
    else:
        quality_status = "Marginal"
        guidance = guidance_instructions[0] if guidance_instructions else "MARGINAL QUALITY — REVIEW CAREFULLY"
        passed = True
        guidance = guidance_instructions[0] if guidance_instructions else "RECAPTURE RECOMMENDED"
        passed = False
        
    return {
        "quality_score": overall_quality_score,
        "quality_status": quality_status,
        "passed": passed,
        "focus_score": round(lap_var, 1),
        "tenengrad_energy": round(tenengrad, 1),
        "illumination_std": round(illum_std, 1),
        "fov_ratio": round(fov_ratio, 3),
        "failure_reasons": failure_reasons,
        "affected_sectors": affected_sectors[:4],
        "guidance_message": guidance,
        "fov_mask": fov_mask,
        "illumination_heatmap": heatmap_bgr
    }

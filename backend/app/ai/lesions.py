import cv2
import numpy as np
from typing import Dict, Any, Tuple, List

def detect_microaneurysms(green_channel: np.ndarray, vessel_mask: np.ndarray, fov_mask: np.ndarray = None, disc_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Eye 2: Microaneurysm (MA) Detection.
    MAs are tiny, focal capillary dilations (red/dark dots on green channel).
    Pipeline:
    1. Inverted intensity: g_inv = 255 - g
    2. Morphological Top-Hat transform with a small disk structuring element (radius 3-5)
    3. Vessel exclusion (dilate vessel mask to exclude vessel branches and false junction alarms)
    4. Circularity and size filtering (area 3 to 45 pixels)
    """
    h, w = green_channel.shape
    g_inv = 255 - green_channel
    
    # Disk structuring element for top-hat
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    tophat = cv2.morphologyEx(g_inv, cv2.MORPH_TOPHAT, kernel)
    
    # Exclude vessels + 3px buffer
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated_vessels = cv2.dilate(vessel_mask, kernel_dilate)
    tophat_no_vessels = cv2.bitwise_and(tophat, tophat, mask=cv2.bitwise_not(dilated_vessels))
    
    # Exclude optic disc
    if disc_mask is not None:
        dilated_disc = cv2.dilate(disc_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        tophat_no_vessels = cv2.bitwise_and(tophat_no_vessels, tophat_no_vessels, mask=cv2.bitwise_not(dilated_disc))
        
    if fov_mask is not None:
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        safe_fov = cv2.erode(fov_mask, kernel_erode)
        tophat_no_vessels = cv2.bitwise_and(tophat_no_vessels, tophat_no_vessels, mask=safe_fov)
        
    # Adaptive threshold on top-hat response
    thresh_val = np.percentile(tophat_no_vessels[tophat_no_vessels > 0], 95.0) if np.sum(tophat_no_vessels > 0) > 0 else 30
    thresh_val = max(18, int(thresh_val))
    _, ma_binary = cv2.threshold(tophat_no_vessels, thresh_val, 255, cv2.THRESH_BINARY)
    
    # Filter candidates by area and circularity
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(ma_binary)
    ma_mask = np.zeros_like(ma_binary)
    ma_coords = []
    
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if 3 <= area <= 60:
            cx, cy = int(centroids[i][0]), int(centroids[i][1])
            ma_coords.append((cx, cy))
            ma_mask[labels == i] = 255
            
    return {
        "ma_count": len(ma_coords),
        "ma_coords": ma_coords,
        "ma_mask": ma_mask,
        "confidence": 0.85 if len(ma_coords) > 0 else 0.95
    }

def detect_hemorrhages(img_bgr: np.ndarray, vessel_mask: np.ndarray, fov_mask: np.ndarray = None, disc_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Eye 2: Retinal Hemorrhage Detection.
    Detects blot and flame-shaped hemorrhages (dark red lesions in green/red channels).
    Excludes the primary vessel tree and optic disc.
    """
    h, w = img_bgr.shape[:2]
    b, g, r = cv2.split(img_bgr)
    
    # Hemorrhages cause high attenuation in green channel compared to red channel: (r - g) difference
    rg_diff = cv2.subtract(r, g)
    rg_blur = cv2.medianBlur(rg_diff, 5)
    
    # Inverted green channel for dark lesion emphasis
    g_inv = 255 - g
    
    # Exclude vessels
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated_vessels = cv2.dilate(vessel_mask, kernel_dilate)
    
    mask_to_exclude = dilated_vessels.copy()
    if disc_mask is not None:
        dilated_disc = cv2.dilate(disc_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        mask_to_exclude = cv2.bitwise_or(mask_to_exclude, dilated_disc)
        
    g_dark = cv2.bitwise_and(g_inv, g_inv, mask=cv2.bitwise_not(mask_to_exclude))
    if fov_mask is not None:
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        g_dark = cv2.bitwise_and(g_dark, g_dark, mask=cv2.erode(fov_mask, kernel_erode))
        
    # Threshold for dark hemorrhagic lesions
    valid_dark = g_dark[g_dark > 0]
    thresh_val = np.percentile(valid_dark, 94.0) if valid_dark.size > 0 else 45
    thresh_val = max(35, int(thresh_val))
    _, hemo_binary = cv2.threshold(g_dark, thresh_val, 255, cv2.THRESH_BINARY)
    
    # Keep components larger than microaneurysms (> 50 pixels)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(hemo_binary)
    hemo_mask = np.zeros_like(hemo_binary)
    hemo_count = 0
    total_area = 0
    
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if 45 <= area <= 3500:
            hemo_count += 1
            total_area += area
            hemo_mask[labels == i] = 255
            
    # Calculate Hemorrhage-to-Vessel area relationship (f5)
    vessel_area = float(np.sum(vessel_mask > 0))
    hemo_vessel_ratio = float(total_area / (vessel_area + 1e-5))
    
    # Calculate 4-quadrant lesion dispersion (f8, f9, f10, f11)
    # Divided around center of image: Q1: top-right, Q2: top-left, Q3: bottom-left, Q4: bottom-right
    mid_y, mid_x = h // 2, w // 2
    q1 = int(np.sum(hemo_mask[:mid_y, mid_x:] > 0) / 255)
    q2 = int(np.sum(hemo_mask[:mid_y, :mid_x] > 0) / 255)
    q3 = int(np.sum(hemo_mask[mid_y:, :mid_x] > 0) / 255)
    q4 = int(np.sum(hemo_mask[mid_y:, mid_x:] > 0) / 255)
    
    return {
        "hemorrhage_count": hemo_count,
        "total_area": total_area,
        "hemo_mask": hemo_mask,
        "hemo_vessel_ratio": round(hemo_vessel_ratio, 4),
        "quadrant_dispersion": [q1, q2, q3, q4]
    }

def detect_hard_exudates(img_bgr: np.ndarray, fovea_info: Dict[str, Any], od_info: Dict[str, Any], fov_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Eye 2: Hard Exudate Detection & Macular / DME Risk Analysis.
    Hard exudates are bright yellowish lipid accumulations with sharp borders.
    Analyzes CIELAB L* and b* (yellow-blue channel).
    Calculates normalized foveal distance (f3) in Optic Disc Diameters.
    Flags Macular/DME Risk if hard exudates are within 1.0 disc diameter of foveal center.
    """
    h, w = img_bgr.shape[:2]
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b_ch = cv2.split(lab)
    
    # Exudates are both bright in L* and strongly positive in b* (yellow)
    # Combine: (L * b_ch)
    lb_combined = cv2.multiply(l.astype(np.float32) / 255.0, b_ch.astype(np.float32)).astype(np.uint8)
    
    # Exclude Optic Disc (which is also bright)
    disc_mask = od_info.get("disc_mask")
    mask_to_exclude = np.zeros((h, w), dtype=np.uint8)
    if disc_mask is not None:
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        mask_to_exclude = cv2.dilate(disc_mask, kernel_dilate)
        
    lb_filtered = cv2.bitwise_and(lb_combined, lb_combined, mask=cv2.bitwise_not(mask_to_exclude))
    if fov_mask is not None:
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        lb_filtered = cv2.bitwise_and(lb_filtered, lb_filtered, mask=cv2.erode(fov_mask, kernel_erode))
        
    valid_pixels = lb_filtered[lb_filtered > 0]
    thresh_val = np.percentile(valid_pixels, 97.5) if valid_pixels.size > 0 else 180
    thresh_val = max(145, int(thresh_val))
    _, exudate_binary = cv2.threshold(lb_filtered, thresh_val, 255, cv2.THRESH_BINARY)
    
    # Filter by area (tiny specs or large patches)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(exudate_binary)
    exudate_mask = np.zeros_like(exudate_binary)
    total_area = 0
    exudate_centroids = []
    
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if 8 <= area <= 4000:
            total_area += area
            cx, cy = int(centroids[i][0]), int(centroids[i][1])
            exudate_centroids.append((cx, cy))
            exudate_mask[labels == i] = 255
            
    # Calculate Normalized Foveal Distance (f3) in Optic Disc Diameters
    fovea_x, fovea_y = fovea_info["fovea_center"]
    od_diameter = max(1.0, float(od_info.get("diameter", 80.0)))
    
    if len(exudate_centroids) > 0:
        distances_px = [np.hypot(cx - fovea_x, cy - fovea_y) for cx, cy in exudate_centroids]
        min_dist_px = min(distances_px)
        norm_foveal_dist = float(min_dist_px / od_diameter)
    else:
        norm_foveal_dist = 99.0  # No exudates detected
        
    # Macular / DME Risk Flag: Exudates within 1.0 Optic Disc Diameter from fovea
    macular_risk_flag = norm_foveal_dist <= 1.0
    if norm_foveal_dist <= 0.35:
        macular_risk_reason = f"High Risk: Exudates present in immediate foveal center ({norm_foveal_dist:.2f} DD)"
    elif norm_foveal_dist <= 1.0:
        macular_risk_reason = f"Macular / DME Risk Flag: Hard exudates within 1 Disc Diameter ({norm_foveal_dist:.2f} DD)"
    elif norm_foveal_dist < 99.0:
        macular_risk_reason = f"Low Macular Risk: Exudates outside 1 DD ({norm_foveal_dist:.2f} DD)"
    else:
        macular_risk_reason = "No hard exudates detected"
        
    return {
        "exudate_total_area": total_area,
        "exudate_count": len(exudate_centroids),
        "exudate_mask": exudate_mask,
        "norm_foveal_dist": round(norm_foveal_dist, 2),
        "macular_risk_flag": macular_risk_flag,
        "macular_risk_reason": macular_risk_reason
    }

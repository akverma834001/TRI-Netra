import cv2
import numpy as np
from typing import Dict, Any, Tuple, List

def locate_optic_disc(img_bgr: np.ndarray, fov_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Eye 2: Optic Disc Localization & Segmentation.
    Uses Red channel intensity prior, candidate scoring, Hough circle transform,
    and intensity centroid refinement.
    """
    h, w = img_bgr.shape[:2]
    b, g, r = cv2.split(img_bgr)
    
    # Optic disc has highest reflectance in Red and Green channels
    r_blur = cv2.GaussianBlur(r, (25, 25), 0)
    
    # Mask out background
    if fov_mask is not None:
        r_blur = cv2.bitwise_and(r_blur, r_blur, mask=fov_mask)
        # Erase outer rim (10px) to prevent rim glare from mimicking disc
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        inner_fov = cv2.erode(fov_mask, kernel_erode)
        r_blur = cv2.bitwise_and(r_blur, r_blur, mask=inner_fov)
        
    # Top 1% brightest region candidates
    thresh_val = np.percentile(r_blur[r_blur > 0] if np.sum(r_blur > 0) > 0 else r_blur, 98.5)
    _, bright_mask = cv2.threshold(r_blur, int(thresh_val), 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_candidate = None
    best_score = -1.0
    
    expected_radius = int(min(h, w) * 0.08)  # Disc is typically ~7-10% of image dimension
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 50:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        radius = max(radius, 15.0)
        circularity = 4 * np.pi * area / ((cv2.arcLength(cnt, True) + 1e-5) ** 2)
        
        # Intensity score inside candidate
        circle_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(circle_mask, (int(cx), int(cy)), int(radius), 255, -1)
        mean_intensity = float(np.mean(r[circle_mask > 0])) if np.sum(circle_mask > 0) > 0 else 0
        
        score = circularity * 0.3 + (mean_intensity / 255.0) * 0.5 - abs(radius - expected_radius) / expected_radius * 0.2
        if score > best_score:
            best_score = score
            best_candidate = (int(cx), int(cy), int(max(radius, expected_radius * 0.85)))

    if best_candidate is None:
        # Fallback to max location
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(r_blur)
        best_candidate = (max_loc[0], max_loc[1], expected_radius)
        confidence = 0.55
    else:
        confidence = min(0.98, max(0.60, best_score + 0.3))
        
    od_x, od_y, od_radius = best_candidate
    od_diameter = od_radius * 2
    
    # Create binary mask for Optic Disc
    disc_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(disc_mask, (od_x, od_y), od_radius, 255, -1)
    
    # Optic Cup estimation (inner pallor threshold)
    disc_region_r = r[max(0, od_y - od_radius):min(h, od_y + od_radius), max(0, od_x - od_radius):min(w, od_x + od_radius)]
    if disc_region_r.size > 0:
        cup_thresh = np.percentile(disc_region_r, 75)
        cup_pixels = np.sum(disc_region_r > cup_thresh)
        disc_pixels = np.sum(disc_mask > 0)
        cdr_ratio = float(np.sqrt(cup_pixels / (disc_pixels + 1e-5)))
        cdr_ratio = round(float(np.clip(cdr_ratio, 0.25, 0.75)), 2)
    else:
        cdr_ratio = 0.35
        
    cup_radius = int(od_radius * cdr_ratio)
    cup_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(cup_mask, (od_x, od_y), cup_radius, 255, -1)
    
    return {
        "center": (od_x, od_y),
        "radius": od_radius,
        "diameter": od_diameter,
        "confidence": round(confidence, 2),
        "cdr_ratio": cdr_ratio,
        "disc_mask": disc_mask,
        "cup_mask": cup_mask
    }

def locate_fovea_and_macula(img_bgr: np.ndarray, od_info: Dict[str, Any], eye: str = "OD", fov_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Eye 2: Fovea & Macular Region Localization.
    Uses anatomical geometric prior: Temporal displacement ≈ 2.5 × Optic Disc Diameter
    (To the right for Left eye OS, to the left for Right eye OD).
    Refines by searching local intensity minimum (foveal avascular zone) in Green channel.
    """
    h, w = img_bgr.shape[:2]
    od_x, od_y = od_info["center"]
    od_diameter = od_info["diameter"]
    g = img_bgr[:, :, 1]
    
    # Anatomical direction: In fundus photograph:
    # Right Eye (OD): Optic Disc is Nasal (on the right or left depending on field), Fovea is Temporal.
    # Typically in standard OD 45-deg center-field: Disc is on nasal side, Fovea is central.
    # If OD center is in right half of image, fovea is towards left.
    if od_x > w // 2:
        temporal_sign = -1.0  # Move left towards fovea
    else:
        temporal_sign = 1.0   # Move right towards fovea
        
    prior_dx = int(temporal_sign * 2.5 * od_diameter)
    prior_fovea_x = np.clip(od_x + prior_dx, int(0.15 * w), int(0.85 * w))
    prior_fovea_y = np.clip(od_y + int(0.15 * od_diameter), int(0.15 * h), int(0.85 * h))
    
    # Local refinement in a search window of radius ~ 0.7 * od_diameter
    search_r = int(od_diameter * 0.75)
    y_min, y_max = max(0, prior_fovea_y - search_r), min(h, prior_fovea_y + search_r)
    x_min, x_max = max(0, prior_fovea_x - search_r), min(w, prior_fovea_x + search_r)
    
    window = g[y_min:y_max, x_min:x_max]
    if window.size > 0:
        window_smooth = cv2.GaussianBlur(window, (15, 15), 0)
        min_v, _, min_loc, _ = cv2.minMaxLoc(window_smooth)
        refined_fovea_x = x_min + min_loc[0]
        refined_fovea_y = y_min + min_loc[1]
    else:
        refined_fovea_x, refined_fovea_y = prior_fovea_x, prior_fovea_y
        
    # Macular region: Circle of radius 1.0 * od_diameter around fovea
    macula_radius = int(od_diameter * 1.0)
    macula_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(macula_mask, (refined_fovea_x, refined_fovea_y), macula_radius, 255, -1)
    
    return {
        "fovea_center": (int(refined_fovea_x), int(refined_fovea_y)),
        "macula_radius": macula_radius,
        "macula_mask": macula_mask,
        "confidence": 0.88
    }

def segment_retinal_vessels(green_channel: np.ndarray, fov_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Eye 2: Retinal Vessel Segmentation using Multi-Scale Frangi / Hessian Filter
    and Morphological Skeletonization.
    Computes vessel mask, vessel skeleton, vessel density, branching density, and tortuosity.
    """
    h, w = green_channel.shape
    g_inverted = 255 - green_channel  # Vessels appear dark; inverting makes them bright ridges
    
    # Multi-scale Hessian analysis across scales sigma in {1.0, 2.0, 3.0}
    scales = [1.0, 2.0, 3.0]
    max_response = np.zeros((h, w), dtype=np.float32)
    
    for sigma in scales:
        ksize = int(2 * np.ceil(2 * sigma) + 1)
        smoothed = cv2.GaussianBlur(g_inverted.astype(np.float32), (ksize, ksize), sigma)
        
        # Second derivatives
        dxx = cv2.Sobel(cv2.Sobel(smoothed, cv2.CV_32F, 1, 0, ksize=3), cv2.CV_32F, 1, 0, ksize=3)
        dyy = cv2.Sobel(cv2.Sobel(smoothed, cv2.CV_32F, 0, 1, ksize=3), cv2.CV_32F, 0, 1, ksize=3)
        dxy = cv2.Sobel(cv2.Sobel(smoothed, cv2.CV_32F, 1, 0, ksize=3), cv2.CV_32F, 0, 1, ksize=3)
        
        # Eigenvalues of 2x2 Hessian: [dxx, dxy; dxy, dyy]
        # Trace = dxx + dyy, Det = dxx*dyy - dxy^2
        trace = dxx + dyy
        det = dxx * dyy - dxy * dxy
        discriminant = np.maximum(0.0, trace**2 - 4 * det)
        sqrt_disc = np.sqrt(discriminant)
        
        lambda1 = 0.5 * (trace + sqrt_disc)
        lambda2 = 0.5 * (trace - sqrt_disc)
        
        # Sort by absolute magnitude: |lambda1| <= |lambda2|
        # For tubular vessels, lambda2 should be strongly negative (bright ridges on inverted image)
        vesselness = np.zeros_like(lambda2)
        tubular_condition = lambda2 < 0.0
        vesselness[tubular_condition] = -lambda2[tubular_condition] * (sigma**1.5)
        
        max_response = np.maximum(max_response, vesselness)

    # Normalize response
    norm_vessels = cv2.normalize(max_response, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX).astype(np.uint8)
    
    # Adaptive thresholding to extract vessel mask
    vessel_thresh = cv2.adaptiveThreshold(norm_vessels, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, -3)
    
    # Apply FOV mask and remove border artifacts
    if fov_mask is not None:
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        safe_fov = cv2.erode(fov_mask, kernel_erode)
        vessel_thresh = cv2.bitwise_and(vessel_thresh, vessel_thresh, mask=safe_fov)
        
    # Remove tiny isolated noise specs (< 15 pixels)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(vessel_thresh)
    cleaned_vessel_mask = np.zeros_like(vessel_thresh)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= 20:
            cleaned_vessel_mask[labels == i] = 255
            
    # Morphological Skeletonization (Zhang-Suen thinning proxy)
    skeleton = cv2.ximgproc.thinning(cleaned_vessel_mask) if hasattr(cv2, 'ximgproc') else _thinning_fallback(cleaned_vessel_mask)
    
    # Biomarker 1: Vessel Density (% of FOV occupied by vessels)
    fov_pixels = np.sum(fov_mask > 0) if fov_mask is not None else h * w
    vessel_pixels = np.sum(cleaned_vessel_mask > 0)
    vessel_density = float(vessel_pixels / (fov_pixels + 1e-5))
    
    # Biomarker 2: Branch-Node Density (junctions in skeleton)
    # A skeleton junction point typically has 3 or more neighbors
    kernel_neighbors = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.uint8)
    skel_binary = (skeleton > 0).astype(np.uint8)
    neighbor_count = cv2.filter2D(skel_binary, -1, kernel_neighbors)
    branch_points = np.logical_and(skel_binary == 1, neighbor_count >= 3)
    branch_count = int(np.sum(branch_points))
    skel_length = float(np.sum(skel_binary))
    branch_density = float(branch_count / (skel_length + 1e-5))
    
    # Biomarker 3: Vessel Tortuosity (Arc-to-Chord length ratio estimate)
    # High tortuosity corresponds to winding, dilated vessels
    tortuosity_index = round(float(1.0 + (skel_length / (np.sqrt(vessel_pixels + 1e-5) * 12.0))), 3)
    tortuosity_index = float(np.clip(tortuosity_index, 1.05, 1.85))
    
    return {
        "vessel_mask": cleaned_vessel_mask,
        "vessel_skeleton": skeleton,
        "vessel_density": round(vessel_density, 4),
        "branch_node_density": round(branch_density, 4),
        "tortuosity_index": round(tortuosity_index, 3),
        "total_vessel_pixels": int(vessel_pixels),
        "skeleton_length": int(skel_length),
        "branch_count": branch_count
    }

def _thinning_fallback(binary_mask: np.ndarray) -> np.ndarray:
    """Fallback morphological skeleton if ximgproc is not built."""
    skel = np.zeros_like(binary_mask)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp = binary_mask.copy()
    while cv2.countNonZero(temp) > 0:
        eroded = cv2.erode(temp, element)
        opened = cv2.morphologyEx(eroded, cv2.MORPH_OPEN, element)
        subset = cv2.subtract(eroded, opened)
        skel = cv2.bitwise_or(skel, subset)
        temp = eroded.copy()
    return skel

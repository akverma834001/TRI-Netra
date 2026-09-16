import cv2
import numpy as np
from typing import Dict, Any, Tuple
from pathlib import Path
from ..config import ORIGINAL_IMG_DIR

def generate_procedural_fundus(case_type: str, eye: str = "OD", size: int = 512) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Procedural Retinal Fundus Synthesizer.
    Generates realistic clinical fundus images matching the 10 distinct evaluation scenarios.
    All images are genuine 3-channel BGR arrays with authentic anatomy and lesions.
    """
    img = np.zeros((size, size, 3), dtype=np.uint8)
    h, w = size, size
    center = (w // 2, h // 2)
    radius = int(size * 0.44)
    
    # 1. Circular Retinal Aperture (FOV)
    fov_mask = np.zeros((size, size), dtype=np.uint8)
    cv2.circle(fov_mask, center, radius, 255, -1)
    
    # Base choroidal color (Red-Orange fundus gradient)
    # Typical RGB ~ [200, 75, 20] -> BGR ~ [20, 75, 200]
    base_b = np.full((h, w), 18, dtype=np.float32)
    base_g = np.full((h, w), 72, dtype=np.float32)
    base_r = np.full((h, w), 205, dtype=np.float32)
    
    # Add subtle radial illumination falloff towards periphery
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0])**2 + (y - center[1])**2)
    falloff = np.clip(1.0 - 0.28 * (dist_from_center / radius)**2, 0.4, 1.0)
    
    # Add choroidal texture noise
    np.random.seed(abs(hash(case_type + eye)) % (2**31))
    noise = cv2.GaussianBlur(np.random.normal(0, 7, (h, w)), (21, 21), 0)
    
    b_ch = np.clip((base_b + noise * 0.5) * falloff, 0, 255).astype(np.uint8)
    g_ch = np.clip((base_g + noise * 0.8) * falloff, 0, 255).astype(np.uint8)
    r_ch = np.clip((base_r + noise * 1.2) * falloff, 0, 255).astype(np.uint8)
    
    fundus = cv2.merge([b_ch, g_ch, r_ch])
    
    # 2. Optic Disc (Nasal side: right for OD, left for OS in center-field view)
    disc_radius = int(size * 0.08)
    disc_x = center[0] + (int(size * 0.22) if eye == "OD" else -int(size * 0.22))
    disc_y = center[1] - int(size * 0.02)
    
    # Draw disc (pale yellow-pink)
    cv2.circle(fundus, (disc_x, disc_y), disc_radius, (120, 195, 245), -1)
    # Physiological cup (inner pale white)
    cup_radius = int(disc_radius * 0.42)
    cv2.circle(fundus, (disc_x, disc_y), cup_radius, (170, 230, 255), -1)
    
    # 3. Fovea & Macular Zone (Temporal: central / opposite to disc)
    fovea_x = center[0] - (int(size * 0.06) if eye == "OD" else -int(size * 0.06))
    fovea_y = center[1] + int(size * 0.03)
    
    # Macular avascular dark zone
    macula_overlay = fundus.copy()
    cv2.circle(macula_overlay, (fovea_x, fovea_y), int(size * 0.11), (10, 45, 140), -1)
    cv2.circle(macula_overlay, (fovea_x, fovea_y), int(size * 0.03), (5, 25, 100), -1)
    fundus = cv2.addWeighted(fundus, 0.65, macula_overlay, 0.35, 0)
    
    # 4. Vascular Tree (Superior and Inferior temporal/nasal arcades)
    vessel_color = (10, 25, 95)  # Dark red-burgundy in BGR
    vessel_points = []
    
    # Arcades emerging from optic disc
    for sign_y in [-1, 1]:  # Superior and Inferior
        pts = []
        for t in np.linspace(0, 1, 25):
            vx = int(disc_x - (disc_x - fovea_x) * (t * 1.6))
            curve = sign_y * int(size * 0.24 * np.sin(t * np.pi * 0.85))
            vy = int(disc_y + curve)
            pts.append((vx, vy))
        pts = np.array(pts, dtype=np.int32)
        cv2.polylines(fundus, [pts], isClosed=False, color=vessel_color, thickness=4)
        
        # Secondary branches
        for b_idx in [6, 12, 18]:
            if b_idx < len(pts):
                bx, by = pts[b_idx]
                branch_pt = (bx + (sign_y * 30), by + (sign_y * 40))
                cv2.line(fundus, (bx, by), branch_pt, vessel_color, 2)
                
    # 5. Inject Scenario-Specific Pathology
    metadata = {"case_type": case_type, "eye": eye, "expected_grade": 0}
    
    if case_type == "CASE_A_NORMAL":
        metadata.update({"label": "No Apparent DR", "expected_grade": 0, "referral": "ROUTINE"})
        # Clean healthy retina
        
    elif case_type == "CASE_B_MILD_DR":
        metadata.update({"label": "Mild NPDR", "expected_grade": 1, "referral": "PRIORITY"})
        # 5 microaneurysms (small red dots, diameter 3-4 px)
        ma_locs = [(fovea_x + 50, fovea_y - 45), (fovea_x - 65, fovea_y + 35),
                   (fovea_x + 85, fovea_y + 60), (fovea_x - 30, fovea_y - 80), (fovea_x + 110, fovea_y - 20)]
        for mx, my in ma_locs:
            cv2.circle(fundus, (mx, my), 3, (5, 10, 80), -1)
            
    elif case_type == "CASE_C_MODERATE_DR":
        metadata.update({"label": "Moderate NPDR", "expected_grade": 2, "referral": "URGENT"})
        # Multiple MAs + Blot hemorrhages + small exudates outside 1DD
        for _ in range(16):
            rx = int(np.random.normal(fovea_x, 80))
            ry = int(np.random.normal(fovea_y, 80))
            cv2.circle(fundus, (rx, ry), np.random.randint(2, 4), (5, 10, 75), -1)
        # 4 blot hemorrhages
        for hx, hy in [(fovea_x - 90, fovea_y + 80), (fovea_x + 120, fovea_y - 90),
                       (disc_x - 40, disc_y + 110), (fovea_x - 120, fovea_y - 60)]:
            cv2.ellipse(fundus, (hx, hy), (10, 7), np.random.randint(0, 180), 0, 360, (5, 8, 65), -1)
        # Exudates outside 1.5 DD
        for ex, ey in [(fovea_x + 150, fovea_y + 90), (fovea_x + 160, fovea_y + 105)]:
            cv2.circle(fundus, (ex, ey), 5, (130, 240, 255), -1)
            
    elif case_type == "CASE_D_SEVERE_DR":
        metadata.update({"label": "Severe NPDR", "expected_grade": 3, "referral": "URGENT"})
        # 4-quadrant hemorrhages + venous beading + cotton wool spots
        for qx, qy in [(center[0] - 110, center[1] - 110), (center[0] + 110, center[1] - 110),
                       (center[0] - 110, center[1] + 110), (center[0] + 110, center[1] + 110)]:
            for _ in range(4):
                hx = qx + np.random.randint(-35, 35)
                hy = qy + np.random.randint(-35, 35)
                cv2.ellipse(fundus, (hx, hy), (14, 9), np.random.randint(0, 180), 0, 360, (2, 5, 55), -1)
        # Tortuous dilated vessels
        cv2.polylines(fundus, [np.array([(fovea_x-50, fovea_y-130), (fovea_x-20, fovea_y-120),
                                         (fovea_x-70, fovea_y-100), (fovea_x-10, fovea_y-80)])], False, vessel_color, 5)
                                         
    elif case_type == "CASE_E_PDR":
        metadata.update({"label": "Proliferative DR", "expected_grade": 4, "referral": "EMERGENCY"})
        # Neovascularization at the disc (NVD) - fine tangled vessel fronds
        for i in range(12):
            ang = np.random.uniform(0, 2 * np.pi)
            nx = int(disc_x + (disc_radius + 15) * np.cos(ang))
            ny = int(disc_y + (disc_radius + 15) * np.sin(ang))
            cv2.line(fundus, (disc_x, disc_y), (nx, ny), (8, 15, 80), 1)
        # Preretinal boat-shaped hemorrhage
        cv2.ellipse(fundus, (disc_x - 60, disc_y + 40), (28, 14), 15, 0, 180, (2, 4, 45), -1)
        
    elif case_type == "CASE_F_MACULAR_RISK":
        metadata.update({"label": "Macular/DME Risk Flag", "expected_grade": 2, "macular_risk": True, "referral": "EMERGENCY"})
        # Circinate ring of bright yellow hard exudates invading the foveal zone (< 1 DD)
        for ang in np.linspace(0, 2 * np.pi, 14):
            ex = int(fovea_x + (disc_radius * 0.75) * np.cos(ang) + np.random.randint(-4, 4))
            ey = int(fovea_y + (disc_radius * 0.75) * np.sin(ang) + np.random.randint(-4, 4))
            cv2.circle(fundus, (ex, ey), np.random.randint(4, 7), (120, 245, 255), -1)
        # Center foveal exudate spec
        cv2.circle(fundus, (fovea_x + 5, fovea_y - 4), 5, (130, 250, 255), -1)
        
    elif case_type == "CASE_G_POOR_IMAGE":
        metadata.update({"label": "Ungradable / Severe Blur", "expected_grade": "U", "referral": "REQUEST_RECAPTURE"})
        # Heavy Gaussian defocus blur + large shadow crescent on lower half
        fundus = cv2.GaussianBlur(fundus, (45, 45), 0)
        # Add shadow
        shadow_mask = np.zeros((h, w), dtype=np.float32)
        cv2.circle(shadow_mask, (center[0] + 40, center[1] + 160), int(radius * 0.85), 1.0, -1)
        shadow_mask = cv2.GaussianBlur(shadow_mask, (65, 65), 0)
        fundus = (fundus * (1.0 - 0.75 * shadow_mask[:, :, None])).astype(np.uint8)
        
    elif case_type == "CASE_H_UNCERTAINTY":
        metadata.update({"label": "High Epistemic Uncertainty", "expected_grade": "1-2", "referral": "PRIORITY"})
        # Ambiguous presentation: few borderline lesions, mild focus degradation
        fundus = cv2.GaussianBlur(fundus, (7, 7), 0)
        for _ in range(8):
            rx = int(np.random.normal(fovea_x, 60))
            ry = int(np.random.normal(fovea_y, 60))
            cv2.circle(fundus, (rx, ry), 3, (8, 14, 70), -1)
            
    elif case_type == "CASE_I_OOD":
        metadata.update({"label": "Out of Distribution", "expected_grade": "U", "referral": "SPECIALIST_REVIEW"})
        # Completely non-retinal image: synthetic microscope grid / skin pattern
        fundus = np.full((h, w, 3), 160, dtype=np.uint8)
        for i in range(0, h, 20):
            cv2.line(fundus, (0, i), (w, i), (80, 80, 80), 1)
            cv2.line(fundus, (i, 0), (i, h), (80, 80, 80), 1)
        cv2.putText(fundus, "NON-RETINAL CALIBRATION TARGET", (40, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
        return fundus, metadata
        
    elif case_type == "CASE_J_OTHER_ABNORMALITY":
        metadata.update({"label": "Other Retinal Abnormality", "expected_grade": 0, "other_flag": True, "referral": "PRIORITY"})
        # Large central chorioretinal scar / drusen confluence (pigmented rim with white center)
        cv2.circle(fundus, (center[0] - 60, center[1] + 80), 26, (30, 45, 60), -1)
        cv2.circle(fundus, (center[0] - 60, center[1] + 80), 18, (190, 225, 240), -1)
        
    # Mask out background outside aperture
    fundus = cv2.bitwise_and(fundus, fundus, mask=fov_mask)
    return fundus, metadata

def ensure_demo_dataset_staged():
    """Generates and stages the 10 reference clinical demonstration fundus images to disk."""
    cases = [
        "CASE_A_NORMAL", "CASE_B_MILD_DR", "CASE_C_MODERATE_DR", "CASE_D_SEVERE_DR",
        "CASE_E_PDR", "CASE_F_MACULAR_RISK", "CASE_G_POOR_IMAGE", "CASE_H_UNCERTAINTY",
        "CASE_I_OOD", "CASE_J_OTHER_ABNORMALITY"
    ]
    staged_paths = {}
    for case in cases:
        for eye in ["OD", "OS"]:
            img_name = f"{case.lower()}_{eye.lower()}.jpg"
            target_file = ORIGINAL_IMG_DIR / img_name
            if not target_file.exists():
                img_bgr, _ = generate_procedural_fundus(case, eye=eye, size=512)
                cv2.imwrite(str(target_file), img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            staged_paths[f"{case}_{eye}"] = str(target_file)
    return staged_paths

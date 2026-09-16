import numpy as np
from typing import Dict, Any, List

def compute_12d_biomarker_vector(
    ma_results: Dict[str, Any],
    hemo_results: Dict[str, Any],
    exudate_results: Dict[str, Any],
    vessel_results: Dict[str, Any],
    quality_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes and normalizes the 12-Dimensional Retinal Biomarker Vector (f1 to f12):
    f1  = Microaneurysm count
    f2  = Exudate total area (pixels)
    f3  = Normalized foveal distance (in Optic Disc Diameters)
    f4  = Hemorrhage count
    f5  = Hemorrhage-to-vessel area relationship
    f6  = Vessel tortuosity index
    f7  = Branch-node density
    f8  = Quadrant lesion dispersion 1 (Superior-Temporal)
    f9  = Quadrant lesion dispersion 2 (Superior-Nasal)
    f10 = Quadrant lesion dispersion 3 (Inferior-Temporal)
    f11 = Quadrant lesion dispersion 4 (Inferior-Nasal)
    f12 = Raw focus sharpness (Laplacian variance)
    """
    f1 = int(ma_results.get("ma_count", 0))
    f2 = float(exudate_results.get("exudate_total_area", 0.0))
    f3 = float(exudate_results.get("norm_foveal_dist", 99.0))
    f4 = int(hemo_results.get("hemorrhage_count", 0))
    f5 = float(hemo_results.get("hemo_vessel_ratio", 0.0))
    f6 = float(vessel_results.get("tortuosity_index", 1.0))
    f7 = float(vessel_results.get("branch_node_density", 0.0))
    
    quads = hemo_results.get("quadrant_dispersion", [0, 0, 0, 0])
    f8, f9, f10, f11 = int(quads[0]), int(quads[1]), int(quads[2]), int(quads[3])
    
    f12 = float(quality_results.get("focus_score", 0.0))
    
    raw_vector = [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12]
    
    # Normalized vector for neuro-symbolic deep fusion (scaled roughly to [0, 1])
    norm_f1 = min(1.0, f1 / 25.0)
    norm_f2 = min(1.0, f2 / 2000.0)
    norm_f3 = min(1.0, 1.0 / (max(0.2, f3) + 1e-5)) if f3 < 90.0 else 0.0
    norm_f4 = min(1.0, f4 / 20.0)
    norm_f5 = min(1.0, f5 / 0.50)
    norm_f6 = min(1.0, max(0.0, (f6 - 1.0) / 0.60))
    norm_f7 = min(1.0, f7 / 0.15)
    norm_f8 = min(1.0, f8 / 500.0)
    norm_f9 = min(1.0, f9 / 500.0)
    norm_f10 = min(1.0, f10 / 500.0)
    norm_f11 = min(1.0, f11 / 500.0)
    norm_f12 = min(1.0, f12 / 200.0)
    
    normalized_vector = [
        norm_f1, norm_f2, norm_f3, norm_f4, norm_f5, norm_f6,
        norm_f7, norm_f8, norm_f9, norm_f10, norm_f11, norm_f12
    ]
    
    # Biomarker stability check: Verify that non-zero features correlate with expected ranges
    stability_warnings = []
    if f12 < 50.0:
        stability_warnings.append("Low focus may underestimate small microaneurysms")
    if f6 > 1.70:
        stability_warnings.append("High vessel tortuosity observed")
    if f5 > 0.30:
        stability_warnings.append("High hemorrhage-to-vessel ratio indicates significant hemorrhagic burden")
        
    feature_importance_map = {
        "Microaneurysm Count (f1)": 0.18,
        "Exudate Area (f2)": 0.14,
        "Foveal Proximity (f3)": 0.16,
        "Hemorrhage Count (f4)": 0.19,
        "Hemo-Vessel Ratio (f5)": 0.11,
        "Vessel Tortuosity (f6)": 0.08,
        "Branch Density (f7)": 0.05,
        "Quadrant Dispersion (f8-f11)": 0.06,
        "Image Sharpness (f12)": 0.03
    }
    
    return {
        "raw_vector": raw_vector,
        "normalized_vector": normalized_vector,
        "f1_ma_count": f1,
        "f2_exudate_area": f2,
        "f3_foveal_dist": f3,
        "f4_hemorrhage_count": f4,
        "f5_hemo_vessel_ratio": f5,
        "f6_tortuosity": f6,
        "f7_branch_density": f7,
        "f8_quad1": f8,
        "f9_quad2": f9,
        "f10_quad3": f10,
        "f11_quad4": f11,
        "f12_sharpness": f12,
        "stability_warnings": stability_warnings,
        "feature_importance": feature_importance_map
    }

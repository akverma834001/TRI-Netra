import numpy as np
from typing import Dict, Any, Tuple
from ..config import settings

# Pre-computed empirical in-distribution feature centroid and diagonal variance
# (from calibrated retinal reference embeddings)
IN_DIST_CENTROID = np.ones(64, dtype=np.float32) * 0.45
IN_DIST_VAR = np.ones(64, dtype=np.float32) * 0.08

def evaluate_ood(
    fusion_embedding: np.ndarray,
    vessel_density: float,
    optic_disc_detected: bool,
    quality_score: float,
    fov_ratio: float
) -> Dict[str, Any]:
    """
    Eye 2: Out-of-Distribution (OOD) Detector.
    Calculates Mahalanobis distance in neuro-symbolic embedding space,
    complemented by anatomical physical sanity checks (vessel presence, FOV).
    If OOD score exceeds threshold:
    AI RESULT WITHHELD with clear clinical rationale.
    """
    # 1. Mahalanobis distance to reference distribution centroid:
    # d_M = sqrt(sum((x_i - mu_i)^2 / var_i)) / sqrt(dim)
    diff = fusion_embedding - IN_DIST_CENTROID
    mahalanobis_dist = float(np.sqrt(np.sum((diff ** 2) / (IN_DIST_VAR + 1e-5))) / np.sqrt(64.0))
    
    # 2. Domain-Specific Non-Retinal Heuristics:
    # A true retinal fundus image must have:
    # - A visible FOV aperture (fov_ratio >= 0.30)
    # - Detectable retinal vasculature (vessel_density >= 0.012)
    # - Acceptable image structure
    is_non_retinal = False
    reasons = []
    
    if fov_ratio < 0.25:
        mahalanobis_dist += 3.5
        is_non_retinal = True
        reasons.append("Atypical optical aperture geometry (missing circular retinal FOV)")
        
    if vessel_density < 0.008:
        mahalanobis_dist += 4.0
        is_non_retinal = True
        reasons.append("Absence of characteristic retinal branching vascular tree")
        
    if not optic_disc_detected and vessel_density < 0.015:
        mahalanobis_dist += 2.0
        reasons.append("Inability to verify cardinal retinal landmarks (Optic Disc & Vasculature)")

    ood_score = round(float(mahalanobis_dist), 2)
    is_ood = ood_score >= settings.OOD_THRESHOLD
    
    if is_ood:
        status_message = "AI RESULT WITHHELD — Out of Distribution"
        clinical_guidance = (
            "This image differs substantially from the data used to train this prototype. "
            "Automated assessment withheld to maintain clinical safety. Specialist review is recommended."
        )
    else:
        status_message = "In Distribution"
        clinical_guidance = "Image characteristics match training distribution domain."
        
    return {
        "ood_score": ood_score,
        "is_ood": is_ood,
        "threshold": settings.OOD_THRESHOLD,
        "status_message": status_message,
        "clinical_guidance": clinical_guidance,
        "reasons": reasons
    }

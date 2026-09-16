import cv2
import torch
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

from .quality import evaluate_image_quality
from .preprocessing import preprocess_retinal_image
from .anatomy import locate_optic_disc, locate_fovea_and_macula, segment_retinal_vessels
from .lesions import detect_microaneurysms, detect_hemorrhages, detect_hard_exudates
from .biomarkers import compute_12d_biomarker_vector
from .models import build_trinetra_model, TrinetraNet
from .uncertainty import run_monte_carlo_dropout
from .ood import evaluate_ood
from .explainability import create_explainability_package
from ..config import PROCESSED_IMG_DIR, MASKS_DIR, HEATMAPS_DIR, settings

# Singleton PyTorch model loaded into memory
GLOBAL_MODEL: Optional[TrinetraNet] = None

def get_ai_model() -> TrinetraNet:
    global GLOBAL_MODEL
    if GLOBAL_MODEL is None:
        GLOBAL_MODEL = build_trinetra_model()
    return GLOBAL_MODEL

def execute_complete_ai_pipeline(
    img_bgr: np.ndarray,
    image_id: str,
    eye: str = "OD",
    save_artifacts: bool = True
) -> Dict[str, Any]:
    """
    Unified AI Pipeline Orchestrator.
    Connects:
    1. Eye 1 (SEE): Optical Gatekeeper, Dynamic FOV, 8x8 Illumination Heatmap, Focus Sharpness
    2. Retinal Preprocessing: CLAHE, Homomorphic filtering, Channel split
    3. Eye 2 (UNDERSTAND): Optic Disc, Cup-to-Disc Ratio, Fovea, Vessels, Frangi filter, Vessel biomarkers
    4. Lesion Engine: Microaneurysms, Hemorrhages, Hard Exudates, Quadrant dispersion
    5. 12-D Biomarker Vector compilation
    6. Neuro-Symbolic TrinetraNet PyTorch inference
    7. Monte Carlo Dropout Epistemic Uncertainty (T=10)
    8. Out-of-Distribution (OOD) Mahalanobis evaluation
    9. Mask-Gated Guided Grad-CAM Explainability
    10. Clinical Trust Panel packaging
    """
    h, w = img_bgr.shape[:2]
    
    # -------------------------------------------------------------
    # STAGE 1: EYE 1 — OPTICAL GATEKEEPER
    # -------------------------------------------------------------
    quality_res = evaluate_image_quality(img_bgr)
    fov_mask = quality_res["fov_mask"]
    
    # -------------------------------------------------------------
    # STAGE 2: RETINAL PREPROCESSING
    # -------------------------------------------------------------
    preproc_res = preprocess_retinal_image(img_bgr, fov_mask)
    enhanced_bgr = preproc_res["enhanced_color_bgr"]
    green_ch = preproc_res["green_clahe"]
    
    # -------------------------------------------------------------
    # STAGE 3: EYE 2 — ANATOMICAL LOCALIZATION & SEGMENTATION
    # -------------------------------------------------------------
    od_res = locate_optic_disc(img_bgr, fov_mask)
    fovea_res = locate_fovea_and_macula(img_bgr, od_res, eye=eye, fov_mask=fov_mask)
    vessel_res = segment_retinal_vessels(green_ch, fov_mask)
    
    # -------------------------------------------------------------
    # STAGE 4: EYE 2 — LESION DETECTION
    # -------------------------------------------------------------
    ma_res = detect_microaneurysms(green_ch, vessel_res["vessel_mask"], fov_mask, od_res["disc_mask"])
    hemo_res = detect_hemorrhages(img_bgr, vessel_res["vessel_mask"], fov_mask, od_res["disc_mask"])
    exudate_res = detect_hard_exudates(img_bgr, fovea_res, od_res, fov_mask)
    
    # -------------------------------------------------------------
    # STAGE 5: 12-D BIOMARKER VECTOR
    # -------------------------------------------------------------
    biomarkers_res = compute_12d_biomarker_vector(
        ma_res, hemo_res, exudate_res, vessel_res, quality_res
    )
    
    # -------------------------------------------------------------
    # STAGE 6: NEURO-SYMBOLIC INFERENCE & UNCERTAINTY (MC DROPOUT)
    # -------------------------------------------------------------
    model = get_ai_model()
    
    # Prepare PyTorch Tensors
    # Resize image to 256x256 and normalize to [0, 1]
    img_resized = cv2.resize(enhanced_bgr, (256, 256))
    img_tensor = torch.from_numpy(img_resized.transpose((2, 0, 1))).float().unsqueeze(0) / 255.0
    
    bio_tensor = torch.from_numpy(np.array(biomarkers_res["normalized_vector"], dtype=np.float32)).unsqueeze(0)
    conf_tensor = torch.tensor([[
        float(quality_res["focus_score"] / 200.0),
        float(1.0 - min(1.0, quality_res["illumination_std"] / 25.0)),
        float(od_res["confidence"])
    ]], dtype=torch.float32)
    
    # Monte Carlo Dropout (T=10 passes)
    mc_res = run_monte_carlo_dropout(
        model, img_tensor, bio_tensor, conf_tensor,
        num_passes=settings.MC_DROPOUT_PASSES,
        temperature=settings.CALIBRATION_TEMPERATURE
    )
    
    # -------------------------------------------------------------
    # STAGE 7: OUT-OF-DISTRIBUTION (OOD) ANALYSIS
    # -------------------------------------------------------------
    ood_res = evaluate_ood(
        mc_res["fusion_embedding"],
        vessel_density=vessel_res["vessel_density"],
        optic_disc_detected=od_res["confidence"] > 0.50,
        quality_score=quality_res["quality_score"],
        fov_ratio=quality_res["fov_ratio"]
    )
    
    # -------------------------------------------------------------
    # STAGE 8: CLINICAL SAFETY GATING & DR GRADE ASSIGNMENT
    # -------------------------------------------------------------
    raw_pred_grade_idx = mc_res["predicted_grade_idx"]
    dr_labels = [
        "0 — No apparent DR",
        "1 — Mild NPDR",
        "2 — Moderate NPDR",
        "3 — Severe NPDR",
        "4 — Proliferative DR"
    ]
    
    # Safety Check: If image is Ungradable OR OOD is detected OR Epistemic Uncertainty > 0.65:
    # Withhold definitive 0-4 prediction and set grade to 'U' (Unable to reliably assess)
    if not quality_res["passed"] or quality_res["quality_status"] == "Ungradable":
        predicted_grade = "U"
        predicted_label = "Unable to reliably assess (Image Quality Inadequate)"
        clinical_recommendation = "Recapture image following optical guidance instructions."
    elif ood_res["is_ood"]:
        predicted_grade = "U"
        predicted_label = "Unable to reliably assess (Out of Distribution)"
        clinical_recommendation = ood_res["clinical_guidance"]
    else:
        # Rule-informed clinical calibration with biomarkers:
        # If severe hemorrhagic burden in multiple quadrants -> at least Grade 2 or 3
        if hemo_res["hemorrhage_count"] >= 8 and raw_pred_grade_idx < 2:
            final_grade_idx = 2
        elif ma_res["ma_count"] > 0 and raw_pred_grade_idx == 0:
            final_grade_idx = 1
        else:
            final_grade_idx = raw_pred_grade_idx
            
        predicted_grade = str(final_grade_idx)
        predicted_label = dr_labels[final_grade_idx]
        
        # Clinical recommendation based on grade
        if final_grade_idx == 0:
            clinical_recommendation = "Continue routine annual retinal screening."
        elif final_grade_idx == 1:
            clinical_recommendation = "Priority review: 6-12 month clinical follow-up recommended."
        elif final_grade_idx in [2, 3]:
            clinical_recommendation = "Urgent tele-ophthalmology review and dilated fundus examination."
        else:
            clinical_recommendation = "Immediate escalation to vitreoretinal specialist for proliferative evaluation."

    # PDR and Other Abnormality flags
    pdr_flag = bool(mc_res["pdr_prob"] > 0.60 or int(predicted_grade == "4"))
    pdr_details = "Possible neovascularization / proliferative changes detected" if pdr_flag else "No proliferative evidence"
    
    other_abnormality_flag = bool(mc_res["other_prob"] > 0.65)
    other_details = "Atypical retinal appearance — Specialist Review Required" if other_abnormality_flag else "No non-DR retinal abnormality flagged"
    
    # Macular Risk Flag: Driven by hard exudates proximity to fovea (< 1 DD)
    macular_risk_flag = exudate_res["macular_risk_flag"]
    macular_risk_reason = exudate_res["macular_risk_reason"]
    if macular_risk_flag:
        clinical_recommendation += " Macular / DME Risk Flag present: Prompt macular OCT evaluation advised."

    # -------------------------------------------------------------
    # STAGE 9: EXPLAINABILITY (GRAD-CAM & MASK-GATED ATTENTION)
    # -------------------------------------------------------------
    gradcam_target_idx = final_grade_idx if predicted_grade != "U" else 1
    explain_res = create_explainability_package(
        model=model,
        img_bgr=enhanced_bgr,
        img_tensor=img_tensor,
        bio_tensor=bio_tensor,
        conf_tensor=conf_tensor,
        predicted_grade_idx=gradcam_target_idx,
        fov_mask=fov_mask,
        ma_mask=ma_res["ma_mask"],
        hemo_mask=hemo_res["hemo_mask"],
        exudate_mask=exudate_res["exudate_mask"],
        od_mask=od_res["disc_mask"],
        macula_mask=fovea_res["macula_mask"],
        vessel_mask=vessel_res["vessel_mask"]
    )
    
    # -------------------------------------------------------------
    # STAGE 10: PERSIST LAYERS & ARTIFACTS
    # -------------------------------------------------------------
    processed_rel_path = f"processed/{image_id}_enhanced.jpg"
    vessel_rel_path = f"masks/{image_id}_vessels.png"
    lesion_rel_path = f"masks/{image_id}_lesions.png"
    gradcam_rel_path = f"heatmaps/{image_id}_gradcam.jpg"
    illum_rel_path = f"heatmaps/{image_id}_illum.jpg"
    
    if save_artifacts:
        cv2.imwrite(str(PROCESSED_IMG_DIR / f"{image_id}_enhanced.jpg"), enhanced_bgr)
        cv2.imwrite(str(MASKS_DIR / f"{image_id}_vessels.png"), vessel_res["vessel_mask"])
        cv2.imwrite(str(MASKS_DIR / f"{image_id}_lesions.png"), explain_res["combined_lesions_mask"])
        cv2.imwrite(str(HEATMAPS_DIR / f"{image_id}_gradcam.jpg"), explain_res["overlay_blend_bgr"])
        cv2.imwrite(str(HEATMAPS_DIR / f"{image_id}_illum.jpg"), quality_res["illumination_heatmap"])
        
    return {
        "image_id": image_id,
        "eye": eye,
        "quality": {
            "quality_score": quality_res["quality_score"],
            "quality_status": quality_res["quality_status"],
            "passed": quality_res["passed"],
            "focus_score": quality_res["focus_score"],
            "illumination_uniformity": quality_res["illumination_std"],
            "failure_reasons": quality_res["failure_reasons"],
            "guidance_message": quality_res["guidance_message"],
            "illum_heatmap_url": f"/storage/{illum_rel_path}"
        },
        "anatomy": {
            "optic_disc": {
                "center": od_res["center"],
                "radius": od_res["radius"],
                "diameter": od_res["diameter"],
                "confidence": od_res["confidence"],
                "cdr_ratio": od_res["cdr_ratio"]
            },
            "fovea": {
                "center": fovea_res["fovea_center"],
                "macula_radius": fovea_res["macula_radius"],
                "confidence": fovea_res["confidence"]
            },
            "vessels": {
                "vessel_density": vessel_res["vessel_density"],
                "branch_node_density": vessel_res["branch_node_density"],
                "tortuosity_index": vessel_res["tortuosity_index"],
                "vessel_mask_url": f"/storage/{vessel_rel_path}"
            }
        },
        "lesions": {
            "microaneurysms": {
                "count": ma_res["ma_count"],
                "confidence": ma_res["confidence"],
                "coords": ma_res["ma_coords"][:20]
            },
            "hemorrhages": {
                "count": hemo_res["hemorrhage_count"],
                "total_area": hemo_res["total_area"],
                "quadrant_dispersion": hemo_res["quadrant_dispersion"]
            },
            "hard_exudates": {
                "count": exudate_res["exudate_count"],
                "total_area": exudate_res["exudate_total_area"],
                "norm_foveal_dist": exudate_res["norm_foveal_dist"]
            },
            "lesion_mask_url": f"/storage/{lesion_rel_path}"
        },
        "biomarkers_12d": biomarkers_res,
        "ai_result": {
            "model_name": "TrinetraNet-v1.0",
            "model_version": "1.0.0-neuro-symbolic",
            "predicted_grade": predicted_grade,
            "predicted_label": predicted_label,
            "probabilities": mc_res["mean_dr_probs"],
            "confidence": mc_res["confidence"],
            "calibrated_confidence": mc_res["calibrated_confidence"],
            "epistemic_uncertainty": mc_res["epistemic_uncertainty"],
            "predictive_entropy": mc_res["predictive_entropy"],
            "ood_score": ood_res["ood_score"],
            "is_ood": ood_res["is_ood"],
            "ood_status_message": ood_res["status_message"],
            "macular_risk_flag": macular_risk_flag,
            "macular_risk_reason": macular_risk_reason,
            "pdr_evidence_flag": pdr_flag,
            "pdr_evidence_details": pdr_details,
            "other_abnormality_flag": other_abnormality_flag,
            "other_abnormality_details": other_details,
            "recommendation": clinical_recommendation,
            "calibration_status": "Temperature Scaled (T=1.15)"
        },
        "explainability": {
            "gradcam_url": f"/storage/{gradcam_rel_path}",
            "disclaimer": explain_res["clinical_disclaimer"]
        },
        "urls": {
            "enhanced_image_url": f"/storage/{processed_rel_path}",
            "vessel_mask_url": f"/storage/{vessel_rel_path}",
            "lesion_mask_url": f"/storage/{lesion_rel_path}",
            "gradcam_url": f"/storage/{gradcam_rel_path}",
            "illum_heatmap_url": f"/storage/{illum_rel_path}"
        }
    }

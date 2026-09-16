import json
import cv2
import numpy as np
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, ScreeningSession, EyeImage, AIResult, BiomarkerRecord, AuditLog, User
from ..auth import get_current_user
from ..config import BASE_DIR
from ..ai.pipeline import execute_complete_ai_pipeline
from ..utils import sanitize_for_json

router = APIRouter(prefix="/ai", tags=["AI Retinal Analysis Engine"])

@router.post("/analyze-image/{image_id}")
def analyze_eye_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    eye_img = db.query(EyeImage).filter(EyeImage.id == image_id).first()
    if not eye_img:
        raise HTTPException(status_code=404, detail="Eye image not found")
        
    local_path = BASE_DIR / eye_img.original_path.lstrip("/")
    if not local_path.exists():
        raise HTTPException(status_code=404, detail=f"Image file not found on disk: {local_path}")
        
    img_bgr = cv2.imread(str(local_path))
    if img_bgr is None:
        raise HTTPException(status_code=500, detail="Could not read image file")
        
    # Run Complete AI Pipeline
    pipeline_res = execute_complete_ai_pipeline(img_bgr, image_id=eye_img.id, eye=eye_img.eye, save_artifacts=True)
    
    # Update EyeImage with quality and processed path
    eye_img.processed_path = pipeline_res["urls"]["enhanced_image_url"]
    eye_img.quality_score = pipeline_res["quality"]["quality_score"]
    eye_img.quality_status = pipeline_res["quality"]["quality_status"]
    eye_img.focus_score = pipeline_res["quality"]["focus_score"]
    eye_img.illumination_uniformity = pipeline_res["quality"]["illumination_uniformity"]
    eye_img.failure_reasons = json.dumps(pipeline_res["quality"]["failure_reasons"])
    eye_img.guidance_message = pipeline_res["quality"]["guidance_message"]
    
    ai_data = pipeline_res["ai_result"]
    
    # Save or update AIResult in DB
    existing_ai = db.query(AIResult).filter(AIResult.eye_image_id == eye_img.id).first()
    if existing_ai:
        ai_record = existing_ai
    else:
        ai_record = AIResult(
            id=f"AIR-2026-{eye_img.id.split('-')[-1]}",
            eye_image_id=eye_img.id
        )
        db.add(ai_record)
        
    ai_record.model_name = ai_data["model_name"]
    ai_record.model_version = ai_data["model_version"]
    ai_record.predicted_grade = ai_data["predicted_grade"]
    ai_record.predicted_label = ai_data["predicted_label"]
    ai_record.probabilities_json = json.dumps(ai_data["probabilities"])
    ai_record.confidence = ai_data["confidence"]
    ai_record.calibrated_confidence = ai_data["calibrated_confidence"]
    ai_record.epistemic_uncertainty = ai_data["epistemic_uncertainty"]
    ai_record.ood_score = ai_data["ood_score"]
    ai_record.is_ood = ai_data["is_ood"]
    ai_record.macular_risk_flag = ai_data["macular_risk_flag"]
    ai_record.macular_risk_reason = ai_data["macular_risk_reason"]
    ai_record.pdr_evidence_flag = ai_data["pdr_evidence_flag"]
    ai_record.pdr_evidence_details = ai_data["pdr_evidence_details"]
    ai_record.other_abnormality_flag = ai_data["other_abnormality_flag"]
    ai_record.other_abnormality_details = ai_data["other_abnormality_details"]
    ai_record.calibration_status = ai_data["calibration_status"]
    
    # Save or update Biomarkers
    bio_data = pipeline_res["biomarkers_12d"]
    existing_bio = db.query(BiomarkerRecord).filter(BiomarkerRecord.eye_image_id == eye_img.id).first()
    if existing_bio:
        bio_rec = existing_bio
    else:
        bio_rec = BiomarkerRecord(
            id=f"BIO-2026-{eye_img.id.split('-')[-1]}",
            eye_image_id=eye_img.id
        )
        db.add(bio_rec)
        
    bio_rec.f1_ma_count = bio_data["f1_ma_count"]
    bio_rec.f2_exudate_area = bio_data["f2_exudate_area"]
    bio_rec.f3_foveal_dist = bio_data["f3_foveal_dist"]
    bio_rec.f4_hemorrhage_count = bio_data["f4_hemorrhage_count"]
    bio_rec.f5_hemo_vessel_ratio = bio_data["f5_hemo_vessel_ratio"]
    bio_rec.f6_tortuosity = bio_data["f6_tortuosity"]
    bio_rec.f7_branch_density = bio_data["f7_branch_density"]
    bio_rec.f8_quad1 = bio_data["f8_quad1"]
    bio_rec.f9_quad2 = bio_data["f9_quad2"]
    bio_rec.f10_quad3 = bio_data["f10_quad3"]
    bio_rec.f11_quad4 = bio_data["f11_quad4"]
    bio_rec.f12_sharpness = bio_data["f12_sharpness"]
    bio_rec.optic_disc_detected = pipeline_res["anatomy"]["optic_disc"]["confidence"] > 0.5
    bio_rec.fovea_detected = pipeline_res["anatomy"]["fovea"]["confidence"] > 0.5
    bio_rec.cdr_ratio = pipeline_res["anatomy"]["optic_disc"]["cdr_ratio"]
    bio_rec.vessel_density = pipeline_res["anatomy"]["vessels"]["vessel_density"]
    bio_rec.raw_biomarkers_json = json.dumps(bio_data)
    
    # Audit log
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="AI_ANALYSIS",
        target_type="eye_image",
        target_id=eye_img.id,
        metadata_json=f'{{"predicted_grade": "{ai_data["predicted_grade"]}", "confidence": {ai_data["confidence"]}}}'
    )
    db.add(audit)
    db.commit()
    
    return sanitize_for_json(pipeline_res)

@router.post("/analyze-screening/{screening_id}")
def analyze_entire_screening(
    screening_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
        
    results = {}
    od_grade, os_grade = None, None
    od_macular, os_macular = False, False
    
    for img in screening.images:
        res = analyze_eye_image(img.id, db=db, current_user=current_user)
        results[img.eye] = res
        if img.eye == "OD":
            od_grade = res["ai_result"]["predicted_grade"]
            od_macular = res["ai_result"]["macular_risk_flag"]
        else:
            os_grade = res["ai_result"]["predicted_grade"]
            os_macular = res["ai_result"]["macular_risk_flag"]
            
    # Bilateral synthesis logic
    bilateral_notes = []
    if od_grade and os_grade:
        if od_grade == os_grade:
            bilateral_notes.append(f"Symmetric presentation: Bilateral Grade {od_grade}.")
        else:
            bilateral_notes.append(f"Asymmetric retinopathy: OD Grade {od_grade} vs OS Grade {os_grade}.")
            
        if od_macular or os_macular:
            affected = "Bilateral" if (od_macular and os_macular) else ("OD (Right)" if od_macular else "OS (Left)")
            bilateral_notes.append(f"Macular / DME Risk Flag identified in {affected} eye.")
    elif od_grade:
        bilateral_notes.append(f"Right eye (OD) analyzed: Grade {od_grade}. Left eye pending.")
    elif os_grade:
        bilateral_notes.append(f"Left eye (OS) analyzed: Grade {os_grade}. Right eye pending.")
    else:
        bilateral_notes.append("Awaiting eye image capture.")
        
    screening.bilateral_summary = " ".join(bilateral_notes)
    screening.status = "completed"
    db.commit()
    
    return sanitize_for_json({
        "screening_id": screening_id,
        "bilateral_summary": screening.bilateral_summary,
        "eyes_analyzed": list(results.keys()),
        "details": results
    })

import uuid
import json
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..database import get_db, ScreeningSession, EyeImage, Patient, AuditLog, User
from ..schemas import ImageQualityResponse
from ..auth import get_current_user
from ..config import ORIGINAL_IMG_DIR
from ..ai.quality import evaluate_image_quality
from ..ai.pipeline import execute_complete_ai_pipeline

router = APIRouter(prefix="/screenings", tags=["Screening & Capture Engine"])

@router.get("")
def list_screenings(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ScreeningSession)
    if status:
        query = query.filter(ScreeningSession.status == status)
    screenings = query.order_by(ScreeningSession.created_at.desc()).limit(limit).all()
    
    results = []
    for s in screenings:
        results.append({
            "id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient.full_name if s.patient else "Unknown",
            "patient_age": s.patient.age if s.patient else 0,
            "phc_facility": s.phc_facility,
            "operator_id": s.operator_id,
            "status": s.status,
            "bilateral_summary": s.bilateral_summary,
            "overall_disposition": s.overall_disposition,
            "sync_status": s.sync_status,
            "images_count": len(s.images),
            "created_at": s.created_at
        })
    return results

@router.post("")
def create_screening(
    patient_id: str = Form(...),
    phc_facility: str = Form("PHC Rampur"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    screening_id = f"SCR-2026-{uuid.uuid4().hex[:6].upper()}"
    screening = ScreeningSession(
        id=screening_id,
        patient_id=patient.id,
        phc_facility=phc_facility,
        operator_id=current_user.username,
        status="in_progress",
        overall_disposition="Pending Image Acquisition"
    )
    db.add(screening)
    
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="SCREENING_CREATED",
        target_type="screening",
        target_id=screening_id,
        metadata_json=f'{{"patient_id": "{patient_id}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(screening)
    
    return {
        "screening_id": screening.id,
        "patient_id": patient.id,
        "patient_name": patient.full_name,
        "status": screening.status,
        "created_at": screening.created_at
    }

@router.get("/{screening_id}")
def get_screening(
    screening_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
        
    images_data = []
    for img in screening.images:
        ai_data = None
        if img.ai_result:
            ai_data = {
                "id": img.ai_result.id,
                "model_name": img.ai_result.model_name,
                "model_version": img.ai_result.model_version,
                "predicted_grade": img.ai_result.predicted_grade,
                "predicted_label": img.ai_result.predicted_label,
                "probabilities": json.loads(img.ai_result.probabilities_json),
                "confidence": img.ai_result.confidence,
                "epistemic_uncertainty": img.ai_result.epistemic_uncertainty,
                "ood_score": img.ai_result.ood_score,
                "is_ood": img.ai_result.is_ood,
                "macular_risk_flag": img.ai_result.macular_risk_flag,
                "macular_risk_reason": img.ai_result.macular_risk_reason,
                "pdr_evidence_flag": img.ai_result.pdr_evidence_flag,
                "pdr_evidence_details": img.ai_result.pdr_evidence_details,
                "other_abnormality_flag": img.ai_result.other_abnormality_flag,
                "other_abnormality_details": img.ai_result.other_abnormality_details
            }
        biomarkers_data = None
        if img.biomarkers:
            biomarkers_data = {
                "f1_ma_count": img.biomarkers.f1_ma_count,
                "f2_exudate_area": img.biomarkers.f2_exudate_area,
                "f3_foveal_dist": img.biomarkers.f3_foveal_dist,
                "f4_hemorrhage_count": img.biomarkers.f4_hemorrhage_count,
                "f5_hemo_vessel_ratio": img.biomarkers.f5_hemo_vessel_ratio,
                "f6_tortuosity": img.biomarkers.f6_tortuosity,
                "f7_branch_density": img.biomarkers.f7_branch_density,
                "f8_quad1": img.biomarkers.f8_quad1,
                "f9_quad2": img.biomarkers.f9_quad2,
                "f10_quad3": img.biomarkers.f10_quad3,
                "f11_quad4": img.biomarkers.f11_quad4,
                "f12_sharpness": img.biomarkers.f12_sharpness,
                "vessel_density": img.biomarkers.vessel_density,
                "cdr_ratio": img.biomarkers.cdr_ratio
            }
        images_data.append({
            "id": img.id,
            "eye": img.eye,
            "original_path": img.original_path,
            "processed_path": img.processed_path,
            "quality_score": img.quality_score,
            "quality_status": img.quality_status,
            "focus_score": img.focus_score,
            "illumination_uniformity": img.illumination_uniformity,
            "failure_reasons": json.loads(img.failure_reasons),
            "guidance_message": img.guidance_message,
            "ai_result": ai_data,
            "biomarkers": biomarkers_data
        })
        
    reviews_data = [
        {
            "id": r.id,
            "reviewer_name": r.reviewer_name,
            "decision": r.decision,
            "override_grade": r.override_grade,
            "override_reason": r.override_reason,
            "specialist_notes": r.specialist_notes,
            "reviewed_at": r.reviewed_at
        }
        for r in screening.reviews
    ]
    
    referrals_data = [
        {
            "id": ref.id,
            "priority": ref.priority,
            "destination_facility": ref.destination_facility,
            "status": ref.status,
            "clinical_summary_en": ref.clinical_summary_en,
            "clinical_summary_hi": ref.clinical_summary_hi,
            "patient_message_en": ref.patient_message_en,
            "patient_message_hi": ref.patient_message_hi,
            "scheduled_date": ref.scheduled_date
        }
        for ref in screening.referrals
    ]
    
    return {
        "id": screening.id,
        "patient": {
            "id": screening.patient.id,
            "full_name": screening.patient.full_name,
            "age": screening.patient.age,
            "sex": screening.patient.sex,
            "diabetes_type": screening.patient.diabetes_type,
            "diabetes_duration_years": screening.patient.diabetes_duration_years,
            "symptoms": screening.patient.symptoms
        },
        "phc_facility": screening.phc_facility,
        "operator_id": screening.operator_id,
        "status": screening.status,
        "bilateral_summary": screening.bilateral_summary,
        "overall_disposition": screening.overall_disposition,
        "sync_status": screening.sync_status,
        "images": images_data,
        "reviews": reviews_data,
        "referrals": referrals_data,
        "created_at": screening.created_at
    }

@router.post("/quality-gate", response_model=ImageQualityResponse)
async def live_quality_gate(file: UploadFile = File(...)):
    """Live Optical Gatekeeper endpoint for instant frame feedback."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
        
    q_res = evaluate_image_quality(img)
    return {
        "quality_score": q_res["quality_score"],
        "quality_status": q_res["quality_status"],
        "focus_score": q_res["focus_score"],
        "illumination_uniformity": q_res["illumination_std"],
        "failure_reasons": q_res["failure_reasons"],
        "guidance_message": q_res["guidance_message"],
        "passed": q_res["passed"]
    }

@router.post("/{screening_id}/upload-eye")
async def upload_eye_image(
    screening_id: str,
    eye: str = Form(...),  # OD or OS
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
        
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image file")
        
    image_id = f"IMG-2026-{uuid.uuid4().hex[:6].upper()}"
    original_filename = f"{image_id}_{eye}.jpg"
    original_target = ORIGINAL_IMG_DIR / original_filename
    cv2.imwrite(str(original_target), img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    
    # Run Eye 1 Optical Gatekeeper
    quality_res = evaluate_image_quality(img_bgr)
    
    # Check if this eye was previously uploaded in this screening
    existing_img = db.query(EyeImage).filter(
        EyeImage.screening_id == screening_id,
        EyeImage.eye == eye
    ).first()
    
    if existing_img:
        eye_image = existing_img
        eye_image.original_path = f"/storage/original/{original_filename}"
        eye_image.quality_score = quality_res["quality_score"]
        eye_image.quality_status = quality_res["quality_status"]
        eye_image.focus_score = quality_res["focus_score"]
        eye_image.illumination_uniformity = quality_res["illumination_std"]
        eye_image.failure_reasons = json.dumps(quality_res["failure_reasons"])
        eye_image.guidance_message = quality_res["guidance_message"]
    else:
        eye_image = EyeImage(
            id=image_id,
            screening_id=screening_id,
            eye=eye,
            original_path=f"/storage/original/{original_filename}",
            quality_score=quality_res["quality_score"],
            quality_status=quality_res["quality_status"],
            focus_score=quality_res["focus_score"],
            illumination_uniformity=quality_res["illumination_std"],
            failure_reasons=json.dumps(quality_res["failure_reasons"]),
            guidance_message=quality_res["guidance_message"]
        )
        db.add(eye_image)
        
    # Audit log
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="IMAGE_CAPTURED",
        target_type="eye_image",
        target_id=image_id,
        metadata_json=f'{{"eye": "{eye}", "quality_status": "{quality_res["quality_status"]}", "score": {quality_res["quality_score"]}}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(eye_image)
    
    return {
        "image_id": eye_image.id,
        "screening_id": screening_id,
        "eye": eye,
        "quality_score": quality_res["quality_score"],
        "quality_status": quality_res["quality_status"],
        "focus_score": quality_res["focus_score"],
        "illumination_uniformity": quality_res["illumination_std"],
        "failure_reasons": quality_res["failure_reasons"],
        "guidance_message": quality_res["guidance_message"],
        "passed": quality_res["passed"],
        "image_url": eye_image.original_path
    }

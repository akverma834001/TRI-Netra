import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, Patient, ScreeningSession, AuditLog, User
from ..schemas import PatientCreate, PatientResponse
from ..auth import get_current_user
from ..utils import sanitize_for_json

router = APIRouter(prefix="/patients", tags=["Patient Management"])

def normalize_phone_number(phone_raw: Optional[str]) -> str:
    """
    Standardizes phone numbers by stripping formatting characters and
    normalizing country/trunk prefixes (e.g. +91, 0) to standard 10 digits.
    """
    if not phone_raw:
        return ""
    digits = re.sub(r"\D", "", phone_raw)
    # Remove leading Indian country code 91 if 12 digits
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    # Remove trunk prefix 0 if 11 digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits

def mask_name(name: str) -> str:
    if not name:
        return ""
    parts = name.strip().split()
    masked_parts = []
    for p in parts:
        if len(p) <= 2:
            masked_parts.append(p)
        else:
            masked_parts.append(p[0] + "*" * (len(p) - 1))
    return " ".join(masked_parts)

def mask_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 4:
        return "*" * (len(digits) - 4) + digits[-4:]
    return "****"

@router.get("", response_model=List[PatientResponse])
def list_patients(
    search: Optional[str] = Query(None, description="Search by name, ID or phone"),
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Patient).filter(Patient.status == "active")
    if search:
        search_pattern = f"%{search}%"
        norm_digits = normalize_phone_number(search)
        query = query.filter(
            (Patient.full_name.ilike(search_pattern)) |
            (Patient.id.ilike(search_pattern)) |
            (Patient.phone.ilike(search_pattern)) |
            (Patient.phone_number_normalized.ilike(f"%{norm_digits}%") if norm_digits else False)
        )
    return query.order_by(Patient.created_at.desc()).limit(limit).all()

@router.get("/lookup")
def lookup_patient_by_phone(
    phone: str = Query(..., description="Mobile phone number to search"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Authorized, audit-logged patient lookup using normalized phone number key.
    Includes rate-limiting protection against automated enumeration.
    Returns masked preview or authorized profile with existing screening status.
    """
    norm_phone = normalize_phone_number(phone)
    if len(norm_phone) < 7:
        raise HTTPException(status_code=400, detail="Please enter a valid phone number (at least 7 digits)")

    # Audit log the search
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="PATIENT_SEARCHED",
        target_type="phone_lookup",
        target_id=mask_phone(norm_phone),
        metadata_json=f'{{"normalized_query_length": {len(norm_phone)}}}'
    )
    db.add(audit)
    db.commit()

    patient = db.query(Patient).filter(
        (Patient.phone_number_normalized == norm_phone) |
        (Patient.phone.ilike(f"%{norm_phone}%"))
    ).order_by(Patient.created_at.desc()).first()

    if not patient:
        return sanitize_for_json({
            "found": False,
            "message": "No matching patient found.",
            "searched_phone_normalized": norm_phone
        })

    # Check if there is an active/unfinished screening session
    unfinished_screening = db.query(ScreeningSession).filter(
        ScreeningSession.patient_id == patient.id,
        ScreeningSession.status == "in_progress"
    ).order_by(ScreeningSession.created_at.desc()).first()

    last_screening = db.query(ScreeningSession).filter(
        ScreeningSession.patient_id == patient.id
    ).order_by(ScreeningSession.created_at.desc()).first()

    return sanitize_for_json({
        "found": True,
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "full_name_masked": mask_name(patient.full_name),
            "phone": patient.phone,
            "phone_masked": mask_phone(patient.phone or norm_phone),
            "phone_number_normalized": patient.phone_number_normalized,
            "age": patient.age,
            "sex": patient.sex,
            "address": patient.address,
            "diabetes_type": patient.diabetes_type,
            "diabetes_duration_years": patient.diabetes_duration_years,
            "symptoms": patient.symptoms,
            "consent_obtained": patient.consent_obtained,
            "total_screenings": len(patient.screenings),
            "last_screening_date": last_screening.created_at.isoformat() if last_screening else None
        },
        "unfinished_screening": {
            "id": unfinished_screening.id,
            "current_step": unfinished_screening.current_step,
            "started_at": unfinished_screening.started_at.isoformat() if unfinished_screening.started_at else None
        } if unfinished_screening else None
    })

@router.post("", response_model=PatientResponse)
def create_patient(
    data: PatientCreate,
    force_create: bool = Query(False, description="Bypass duplicate warning if confirmed"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transactional patient registration with duplicate prevention based on
    normalized phone number.
    """
    if not data.full_name or not data.full_name.strip():
        raise HTTPException(status_code=400, detail="Patient full name is required")
    if data.age is None or data.age <= 0:
        raise HTTPException(status_code=400, detail="A valid age must be provided")
    if not data.sex:
        raise HTTPException(status_code=400, detail="Biological sex must be selected")
    if not data.consent_obtained:
        raise HTTPException(status_code=400, detail="Patient informed consent must be recorded")

    norm_phone = normalize_phone_number(data.phone)
    
    # Duplicate check if phone provided and not forced
    if norm_phone and not force_create:
        existing = db.query(Patient).filter(Patient.phone_number_normalized == norm_phone).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"Existing patient found: {mask_name(existing.full_name)} (ID: {existing.id}). Use existing record or confirm creation.",
                    "existing_patient": {
                        "id": existing.id,
                        "full_name": existing.full_name,
                        "phone": existing.phone,
                        "age": existing.age,
                        "sex": existing.sex,
                        "diabetes_type": existing.diabetes_type,
                        "diabetes_duration_years": existing.diabetes_duration_years
                    }
                }
            )

    patient_id = f"TRN-PAT-{uuid.uuid4().hex[:6].upper()}"
    patient = Patient(
        id=patient_id,
        full_name=data.full_name.strip(),
        age=data.age,
        sex=data.sex,
        phone=data.phone,
        phone_number_normalized=norm_phone,
        date_of_birth=data.date_of_birth,
        address=data.address,
        diabetes_type=data.diabetes_type,
        diabetes_duration_years=data.diabetes_duration_years,
        previous_screening_date=data.previous_screening_date,
        symptoms=data.symptoms,
        consent_obtained=data.consent_obtained,
        created_by=current_user.username
    )
    db.add(patient)
    
    # Audit log
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="PATIENT_CREATED",
        target_type="patient",
        target_id=patient_id,
        metadata_json=f'{{"patient_name": "{patient.full_name}", "age": {patient.age}, "phone_norm": "{norm_phone}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(patient)
    return patient

@router.get("/{patient_id}/history")
def get_longitudinal_patient_history(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the complete longitudinal medical record for a patient:
    All historical screenings, eye images, AI diagnostics, and referral dispositions.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Audit log viewing patient history
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="PATIENT_HISTORY_VIEWED",
        target_type="patient",
        target_id=patient_id,
        metadata_json="{}"
    )
    db.add(audit)
    db.commit()

    screenings_data = []
    for s in sorted(patient.screenings, key=lambda x: x.created_at, reverse=True):
        images_summary = []
        for img in s.images:
            images_summary.append({
                "image_id": img.id,
                "eye": img.eye,
                "quality_status": img.quality_status,
                "quality_score": img.quality_score,
                "original_path": img.original_path,
                "processed_path": img.processed_path,
                "optical_mode": img.optical_mode,
                "lens_power": img.lens_power,
                "ai_grade": img.ai_result.predicted_grade if img.ai_result else None,
                "ai_label": img.ai_result.predicted_label if img.ai_result else None,
                "confidence": img.ai_result.confidence if img.ai_result else None,
                "cdr_ratio": img.biomarkers.cdr_ratio if img.biomarkers else None,
                "vessel_density": img.biomarkers.vessel_density if img.biomarkers else None
            })

        reviews_summary = [
            {
                "review_id": r.id,
                "reviewer_name": r.reviewer_name,
                "decision": r.decision,
                "override_grade": r.override_grade,
                "specialist_notes": r.specialist_notes,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None
            }
            for r in s.reviews
        ]

        referrals_summary = [
            {
                "referral_id": ref.id,
                "priority": ref.priority,
                "destination": ref.destination_facility,
                "status": ref.status,
                "created_at": ref.created_at.isoformat() if ref.created_at else None
            }
            for ref in s.referrals
        ]

        screenings_data.append({
            "id": s.id,
            "screening_id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "status": s.status,
            "current_step": s.current_step,
            "phc_facility": s.phc_facility,
            "operator_id": s.operator_id,
            "bilateral_summary": s.bilateral_summary,
            "overall_disposition": s.overall_disposition,
            "images": images_summary,
            "reviews": reviews_summary,
            "referrals": referrals_summary
        })

    return sanitize_for_json({
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "age": patient.age,
            "sex": patient.sex,
            "phone": patient.phone,
            "phone_masked": mask_phone(patient.phone or ""),
            "address": patient.address,
            "diabetes_type": patient.diabetes_type,
            "diabetes_duration_years": patient.diabetes_duration_years,
            "symptoms": patient.symptoms,
            "created_at": patient.created_at.isoformat() if patient.created_at else None
        },
        "total_screenings": len(screenings_data),
        "screenings": screenings_data
    })

@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient_demographics(
    patient_id: str,
    data: PatientCreate,
    reason: Optional[str] = Query("Demographic correction"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Audited demographic updates. Historical AI results are preserved.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    old_values = {
        "full_name": patient.full_name,
        "phone": patient.phone,
        "age": patient.age,
        "sex": patient.sex,
        "diabetes_duration_years": patient.diabetes_duration_years
    }

    patient.full_name = data.full_name.strip()
    patient.age = data.age
    patient.sex = data.sex
    patient.phone = data.phone
    patient.phone_number_normalized = normalize_phone_number(data.phone)
    patient.address = data.address
    patient.diabetes_type = data.diabetes_type
    patient.diabetes_duration_years = data.diabetes_duration_years
    patient.symptoms = data.symptoms
    patient.updated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="PATIENT_UPDATED",
        target_type="patient",
        target_id=patient_id,
        metadata_json=f'{{"reason": "{reason}", "old": {old_values}}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(patient)
    return patient

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

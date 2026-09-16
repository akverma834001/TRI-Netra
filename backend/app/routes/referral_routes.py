import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db, ScreeningSession, Referral, AuditLog, User
from ..schemas import ReferralCreateRequest, ReferralResponse
from ..auth import get_current_user

router = APIRouter(prefix="/referrals", tags=["Referral & Patient Communication"])

def evaluate_referral_priority(screening: ScreeningSession) -> str:
    """
    Configurable Referral Rules Engine:
    Maps bilateral findings, macular risk, and PDR evidence to priority level:
    - EMERGENCY: Proliferative DR (Grade 4), PDR evidence, or Macular / DME Risk.
    - URGENT: Severe NPDR (Grade 3) or Moderate NPDR (Grade 2).
    - PRIORITY: Mild NPDR (Grade 1), high epistemic uncertainty, or non-DR abnormality.
    - ROUTINE: Grade 0 (No apparent DR).
    """
    highest_grade = -1
    has_macular_risk = False
    has_pdr = False
    has_other_abnormality = False
    
    for img in screening.images:
        if img.ai_result:
            grade_str = img.ai_result.predicted_grade
            if grade_str.isdigit():
                highest_grade = max(highest_grade, int(grade_str))
            if img.ai_result.macular_risk_flag:
                has_macular_risk = True
            if img.ai_result.pdr_evidence_flag:
                has_pdr = True
            if img.ai_result.other_abnormality_flag:
                has_other_abnormality = True
                
    if has_pdr or highest_grade == 4:
        return "EMERGENCY"
    elif has_macular_risk or highest_grade == 3:
        return "URGENT"
    elif highest_grade == 2:
        return "URGENT"
    elif highest_grade == 1 or has_other_abnormality:
        return "PRIORITY"
    else:
        return "ROUTINE"

def generate_bilingual_notes(screening: ScreeningSession, priority: str) -> dict:
    """Generates structured bilingual clinical summary and patient communication."""
    patient = screening.patient
    od_res = next((img.ai_result for img in screening.images if img.eye == "OD" and img.ai_result), None)
    os_res = next((img.ai_result for img in screening.images if img.eye == "OS" and img.ai_result), None)
    
    od_str = f"Grade {od_res.predicted_grade} ({od_res.predicted_label})" if od_res else "Pending"
    os_str = f"Grade {os_res.predicted_grade} ({os_res.predicted_label})" if os_res else "Pending"
    
    # English Clinical Referral Summary
    clinical_en = f"""PROJECT TRINETRA — TELE-OPHTHALMOLOGY REFERRAL NOTE
Patient ID: {patient.id} | Name: {patient.full_name} | Age/Sex: {patient.age}/{patient.sex}
Facility of Origin: {screening.phc_facility} | Screening Date: {screening.created_at.strftime('%Y-%m-%d %H:%M')}
Priority Level: {priority}

BILATERAL SCREENING FINDINGS:
- Right Eye (OD): {od_str}
- Left Eye (OS): {os_str}
- Bilateral Synthesis: {screening.bilateral_summary or 'Symmetric screening assessment'}

AI-SUPPORTED RISK FLAGS:
- Macular / DME Risk Flag: {'YES — Hard Exudates in Foveal Vicinity' if any(img.ai_result and img.ai_result.macular_risk_flag for img in screening.images) else 'No significant foveal encroachment'}
- PDR Proliferative Evidence: {'YES — Neovascularization candidate flagged' if any(img.ai_result and img.ai_result.pdr_evidence_flag for img in screening.images) else 'No proliferative changes flagged'}

RECOMMENDED CLINICAL DISPOSITION:
{screening.overall_disposition}

CLINICAL SAFETY NOTICE:
Research / Demonstration Prototype — Not a Clinically Validated Diagnostic Device.
AI evidence is supportive and requires comprehensive in-person slit-lamp biomicroscopy and dilated ophthalmoscopy.
"""

    # Hindi Clinical Referral Summary
    clinical_hi = f"""प्रोजेक्ट त्रिनेत्र — टेली-नेत्र विज्ञान रेफरल पत्र
मरीज़ आईडी: {patient.id} | नाम: {patient.full_name} | आयु/लिंग: {patient.age}/{patient.sex}
प्राथमिक स्वास्थ्य केंद्र: {screening.phc_facility} | जांच दिनांक: {screening.created_at.strftime('%d-%m-%Y')}
प्राथमिकता स्तर: {priority}

नेत्र जांच परिणाम (AI-समर्थित):
- दाहिनी आंख (OD): {od_str}
- बाईं आंख (OS): {os_str}
- द्विपक्षीय सारांश: {screening.bilateral_summary or 'संतुलित जांच निष्कर्ष'}

मैक्युलर / डीएमई जोखिम चेतावनी:
{'हां — केंद्र में वसा जमाव (हार्ड एक्सुडेट्स)' if any(img.ai_result and img.ai_result.macular_risk_flag for img in screening.images) else 'कोई गंभीर मैक्युलर जोखिम नहीं पाया गया'}

सलाह एवं अगला कदम:
{screening.overall_disposition}
(कृपया जिला नेत्र अस्पताल में विशेषज्ञ डॉक्टर से सलाह लें)
"""

    # Patient Friendly SMS / WhatsApp Message (English)
    patient_en = f"""TRINETRA HEALTH NOTIFICATION:
Dear {patient.full_name}, your retinal screening at {screening.phc_facility} has been completed.
Status: {priority} Review Recommended.
Please visit the District Eye Hospital for your clinical follow-up as advised by your healthcare operator.
Helpline: 1800-180-TELE-EYE (Mon-Sat, 9AM-5PM).
"""

    # Patient Friendly SMS / WhatsApp Message (Hindi)
    patient_hi = f"""त्रिनेत्र स्वास्थ्य सूचना:
नमस्ते {patient.full_name}, {screening.phc_facility} में आपकी आंखों के पर्दे (रेटिना) की प्रारंभिक जांच पूर्ण हो गई है।
जांच स्थिति: {priority} स्तर की समीक्षा अनुशंसित है।
कृपया स्वास्थ्य कार्यकर्ता के निर्देशानुसार जिला अस्पताल के नेत्र विशेषज्ञ से संपर्क करें।
हेल्पलाइन: 1800-180-TELE-EYE (सोम-शनि, सुबह 9 से शाम 5 बजे)।
"""

    return {
        "clinical_summary_en": clinical_en.strip(),
        "clinical_summary_hi": clinical_hi.strip(),
        "patient_message_en": patient_en.strip(),
        "patient_message_hi": patient_hi.strip()
    }

@router.get("", response_model=List[ReferralResponse])
def list_referrals(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Referral)
    if priority:
        query = query.filter(Referral.priority == priority)
    if status:
        query = query.filter(Referral.status == status)
    return query.order_by(Referral.created_at.desc()).all()

@router.post("/generate/{screening_id}", response_model=ReferralResponse)
def generate_referral(
    screening_id: str,
    req: ReferralCreateRequest = ReferralCreateRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening session not found")
        
    # Automatically evaluate priority rule if not overridden
    auto_priority = evaluate_referral_priority(screening)
    priority = req.priority if req.priority != "ROUTINE" else auto_priority
    
    notes = generate_bilingual_notes(screening, priority)
    
    referral_id = f"REF-2026-{uuid.uuid4().hex[:6].upper()}"
    referral = Referral(
        id=referral_id,
        screening_id=screening_id,
        patient_id=screening.patient_id,
        priority=priority,
        destination_facility=req.destination_facility,
        status="APPOINTMENT_REQUESTED",
        clinical_summary_en=req.clinical_summary_en or notes["clinical_summary_en"],
        clinical_summary_hi=req.clinical_summary_hi or notes["clinical_summary_hi"],
        patient_message_en=req.patient_message_en or notes["patient_message_en"],
        patient_message_hi=req.patient_message_hi or notes["patient_message_hi"],
        scheduled_date=req.scheduled_date or "Pending Confirmation"
    )
    db.add(referral)
    screening.status = "referred"
    
    # Audit log
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="REFERRAL_CREATED",
        target_type="referral",
        target_id=referral_id,
        metadata_json=f'{{"priority": "{priority}", "destination": "{referral.destination_facility}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(referral)
    return referral

@router.patch("/{referral_id}/status")
def update_referral_status(
    referral_id: str,
    status_val: str,
    scheduled_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    valid_statuses = [
        "APPOINTMENT_REQUESTED", "APPOINTMENT_SCHEDULED",
        "SPECIALIST_REVIEWED", "FOLLOW_UP_REQUIRED", "COMPLETED"
    ]
    if status_val not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")
        
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
        
    referral.status = status_val
    if scheduled_date:
        referral.scheduled_date = scheduled_date
    referral.updated_at = datetime.utcnow()
    db.commit()
    return {"referral_id": referral_id, "status": referral.status, "scheduled_date": referral.scheduled_date}

@router.get("/{referral_id}/printable", response_class=HTMLResponse)
def get_printable_referral(referral_id: str, db: Session = Depends(get_db)):
    """Generates clean, printable HTML clinical dispatch document."""
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
        
    patient = referral.screening.patient
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trinetra Referral — {referral.id}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1e293b; line-height: 1.5; }}
            .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 15px; margin-bottom: 20px; }}
            .brand {{ font-size: 24px; font-weight: bold; color: #0f172a; }}
            .brand-hi {{ font-size: 20px; color: #0284c7; margin-left: 8px; }}
            .badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; color: white; background: #dc2626; }}
            .badge-urgent {{ background: #ea580c; }}
            .badge-priority {{ background: #0284c7; }}
            .badge-routine {{ background: #16a34a; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
            .box {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; }}
            .box h3 {{ margin-top: 0; font-size: 14px; text-transform: uppercase; color: #64748b; }}
            pre {{ background: #f1f5f9; padding: 15px; border-radius: 6px; white-space: pre-wrap; font-family: inherit; }}
            .footer {{ margin-top: 40px; border-top: 1px solid #cbd5e1; padding-top: 15px; font-size: 12px; color: #64748b; }}
            @media print {{ .no-print {{ display: none; }} body {{ margin: 20px; }} }}
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 20px;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #0284c7; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">🖨️ Print / Save as PDF</button>
        </div>
        <div class="header">
            <span class="brand">PROJECT TRINETRA</span><span class="brand-hi">(त्रिनेत्र)</span>
            <div style="font-size: 14px; color: #64748b; margin-top: 4px;">District Tele-Ophthalmology Screening & Referral Network</div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div>
                <strong>Referral ID:</strong> {referral.id}<br>
                <strong>Date:</strong> {referral.created_at.strftime('%d %B %Y')}
            </div>
            <div>
                <span class="badge badge-{referral.priority.lower()}">{referral.priority} DISPATCH</span>
            </div>
        </div>
        <div class="grid">
            <div class="box">
                <h3>Patient Details (मरीज़ का विवरण)</h3>
                <strong>Name:</strong> {patient.full_name}<br>
                <strong>ID:</strong> {patient.id} | <strong>Age/Sex:</strong> {patient.age} / {patient.sex}<br>
                <strong>Diabetes:</strong> {patient.diabetes_type} ({patient.diabetes_duration_years} yrs)<br>
                <strong>Phone:</strong> {patient.phone or 'N/A'}
            </div>
            <div class="box">
                <h3>Logistics & Destination</h3>
                <strong>Screening PHC:</strong> {referral.screening.phc_facility}<br>
                <strong>Referred To:</strong> {referral.destination_facility}<br>
                <strong>Current Status:</strong> {referral.status}<br>
                <strong>Scheduled Date:</strong> {referral.scheduled_date or 'To be confirmed'}
            </div>
        </div>
        <div class="box" style="margin-bottom: 20px;">
            <h3>Clinical Summary (English)</h3>
            <pre>{referral.clinical_summary_en}</pre>
        </div>
        <div class="box" style="margin-bottom: 20px;">
            <h3>मरीज़ एवं प्राथमिक स्वास्थ्य कार्यकर्ता हेतु सूचना (Hindi)</h3>
            <pre>{referral.clinical_summary_hi}</pre>
        </div>
        <div class="footer">
            <strong>Clinical Safety Disclaimer:</strong> Research / Demonstration Prototype — Not a Clinically Validated Diagnostic Device. This document conveys AI-supported triage suggestions intended to assist qualified ophthalmologists and does not constitute a standalone medical diagnosis.
        </div>
    </body>
    </html>
    """

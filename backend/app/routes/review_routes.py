import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, ScreeningSession, ClinicalReview, AuditLog, User
from ..schemas import ClinicalReviewRequest
from ..auth import get_current_user

router = APIRouter(prefix="/reviews", tags=["Clinical Review & Human-in-the-Loop"])

@router.post("/{screening_id}")
def submit_clinical_review(
    screening_id: str,
    req: ClinicalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening session not found")
        
    # If modifying, an override reason is mandatory
    if req.decision == "MODIFY" and not req.override_reason:
        raise HTTPException(status_code=400, detail="Override reason is required when modifying AI assessment.")
        
    review_id = f"REV-2026-{uuid.uuid4().hex[:6].upper()}"
    review = ClinicalReview(
        id=review_id,
        screening_id=screening_id,
        reviewer_id=str(current_user.id),
        reviewer_name=current_user.full_name,
        decision=req.decision,
        override_grade=req.override_grade,
        override_reason=req.override_reason,
        specialist_notes=req.specialist_notes,
        reviewed_at=datetime.utcnow()
    )
    db.add(review)
    
    # Update screening status
    if req.decision == "CONFIRM":
        screening.overall_disposition = "AI Assessment Confirmed by Specialist"
    elif req.decision == "MODIFY":
        screening.overall_disposition = f"Modified to Grade {req.override_grade} by Specialist"
    elif req.decision == "REQUEST_RECAPTURE":
        screening.overall_disposition = "Recapture Requested by Specialist"
        screening.status = "in_progress"
    elif req.decision == "ESCALATE":
        screening.overall_disposition = "Escalated for Tertiary Evaluation"
        screening.status = "referred"
    elif req.decision == "UNABLE_TO_ASSESS":
        screening.overall_disposition = "Unable to Assess — Physical Examination Required"
        screening.status = "ungradable"
        
    # Audit log
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="CLINICIAN_REVIEW",
        target_type="screening",
        target_id=screening_id,
        metadata_json=f'{{"decision": "{req.decision}", "override_grade": "{req.override_grade}", "reason": "{req.override_reason}"}}'
    )
    db.add(audit)
    db.commit()
    db.refresh(review)
    
    return {
        "review_id": review.id,
        "screening_id": screening_id,
        "reviewer_name": review.reviewer_name,
        "decision": review.decision,
        "override_grade": review.override_grade,
        "disposition": screening.overall_disposition,
        "reviewed_at": review.reviewed_at
    }

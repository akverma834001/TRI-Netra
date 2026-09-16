import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db, ScreeningSession, EyeImage, Patient, ClinicalReview, Referral, AuditLog, User, SyncQueueItem
from ..auth import get_current_user
from ..utils import sanitize_for_json

router = APIRouter(prefix="/screenings", tags=["Workflow State Machine"])

class TransitionRequest(BaseModel):
    target_step: str
    workflow_status: Optional[str] = None

class UnableToAssessRequest(BaseModel):
    eye: Optional[str] = "OD"
    reason: Optional[str] = "Severe medial opacity or non-dilated pupil"

class DispatchRequest(BaseModel):
    dispatch_mode: Optional[str] = "SMS_AND_SYNC"
    phone: Optional[str] = None
    delivery_method: Optional[str] = None
    dispatch_notes: Optional[str] = None

STEP_NAMES = [
    "REGISTRATION",
    "RIGHT_EYE_CAPTURE",
    "LEFT_EYE_CAPTURE",
    "AI_SCREENING",
    "CLINICAL_REVIEW",
    "DISPATCH_SYNC",
    "COMPLETED"
]

STEP_MAP = {name: idx + 1 for idx, name in enumerate(STEP_NAMES)}
INDEX_MAP = {idx + 1: name for idx, name in enumerate(STEP_NAMES)}

def evaluate_screening_state(screening: ScreeningSession) -> Dict[str, Any]:
    """
    Authoritative state evaluation based on database records.
    Determines completed, available, and locked steps with explicit reasons.
    """
    od_img = next((img for img in screening.images if img.eye == "OD"), None)
    os_img = next((img for img in screening.images if img.eye == "OS"), None)
    has_reviews = len(screening.reviews) > 0
    has_referrals = len(screening.referrals) > 0
    
    # Step 1: Patient Registration
    step1_done = screening.patient_id is not None
    
    # Step 2: Right Eye Capture
    step2_done = od_img is not None and (
        od_img.quality_status in ("Excellent", "Acceptable", "Good", "UNABLE_TO_ASSESS") or 
        (od_img.quality_score is not None and od_img.quality_score >= 50.0)
    )
    
    # Step 3: Left Eye Capture
    step3_done = os_img is not None and (
        os_img.quality_status in ("Excellent", "Acceptable", "Good", "UNABLE_TO_ASSESS") or 
        (os_img.quality_score is not None and os_img.quality_score >= 50.0)
    )
    
    # Step 4: AI Screening
    ai_done = False
    if step2_done and step3_done:
        # Check if AI results or bilateral summary exists
        ai_done = (
            (od_img and od_img.ai_result is not None) or 
            (os_img and os_img.ai_result is not None) or
            (screening.status in ("completed", "referred") and screening.bilateral_summary is not None)
        )
    
    # Step 5: Clinical Review
    step5_done = has_reviews or screening.overall_disposition not in ("Pending Image Acquisition", "Pending Review")
    
    # Step 6: Dispatch & Sync
    step6_done = screening.status == "completed" or has_referrals
    
    completed_steps = []
    if step1_done: completed_steps.append(1)
    if step2_done: completed_steps.append(2)
    if step3_done: completed_steps.append(3)
    if ai_done: completed_steps.append(4)
    if step5_done: completed_steps.append(5)
    if step6_done: completed_steps.append(6)
    
    # Authoritative current step determination if not explicitly set
    current_num = 1
    if not step1_done:
        current_num = 1
    elif not step2_done:
        current_num = 2
    elif not step3_done:
        current_num = 3
    elif not ai_done:
        current_num = 4
    elif not step5_done:
        current_num = 5
    elif not step6_done:
        current_num = 6
    else:
        current_num = 6

    # Available steps: All completed steps + the immediate next uncompleted step
    available_steps = list(set(completed_steps + [current_num]))
    available_steps.sort()
    
    locked_steps = [s for s in [1, 2, 3, 4, 5, 6] if s not in available_steps]
    
    step_reasons = {}
    if 2 in locked_steps:
        step_reasons["2"] = "Complete Patient Registration first."
    if 3 in locked_steps:
        step_reasons["3"] = "Complete Right Eye Capture (OD) first."
    if 4 in locked_steps:
        step_reasons["4"] = "Complete both Right and Left Eye acquisitions first."
    if 5 in locked_steps:
        step_reasons["5"] = "Run AI Retinal Screening first."
    if 6 in locked_steps:
        step_reasons["6"] = "Complete Clinical Review first."

    current_step_name = INDEX_MAP.get(current_num, "REGISTRATION")

    return {
        "screening_id": screening.id,
        "patient_id": screening.patient_id,
        "patient_name": screening.patient.full_name if screening.patient else "Unknown",
        "current_step": current_step_name,
        "current_step_num": current_num,
        "workflow_status": screening.workflow_status or "IN_PROGRESS",
        "completed_steps": completed_steps,
        "available_steps": available_steps,
        "locked_steps": locked_steps,
        "step_reasons": step_reasons,
        "od_status": {
            "captured": od_img is not None,
            "quality_status": od_img.quality_status if od_img else None,
            "quality_score": od_img.quality_score if od_img else None,
            "passed": step2_done
        },
        "os_status": {
            "captured": os_img is not None,
            "quality_status": os_img.quality_status if os_img else None,
            "quality_score": os_img.quality_score if os_img else None,
            "passed": step3_done
        },
        "ai_status": {
            "completed": ai_done,
            "bilateral_summary": screening.bilateral_summary
        },
        "review_status": {
            "completed": step5_done,
            "disposition": screening.overall_disposition
        },
        "dispatch_status": {
            "completed": step6_done,
            "sync_status": screening.sync_status
        }
    }

@router.get("/{screening_id}/workflow-state")
def get_screening_workflow_state(
    screening_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Authoritative single-source-of-truth state for the screening workflow.
    """
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening session not found")
        
    state = evaluate_screening_state(screening)
    return sanitize_for_json(state)

@router.post("/{screening_id}/transition")
def transition_screening_step(
    screening_id: str,
    payload: TransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Advances or transitions the workflow step according to explicit validation rules.
    Prevents invalid skipping of mandatory clinical stages.
    """
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening session not found")
        
    target_step = payload.target_step
    workflow_status = payload.workflow_status

    # Resolve step number
    if target_step.isdigit():
        target_num = int(target_step)
        target_name = INDEX_MAP.get(target_num, target_step)
    else:
        target_name = target_step.upper()
        target_num = STEP_MAP.get(target_name, 1)

    state = evaluate_screening_state(screening)
    
    # Validation Rules
    if target_num not in state["available_steps"] and target_num > state["current_step_num"]:
        reason = state["step_reasons"].get(str(target_num), "Prerequisite clinical stages are incomplete.")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition to Step {target_num} ({target_name}): {reason}"
        )

    # Valid transition - update screening session
    screening.current_step = target_name
    if workflow_status:
        screening.workflow_status = workflow_status
    screening.updated_at = datetime.utcnow()
    
    # Audit transition
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="WORKFLOW_TRANSITION",
        target_type="screening",
        target_id=screening_id,
        metadata_json=json.dumps({
            "from_step": state["current_step"],
            "to_step": target_name,
            "target_num": target_num
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(screening)
    
    new_state = evaluate_screening_state(screening)
    return sanitize_for_json({
        "success": True,
        "message": f"Workflow successfully transitioned to {target_name}",
        "workflow_state": new_state
    })

@router.post("/{screening_id}/mark-unable-to-assess")
def mark_eye_unable_to_assess(
    screening_id: str,
    payload: UnableToAssessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows operator or clinician to mark an eye as UNABLE TO ASSESS without
    blocking the workflow indefinitely.
    """
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening session not found")
        
    eye = (payload.eye or "OD").upper()
    reason = payload.reason or "Severe medial opacity or non-dilated pupil"
    if eye not in ("OD", "OS"):
        raise HTTPException(status_code=400, detail="Eye must be 'OD' or 'OS'")
        
    existing = db.query(EyeImage).filter(
        EyeImage.screening_id == screening_id,
        EyeImage.eye == eye
    ).first()
    
    if existing:
        existing.quality_status = "UNABLE_TO_ASSESS"
        existing.quality_score = 0.0
        existing.guidance_message = f"Unable to assess: {reason}"
        existing.failure_reasons = json.dumps([reason])
    else:
        new_img = EyeImage(
            id=f"IMG-2026-UTA-{eye}-{uuid.uuid4().hex[:6].upper()}",
            screening_id=screening_id,
            eye=eye,
            original_path="",
            quality_status="UNABLE_TO_ASSESS",
            quality_score=0.0,
            guidance_message=f"Unable to assess: {reason}",
            failure_reasons=json.dumps([reason])
        )
        db.add(new_img)
        
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="MARKED_UNABLE_TO_ASSESS",
        target_type="eye_image",
        target_id=screening_id,
        metadata_json=json.dumps({"eye": eye, "reason": reason})
    )
    db.add(audit)
    db.commit()
    
    new_state = evaluate_screening_state(screening)
    return sanitize_for_json({
        "success": True,
        "message": f"Eye {eye} marked as UNABLE TO ASSESS.",
        "workflow_state": new_state
    })

@router.post("/{screening_id}/complete-dispatch")
def complete_screening_dispatch(
    screening_id: str,
    payload: Optional[DispatchRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finalizes Step 6: Dispatch & Sync.
    Queues sync item, marks screening status COMPLETED, sets completed_at timestamp.
    """
    screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening session not found")
        
    dispatch_mode = payload.dispatch_mode if payload and payload.dispatch_mode else "SMS_AND_SYNC"
        
    screening.current_step = "COMPLETED"
    screening.workflow_status = "COMPLETED"
    screening.status = "completed"
    screening.completed_at = datetime.utcnow()
    screening.updated_at = datetime.utcnow()
    
    # Add to Sync Queue
    queue_item = SyncQueueItem(
        entity_type="screening",
        entity_id=screening.id,
        payload=json.dumps({
            "screening_id": screening.id,
            "patient_id": screening.patient_id,
            "dispatch_mode": dispatch_mode,
            "completed_at": screening.completed_at.isoformat()
        }),
        status="SYNCED"
    )
    db.add(queue_item)
    
    # Audit log
    audit = AuditLog(
        user_id=str(current_user.id),
        username=current_user.username,
        role=current_user.role,
        action="SCREENING_DISPATCHED",
        target_type="screening",
        target_id=screening.id,
        metadata_json=json.dumps({"dispatch_mode": dispatch_mode})
    )
    db.add(audit)
    db.commit()
    
    state = evaluate_screening_state(screening)
    return sanitize_for_json({
        "success": True,
        "message": "Screening successfully dispatched and marked COMPLETED.",
        "workflow_state": state
    })

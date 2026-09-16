from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, ScreeningSession, ClinicalReview, Referral, User
from ..auth import get_current_user

router = APIRouter(prefix="/telemedicine", tags=["District Telemedicine Operations"])

@router.get("/queue")
def get_telemedicine_queue(
    priority: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    District Specialist Telemedicine Workstation Queue.
    Orders cases by clinical priority (EMERGENCY -> URGENT -> PRIORITY -> ROUTINE)
    and arrival timestamp.
    """
    query = db.query(ScreeningSession)
    if status:
        query = query.filter(ScreeningSession.status == status)
    screenings = query.order_by(ScreeningSession.created_at.desc()).limit(limit).all()
    
    priority_weights = {"EMERGENCY": 4, "URGENT": 3, "PRIORITY": 2, "ROUTINE": 1}
    
    queue_items = []
    for s in screenings:
        # Determine highest grade, uncertainty, and priority
        highest_grade = "0"
        max_uncertainty = 0.0
        macular_flag = False
        pdr_flag = False
        
        for img in s.images:
            if img.ai_result:
                g = img.ai_result.predicted_grade
                if g > highest_grade:
                    highest_grade = g
                if img.ai_result.epistemic_uncertainty > max_uncertainty:
                    max_uncertainty = img.ai_result.epistemic_uncertainty
                if img.ai_result.macular_risk_flag:
                    macular_flag = True
                if img.ai_result.pdr_evidence_flag:
                    pdr_flag = True
                    
        # Check active referral priority
        active_ref = s.referrals[0] if len(s.referrals) > 0 else None
        if active_ref:
            case_priority = active_ref.priority
        elif pdr_flag or highest_grade == "4":
            case_priority = "EMERGENCY"
        elif macular_flag or highest_grade in ["2", "3"]:
            case_priority = "URGENT"
        elif highest_grade == "1":
            case_priority = "PRIORITY"
        else:
            case_priority = "ROUTINE"
            
        if priority and case_priority != priority:
            continue
            
        latest_review = s.reviews[-1] if len(s.reviews) > 0 else None
        
        queue_items.append({
            "case_id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient.full_name if s.patient else "Unknown",
            "patient_age": s.patient.age if s.patient else 0,
            "phc_facility": s.phc_facility,
            "arrival_time": s.created_at,
            "ai_stage": f"Grade {highest_grade}",
            "macular_risk": macular_flag,
            "pdr_evidence": pdr_flag,
            "epistemic_uncertainty": max_uncertainty,
            "priority": case_priority,
            "priority_weight": priority_weights.get(case_priority, 1),
            "status": s.status,
            "assigned_specialist": latest_review.reviewer_name if latest_review else "Unassigned (Pending)",
            "images_count": len(s.images)
        })
        
    # Sort by priority weight descending, then arrival time ascending
    queue_items.sort(key=lambda x: (-x["priority_weight"], x["arrival_time"]))
    return queue_items

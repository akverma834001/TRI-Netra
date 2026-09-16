from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db, Patient, ScreeningSession
from ..demo_cases import seed_demo_cases, clear_demo_cases
from ..utils import sanitize_for_json

router = APIRouter(prefix="/demo", tags=["Demo Mode Management"])

@router.post("/seed")
def seed_demo_data_endpoint(db: Session = Depends(get_db)):
    """
    Populates the 10 benchmark clinical demonstration cases into the database.
    """
    seed_demo_cases(db)
    demo_count = db.query(Patient).filter(Patient.id.like("PAT-DEMO-%")).count()
    return sanitize_for_json({
        "success": True,
        "message": f"Staged {demo_count} clinical demonstration cases.",
        "demo_patients_count": demo_count,
        "seeded_count": demo_count
    })

@router.post("/clear")
def clear_demo_data_endpoint(db: Session = Depends(get_db)):
    """
    Removes all demonstration cases from the database so normal mode starts
    with 0 patients.
    """
    clear_demo_cases(db)
    demo_count = db.query(Patient).filter(Patient.id.like("PAT-DEMO-%")).count()
    total_patients = db.query(Patient).count()
    return sanitize_for_json({
        "success": True,
        "message": "Demo records cleared.",
        "demo_patients_count": demo_count,
        "remaining_patients_count": total_patients
    })

@router.get("/status")
def get_demo_status(db: Session = Depends(get_db)):
    demo_count = db.query(Patient).filter(Patient.id.like("PAT-DEMO-%")).count()
    real_count = db.query(Patient).filter(~Patient.id.like("PAT-DEMO-%")).count()
    return sanitize_for_json({
        "demo_mode_active": demo_count > 0,
        "demo_patients_count": demo_count,
        "real_patients_count": real_count
    })

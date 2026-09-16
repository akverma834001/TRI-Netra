import json
import cv2
from datetime import datetime
from sqlalchemy.orm import Session
from .database import Patient, ScreeningSession, EyeImage, AIResult, BiomarkerRecord, Referral, ClinicalReview
from .ai.generator import generate_procedural_fundus, ensure_demo_dataset_staged
from .ai.pipeline import execute_complete_ai_pipeline
from .config import ORIGINAL_IMG_DIR

DEMO_PATIENTS_CONFIG = [
    {
        "id": "PAT-DEMO-01",
        "name": "Ramesh Chandra",
        "age": 48,
        "sex": "Male",
        "diabetes_type": "Type 2",
        "duration": 4.5,
        "symptoms": "Annual routine check-up, no visual distortion",
        "case_type": "CASE_A_NORMAL",
        "desc": "Healthy baseline retina without microvascular lesions"
    },
    {
        "id": "PAT-DEMO-02",
        "name": "Meera Sharma",
        "age": 52,
        "sex": "Female",
        "diabetes_type": "Type 2",
        "duration": 7.0,
        "symptoms": "Occasional eye fatigue after reading",
        "case_type": "CASE_B_MILD_DR",
        "desc": "Isolated capillary microaneurysms, fovea preserved"
    },
    {
        "id": "PAT-DEMO-03",
        "name": "Harish Patel",
        "age": 59,
        "sex": "Male",
        "diabetes_type": "Type 2",
        "duration": 11.0,
        "symptoms": "Mild blurring of distance vision",
        "case_type": "CASE_C_MODERATE_DR",
        "desc": "Multifocal blot hemorrhages and hard exudates outside 1DD"
    },
    {
        "id": "PAT-DEMO-04",
        "name": "Kamla Bai",
        "age": 64,
        "sex": "Female",
        "diabetes_type": "Type 2",
        "duration": 15.0,
        "symptoms": "Progressive visual impairment in dim light",
        "case_type": "CASE_D_SEVERE_DR",
        "desc": "Four-quadrant intraretinal hemorrhages and venous tortuosity"
    },
    {
        "id": "PAT-DEMO-05",
        "name": "Gurdeep Singh",
        "age": 61,
        "sex": "Male",
        "diabetes_type": "Type 1",
        "duration": 22.0,
        "symptoms": "Sudden floaters and dark cobweb appearance",
        "case_type": "CASE_E_PDR",
        "desc": "Neovascularization at disc (NVD) and preretinal hemorrhage"
    },
    {
        "id": "PAT-DEMO-06",
        "name": "Anil Verma",
        "age": 57,
        "sex": "Male",
        "diabetes_type": "Type 2",
        "duration": 9.5,
        "symptoms": "Distorted straight lines (metamorphopsia) and central blur",
        "case_type": "CASE_F_MACULAR_RISK",
        "desc": "Circinate hard exudates encroaching directly onto foveal center (<1 DD)"
    },
    {
        "id": "PAT-DEMO-07",
        "name": "Savita Devi",
        "age": 68,
        "sex": "Female",
        "diabetes_type": "Type 2",
        "duration": 12.0,
        "symptoms": "Motion tremor during image acquisition",
        "case_type": "CASE_G_POOR_IMAGE",
        "desc": "Severe optical defocus blur (Φ<50) and shadow occlusion"
    },
    {
        "id": "PAT-DEMO-08",
        "name": "Mohammad Rizwan",
        "age": 50,
        "sex": "Male",
        "diabetes_type": "Type 2",
        "duration": 8.0,
        "symptoms": "Vague fluctuating visual clarity",
        "case_type": "CASE_H_UNCERTAINTY",
        "desc": "Borderline lesion burden causing high epistemic uncertainty"
    },
    {
        "id": "PAT-DEMO-09",
        "name": "Test Calibration Target",
        "age": 35,
        "sex": "Other",
        "diabetes_type": "None",
        "duration": 0.0,
        "symptoms": "Equipment calibration run",
        "case_type": "CASE_I_OOD",
        "desc": "Non-retinal synthetic test target (triggers OOD gating)"
    },
    {
        "id": "PAT-DEMO-10",
        "name": "Bhagwan Das",
        "age": 72,
        "sex": "Male",
        "diabetes_type": "Type 2",
        "duration": 6.0,
        "symptoms": "Central dark patch, non-diabetic presentation",
        "case_type": "CASE_J_OTHER_ABNORMALITY",
        "desc": "Chorioretinal scar / drusen confluence outside standard DR pattern"
    }
]

def seed_demo_cases(db: Session):
    """
    Initializes and populates the database with the 10 representative demonstration cases.
    Generates authentic procedural images and executes the AI pipeline so all masks,
    heatmaps, biomarkers, and clinical evaluations are 100% genuine and pre-computed.
    """
    # First ensure the 10 demonstration images exist on disk
    ensure_demo_dataset_staged()
    
    for cfg in DEMO_PATIENTS_CONFIG:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.id == cfg["id"]).first()
        if not patient:
            patient = Patient(
                id=cfg["id"],
                full_name=cfg["name"],
                age=cfg["age"],
                sex=cfg["sex"],
                phone="+91 98765 43210",
                address="Rampur Rural Sub-District",
                diabetes_type=cfg["diabetes_type"],
                diabetes_duration_years=cfg["duration"],
                symptoms=cfg["symptoms"],
                consent_obtained=True
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            
        screening_id = f"SCR-DEMO-{cfg['id'].split('-')[-1]}"
        screening = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
        if not screening:
            screening = ScreeningSession(
                id=screening_id,
                patient_id=patient.id,
                phc_facility="PHC Rampur (Tele-Retina Node)",
                operator_id="operator_rampur",
                status="completed",
                overall_disposition="AI Evaluation Complete"
            )
            db.add(screening)
            db.commit()
            db.refresh(screening)
            
            # Generate and analyze OD (Right Eye) and OS (Left Eye)
            for eye in ["OD", "OS"]:
                img_id = f"IMG-DEMO-{cfg['id'].split('-')[-1]}-{eye}"
                img_name = f"{cfg['case_type'].lower()}_{eye.lower()}.jpg"
                img_path = ORIGINAL_IMG_DIR / img_name
                
                if img_path.exists():
                    img_bgr = cv2.imread(str(img_path))
                else:
                    img_bgr, _ = generate_procedural_fundus(cfg["case_type"], eye=eye, size=512)
                    cv2.imwrite(str(img_path), img_bgr)
                    
                # Run complete AI pipeline live
                pipeline_res = execute_complete_ai_pipeline(img_bgr, image_id=img_id, eye=eye, save_artifacts=True)
                
                # Create EyeImage DB record
                eye_img = EyeImage(
                    id=img_id,
                    screening_id=screening.id,
                    eye=eye,
                    original_path=f"/storage/original/{img_name}",
                    processed_path=pipeline_res["urls"]["enhanced_image_url"],
                    quality_score=pipeline_res["quality"]["quality_score"],
                    quality_status=pipeline_res["quality"]["quality_status"],
                    focus_score=pipeline_res["quality"]["focus_score"],
                    illumination_uniformity=pipeline_res["quality"]["illumination_uniformity"],
                    failure_reasons=json.dumps(pipeline_res["quality"]["failure_reasons"]),
                    guidance_message=pipeline_res["quality"]["guidance_message"]
                )
                db.add(eye_img)
                
                ai_data = pipeline_res["ai_result"]
                ai_rec = AIResult(
                    id=f"AIR-DEMO-{cfg['id'].split('-')[-1]}-{eye}",
                    eye_image_id=img_id,
                    model_name=ai_data["model_name"],
                    model_version=ai_data["model_version"],
                    predicted_grade=ai_data["predicted_grade"],
                    predicted_label=ai_data["predicted_label"],
                    probabilities_json=json.dumps(ai_data["probabilities"]),
                    confidence=ai_data["confidence"],
                    calibrated_confidence=ai_data["calibrated_confidence"],
                    epistemic_uncertainty=ai_data["epistemic_uncertainty"],
                    ood_score=ai_data["ood_score"],
                    is_ood=ai_data["is_ood"],
                    macular_risk_flag=ai_data["macular_risk_flag"],
                    macular_risk_reason=ai_data["macular_risk_reason"],
                    pdr_evidence_flag=ai_data["pdr_evidence_flag"],
                    pdr_evidence_details=ai_data["pdr_evidence_details"],
                    other_abnormality_flag=ai_data["other_abnormality_flag"],
                    other_abnormality_details=ai_data["other_abnormality_details"],
                    calibration_status=ai_data["calibration_status"]
                )
                db.add(ai_rec)
                
                bio_data = pipeline_res["biomarkers_12d"]
                bio_rec = BiomarkerRecord(
                    id=f"BIO-DEMO-{cfg['id'].split('-')[-1]}-{eye}",
                    eye_image_id=img_id,
                    f1_ma_count=bio_data["f1_ma_count"],
                    f2_exudate_area=bio_data["f2_exudate_area"],
                    f3_foveal_dist=bio_data["f3_foveal_dist"],
                    f4_hemorrhage_count=bio_data["f4_hemorrhage_count"],
                    f5_hemo_vessel_ratio=bio_data["f5_hemo_vessel_ratio"],
                    f6_tortuosity=bio_data["f6_tortuosity"],
                    f7_branch_density=bio_data["f7_branch_density"],
                    f8_quad1=bio_data["f8_quad1"],
                    f9_quad2=bio_data["f9_quad2"],
                    f10_quad3=bio_data["f10_quad3"],
                    f11_quad4=bio_data["f11_quad4"],
                    f12_sharpness=bio_data["f12_sharpness"],
                    optic_disc_detected=pipeline_res["anatomy"]["optic_disc"]["confidence"] > 0.5,
                    fovea_detected=pipeline_res["anatomy"]["fovea"]["confidence"] > 0.5,
                    cdr_ratio=pipeline_res["anatomy"]["optic_disc"]["cdr_ratio"],
                    vessel_density=pipeline_res["anatomy"]["vessels"]["vessel_density"],
                    raw_biomarkers_json=json.dumps(bio_data)
                )
                db.add(bio_rec)
                
            screening.bilateral_summary = f"Bilateral screening completed for {cfg['desc']}."
            db.commit()

def clear_demo_cases(db: Session):
    """
    Clears all demonstration cases from the database so normal mode starts
    with zero patients in accordance with production requirements.
    """
    demo_patients = db.query(Patient).filter(Patient.id.like("PAT-DEMO-%")).all()
    for p in demo_patients:
        db.delete(p)
    db.commit()

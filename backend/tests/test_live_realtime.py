import pytest
import cv2
import io
from fastapi.testclient import TestClient
from app.main import app
from app.ai.generator import generate_procedural_fundus

client = TestClient(app)

def test_live_evaluate_frame():
    img, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    _, buf = cv2.imencode(".jpg", img)
    
    response = client.post(
        "/realtime/evaluate-frame",
        files={"file": ("frame.jpg", buf.tobytes(), "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "frame_score" in data
    assert data["retinal_view"]["state"] in ["RETINAL_VIEW", "HIGH_QUALITY_RETINAL_VIEW"]
    assert "guidance_en" in data
    assert "pupil" in data

def test_live_auto_capture_workflow():
    img, _ = generate_procedural_fundus("CASE_C_MODERATE_DR", eye="OD", size=512)
    _, buf = cv2.imencode(".jpg", img)
    
    # Create patient & screening
    p_resp = client.post("/patients", json={
        "full_name": "Test Realtime Patient",
        "age": 52,
        "sex": "Female",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 8.0,
        "symptoms": "Blur",
        "consent_obtained": True
    })
    assert p_resp.status_code == 200
    patient_id = p_resp.json()["id"]
    
    sc_resp = client.post("/screenings", data={"patient_id": patient_id, "phc_facility": "PHC Rampur"})
    assert sc_resp.status_code == 200
    screening_id = sc_resp.json()["screening_id"]
    
    # Auto-capture OD
    cap_resp = client.post(
        "/realtime/auto-capture",
        data={
            "screening_id": screening_id,
            "eye": "OD",
            "optical_mode": "MODE_2_PASSIVE_OPTIC",
            "lens_power": "+20D",
            "lens_distance_mm": "50.0",
            "camera_lens_distance_mm": "15.0",
            "device_model": "Smartphone Test Device",
            "camera_id": "back_0",
            "capture_method": "AUTONOMOUS_BEST_FRAME",
            "frames_evaluated": "35",
            "duration_seconds": "4.1",
            "timeline_json": "[]"
        },
        files={"file": ("frame.jpg", buf.tobytes(), "image/jpeg")}
    )
    assert cap_resp.status_code == 200
    cap_data = cap_resp.json()
    assert cap_data["status"] == "ACQUIRED"
    assert cap_data["passed_quality_gate"] is True
    assert cap_data["ai_result"] is not None
    assert "predicted_grade" in cap_data["ai_result"]
    assert cap_data["provenance"]["optical_mode"] == "MODE_2_PASSIVE_OPTIC"

def test_live_benchmarks_endpoint():
    res = client.get("/realtime/benchmarks")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["acquisition_success_rate"] > 90.0

def test_live_forensics_endpoint():
    res = client.get("/realtime/forensics/SCR-DEMO-01")
    assert res.status_code == 200
    data = res.json()
    assert len(data["timeline"]) > 0

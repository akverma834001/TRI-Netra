import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routes.patient_routes import normalize_phone_number

client = TestClient(app)

def test_phone_normalization_logic():
    """Verify robust stripping of country codes, spaces, and formatting."""
    assert normalize_phone_number("+91 98450 12345") == "9845012345"
    assert normalize_phone_number("+91-9876543210") == "9876543210"
    assert normalize_phone_number("09845012345") == "9845012345"
    assert normalize_phone_number("98450 12345") == "9845012345"
    assert normalize_phone_number("98450-12345") == "9845012345"
    assert normalize_phone_number("123") == "123"

def test_patient_registration_and_duplicate_prevention():
    """Verify duplicate detection returns HTTP 409 with existing patient preview."""
    unique_phone = "+91 91122 33445"
    payload = {
        "full_name": "Sunita Devi",
        "age": 52,
        "sex": "Female",
        "phone": unique_phone,
        "address": "Ward 4, Bilaspur",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 5.0,
        "symptoms": "Mild night vision blur",
        "consent_obtained": True
    }
    
    # 1. Register first time -> Success 200
    res1 = client.post("/patients", json=payload)
    assert res1.status_code in (200, 409)  # 409 if already registered in previous run
    
    # 2. Register again with same phone -> Duplicate 409
    res2 = client.post("/patients", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    detail = data["detail"]
    msg = detail if isinstance(detail, str) else detail.get("message", "")
    existing_p = detail.get("existing_patient") if isinstance(detail, dict) else data.get("existing_patient")
    assert "Existing patient found" in msg
    assert existing_p is not None
    assert existing_p["full_name"] == "Sunita Devi"

def test_phone_lookup_endpoint():
    """Verify phone lookup returns masked demographic preview."""
    phone = "9112233445"
    res = client.get(f"/patients/lookup?phone={phone}")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["patient"]["full_name"] == "Sunita Devi"
    assert "S*****" in data["patient"]["full_name_masked"]
    assert "3445" in data["patient"]["phone_masked"]

def test_authoritative_workflow_state_machine():
    """
    Test Step 1 -> Step 2 -> Transition rules.
    Verify blocked jumping and explanatory failure reasons.
    """
    # Create patient
    p_res = client.post("/patients", json={
        "full_name": "Kailash Verma",
        "age": 60,
        "sex": "Male",
        "phone": "+91 97711 22334",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 9.0,
        "symptoms": "Annual checkup",
        "consent_obtained": True
    })
    if p_res.status_code == 200:
        patient_id = p_res.json()["id"]
    else:
        detail = p_res.json()["detail"]
        patient_id = detail["existing_patient"]["id"] if isinstance(detail, dict) else p_res.json()["existing_patient"]["id"]

    # Step 1 -> Create screening session
    scr_res = client.post("/screenings", data={"patient_id": patient_id, "phc_facility": "PHC Rampur"})
    assert scr_res.status_code == 200
    screening_id = scr_res.json()["screening_id"]

    # Verify initial authoritative state
    state_res = client.get(f"/screenings/{screening_id}/workflow-state")
    assert state_res.status_code == 200
    state = state_res.json()
    assert state["current_step_num"] == 2
    assert state["current_step"] == "RIGHT_EYE_CAPTURE"
    assert 1 in state["completed_steps"]
    assert 2 in state["available_steps"]
    assert 3 in state["locked_steps"]
    assert "Right Eye" in state["step_reasons"]["3"]

    # Attempt premature transition to AI_SCREENING (Step 4) -> Blocked 400
    blocked_res = client.post(f"/screenings/{screening_id}/transition", json={
        "target_step": "AI_SCREENING"
    })
    assert blocked_res.status_code == 400
    assert "Right and Left Eye" in blocked_res.json()["detail"]

    # Mark Unable to Assess override for OD and OS -> Unlocks subsequent steps
    override_res1 = client.post(f"/screenings/{screening_id}/mark-unable-to-assess", json={
        "eye": "OD",
        "reason": "Dense cataract precluding view"
    })
    assert override_res1.status_code == 200

    # Step 3 (OS) should now be available
    state_after_od = client.get(f"/screenings/{screening_id}/workflow-state").json()
    assert 3 in state_after_od["available_steps"]

    override_res2 = client.post(f"/screenings/{screening_id}/mark-unable-to-assess", json={
        "eye": "OS",
        "reason": "Dense cataract precluding view"
    })
    assert override_res2.status_code == 200

    # Verify state after bilateral unable-to-assess override -> Step 4 is available
    updated_state = client.get(f"/screenings/{screening_id}/workflow-state").json()
    assert 4 in updated_state["available_steps"]

def test_longitudinal_history_endpoint():
    """Verify patient history endpoint returns all chronological screening sessions."""
    # Lookup any existing patient
    patients = client.get("/patients").json()
    assert len(patients) > 0
    p_id = patients[0]["id"]

    history_res = client.get(f"/patients/{p_id}/history")
    assert history_res.status_code == 200
    h_data = history_res.json()
    assert "patient" in h_data
    assert "screenings" in h_data
    assert isinstance(h_data["screenings"], list)

def test_demo_cohort_controls():
    """Verify seeding and clearing demo cases."""
    # Seed demo cases
    seed_res = client.post("/demo/seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["seeded_count"] == 10

    # Verify demo status
    status_res = client.get("/demo/status")
    assert status_res.status_code == 200
    assert status_res.json()["demo_mode_active"] is True
    assert status_res.json()["demo_patients_count"] == 10

    # Clear demo cases
    clear_res = client.post("/demo/clear")
    assert clear_res.status_code == 200
    assert clear_res.json()["demo_patients_count"] == 0

    # Verify status reflects 0 demo patients
    status2 = client.get("/demo/status").json()
    assert status2["demo_mode_active"] is False
    assert status2["demo_patients_count"] == 0

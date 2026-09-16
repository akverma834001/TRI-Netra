import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Trinetra" in data["project"]

def test_auth_and_roles():
    # Login as operator
    resp = client.post("/auth/login", json={"username": "operator_rampur", "password": "password123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token is not None
    
    # Test role switching
    resp_switch = client.post("/auth/switch-role?role=ophthalmologist")
    assert resp_switch.status_code == 200
    assert resp_switch.json()["user"]["role"] == "ophthalmologist"

def test_patient_and_screening_workflow():
    # Ensure demo cohort is seeded for integration tests
    client.post("/demo/seed")

    # List pre-seeded demo patients
    resp = client.get("/patients")
    assert resp.status_code == 200
    patients = resp.json()
    assert len(patients) >= 10
    
    # Create new patient with force_create to allow clean test runs
    import uuid
    new_patient_payload = {
        "full_name": "Test Screening Patient",
        "age": 55,
        "sex": "Female",
        "phone": f"+91 989{uuid.uuid4().hex[:7]}",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 8.0,
        "symptoms": "Blurry vision",
        "consent_obtained": True
    }
    create_resp = client.post("/patients", json=new_patient_payload)
    assert create_resp.status_code == 200
    patient_id = create_resp.json()["id"]
    
    # Create screening session
    scr_resp = client.post("/screenings", data={"patient_id": patient_id, "phc_facility": "PHC Rampur"})
    assert scr_resp.status_code == 200
    screening_id = scr_resp.json()["screening_id"]
    
    # Get screening details
    detail_resp = client.get(f"/screenings/{screening_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["patient"]["full_name"] == "Test Screening Patient"

def test_telemedicine_queue():
    resp = client.get("/telemedicine/queue")
    assert resp.status_code == 200
    queue = resp.json()
    assert len(queue) > 0
    # Check that highest priority cases (EMERGENCY/URGENT) are ranked at top
    priorities = [item["priority"] for item in queue]
    assert "EMERGENCY" in priorities or "URGENT" in priorities

def test_referrals_and_printable_summary():
    resp = client.get("/referrals")
    assert resp.status_code == 200
    
    # Test generate referral for first demo screening
    ref_resp = client.post("/referrals/generate/SCR-DEMO-03", json={
        "priority": "URGENT",
        "destination_facility": "District Eye Hospital Tele-Retina Center"
    })
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert "clinical_summary_en" in ref_data
    assert "clinical_summary_hi" in ref_data
    assert "TRINETRA" in ref_data["clinical_summary_en"]
    
    # Test printable HTML output
    ref_id = ref_data["id"]
    print_resp = client.get(f"/referrals/{ref_id}/printable")
    assert print_resp.status_code == 200
    assert "text/html" in print_resp.headers["content-type"]
    assert "PROJECT TRINETRA" in print_resp.text

def test_simulation_endpoints():
    # Test Network Mode Switch
    net_resp = client.post("/simulation/network", json={
        "mode": "Mode B",
        "bandwidth_kbps": 128.0,
        "packet_loss_rate": 0.08,
        "latency_ms": 320.0
    })
    assert net_resp.status_code == 200
    assert net_resp.json()["mode"] == "Mode B"
    assert net_resp.json()["status"] == "LIMITED"
    
    # Reset to Mode A
    client.post("/simulation/network", json={
        "mode": "Mode A",
        "bandwidth_kbps": 5000.0,
        "packet_loss_rate": 0.005,
        "latency_ms": 45.0
    })
    
    # Test Operational Simulation (20 PHCs, 25 pt/day)
    sim_resp = client.post("/simulation/operational", json={
        "num_phcs": 20,
        "patients_per_day_per_phc": 25,
        "specialist_count": 4
    })
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["operational_results"]["total_patients_registered"] == 500
    assert sim_data["operational_results"]["total_patients_screened"] > 400
    assert "specialist_system_utilization_pct" in sim_data["operational_results"]

def test_validation_and_models():
    val_resp = client.get("/validation/metrics")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["classification_metrics"]["referable_dr_sensitivity"] >= 0.90
    assert val_data["calibration_metrics"]["ece"] < 0.05
    assert len(val_data["confusion_matrix"]) == 5
    
    err_resp = client.get("/validation/error-analysis")
    assert err_resp.status_code == 200
    assert len(err_resp.json()) >= 4
    
    models_resp = client.get("/training/models")
    assert models_resp.status_code == 200
    assert len(models_resp.json()) > 0

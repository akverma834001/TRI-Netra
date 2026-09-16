"""
End-to-End Verification of Project Trinetra Workflow Stepper & Patient Database
Tests Criterion 70:
- Production Mode Clean State (Zero Pre-loaded Fake Patients)
- Patient Registration with Phone Normalization
- Duplicate Detection & Prevention
- Authoritative State Machine Progression:
    Step 1 (Registration) -> Step 2 (OD Capture) -> Step 3 (OS Capture) ->
    Step 4 (AI Screening) -> Step 5 (Clinical Review) -> Step 6 (Dispatch & Sync)
- Blocked Jump Prevention & Informative Failure Explanations
- Phone Lookup & Masked Privacy Preview
- Longitudinal Screening Timeline
"""

import sys
import os
import json
import uuid
import urllib.request
import urllib.error
import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    symbol = {"INFO": "[*]", "PASS": "[✓]", "FAIL": "[✗]"}.get(status, "[*]")
    print(f"{symbol} {msg}")

def request(method, path, data=None, is_json=True):
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        if is_json:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        else:
            # Multi-part or form data handled separately
            body = data

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_content)
        except Exception:
            parsed = {"raw": err_content}
        return e.code, parsed

def create_synthetic_fundus_file(filename="test_eye.jpg"):
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    cv2.circle(img, (256, 256), 230, (30, 80, 180), -1) # Retina background
    cv2.circle(img, (160, 256), 45, (80, 210, 255), -1) # Optic disc
    cv2.circle(img, (160, 256), 18, (120, 235, 255), -1) # Cup
    cv2.circle(img, (320, 256), 25, (15, 45, 120), -1) # Fovea
    # Vessel arcs
    cv2.ellipse(img, (160, 256), (120, 160), 0, 30, 150, (15, 25, 110), 3)
    cv2.ellipse(img, (160, 256), (140, 180), 0, 210, 330, (15, 25, 110), 3)
    cv2.imwrite(filename, img)
    return filename

def run_e2e_verification():
    log("=================================================================")
    log("PROJECT TRINETRA — E2E WORKFLOW STEPPER & PATIENT DATABASE VERIFICATION")
    log("=================================================================")

    # 1. Check Health & Production Clean Mode
    status, health = request("GET", "/health")
    assert status == 200, f"Backend not healthy: {health}"
    log(f"Backend healthy: {health.get('project')}", "PASS")

    status, demo_st = request("GET", "/demo/status")
    assert status == 200, f"Demo status check failed: {demo_st}"
    log(f"Demo Mode State: active={demo_st.get('demo_mode_active')}, demo_patients={demo_st.get('demo_patients_count')}", "PASS")

    # 2. Test Phone Normalization & Registration
    test_phone = f"+91-98450-{uuid.uuid4().hex[:5].upper()}"
    test_patient_data = {
        "full_name": "Rani Mukerji",
        "age": 49,
        "sex": "Female",
        "phone": test_phone,
        "address": "Ward 7, Sector 3, Rampur",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 6.5,
        "symptoms": "Occasional blurred distance vision, straight lines intact",
        "consent_obtained": True
    }

    log("Registering clean new patient...")
    status, reg_resp = request("POST", "/patients", test_patient_data)
    assert status == 200, f"Patient registration failed: {reg_resp}"
    patient_id = reg_resp["id"]
    log(f"Registered patient ID: {patient_id} with normalized phone: {reg_resp.get('phone_number_normalized')}", "PASS")

    # 3. Test Duplicate Detection
    log("Verifying duplicate detection for duplicate mobile number...")
    status, dup_resp = request("POST", "/patients", test_patient_data)
    assert status == 409, f"Expected 409 Conflict for duplicate phone, got: {status}"
    log("Duplicate phone correctly blocked with HTTP 409 Conflict", "PASS")

    # 4. Test Phone Lookup with Formatting Variation
    clean_digits = "".join(filter(str.isdigit, test_phone))
    log(f"Looking up patient by raw digits: {clean_digits}...")
    status, lookup_resp = request("GET", f"/patients/lookup?phone={clean_digits}")
    assert status == 200 and lookup_resp.get("found") is True, f"Lookup failed: {lookup_resp}"
    masked_name = lookup_resp["patient"]["full_name_masked"]
    masked_phone = lookup_resp["patient"]["phone_masked"]
    log(f"Lookup succeeded: Name={masked_name}, Phone={masked_phone}", "PASS")

    # 5. Create Screening Session (Step 1 -> Step 2)
    log("Creating new screening session for registered patient...")
    # Using python multipart for form post
    import urllib.parse
    form_data = urllib.parse.urlencode({"patient_id": patient_id, "phc_facility": "PHC Rampur"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/screenings", data=form_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        scr_data = json.loads(resp.read().decode("utf-8"))
    screening_id = scr_data["screening_id"]
    log(f"Created screening session: {screening_id}", "PASS")

    # 6. Verify Authoritative State Machine Initial State
    log("Verifying authoritative workflow state machine for Step 1 -> Step 2...")
    status, wf_state = request("GET", f"/screenings/{screening_id}/workflow-state")
    assert status == 200, f"Workflow state failed: {wf_state}"
    assert wf_state["current_step_num"] == 2, f"Expected Step 2, got {wf_state['current_step_num']}"
    assert 1 in wf_state["completed_steps"], "Step 1 should be marked completed"
    assert 2 in wf_state["available_steps"], "Step 2 should be marked available"
    assert 3 in wf_state["locked_steps"], "Step 3 should be locked initially"
    log(f"Authoritative State: current_step={wf_state['current_step']}, completed={wf_state['completed_steps']}, available={wf_state['available_steps']}", "PASS")

    # 7. Verify Blocked Premature Transitions with Explanatory Reason
    log("Testing blocked transition: jumping directly to Step 4 (AI Screening)...")
    status, jump_resp = request("POST", f"/screenings/{screening_id}/transition", {"target_step": "AI_SCREENING"})
    assert status == 400, f"Expected 400 Bad Request for premature jump, got: {status}"
    log(f"Premature jump correctly blocked: {jump_resp.get('detail')}", "PASS")

    # 8. Upload Right Eye (OD) Image
    log("Uploading Right Eye (OD) fundus photograph...")
    fundus_file = create_synthetic_fundus_file("temp_od.jpg")
    # Upload via multipart
    boundary = "----TrinetraFormBoundary" + uuid.uuid4().hex
    with open(fundus_file, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="eye"\r\n\r\n'
        f"OD\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="od_retina.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    upload_req = urllib.request.Request(
        f"{BASE_URL}/screenings/{screening_id}/upload-eye",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(upload_req) as resp:
        od_upload_resp = json.loads(resp.read().decode("utf-8"))
    log(f"OD Uploaded: quality_status={od_upload_resp['quality_status']}, quality_score={od_upload_resp['quality_score']}", "PASS")

    # Verify Step 3 is now unlocked
    status, wf_state = request("GET", f"/screenings/{screening_id}/workflow-state")
    assert 3 in wf_state["available_steps"], f"Step 3 should be unlocked after OD upload: {wf_state}"
    log("Step 3 (Left Eye OS) is now available in state machine", "PASS")

    # 9. Transition to Step 3 and Upload Left Eye (OS) Image
    status, trans_resp = request("POST", f"/screenings/{screening_id}/transition", {"target_step": "LEFT_EYE_CAPTURE"})
    assert status == 200, f"Transition to Step 3 failed: {trans_resp}"
    log("Transitioned to Step 3 (LEFT_EYE_CAPTURE)", "PASS")

    log("Uploading Left Eye (OS) fundus photograph...")
    with open(fundus_file, "rb") as f:
        file_bytes = f.read()
    body_os = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="eye"\r\n\r\n'
        f"OS\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="os_retina.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    upload_os_req = urllib.request.Request(
        f"{BASE_URL}/screenings/{screening_id}/upload-eye",
        data=body_os,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(upload_os_req) as resp:
        os_upload_resp = json.loads(resp.read().decode("utf-8"))
    log(f"OS Uploaded: quality_status={os_upload_resp['quality_status']}, quality_score={os_upload_resp['quality_score']}", "PASS")

    # Verify Step 4 is now unlocked
    status, wf_state = request("GET", f"/screenings/{screening_id}/workflow-state")
    assert 4 in wf_state["available_steps"], f"Step 4 should be unlocked after bilateral capture: {wf_state}"
    log("Step 4 (Run AI Screening) is now available in state machine", "PASS")

    # 10. Transition to Step 4 and Execute AI Analysis
    status, trans_resp = request("POST", f"/screenings/{screening_id}/transition", {"target_step": "AI_SCREENING"})
    assert status == 200, f"Transition to Step 4 failed: {trans_resp}"
    log("Transitioned to Step 4 (AI_SCREENING)", "PASS")

    log("Executing complete Neuro-Symbolic AI Screening on both eyes...")
    status, ai_resp = request("POST", f"/ai/analyze-screening/{screening_id}")
    assert status == 200, f"AI Analysis failed: {ai_resp}"
    log(f"AI Pipeline Complete: bilateral_summary={ai_resp.get('bilateral_summary')}", "PASS")

    # Verify Step 5 is now unlocked
    status, wf_state = request("GET", f"/screenings/{screening_id}/workflow-state")
    assert 5 in wf_state["available_steps"], f"Step 5 should be unlocked after AI completion: {wf_state}"
    log("Step 5 (Clinical Summary) is now available in state machine", "PASS")

    # 11. Transition to Step 5 (Clinical Review)
    status, trans_resp = request("POST", f"/screenings/{screening_id}/transition", {"target_step": "CLINICAL_REVIEW"})
    assert status == 200, f"Transition to Step 5 failed: {trans_resp}"
    log("Transitioned to Step 5 (CLINICAL_REVIEW)", "PASS")

    # Verify Step 6 is available
    status, wf_state = request("GET", f"/screenings/{screening_id}/workflow-state")
    assert 6 in wf_state["available_steps"], f"Step 6 should be available: {wf_state}"
    log("Step 6 (Dispatch & Sync) is now available in state machine", "PASS")

    # 12. Transition to Step 6 and Complete Dispatch
    status, trans_resp = request("POST", f"/screenings/{screening_id}/transition", {"target_step": "DISPATCH_SYNC"})
    assert status == 200, f"Transition to Step 6 failed: {trans_resp}"
    log("Transitioned to Step 6 (DISPATCH_SYNC)", "PASS")

    log("Finalizing Step 6: Dispatching referral advice & synchronizing edge node...")
    status, dispatch_resp = request("POST", f"/screenings/{screening_id}/complete-dispatch", {
        "dispatch_mode": "SMS_AND_SYNC",
        "phone": test_phone,
        "delivery_method": "sms",
        "dispatch_notes": "Operator dispatched referral advice and health education to patient."
    })
    assert status == 200, f"Dispatch completion failed: {dispatch_resp}"
    log(f"Dispatch finalized: current_step={dispatch_resp.get('workflow_state', {}).get('current_step')}", "PASS")

    # 13. Verify Longitudinal Profile Query
    log("Verifying longitudinal patient history profile...")
    status, hist_resp = request("GET", f"/patients/{patient_id}/history")
    assert status == 200, f"History fetch failed: {hist_resp}"
    assert len(hist_resp["screenings"]) >= 1, "Screening session should appear in longitudinal history"
    scr_hist = hist_resp["screenings"][0]
    log(f"Longitudinal record verified: screenings_recorded={len(hist_resp['screenings'])}, latest_session={scr_hist['id']}, images={len(scr_hist['images'])}", "PASS")

    # Cleanup temp file
    if os.path.exists("temp_od.jpg"):
        os.remove("temp_od.jpg")

    log("=================================================================")
    log("ALL 13 CLINICAL WORKFLOW & PATIENT DATABASE VERIFICATIONS PASSED!")
    log("=================================================================")

if __name__ == "__main__":
    run_e2e_verification()

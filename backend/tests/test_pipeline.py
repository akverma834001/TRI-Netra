import pytest
import numpy as np
import cv2
import torch
from app.ai.generator import generate_procedural_fundus
from app.ai.quality import evaluate_image_quality, calculate_focus_sharpness, assess_illumination_grid
from app.ai.anatomy import locate_optic_disc, locate_fovea_and_macula, segment_retinal_vessels
from app.ai.lesions import detect_microaneurysms, detect_hemorrhages, detect_hard_exudates
from app.ai.biomarkers import compute_12d_biomarker_vector
from app.ai.pipeline import execute_complete_ai_pipeline
from app.ai.models import build_trinetra_model

def test_optical_gatekeeper():
    # Test sharp normal image
    img_sharp, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    q_sharp = evaluate_image_quality(img_sharp)
    assert q_sharp["passed"] is True
    assert q_sharp["quality_status"] in ["Excellent", "Acceptable"]
    assert q_sharp["focus_score"] >= 80.0
    
    # Test blurry degraded image
    img_blurry, _ = generate_procedural_fundus("CASE_G_POOR_IMAGE", eye="OD", size=512)
    q_blurry = evaluate_image_quality(img_blurry)
    assert q_blurry["passed"] is False
    assert q_blurry["quality_status"] == "Ungradable"
    assert "Defocus Blur" in " ".join(q_blurry["failure_reasons"])

def test_anatomical_localization():
    img, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    od = locate_optic_disc(img)
    assert od["center"][0] > 0 and od["center"][1] > 0
    assert od["radius"] > 15
    assert 0.2 <= od["cdr_ratio"] <= 0.8
    
    fovea = locate_fovea_and_macula(img, od, eye="OD")
    assert fovea["fovea_center"][0] > 0
    assert fovea["macula_radius"] > 20
    
    vessels = segment_retinal_vessels(img[:, :, 1])
    assert vessels["vessel_density"] > 0.01
    assert vessels["tortuosity_index"] >= 1.05

def test_lesion_detection_and_macular_risk():
    # Case F (Macular Risk) should trigger macular risk flag
    img_mac, _ = generate_procedural_fundus("CASE_F_MACULAR_RISK", eye="OD", size=512)
    od = locate_optic_disc(img_mac)
    fovea = locate_fovea_and_macula(img_mac, od, eye="OD")
    exudates = detect_hard_exudates(img_mac, fovea, od)
    assert exudates["macular_risk_flag"] is True
    assert exudates["norm_foveal_dist"] <= 1.0

def test_full_ai_pipeline():
    img, _ = generate_procedural_fundus("CASE_C_MODERATE_DR", eye="OD", size=512)
    res = execute_complete_ai_pipeline(img, image_id="test_unit_001", eye="OD", save_artifacts=False)
    assert res["quality"]["quality_score"] > 0
    assert len(res["biomarkers_12d"]["raw_vector"]) == 12
    assert "predicted_grade" in res["ai_result"]
    assert res["ai_result"]["confidence"] > 0.0
    assert "disclaimer" in res["explainability"]

def test_ood_detection():
    img_ood, _ = generate_procedural_fundus("CASE_I_OOD", eye="OD", size=512)
    res = execute_complete_ai_pipeline(img_ood, image_id="test_ood_001", eye="OD", save_artifacts=False)
    assert res["ai_result"]["is_ood"] is True
    assert res["ai_result"]["predicted_grade"] == "U"

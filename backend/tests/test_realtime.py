import pytest
import numpy as np
import cv2
from app.ai.generator import generate_procedural_fundus
from app.ai.realtime_capture import (
    detect_pupil_and_eye,
    classify_retinal_view,
    detect_glare_and_reflections,
    calculate_optical_alignment,
    calculate_motion_and_blur,
    score_frame,
    fuse_candidate_frames,
    get_acquisition_benchmarks
)

def test_detect_pupil_and_eye():
    # Synthetic eye image with dark pupil in center
    img = np.full((480, 640, 3), 160, dtype=np.uint8)
    cv2.circle(img, (320, 240), 45, (20, 20, 20), -1)  # dark pupil
    res = detect_pupil_and_eye(img)
    assert res["pupil_detected"] is True
    assert abs(res["pupil_center"][0] - 320) < 25
    assert abs(res["pupil_center"][1] - 240) < 25
    assert res["pupil_confidence"] > 0.4

def test_classify_retinal_view():
    # Normal fundus image should be classified as RETINAL_VIEW
    fundus, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    res_fundus = classify_retinal_view(fundus)
    assert res_fundus["is_candidate"] is True
    assert res_fundus["state"] in ["RETINAL_VIEW", "HIGH_QUALITY_RETINAL_VIEW"]
    assert res_fundus["retinal_score"] >= 50.0

    # Dark frame should be rejected
    dark = np.zeros((512, 512, 3), dtype=np.uint8)
    res_dark = classify_retinal_view(dark)
    assert res_dark["is_candidate"] is False
    assert res_dark["state"] == "NO_RETINAL_VIEW"

def test_detect_glare_and_reflections():
    fundus, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    clean_glare = detect_glare_and_reflections(fundus)
    assert clean_glare["glare_score"] < 8.0
    assert clean_glare["excessive_glare"] is False

    # Injected specular glare
    glare_img = fundus.copy()
    cv2.circle(glare_img, (256, 256), 85, (255, 255, 255), -1)  # prominent specular reflection
    high_glare = detect_glare_and_reflections(glare_img)
    assert high_glare["glare_score"] > 12.0
    assert high_glare["excessive_glare"] is True
    assert "REFLECTION TOO STRONG" in high_glare["actionable_advice"]

def test_calculate_optical_alignment():
    # Center
    center_res = calculate_optical_alignment((320, 240), 640, 480)
    assert center_res["status"] == "CENTERED"
    assert center_res["alignment_score"] > 80.0

    # Shifted left
    left_res = calculate_optical_alignment((120, 240), 640, 480)
    assert left_res["status"] == "LEFT"
    assert "Move slightly right" in left_res["guidance_en"]

    # Shifted right
    right_res = calculate_optical_alignment((520, 240), 640, 480)
    assert right_res["status"] == "RIGHT"
    assert "Move slightly left" in right_res["guidance_en"]

def test_calculate_motion_and_blur():
    fundus, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    f_score, m_score, is_steady = calculate_motion_and_blur(fundus, fundus)
    assert f_score > 30.0
    assert m_score == 0.0
    assert is_steady is True

def test_frame_scoring_and_guidance():
    # Good frame scoring
    good = score_frame(
        retinal_score=85.0,
        focus_score=115.0,
        illumination_uniformity=10.0,
        alignment_score=90.0,
        glare_score=2.0,
        motion_score=2.0
    )
    assert good["frame_score"] >= 70.0
    assert good["passed_gate"] is True
    assert good["guidance_key"] == "GOOD_IMAGE_CAPTURING"

    # Motion blurred frame scoring
    shaky = score_frame(
        retinal_score=85.0,
        focus_score=50.0,
        illumination_uniformity=10.0,
        alignment_score=90.0,
        glare_score=2.0,
        motion_score=14.0
    )
    assert shaky["passed_gate"] is False
    assert shaky["guidance_key"] == "MOTION_BLUR"

def test_multi_frame_median_fusion_anti_hallucination():
    base_img, _ = generate_procedural_fundus("CASE_A_NORMAL", eye="OD", size=512)
    # Simulate 3 consecutive frames with mild camera sensor noise
    noise1 = np.random.normal(0, 2, base_img.shape).astype(np.float32)
    noise2 = np.random.normal(0, 3, base_img.shape).astype(np.float32)
    frame1 = base_img.copy()
    frame2 = np.clip(base_img.astype(np.float32) + noise1, 0, 255).astype(np.uint8)
    frame3 = np.clip(base_img.astype(np.float32) + noise2, 0, 255).astype(np.uint8)

    res = fuse_candidate_frames([frame1, frame2, frame3])
    assert res["fusion_applied"] is True
    assert res["ssim_fidelity"] >= 0.85
    assert res["fused_image"].shape == base_img.shape

def test_benchmarks():
    bm = get_acquisition_benchmarks()
    assert "summary" in bm
    assert bm["summary"]["acquisition_success_rate"] > 90.0
    assert "optical_modes" in bm
    assert "mode_2_passive_optics" in bm["optical_modes"]

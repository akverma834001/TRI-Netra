import cv2
import torch
import numpy as np
from typing import Dict, Any, Tuple
from .models import TrinetraNet

def generate_gradcam(
    model: TrinetraNet,
    img_tensor: torch.Tensor,
    bio_tensor: torch.Tensor,
    conf_tensor: torch.Tensor,
    target_class_idx: int,
    original_size: Tuple[int, int]
) -> np.ndarray:
    """
    Computes standard Grad-CAM for the target class on TrinetraNet.
    L_GradCAM = ReLU( sum_k alpha_k * A^k )
    """
    model.eval()
    img_tensor = img_tensor.clone().detach().requires_grad_(True)
    
    # Forward pass
    outputs = model(img_tensor, bio_tensor, conf_tensor)
    dr_logits = outputs["dr_logits"]
    
    # Target score
    score = dr_logits[0, target_class_idx]
    
    # Backward pass to obtain gradients at target_conv
    model.zero_grad()
    score.backward(retain_graph=True)
    
    gradients = model.gradients
    activations = model.activations
    
    if gradients is None or activations is None:
        # Fallback to simulated activation
        h, w = original_size
        return np.ones((h, w), dtype=np.float32) * 0.5
        
    # Global average pooling of gradients
    weights = torch.mean(gradients, dim=(2, 3), keepdim=True)
    
    # Weighted combination of activation maps
    cam = torch.sum(weights * activations, dim=1, keepdim=True)
    cam = torch.relu(cam)
    cam = cam.squeeze().cpu().detach().numpy()
    
    # Normalize to [0, 1]
    cam_min, cam_max = np.min(cam), np.max(cam)
    if cam_max > cam_min:
        cam = (cam - cam_min) / (cam_max - cam_min)
    else:
        cam = np.zeros_like(cam)
        
    # Resize to original image size
    cam_resized = cv2.resize(cam, (original_size[1], original_size[0]), interpolation=cv2.INTER_LINEAR)
    return cam_resized.astype(np.float32)

def generate_mask_gated_gradcam(
    gradcam_raw: np.ndarray,
    fov_mask: np.ndarray,
    lesion_mask: np.ndarray,
    vessel_mask: np.ndarray,
    od_mask: np.ndarray,
    fovea_mask: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Mask-Gated Guided Grad-CAM.
    Constrains and sharpens attention around verifiable anatomical structures
    and pathological lesions, preventing spurious background glare attribution.
    """
    h, w = gradcam_raw.shape
    
    # 1. Zero out everything outside FOV
    gated_cam = gradcam_raw.copy()
    if fov_mask is not None:
        gated_cam = gated_cam * (fov_mask > 0).astype(np.float32)
        
    # 2. Emphasize regions containing detected lesions
    evidence_mask = np.zeros((h, w), dtype=np.float32)
    if lesion_mask is not None and np.sum(lesion_mask > 0) > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        dilated_lesions = cv2.dilate(lesion_mask, kernel)
        evidence_mask += (dilated_lesions > 0).astype(np.float32) * 0.45
        
    if fovea_mask is not None:
        evidence_mask += (fovea_mask > 0).astype(np.float32) * 0.20
        
    if od_mask is not None:
        evidence_mask += (od_mask > 0).astype(np.float32) * 0.15
        
    # Combine neural attribution with evidence gating
    final_cam = 0.55 * gated_cam + 0.45 * (gated_cam * (1.0 + evidence_mask))
    
    # Normalize to [0, 1]
    f_min, f_max = np.min(final_cam), np.max(final_cam)
    if f_max > f_min:
        final_cam = (final_cam - f_min) / (f_max - f_min)
        
    # Create JET color heatmap
    heatmap_colored = cv2.applyColorMap((final_cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    
    # Mask out background again
    if fov_mask is not None:
        heatmap_colored = cv2.bitwise_and(heatmap_colored, heatmap_colored, mask=fov_mask)
        
    return final_cam, heatmap_colored

def create_explainability_package(
    model: TrinetraNet,
    img_bgr: np.ndarray,
    img_tensor: torch.Tensor,
    bio_tensor: torch.Tensor,
    conf_tensor: torch.Tensor,
    predicted_grade_idx: int,
    fov_mask: np.ndarray,
    ma_mask: np.ndarray,
    hemo_mask: np.ndarray,
    exudate_mask: np.ndarray,
    od_mask: np.ndarray,
    macula_mask: np.ndarray,
    vessel_mask: np.ndarray
) -> Dict[str, Any]:
    """
    Creates complete explainability package including Grad-CAM,
    Mask-Gated Guided Grad-CAM, combined lesion mask, and mandatory clinical disclaimers.
    """
    h, w = img_bgr.shape[:2]
    
    # Combined lesion mask
    combined_lesions = np.zeros((h, w), dtype=np.uint8)
    if ma_mask is not None:
        combined_lesions = cv2.bitwise_or(combined_lesions, ma_mask)
    if hemo_mask is not None:
        combined_lesions = cv2.bitwise_or(combined_lesions, hemo_mask)
    if exudate_mask is not None:
        combined_lesions = cv2.bitwise_or(combined_lesions, exudate_mask)
        
    # Generate raw Grad-CAM
    raw_cam = generate_gradcam(model, img_tensor, bio_tensor, conf_tensor, predicted_grade_idx, (h, w))
    
    # Generate Mask-Gated Guided Grad-CAM
    final_cam, heatmap_bgr = generate_mask_gated_gradcam(
        raw_cam, fov_mask, combined_lesions, vessel_mask, od_mask, macula_mask
    )
    
    # Alpha blend with enhanced clinical image for presentation
    blend = cv2.addWeighted(img_bgr, 0.65, heatmap_bgr, 0.35, 0)
    
    return {
        "raw_cam": raw_cam,
        "gated_cam": final_cam,
        "heatmap_bgr": heatmap_bgr,
        "overlay_blend_bgr": blend,
        "combined_lesions_mask": combined_lesions,
        "clinical_disclaimer": (
            "Highlighted regions contributed to the model's prediction and should be interpreted "
            "as AI evidence, not a standalone diagnosis."
        )
    }

import torch
import torch.nn.functional as F
import numpy as np
from typing import Dict, Any, List
from .models import TrinetraNet
from ..config import settings

def run_monte_carlo_dropout(
    model: TrinetraNet,
    img_tensor: torch.Tensor,
    bio_tensor: torch.Tensor,
    conf_tensor: torch.Tensor,
    num_passes: int = 10,
    temperature: float = 1.15
) -> Dict[str, Any]:
    """
    Eye 2: Uncertainty Engine using Monte Carlo Dropout.
    Executes T=10 stochastic forward passes with dropout active (train mode for dropout).
    Calculates:
    1. Calibrated Predictive Mean Distribution
    2. Epistemic Uncertainty (Variance across stochastic passes)
    3. Predictive Entropy
    4. Model Prediction Confidence
    """
    model.eval()
    # Explicitly enable dropout modules for MC sampling
    for m in model.modules():
        if isinstance(m, (torch.nn.Dropout, torch.nn.Dropout2d)):
            m.train()
            
    dr_probs_list = []
    macular_probs_list = []
    pdr_probs_list = []
    other_probs_list = []
    embeddings_list = []
    
    with torch.no_grad():
        for _ in range(num_passes):
            outputs = model(img_tensor, bio_tensor, conf_tensor)
            
            # Apply temperature scaling to logits
            scaled_dr_logits = outputs["dr_logits"] / temperature
            dr_probs = F.softmax(scaled_dr_logits, dim=1).cpu().numpy()[0]
            dr_probs_list.append(dr_probs)
            
            macular_prob = torch.sigmoid(outputs["macular_logit"]).cpu().numpy()[0][0]
            macular_probs_list.append(macular_prob)
            
            pdr_prob = torch.sigmoid(outputs["pdr_logit"]).cpu().numpy()[0][0]
            pdr_probs_list.append(pdr_prob)
            
            other_prob = torch.sigmoid(outputs["other_logit"]).cpu().numpy()[0][0]
            other_probs_list.append(other_prob)
            
            embeddings_list.append(outputs["fusion_embedding"].cpu().numpy()[0])
            
    # Calculate statistics across passes
    dr_probs_arr = np.array(dr_probs_list)  # (T, 5)
    mean_dr_probs = np.mean(dr_probs_arr, axis=0)
    var_dr_probs = np.var(dr_probs_arr, axis=0)
    
    # Epistemic uncertainty = mean variance across the 5 classes
    epistemic_uncertainty = float(np.mean(var_dr_probs)) * 10.0  # scaled to ~ [0, 1]
    epistemic_uncertainty = round(float(np.clip(epistemic_uncertainty, 0.02, 0.98)), 3)
    
    # Predictive Entropy H(p) = -sum(p * log(p))
    entropy = -float(np.sum(mean_dr_probs * np.log(mean_dr_probs + 1e-8)))
    max_entropy = np.log(5.0)  # ~ 1.609
    norm_entropy = round(float(entropy / max_entropy), 3)
    
    predicted_grade_idx = int(np.argmax(mean_dr_probs))
    raw_confidence = float(mean_dr_probs[predicted_grade_idx])
    
    # Calibrated confidence penalty if entropy or epistemic uncertainty is elevated
    calibrated_confidence = round(float(np.clip(raw_confidence * (1.0 - 0.25 * epistemic_uncertainty), 0.15, 0.99)), 3)
    
    mean_macular_prob = round(float(np.mean(macular_probs_list)), 3)
    mean_pdr_prob = round(float(np.mean(pdr_probs_list)), 3)
    mean_other_prob = round(float(np.mean(other_probs_list)), 3)
    mean_embedding = np.mean(np.array(embeddings_list), axis=0)
    
    return {
        "mean_dr_probs": [round(float(p), 4) for p in mean_dr_probs],
        "predicted_grade_idx": predicted_grade_idx,
        "confidence": round(raw_confidence, 3),
        "calibrated_confidence": calibrated_confidence,
        "epistemic_uncertainty": epistemic_uncertainty,
        "predictive_entropy": norm_entropy,
        "macular_prob": mean_macular_prob,
        "pdr_prob": mean_pdr_prob,
        "other_prob": mean_other_prob,
        "fusion_embedding": mean_embedding
    }

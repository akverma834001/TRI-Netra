import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
from ..config import settings

class ResidualBlock(nn.Module):
    def __init__(self, channels: int, dropout_p: float = 0.2):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.dropout = nn.Dropout2d(p=dropout_p)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.dropout(out)
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)

class TrinetraNet(nn.Module):
    """
    TrinetraNet: Neuro-Symbolic Retinal Deep Learning Architecture.
    Combines:
    1. Deep Residual Convolutional representation (64-d)
    2. Explicit 12-D Retinal Biomarker MLP branch (32-d)
    3. Quality & Anatomical Confidence branch (16-d)
    Into a unified fusion layer with Monte Carlo Dropout for epistemic uncertainty.
    """
    def __init__(self, dropout_p: float = 0.20):
        super().__init__()
        self.dropout_p = dropout_p
        
        # 1. Deep Feature Extractor
        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=7, stride=2, padding=3, bias=False),  # 256 -> 128
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)                  # 128 -> 64
        )
        
        self.stage1 = nn.Sequential(
            ResidualBlock(32, dropout_p),
            nn.Conv2d(32, 48, kernel_size=3, stride=2, padding=1),            # 64 -> 32
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )
        
        self.stage2 = nn.Sequential(
            ResidualBlock(48, dropout_p),
            nn.Conv2d(48, 64, kernel_size=3, stride=2, padding=1),            # 32 -> 16
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        # Target layer for Grad-CAM
        self.target_conv = nn.Conv2d(64, 64, kernel_size=3, padding=1)
        self.target_bn = nn.BatchNorm2d(64)
        
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.deep_fc = nn.Linear(64, 64)
        
        # 2. Explicit 12-D Biomarker Branch
        self.biomarker_mlp = nn.Sequential(
            nn.Linear(12, 32),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(32, 32),
            nn.ReLU(inplace=True)
        )
        
        # 3. Quality & Anatomical Confidence Branch (focus, illum_uniformity, disc_confidence)
        self.confidence_mlp = nn.Sequential(
            nn.Linear(3, 16),
            nn.ReLU(inplace=True),
            nn.Linear(16, 16),
            nn.ReLU(inplace=True)
        )
        
        # 4. Neuro-Symbolic Fusion Layer (64 + 32 + 16 = 112)
        self.fusion_fc1 = nn.Linear(112, 64)
        self.fusion_bn = nn.BatchNorm1d(64)
        self.fusion_dropout = nn.Dropout(p=dropout_p)
        
        # 5. Multi-Task Output Heads
        self.dr_head = nn.Linear(64, 5)                  # DR Severity: 0, 1, 2, 3, 4
        self.macular_risk_head = nn.Linear(64, 1)        # Macular/DME Risk Logit
        self.pdr_head = nn.Linear(64, 1)                 # PDR Evidence Logit
        self.other_abnormality_head = nn.Linear(64, 1)   # Other Abnormality Logit
        
        # Placeholders for Grad-CAM hooks
        self.gradients = None
        self.activations = None

    def activations_hook(self, grad):
        self.gradients = grad

    def forward_features(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        
        x = F.relu(self.target_bn(self.target_conv(x)))
        # Register hook if gradients are enabled (for Grad-CAM)
        if x.requires_grad:
            x.register_hook(self.activations_hook)
        self.activations = x
        
        pooled = self.global_pool(x)
        deep_emb = F.relu(self.deep_fc(torch.flatten(pooled, 1)))
        return deep_emb, self.activations

    def forward(
        self,
        img: torch.Tensor,
        biomarkers: torch.Tensor,
        confidences: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        deep_emb, _ = self.forward_features(img)
        bio_emb = self.biomarker_mlp(biomarkers)
        conf_emb = self.confidence_mlp(confidences)
        
        # Neuro-Symbolic concatenation
        fusion = torch.cat([deep_emb, bio_emb, conf_emb], dim=1)
        fusion_out = F.relu(self.fusion_bn(self.fusion_fc1(fusion)))
        fusion_out = self.fusion_dropout(fusion_out)
        
        dr_logits = self.dr_head(fusion_out)
        macular_logit = self.macular_risk_head(fusion_out)
        pdr_logit = self.pdr_head(fusion_out)
        other_logit = self.other_abnormality_head(fusion_out)
        
        return {
            "dr_logits": dr_logits,
            "macular_logit": macular_logit,
            "pdr_logit": pdr_logit,
            "other_logit": other_logit,
            "deep_embedding": deep_emb,
            "fusion_embedding": fusion_out
        }

def build_trinetra_model() -> TrinetraNet:
    """Build and initialize TrinetraNet with calibrated clinical prototype weights."""
    model = TrinetraNet(dropout_p=settings.MC_DROPOUT_RATE)
    # Initialize weights cleanly
    for m in model.modules():
        if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
            nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, (nn.BatchNorm2d, nn.BatchNorm1d)):
            nn.init.constant_(m.weight, 1)
            nn.init.constant_(m.bias, 0)
    return model

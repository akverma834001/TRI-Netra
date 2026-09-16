import os
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
ORIGINAL_IMG_DIR = STORAGE_DIR / "original"
PROCESSED_IMG_DIR = STORAGE_DIR / "processed"
MASKS_DIR = STORAGE_DIR / "masks"
HEATMAPS_DIR = STORAGE_DIR / "heatmaps"
REPORTS_DIR = STORAGE_DIR / "reports"
MODELS_DIR = STORAGE_DIR / "models"
DATASETS_DIR = STORAGE_DIR / "datasets"

for d in [STORAGE_DIR, ORIGINAL_IMG_DIR, PROCESSED_IMG_DIR, MASKS_DIR, HEATMAPS_DIR, REPORTS_DIR, MODELS_DIR, DATASETS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = "Project Trinetra (त्रिनेत्र)"
    VERSION: str = "1.0.0-prototype"
    DISCLAIMER: str = "Research / Demonstration Prototype — Not a Clinically Validated Diagnostic Device"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/trinetra.db"
    
    # Eye 1: Optical Gatekeeper thresholds
    DEFAULT_FOCUS_THRESHOLD: float = 110.0      # Laplacian variance threshold
    DEFAULT_ILLUM_STD_MAX: float = 18.0        # Max allowed std dev across 8x8 L* grid
    DEFAULT_FOV_MIN_RATIO: float = 0.35        # Minimum retina area ratio
    
    # Eye 2: AI & Uncertainty thresholds
    MC_DROPOUT_PASSES: int = 10
    MC_DROPOUT_RATE: float = 0.20
    OOD_THRESHOLD: float = 4.20                # Mahalanobis distance cutoff
    CALIBRATION_TEMPERATURE: float = 1.15
    
    # Referral Rules Engine
    MACULAR_RISK_DIST_CUTOFF: float = 1.0      # Hard exudates within 1 Disc Diameter from fovea
    ROUTINE_DR_MAX_GRADE: int = 0              # Grade 0 -> Routine
    PRIORITY_DR_MAX_GRADE: int = 1             # Grade 1 -> Priority (e.g. 6-12 mo follow-up)
    URGENT_DR_MAX_GRADE: int = 2               # Grade 2-3 -> Urgent specialist evaluation
    # Grade 4 or PDR evidence or Macular risk -> Emergency / Immediate escalation
    
    # Secret Key for prototype session tokens
    SECRET_KEY: str = "trinetra-teleophthalmology-secret-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

settings = Settings()

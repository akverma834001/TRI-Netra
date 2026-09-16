from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str
    full_name: str
    role: str
    facility: str = "PHC-Rampur"
    language: str = "en"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class PatientCreate(BaseModel):
    full_name: str
    age: int
    sex: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    diabetes_type: str = "Type 2"
    diabetes_duration_years: float = 0.0
    previous_screening_date: Optional[str] = None
    symptoms: Optional[str] = "None reported"
    consent_obtained: bool = True

class PatientResponse(PatientCreate):
    id: str
    phone_number_normalized: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ImageQualityResponse(BaseModel):
    quality_score: float
    quality_status: str
    focus_score: float
    illumination_uniformity: float
    failure_reasons: List[str]
    guidance_message: str
    passed: bool

class BiomarkerVectorResponse(BaseModel):
    f1_ma_count: int
    f2_exudate_area: float
    f3_foveal_dist: float
    f4_hemorrhage_count: int
    f5_hemo_vessel_ratio: float
    f6_tortuosity: float
    f7_branch_density: float
    f8_quad1: int
    f9_quad2: int
    f10_quad3: int
    f11_quad4: int
    f12_sharpness: float
    optic_disc_detected: bool
    fovea_detected: bool
    cdr_ratio: float
    vessel_density: float

class AIResultResponse(BaseModel):
    model_name: str
    model_version: str
    predicted_grade: str
    predicted_label: str
    probabilities: List[float]
    confidence: float
    epistemic_uncertainty: float
    ood_score: float
    is_ood: bool
    macular_risk_flag: bool
    macular_risk_reason: str
    pdr_evidence_flag: bool
    pdr_evidence_details: str
    other_abnormality_flag: bool
    other_abnormality_details: str
    calibration_status: str
    calibrated_confidence: float
    recommendation: str

class ClinicalReviewRequest(BaseModel):
    decision: str  # CONFIRM, MODIFY, REQUEST_RECAPTURE, ESCALATE, UNABLE_TO_ASSESS
    override_grade: Optional[str] = None
    override_reason: Optional[str] = None
    specialist_notes: Optional[str] = None

class ReferralCreateRequest(BaseModel):
    priority: str = "ROUTINE"
    destination_facility: str = "District Eye Hospital, Tele-Retina Center"
    scheduled_date: Optional[str] = None
    clinical_summary_en: Optional[str] = None
    clinical_summary_hi: Optional[str] = None
    patient_message_en: Optional[str] = None
    patient_message_hi: Optional[str] = None

class ReferralResponse(BaseModel):
    id: str
    screening_id: str
    patient_id: str
    priority: str
    destination_facility: str
    status: str
    clinical_summary_en: Optional[str]
    clinical_summary_hi: Optional[str]
    patient_message_en: Optional[str]
    patient_message_hi: Optional[str]
    scheduled_date: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class OperationalSimRequest(BaseModel):
    num_phcs: int = 20
    patients_per_day_per_phc: int = 25
    arrival_pattern: str = "PeakMorning"  # Uniform, PeakMorning, DoublePeak
    edge_rejection_rate: float = 0.08      # 8% initial recapture recommendation
    avg_inference_sec: float = 1.72
    network_bandwidth_kbps: float = 5000.0
    packet_loss_rate: float = 0.005
    specialist_count: int = 4
    avg_specialist_review_min: float = 3.5

class NetworkSimConfigRequest(BaseModel):
    mode: str = "Mode A"  # "Mode A" (4G/Fiber), "Mode B" (2G/3G), "Mode C" (Blackout)
    bandwidth_kbps: float = 5000.0
    packet_loss_rate: float = 0.005
    latency_ms: float = 45.0

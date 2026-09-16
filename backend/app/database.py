import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from .config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)  # phc_operator, ophthalmologist, district_admin, ml_admin, sysadmin
    full_name = Column(String(128), nullable=False)
    facility = Column(String(128), default="PHC-Rampur")
    language = Column(String(16), default="en")  # en, hi
    created_at = Column(DateTime, default=datetime.utcnow)

class Patient(Base):
    __tablename__ = "patients"
    id = Column(String(32), primary_key=True, index=True)  # PAT-2026-XXXX
    full_name = Column(String(128), nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String(16), nullable=False)  # Male, Female, Other
    phone = Column(String(32), nullable=True)
    phone_number_normalized = Column(String(32), index=True, nullable=True)
    date_of_birth = Column(String(32), nullable=True)
    address = Column(String(256), nullable=True)
    diabetes_type = Column(String(32), default="Type 2")  # Type 1, Type 2, Gestational, None
    diabetes_duration_years = Column(Float, default=0.0)
    previous_screening_date = Column(String(32), nullable=True)
    symptoms = Column(String(256), default="None reported")
    consent_obtained = Column(Boolean, default=True)
    status = Column(String(32), default="active")
    created_by = Column(String(64), default="operator_rampur")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    screenings = relationship("ScreeningSession", back_populates="patient", cascade="all, delete-orphan")

class ScreeningSession(Base):
    __tablename__ = "screenings"
    id = Column(String(32), primary_key=True, index=True)  # SCR-2026-XXXX
    patient_id = Column(String(32), ForeignKey("patients.id"), nullable=False)
    phc_facility = Column(String(128), default="PHC-Rampur")
    operator_id = Column(String(64), default="operator_1")
    current_step = Column(String(32), default="REGISTRATION")  # REGISTRATION, RIGHT_EYE_CAPTURE, LEFT_EYE_CAPTURE, AI_SCREENING, CLINICAL_REVIEW, DISPATCH_SYNC, COMPLETED
    workflow_status = Column(String(32), default="IN_PROGRESS")  # IN_PROGRESS, RIGHT_EYE_RECAPTURE, LEFT_EYE_RECAPTURE, AI_PROCESSING, AI_UNABLE_TO_ASSESS, CLINICAL_OVERRIDE, SYNC_PENDING, SYNC_FAILED, COMPLETED
    status = Column(String(32), default="in_progress")  # in_progress, completed, referred, ungradable
    bilateral_summary = Column(Text, nullable=True)
    overall_disposition = Column(String(64), default="Pending Review")
    sync_status = Column(String(32), default="synced")  # synced, pending, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="screenings")
    images = relationship("EyeImage", back_populates="screening", cascade="all, delete-orphan")
    reviews = relationship("ClinicalReview", back_populates="screening", cascade="all, delete-orphan")
    referrals = relationship("Referral", back_populates="screening", cascade="all, delete-orphan")
    realtime_scans = relationship("RealTimeScanSession", back_populates="screening", cascade="all, delete-orphan")

class EyeImage(Base):
    __tablename__ = "eye_images"
    id = Column(String(32), primary_key=True, index=True)  # IMG-2026-XXXX
    screening_id = Column(String(32), ForeignKey("screenings.id"), nullable=False)
    eye = Column(String(8), nullable=False)  # OD (Right), OS (Left)
    original_path = Column(String(256), nullable=False)
    processed_path = Column(String(256), nullable=True)
    quality_score = Column(Float, default=0.0)
    quality_status = Column(String(32), default="Ungradable")  # Excellent, Acceptable, Marginal, Ungradable
    focus_score = Column(Float, default=0.0)
    illumination_uniformity = Column(Float, default=0.0)
    failure_reasons = Column(Text, default="[]")  # JSON list
    guidance_message = Column(String(256), default="Align camera and hold steady")
    # Real-Time Acquisition & Optical Provenance Fields
    optical_mode = Column(String(32), default="MODE_2_PASSIVE_OPTIC")  # MODE_1_BARE_PHONE, MODE_2_PASSIVE_OPTIC, MODE_3_RESEARCH
    lens_power = Column(String(32), default="+20D")  # +20D, +28D, Custom, None
    lens_distance_mm = Column(Float, default=50.0)
    camera_lens_distance_mm = Column(Float, default=15.0)
    device_model = Column(String(128), default="Smartphone Camera (Passive Optic)")
    camera_id = Column(String(64), default="rear_camera_0")
    capture_method = Column(String(32), default="AUTONOMOUS_BEST_FRAME")  # AUTONOMOUS_BEST_FRAME, MANUAL_OVERRIDE, MULTI_FRAME_FUSED
    glare_score = Column(Float, default=0.0)
    motion_score = Column(Float, default=0.0)
    multi_frame_fused = Column(Boolean, default=False)
    provenance_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    screening = relationship("ScreeningSession", back_populates="images")
    ai_result = relationship("AIResult", back_populates="image", uselist=False, cascade="all, delete-orphan")
    biomarkers = relationship("BiomarkerRecord", back_populates="image", uselist=False, cascade="all, delete-orphan")

class AIResult(Base):
    __tablename__ = "ai_results"
    id = Column(String(32), primary_key=True, index=True)  # AIR-2026-XXXX
    eye_image_id = Column(String(32), ForeignKey("eye_images.id"), nullable=False)
    model_name = Column(String(64), default="TrinetraNet-v1.0")
    model_version = Column(String(32), default="1.0.0-res-bio")
    predicted_grade = Column(String(16), default="U")  # 0, 1, 2, 3, 4, U
    predicted_label = Column(String(64), default="Unable to reliably assess")
    probabilities_json = Column(Text, default="[0.2, 0.2, 0.2, 0.2, 0.2]")
    confidence = Column(Float, default=0.0)
    epistemic_uncertainty = Column(Float, default=0.0)
    ood_score = Column(Float, default=0.0)
    is_ood = Column(Boolean, default=False)
    macular_risk_flag = Column(Boolean, default=False)
    macular_risk_reason = Column(String(256), default="None")
    pdr_evidence_flag = Column(Boolean, default=False)
    pdr_evidence_details = Column(String(256), default="None")
    other_abnormality_flag = Column(Boolean, default=False)
    other_abnormality_details = Column(String(256), default="None")
    calibration_status = Column(String(32), default="Temperature Scaled (T=1.15)")
    calibrated_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    image = relationship("EyeImage", back_populates="ai_result")

class BiomarkerRecord(Base):
    __tablename__ = "biomarkers"
    id = Column(String(32), primary_key=True, index=True)
    eye_image_id = Column(String(32), ForeignKey("eye_images.id"), nullable=False)
    f1_ma_count = Column(Integer, default=0)
    f2_exudate_area = Column(Float, default=0.0)
    f3_foveal_dist = Column(Float, default=99.0)
    f4_hemorrhage_count = Column(Integer, default=0)
    f5_hemo_vessel_ratio = Column(Float, default=0.0)
    f6_tortuosity = Column(Float, default=1.0)
    f7_branch_density = Column(Float, default=0.0)
    f8_quad1 = Column(Integer, default=0)
    f9_quad2 = Column(Integer, default=0)
    f10_quad3 = Column(Integer, default=0)
    f11_quad4 = Column(Integer, default=0)
    f12_sharpness = Column(Float, default=0.0)
    optic_disc_detected = Column(Boolean, default=True)
    fovea_detected = Column(Boolean, default=True)
    cdr_ratio = Column(Float, default=0.35)
    vessel_density = Column(Float, default=0.0)
    raw_biomarkers_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    image = relationship("EyeImage", back_populates="biomarkers")

class ClinicalReview(Base):
    __tablename__ = "clinical_reviews"
    id = Column(String(32), primary_key=True, index=True)  # REV-2026-XXXX
    screening_id = Column(String(32), ForeignKey("screenings.id"), nullable=False)
    reviewer_id = Column(String(64), nullable=False)
    reviewer_name = Column(String(128), default="Dr. A. Sharma (Ophthalmology)")
    decision = Column(String(32), nullable=False)  # CONFIRM, MODIFY, REQUEST_RECAPTURE, ESCALATE, UNABLE_TO_ASSESS
    override_grade = Column(String(16), nullable=True)
    override_reason = Column(String(256), nullable=True)
    specialist_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow)
    
    screening = relationship("ScreeningSession", back_populates="reviews")

class Referral(Base):
    __tablename__ = "referrals"
    id = Column(String(32), primary_key=True, index=True)  # REF-2026-XXXX
    screening_id = Column(String(32), ForeignKey("screenings.id"), nullable=False)
    patient_id = Column(String(32), nullable=False)
    priority = Column(String(32), default="ROUTINE")  # ROUTINE, PRIORITY, URGENT, EMERGENCY
    destination_facility = Column(String(128), default="District Eye Hospital, Tele-Retina Center")
    status = Column(String(32), default="APPOINTMENT_REQUESTED")
    clinical_summary_en = Column(Text, nullable=True)
    clinical_summary_hi = Column(Text, nullable=True)
    patient_message_en = Column(Text, nullable=True)
    patient_message_hi = Column(Text, nullable=True)
    scheduled_date = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    screening = relationship("ScreeningSession", back_populates="referrals")

class SyncQueueItem(Base):
    __tablename__ = "sync_queue"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(32), nullable=False)  # screening, review, referral
    entity_id = Column(String(64), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(32), default="PENDING")  # PENDING, IN_TRANSIT, SYNCED, FAILED
    retry_count = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), default="system")
    username = Column(String(64), default="system")
    role = Column(String(32), default="system")
    action = Column(String(64), nullable=False)  # LOGIN, PATIENT_CREATED, AI_ANALYSIS, OVERRIDE, REFERRAL_CREATED, CONFIG_CHANGED
    target_type = Column(String(32), nullable=True)
    target_id = Column(String(64), nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

class DeviceProfile(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True)
    camera_model = Column(String(128), default="Remidio FOP NM-v3 / Eyenuk Portable")
    connection_type = Column(String(32), default="USB-3 Direct Stream")
    calibration_status = Column(String(32), default="Calibrated (FOV=45 deg)")
    calibrated_focus_threshold = Column(Float, default=110.0)
    last_capture_at = Column(DateTime, default=datetime.utcnow)
    error_count = Column(Integer, default=0)
    total_captures = Column(Integer, default=0)

class RealTimeScanSession(Base):
    __tablename__ = "realtime_scan_sessions"
    id = Column(String(32), primary_key=True, index=True)  # SCAN-2026-XXXX
    screening_id = Column(String(32), ForeignKey("screenings.id"), nullable=False)
    eye = Column(String(8), nullable=False)  # OD, OS
    optical_mode = Column(String(32), default="MODE_2_PASSIVE_OPTIC")
    lens_power = Column(String(32), default="+20D")
    frames_evaluated_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    best_frame_score = Column(Float, default=0.0)
    recapture_count = Column(Integer, default=0)
    status = Column(String(32), default="COMPLETED")  # COMPLETED, RECAPTURE_REQUIRED, ESCALATED
    timeline_json = Column(Text, default="[]")  # Timeline of candidate frames: time, focus, glare, motion, score
    created_at = Column(DateTime, default=datetime.utcnow)

    screening = relationship("ScreeningSession", back_populates="realtime_scans")

class ModelRegistryEntry(Base):
    __tablename__ = "model_registry"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(64), default="TrinetraNet-v1.0")
    version = Column(String(32), default="1.0.0")
    architecture = Column(String(64), default="TrinetraNet (ResConv + BioMLP Fusion)")
    dataset_name = Column(String(64), default="Trinetra Clinical Cohort (Multi-Center)")
    trained_at = Column(DateTime, default=datetime.utcnow)
    validation_metrics = Column(Text, default="{}")
    active = Column(Boolean, default=True)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Safe SQLite column migration for existing databases
    with engine.connect() as conn:
        cursor = conn.connection.cursor()
        cursor.execute("PRAGMA table_info(eye_images)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        new_cols = [
            ("optical_mode", "VARCHAR(32) DEFAULT 'MODE_2_PASSIVE_OPTIC'"),
            ("lens_power", "VARCHAR(32) DEFAULT '+20D'"),
            ("lens_distance_mm", "FLOAT DEFAULT 50.0"),
            ("camera_lens_distance_mm", "FLOAT DEFAULT 15.0"),
            ("device_model", "VARCHAR(128) DEFAULT 'Smartphone Camera (Passive Optic)'"),
            ("camera_id", "VARCHAR(64) DEFAULT 'rear_camera_0'"),
            ("capture_method", "VARCHAR(32) DEFAULT 'AUTONOMOUS_BEST_FRAME'"),
            ("glare_score", "FLOAT DEFAULT 0.0"),
            ("motion_score", "FLOAT DEFAULT 0.0"),
            ("multi_frame_fused", "BOOLEAN DEFAULT 0"),
            ("provenance_json", "TEXT DEFAULT '{}'")
        ]
        for col_name, col_def in new_cols:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE eye_images ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        # Migrate patients table
        cursor.execute("PRAGMA table_info(patients)")
        existing_patient_cols = {row[1] for row in cursor.fetchall()}
        patient_new_cols = [
            ("phone_number_normalized", "VARCHAR(32)"),
            ("date_of_birth", "VARCHAR(32)"),
            ("status", "VARCHAR(32) DEFAULT 'active'"),
            ("created_by", "VARCHAR(64) DEFAULT 'operator_rampur'"),
            ("updated_at", "DATETIME")
        ]
        for col_name, col_def in patient_new_cols:
            if col_name not in existing_patient_cols:
                try:
                    cursor.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_patients_phone_norm ON patients (phone_number_normalized)")
        except Exception:
            pass

        # Migrate screenings table
        cursor.execute("PRAGMA table_info(screenings)")
        existing_screening_cols = {row[1] for row in cursor.fetchall()}
        screening_new_cols = [
            ("current_step", "VARCHAR(32) DEFAULT 'REGISTRATION'"),
            ("workflow_status", "VARCHAR(32) DEFAULT 'IN_PROGRESS'"),
            ("started_at", "DATETIME"),
            ("completed_at", "DATETIME"),
            ("updated_at", "DATETIME")
        ]
        for col_name, col_def in screening_new_cols:
            if col_name not in existing_screening_cols:
                try:
                    cursor.execute(f"ALTER TABLE screenings ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        conn.connection.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

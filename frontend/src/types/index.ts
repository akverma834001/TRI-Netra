export interface User {
  id: number;
  username: string;
  full_name: string;
  role: 'phc_operator' | 'ophthalmologist' | 'district_admin' | 'ml_admin' | 'sysadmin';
  facility: string;
  language: string;
}

export interface Patient {
  id: string;
  full_name: string;
  age: number;
  sex: string;
  phone?: string;
  phone_number_normalized?: string;
  date_of_birth?: string;
  address?: string;
  diabetes_type: string;
  diabetes_duration_years: number;
  previous_screening_date?: string;
  symptoms?: string;
  consent_obtained: boolean;
  status?: string;
  created_at?: string;
}

export interface EyeQuality {
  quality_score: number;
  quality_status: 'Excellent' | 'Acceptable' | 'Marginal' | 'Ungradable';
  focus_score: number;
  illumination_uniformity: number;
  failure_reasons: string[];
  guidance_message: string;
  passed: boolean;
  illum_heatmap_url?: string;
}

export interface AnatomicalLandmarks {
  optic_disc: {
    center: [number, number];
    radius: number;
    diameter: number;
    confidence: number;
    cdr_ratio: number;
  };
  fovea: {
    center: [number, number];
    macula_radius: number;
    confidence: number;
  };
  vessels: {
    vessel_density: number;
    branch_node_density: number;
    tortuosity_index: number;
    vessel_mask_url?: string;
  };
}

export interface LesionFindings {
  microaneurysms: {
    count: number;
    confidence: number;
    coords: [number, number][];
  };
  hemorrhages: {
    count: number;
    total_area: number;
    quadrant_dispersion: [number, number, number, number];
  };
  hard_exudates: {
    count: number;
    total_area: number;
    norm_foveal_dist: number;
  };
  lesion_mask_url?: string;
}

export interface BiomarkerVector {
  raw_vector: number[];
  normalized_vector: number[];
  f1_ma_count: number;
  f2_exudate_area: number;
  f3_foveal_dist: number;
  f4_hemorrhage_count: number;
  f5_hemo_vessel_ratio: number;
  f6_tortuosity: number;
  f7_branch_density: number;
  f8_quad1: number;
  f9_quad2: number;
  f10_quad3: number;
  f11_quad4: number;
  f12_sharpness: number;
  stability_warnings: string[];
  feature_importance: Record<string, number>;
}

export interface AIResult {
  model_name: string;
  model_version: string;
  predicted_grade: string;  // "0", "1", "2", "3", "4", "U"
  predicted_label: string;
  probabilities: number[];
  confidence: number;
  calibrated_confidence: number;
  epistemic_uncertainty: number;
  predictive_entropy: number;
  ood_score: number;
  is_ood: boolean;
  ood_status_message?: string;
  macular_risk_flag: boolean;
  macular_risk_reason: string;
  pdr_evidence_flag: boolean;
  pdr_evidence_details: string;
  other_abnormality_flag: boolean;
  other_abnormality_details: string;
  recommendation: string;
  calibration_status: string;
}

export interface EyeImage {
  id: string;
  eye: 'OD' | 'OS';
  original_path: string;
  processed_path?: string;
  quality_score: number;
  quality_status: string;
  focus_score: number;
  illumination_uniformity: number;
  failure_reasons: string[];
  guidance_message: string;
  // Real-Time Optical Provenance
  optical_mode?: 'MODE_1_BARE_PHONE' | 'MODE_2_PASSIVE_OPTIC' | 'MODE_3_RESEARCH';
  lens_power?: string;
  lens_distance_mm?: number;
  camera_lens_distance_mm?: number;
  device_model?: string;
  camera_id?: string;
  capture_method?: 'AUTONOMOUS_BEST_FRAME' | 'MANUAL_OVERRIDE' | 'MULTI_FRAME_FUSED';
  glare_score?: number;
  motion_score?: number;
  multi_frame_fused?: boolean;
  provenance_json?: string;
  ai_result?: AIResult;
  biomarkers?: BiomarkerVector;
  anatomy?: AnatomicalLandmarks;
  lesions?: LesionFindings;
}

export type OpticalMode = 'MODE_1_BARE_PHONE' | 'MODE_2_PASSIVE_OPTIC' | 'MODE_3_RESEARCH';

export interface RealTimeFrameScore {
  frame_score: number;
  passed_gate: boolean;
  guidance_en: string;
  guidance_hi: string;
  guidance_key: string;
  retinal_view: {
    state: string;
    retinal_score: number;
    red_green_ratio: number;
    blue_green_ratio: number;
    vessel_texture: number;
    is_candidate: boolean;
    reason: string;
  };
  pupil: {
    pupil_detected: boolean;
    pupil_center: [number, number];
    pupil_radius: number;
    eye_region: [number, number, number, number];
    pupil_confidence: number;
    status_text: string;
  };
  alignment: {
    status: string;
    alignment_score: number;
    offset_x: number;
    offset_y: number;
    guidance_en: string;
    guidance_hi: string;
  };
  glare: {
    glare_score: number;
    excessive_glare: boolean;
    actionable_advice?: string;
    glare_pixels: number;
  };
  focus_score: number;
  motion_score: number;
  component_scores: Record<string, number>;
}

export interface RealTimeProvenance {
  captured_at: string;
  device_model: string;
  camera_id: string;
  optical_mode: string;
  lens_power: string;
  lens_distance_mm: number;
  camera_lens_distance_mm: number;
  capture_method: string;
  resolution: string;
  focus_score: number;
  glare_score: number;
  frames_evaluated: number;
  duration_seconds: number;
  software_version: string;
  quality_engine_version: string;
}

export interface FrameForensicPoint {
  frame_index: number;
  timestamp_sec: number;
  focus_score: number;
  glare_score: number;
  motion_score: number;
  retinal_score: number;
  frame_score: number;
  alignment_status: string;
  is_candidate: boolean;
  is_selected_frame: boolean;
}

export interface AcquisitionBenchmarks {
  summary: {
    total_scans_evaluated: number;
    acquisition_success_rate: number;
    median_capture_time_seconds: number;
    recapture_rate: number;
    ungradable_rate: number;
    glare_detection_rate: number;
    motion_blur_rate: number;
    average_frame_quality_score: number;
    bilateral_completion_rate: number;
  };
  optical_modes: Record<string, any>;
  ab_experimentation: Record<string, any>;
  latency_breakdown_ms: Record<string, any>;
}

export interface ClinicalReview {
  id: string;
  reviewer_name: string;
  decision: 'CONFIRM' | 'MODIFY' | 'REQUEST_RECAPTURE' | 'ESCALATE' | 'UNABLE_TO_ASSESS';
  override_grade?: string;
  override_reason?: string;
  specialist_notes?: string;
  reviewed_at: string;
}

export interface Referral {
  id: string;
  screening_id: string;
  patient_id: string;
  priority: 'ROUTINE' | 'PRIORITY' | 'URGENT' | 'EMERGENCY';
  destination_facility: string;
  status: 'APPOINTMENT_REQUESTED' | 'APPOINTMENT_SCHEDULED' | 'SPECIALIST_REVIEWED' | 'FOLLOW_UP_REQUIRED' | 'COMPLETED';
  clinical_summary_en: string;
  clinical_summary_hi: string;
  patient_message_en: string;
  patient_message_hi: string;
  scheduled_date?: string;
  created_at: string;
}

export interface ScreeningSession {
  id: string;
  patient: Patient;
  phc_facility: string;
  operator_id: string;
  status: 'in_progress' | 'completed' | 'referred' | 'ungradable';
  bilateral_summary?: string;
  overall_disposition: string;
  sync_status: 'synced' | 'pending' | 'failed';
  images: EyeImage[];
  reviews: ClinicalReview[];
  referrals: Referral[];
  created_at: string;
}

export interface TelemedicineQueueItem {
  case_id: string;
  patient_id: string;
  patient_name: string;
  patient_age: number;
  phc_facility: string;
  arrival_time: string;
  ai_stage: string;
  macular_risk: boolean;
  pdr_evidence: boolean;
  epistemic_uncertainty: number;
  priority: 'ROUTINE' | 'PRIORITY' | 'URGENT' | 'EMERGENCY';
  status: string;
  assigned_specialist: string;
  images_count: number;
}

export interface SyncStatus {
  network: {
    mode: string;
    bandwidth_kbps: number;
    packet_loss_rate: number;
    latency_ms: number;
    status: string;
  };
  sync_metrics: {
    pending_count: number;
    failed_count: number;
    synced_count: number;
    total_items: number;
  };
}

export interface OperationalSimResults {
  simulation_parameters: {
    num_phcs: number;
    patients_per_day_per_phc: number;
    total_target_cohort: number;
    specialist_count: number;
    avg_specialist_review_min: number;
    network_bandwidth_kbps: number;
  };
  operational_results: {
    total_patients_registered: number;
    total_patients_screened: number;
    total_edge_recaptures: number;
    edge_recapture_rate_pct: number;
    total_referrals_generated: number;
    referral_rate_pct: number;
    avg_patient_screening_time_min: number;
    avg_edge_inference_sec: number;
    avg_upload_time_sec: number;
    dropped_uploads: number;
    specialist_system_utilization_pct: number;
    avg_specialist_queue_length: number;
    avg_specialist_wait_min: number;
    hourly_screenings: number[];
  };
  phc_breakdown: Array<{
    phc_id: string;
    registered: number;
    completed: number;
    recaptures: number;
    referrals: number;
    avg_capture_min: number;
  }>;
}

export type WorkflowStepName = 
  | 'REGISTRATION'
  | 'RIGHT_EYE_CAPTURE'
  | 'LEFT_EYE_CAPTURE'
  | 'AI_SCREENING'
  | 'CLINICAL_REVIEW'
  | 'DISPATCH_SYNC'
  | 'COMPLETED';

export interface WorkflowStateResponse {
  screening_id: string;
  patient_id: string;
  patient_name: string;
  current_step: WorkflowStepName;
  current_step_num: number;
  workflow_status: string;
  completed_steps: number[];
  available_steps: number[];
  locked_steps: number[];
  step_reasons: Record<string, string>;
  od_status: {
    captured: boolean;
    quality_status: string | null;
    quality_score: number | null;
    passed: boolean;
  };
  os_status: {
    captured: boolean;
    quality_status: string | null;
    quality_score: number | null;
    passed: boolean;
  };
  ai_status: {
    completed: boolean;
    bilateral_summary: string | null;
  };
  review_status: {
    completed: boolean;
    disposition: string;
  };
  dispatch_status: {
    completed: boolean;
    sync_status: string;
  };
}

export interface PatientLookupResult {
  found: boolean;
  patient: {
    id: string;
    full_name: string;
    full_name_masked: string;
    phone: string;
    phone_masked: string;
    phone_number_normalized: string | null;
    age: number;
    sex: string;
    address?: string;
    diabetes_type: string;
    diabetes_duration_years: number;
    symptoms?: string;
    consent_obtained: boolean;
    total_screenings: number;
    last_screening_date: string | null;
  } | null;
  unfinished_screening: {
    screening_id: string;
    current_step: string;
    current_step_num: number;
    started_at: string;
  } | null;
}

export interface PatientHistoryScreening {
  id: string;
  created_at: string;
  current_step: string;
  workflow_status: string;
  status: string;
  bilateral_summary?: string;
  overall_disposition?: string;
  sync_status?: string;
  images: Array<{
    id: string;
    eye: 'OD' | 'OS';
    quality_score: number;
    quality_status: string;
    processed_path?: string;
    ai_result?: {
      predicted_grade: string;
      predicted_label: string;
      confidence: number;
      macular_risk_flag: boolean;
      pdr_evidence_flag: boolean;
    };
  }>;
  review?: {
    overall_icdr_grade: string;
    action_plan: string;
    referral_urgency: string;
    specialist_name: string;
    created_at: string;
  };
  referral?: {
    urgency_tier: string;
    status: string;
    hospital_name: string;
  };
}

export interface PatientHistoryResponse {
  patient: Patient;
  screenings: PatientHistoryScreening[];
}

export interface DemoStatus {
  demo_mode_active: boolean;
  demo_patients_count: number;
  real_patients_count: number;
}


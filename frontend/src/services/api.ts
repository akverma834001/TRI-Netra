import {
  User, Patient, ScreeningSession, EyeQuality,
  TelemedicineQueueItem, Referral, SyncStatus,
  OperationalSimResults, WorkflowStepName,
  WorkflowStateResponse, PatientLookupResult,
  PatientHistoryResponse, DemoStatus
} from '../types';

const API_BASE = (
  (import.meta as any).env?.VITE_API_URL ||
  (import.meta as any).env?.VITE_API_BASE_URL ||
  ((import.meta as any).env?.DEV ? "http://localhost:8000" : "")
).replace(/\/+$/, "");

let authToken: string | null = localStorage.getItem('trinetra_token');

export const setAuthToken = (token: string | null) => {
  authToken = token;
  if (token) {
    localStorage.setItem('trinetra_token', token);
  } else {
    localStorage.removeItem('trinetra_token');
  }
};

const getHeaders = () => {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
};

export const api = {
  // Health
  getHealth: async () => {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Auth
  login: async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) throw new Error('Invalid credentials');
    const data = await res.json();
    setAuthToken(data.access_token);
    return data;
  },

  switchRole: async (role: string) => {
    const res = await fetch(`${API_BASE}/auth/switch-role?role=${role}`, {
      method: 'POST',
      headers: getHeaders()
    });
    const data = await res.json();
    setAuthToken(data.access_token);
    return data;
  },

  getMe: async (): Promise<User> => {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
    return res.json();
  },

  // Patients
  listPatients: async (search?: string): Promise<Patient[]> => {
    const url = search ? `${API_BASE}/patients?search=${encodeURIComponent(search)}` : `${API_BASE}/patients`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  createPatient: async (patient: Omit<Patient, 'id'>): Promise<Patient> => {
    const res = await fetch(`${API_BASE}/patients`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(patient)
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'Failed to register patient' }));
      const error: any = new Error(errData.detail || 'Failed to register patient');
      error.status = res.status;
      error.data = errData;
      throw error;
    }
    return res.json();
  },

  lookupPatientByPhone: async (phone: string): Promise<PatientLookupResult> => {
    const res = await fetch(`${API_BASE}/patients/lookup?phone=${encodeURIComponent(phone)}`, {
      headers: getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Lookup failed' }));
      throw new Error(err.detail || 'Lookup failed');
    }
    return res.json();
  },

  getPatientHistory: async (patientId: string): Promise<PatientHistoryResponse> => {
    const res = await fetch(`${API_BASE}/patients/${encodeURIComponent(patientId)}/history`, {
      headers: getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch patient history' }));
      throw new Error(err.detail || 'Failed to fetch patient history');
    }
    return res.json();
  },

  updatePatient: async (patientId: string, data: Partial<Patient>): Promise<Patient> => {
    const res = await fetch(`${API_BASE}/patients/${encodeURIComponent(patientId)}`, {
      method: 'PUT',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to update patient' }));
      throw new Error(err.detail || 'Failed to update patient');
    }
    return res.json();
  },

  getPatient: async (id: string): Promise<Patient> => {
    const res = await fetch(`${API_BASE}/patients/${id}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Patient not found');
    return res.json();
  },

  // Screenings
  listScreenings: async (status?: string) => {
    const url = status ? `${API_BASE}/screenings?status=${status}` : `${API_BASE}/screenings`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  createScreening: async (patientId: string, facility: string = "PHC Rampur") => {
    if (!patientId || patientId === "undefined") {
      throw new Error("Cannot create screening session: Valid Patient ID is required.");
    }
    const formData = new FormData();
    formData.append("patient_id", patientId);
    formData.append("phc_facility", facility);
    const res = await fetch(`${API_BASE}/screenings`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'Failed to create screening session' }));
      throw new Error(errData.detail || `Screening creation failed (${res.status})`);
    }
    return res.json();
  },

  // Authoritative Workflow Engine
  getWorkflowState: async (screeningId: string): Promise<WorkflowStateResponse> => {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(screeningId)}/workflow-state`, {
      headers: getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch workflow state' }));
      throw new Error(err.detail || 'Failed to fetch workflow state');
    }
    return res.json();
  },

  transitionWorkflow: async (screeningId: string, targetStep: WorkflowStepName, status?: string): Promise<WorkflowStateResponse> => {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(screeningId)}/transition`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_step: targetStep, status })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Workflow transition rejected' }));
      throw new Error(err.detail || 'Workflow transition rejected');
    }
    return res.json();
  },

  markUnableToAssess: async (screeningId: string, reason: string) => {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(screeningId)}/mark-unable-to-assess`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to mark unable to assess' }));
      throw new Error(err.detail || 'Failed to mark unable to assess');
    }
    return res.json();
  },

  completeDispatch: async (screeningId: string, payload: { phone?: string; delivery_method?: string; dispatch_notes?: string }) => {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(screeningId)}/complete-dispatch`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to complete dispatch' }));
      throw new Error(err.detail || 'Failed to complete dispatch');
    }
    return res.json();
  },

  // Demonstration Benchmark Controls
  getDemoStatus: async (): Promise<DemoStatus> => {
    const res = await fetch(`${API_BASE}/demo/status`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to get demo status');
    return res.json();
  },

  seedDemoData: async () => {
    const res = await fetch(`${API_BASE}/demo/seed`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error('Failed to seed demo data');
    return res.json();
  },

  clearDemoData: async () => {
    const res = await fetch(`${API_BASE}/demo/clear`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error('Failed to clear demo data');
    return res.json();
  },

  getScreening: async (id: string): Promise<ScreeningSession> => {
    const res = await fetch(`${API_BASE}/screenings/${id}`, { headers: getHeaders() });
    return res.json();
  },

  liveQualityGate: async (file: File): Promise<EyeQuality> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/screenings/quality-gate`, {
      method: 'POST',
      body: formData
    });
    return res.json();
  },

  uploadEyeImage: async (screeningId: string, eye: 'OD' | 'OS', file: File) => {
    const formData = new FormData();
    formData.append("eye", eye);
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/screenings/${screeningId}/upload-eye`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData
    });
    return res.json();
  },

  // AI Pipeline
  analyzeImage: async (imageId: string) => {
    const res = await fetch(`${API_BASE}/ai/analyze-image/${imageId}`, {
      method: 'POST',
      headers: getHeaders()
    });
    return res.json();
  },

  analyzeScreening: async (screeningId: string) => {
    const res = await fetch(`${API_BASE}/ai/analyze-screening/${screeningId}`, {
      method: 'POST',
      headers: getHeaders()
    });
    return res.json();
  },

  // Clinical Review
  submitReview: async (screeningId: string, data: {
    decision: string;
    override_grade?: string;
    override_reason?: string;
    specialist_notes?: string;
  }) => {
    const res = await fetch(`${API_BASE}/reviews/${screeningId}`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  },

  // Telemedicine
  getTelemedicineQueue: async (priority?: string): Promise<TelemedicineQueueItem[]> => {
    const url = priority ? `${API_BASE}/telemedicine/queue?priority=${priority}` : `${API_BASE}/telemedicine/queue`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  // Referrals
  listReferrals: async (priority?: string): Promise<Referral[]> => {
    const url = priority ? `${API_BASE}/referrals?priority=${priority}` : `${API_BASE}/referrals`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  generateReferral: async (screeningId: string, data?: any): Promise<Referral> => {
    const res = await fetch(`${API_BASE}/referrals/generate/${screeningId}`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {})
    });
    return res.json();
  },

  updateReferralStatus: async (referralId: string, status: string, scheduledDate?: string) => {
    const url = scheduledDate
      ? `${API_BASE}/referrals/${referralId}/status?status_val=${status}&scheduled_date=${encodeURIComponent(scheduledDate)}`
      : `${API_BASE}/referrals/${referralId}/status?status_val=${status}`;
    const res = await fetch(url, {
      method: 'PATCH',
      headers: getHeaders()
    });
    return res.json();
  },

  getPrintableReferralUrl: (referralId: string) => {
    return `${API_BASE}/referrals/${referralId}/printable`;
  },

  // Offline Sync & Network Simulation
  getSyncStatus: async (): Promise<SyncStatus> => {
    const res = await fetch(`${API_BASE}/sync/status`, { headers: getHeaders() });
    return res.json();
  },

  getSyncQueue: async () => {
    const res = await fetch(`${API_BASE}/sync/queue`, { headers: getHeaders() });
    return res.json();
  },

  triggerSync: async () => {
    const res = await fetch(`${API_BASE}/sync/trigger`, {
      method: 'POST',
      headers: getHeaders()
    });
    return res.json();
  },

  configureNetwork: async (config: {
    mode: string;
    bandwidth_kbps: number;
    packet_loss_rate: number;
    latency_ms: number;
  }) => {
    const res = await fetch(`${API_BASE}/simulation/network`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return res.json();
  },

  // Operational Simulation
  runOperationalSimulation: async (params: {
    num_phcs: number;
    patients_per_day_per_phc: number;
    specialist_count: number;
    avg_specialist_review_min: number;
    network_bandwidth_kbps: number;
  }): Promise<OperationalSimResults> => {
    const res = await fetch(`${API_BASE}/simulation/operational`, {
      method: 'POST',
      headers: { ...getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return res.json();
  },

  // Validation & Models
  getValidationMetrics: async () => {
    const res = await fetch(`${API_BASE}/validation/metrics`, { headers: getHeaders() });
    return res.json();
  },

  getErrorAnalysis: async () => {
    const res = await fetch(`${API_BASE}/validation/error-analysis`, { headers: getHeaders() });
    return res.json();
  },

  listModels: async () => {
    const res = await fetch(`${API_BASE}/training/models`, { headers: getHeaders() });
    return res.json();
  },

  listDatasets: async () => {
    const res = await fetch(`${API_BASE}/training/datasets`, { headers: getHeaders() });
    return res.json();
  },

  listExperiments: async () => {
    const res = await fetch(`${API_BASE}/training/experiments`, { headers: getHeaders() });
    return res.json();
  },

  flagActiveLearning: async (screeningId: string, reason: string) => {
    const res = await fetch(`${API_BASE}/training/flag-active-learning/${screeningId}?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
      headers: getHeaders()
    });
    return res.json();
  },

  // Devices & Audit
  listDevices: async () => {
    const res = await fetch(`${API_BASE}/devices`, { headers: getHeaders() });
    return res.json();
  },

  listAuditLogs: async (action?: string) => {
    const url = action ? `${API_BASE}/audit/logs?action=${action}` : `${API_BASE}/audit/logs`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  // Real-Time Acquisition & Forensics
  evaluateFrame: async (blob: Blob) => {
    const formData = new FormData();
    formData.append("file", blob, "frame.jpg");
    const res = await fetch(`${API_BASE}/realtime/evaluate-frame`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Frame evaluation failed');
    return res.json();
  },

  autoCapture: async (formData: FormData) => {
    const res = await fetch(`${API_BASE}/realtime/auto-capture`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData
    });
    if (!res.ok) throw new Error('Autonomous capture failed');
    return res.json();
  },

  fuseFrames: async (formData: FormData) => {
    const res = await fetch(`${API_BASE}/realtime/multi-frame-fuse`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData
    });
    if (!res.ok) throw new Error('Multi-frame fusion failed');
    return res.json();
  },

  getForensics: async (screeningId: string, eye?: string) => {
    const url = eye
      ? `${API_BASE}/realtime/forensics/${screeningId}?eye=${eye}`
      : `${API_BASE}/realtime/forensics/${screeningId}`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  getReplay: async (screeningId: string) => {
    const res = await fetch(`${API_BASE}/realtime/replay/${screeningId}`, { headers: getHeaders() });
    return res.json();
  },

  getBenchmarks: async () => {
    const res = await fetch(`${API_BASE}/realtime/benchmarks`, { headers: getHeaders() });
    return res.json();
  },

  calibrateGeometry: async (formData: FormData) => {
    const res = await fetch(`${API_BASE}/realtime/calibrate-geometry`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData
    });
    return res.json();
  },

  getImageUrl: (relPath: string) => {
    if (!relPath) return '';
    if (relPath.startsWith('http://') || relPath.startsWith('https://')) return relPath;
    let cleanPath = relPath.startsWith('/') ? relPath : `/${relPath}`;
    if (!cleanPath.startsWith('/storage/')) {
      cleanPath = `/storage${cleanPath}`;
    }
    return `${API_BASE}${cleanPath}`;
  }
};

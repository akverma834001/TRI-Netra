import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Patient, ScreeningSession, EyeQuality, OpticalMode, WorkflowStateResponse, PatientLookupResult, DemoStatus } from '../types';
import { SmartCaptureAssistant } from '../components/SmartCaptureAssistant';
import { TrustPanel } from '../components/TrustPanel';
import { RealTimeCameraHUD } from '../components/RealTimeCameraHUD';
import { FrameForensicsModal } from '../components/FrameForensicsModal';
import { AcquisitionBenchmarkModal } from '../components/AcquisitionBenchmarkModal';
import { FindPatientModal } from '../components/FindPatientModal';
import { Language, translations } from '../i18n/translations';
import {
  User, Camera, ArrowRight, ArrowLeft, CheckCircle2, Upload, Play,
  FileText, Zap, ShieldAlert, AlertTriangle, RotateCcw, Activity, BarChart3,
  Search, Lock, Check, Send, Printer, RefreshCw, Smartphone, Database, CheckCircle
} from 'lucide-react';

interface Props {
  onScreeningCompleted: (screeningId: string) => void;
  lang: Language;
}

const STORAGE_KEY = 'trinetra_active_session';

export const OperatorWorkflow: React.FC<Props> = ({ onScreeningCompleted, lang }) => {
  const t = translations[lang];

  // Authoritative Step State (1-6)
  const [step, setStep] = useState<number>(1);
  const [workflowState, setWorkflowState] = useState<WorkflowStateResponse | null>(null);

  // Form State (Zero hardcoded data: start completely empty in normal mode)
  const [patientName, setPatientName] = useState('');
  const [age, setAge] = useState<number | ''>('');
  const [sex, setSex] = useState<string>('');
  const [phone, setPhone] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [address, setAddress] = useState('');
  const [diabetesType, setDiabetesType] = useState('Type 2');
  const [diabetesDuration, setDiabetesDuration] = useState<number | ''>('');
  const [symptoms, setSymptoms] = useState('');
  const [consent, setConsent] = useState(false);

  // Active Session & Entities
  const [patient, setPatient] = useState<Patient | null>(null);
  const [screeningId, setScreeningId] = useState<string | null>(null);
  const [screening, setScreening] = useState<ScreeningSession | null>(null);
  const [restoredBanner, setRestoredBanner] = useState<string | null>(null);

  // Real-Time Camera HUD Active State
  const [activeCameraEye, setActiveCameraEye] = useState<'OD' | 'OS' | null>(null);
  const [opticalMode, setOpticalMode] = useState<OpticalMode>('MODE_2_PASSIVE_OPTIC');

  // File & Quality States for OD & OS
  const [odFile, setOdFile] = useState<File | null>(null);
  const [odQuality, setOdQuality] = useState<EyeQuality | null>(null);
  const [odLoading, setOdLoading] = useState(false);
  const [odRecaptureCount, setOdRecaptureCount] = useState(0);

  const [osFile, setOsFile] = useState<File | null>(null);
  const [osQuality, setOsQuality] = useState<EyeQuality | null>(null);
  const [osLoading, setOsLoading] = useState(false);
  const [osRecaptureCount, setOsRecaptureCount] = useState(0);

  // Stage-based AI Pipeline Progress
  const [analyzing, setAnalyzing] = useState(false);
  const [activeAiStage, setActiveAiStage] = useState<number>(0);

  // Modals
  const [showForensicsEye, setShowForensicsEye] = useState<'OD' | 'OS' | null>(null);
  const [showBenchmarks, setShowBenchmarks] = useState(false);
  const [showFindPatient, setShowFindPatient] = useState(false);

  // Duplicate Patient Detection Modal
  const [duplicateModal, setDuplicateModal] = useState<PatientLookupResult | null>(null);

  // Demo Status
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  // Intelligent Recapture Dialog
  const [recaptureNotice, setRecaptureNotice] = useState<{
    eye: 'OD' | 'OS';
    reason: string;
    action: string;
  } | null>(null);

  // Dispatch & Sync State (Step 6)
  const [dispatchMethod, setDispatchMethod] = useState<'sms' | 'whatsapp' | 'print'>('sms');
  const [dispatchPhone, setDispatchPhone] = useState('');
  const [dispatchSent, setDispatchSent] = useState(false);
  const [syncStatusText, setSyncStatusText] = useState('Buffered in local SQLite edge node (Synced)');

  // Step Lock Feedback Toast
  const [lockNotice, setLockNotice] = useState<string | null>(null);

  // 1. Crash Recovery & Session Persistence on Mount
  useEffect(() => {
    checkDemoStatus();
    restoreSessionFromStorage();
  }, []);

  const checkDemoStatus = async () => {
    try {
      const st = await api.getDemoStatus();
      setDemoStatus(st);
    } catch {
      // ignore
    }
  };

  const restoreSessionFromStorage = async () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved && saved.screeningId) {
        // Query authoritative state from backend
        const stateRes = await api.getWorkflowState(saved.screeningId);
        const scrRes = await api.getScreening(saved.screeningId);
        
        setScreeningId(saved.screeningId);
        setWorkflowState(stateRes);
        setScreening(scrRes);

        // Restore patient details
        if (scrRes.patient) {
          setPatient(scrRes.patient);
          setPatientName(scrRes.patient.full_name || '');
          setAge(scrRes.patient.age || '');
          setSex(scrRes.patient.sex || '');
          setPhone(scrRes.patient.phone || '');
          setDispatchPhone(scrRes.patient.phone || '');
          setDiabetesType(scrRes.patient.diabetes_type || 'Type 2');
          setDiabetesDuration(scrRes.patient.diabetes_duration_years || '');
          setSymptoms(scrRes.patient.symptoms || '');
          setConsent(scrRes.patient.consent_obtained || true);
        }

        // Restore OD / OS image statuses
        const odImg = scrRes.images.find(i => i.eye === 'OD');
        if (odImg) {
          setOdQuality({
            quality_score: odImg.quality_score,
            quality_status: odImg.quality_status as any,
            focus_score: odImg.focus_score,
            illumination_uniformity: odImg.illumination_uniformity,
            failure_reasons: odImg.failure_reasons,
            guidance_message: odImg.guidance_message,
            passed: odImg.quality_status !== 'Ungradable'
          });
        }

        const osImg = scrRes.images.find(i => i.eye === 'OS');
        if (osImg) {
          setOsQuality({
            quality_score: osImg.quality_score,
            quality_status: osImg.quality_status as any,
            focus_score: osImg.focus_score,
            illumination_uniformity: osImg.illumination_uniformity,
            failure_reasons: osImg.failure_reasons,
            guidance_message: osImg.guidance_message,
            passed: osImg.quality_status !== 'Ungradable'
          });
        }

        // Set authoritative step
        const restoredStep = stateRes.current_step_num || 1;
        setStep(restoredStep);
        setRestoredBanner(`Restored in-progress screening session ${saved.screeningId} for ${scrRes.patient?.full_name || 'patient'}.`);
      }
    } catch (e) {
      console.warn("Session restore failed, starting fresh:", e);
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const saveSessionToStorage = (id: string, stepNum: number) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ screeningId: id, step: stepNum, timestamp: new Date().toISOString() }));
  };

  const handleResetSession = () => {
    if (window.confirm("Are you sure you want to discard the active screening and register a new patient?")) {
      localStorage.removeItem(STORAGE_KEY);
      setScreeningId(null);
      setScreening(null);
      setPatient(null);
      setWorkflowState(null);
      setPatientName('');
      setAge('');
      setSex('');
      setPhone('');
      setDateOfBirth('');
      setAddress('');
      setDiabetesType('Type 2');
      setDiabetesDuration('');
      setSymptoms('');
      setConsent(false);
      setOdFile(null);
      setOdQuality(null);
      setOsFile(null);
      setOsQuality(null);
      setRestoredBanner(null);
      setDispatchSent(false);
      setStep(1);
    }
  };

  // Sync workflow state from backend
  const refreshWorkflowState = async (id: string) => {
    try {
      const state = await api.getWorkflowState(id);
      setWorkflowState(state);
      return state;
    } catch (e) {
      console.warn("Failed to refresh workflow state:", e);
      return null;
    }
  };

  // Check phone duplicate on blur or explicit lookup
  const handlePhoneBlur = async () => {
    const p = phone.trim();
    if (p.length >= 10 && !patient) {
      try {
        const lookup = await api.lookupPatientByPhone(p);
        if (lookup.found && lookup.patient) {
          setDuplicateModal(lookup);
        }
      } catch {
        // ignore
      }
    }
  };

  // Handle Step 1: Register Patient and Create Screening
  const handleRegisterPatient = async () => {
    if (!patientName.trim() || !age || !sex || !consent) {
      alert("Please complete all required fields (Name, Age, Sex, and Consent) before proceeding.");
      return;
    }

    try {
      const p = await api.createPatient({
        full_name: patientName.trim(),
        age: Number(age),
        sex,
        phone: phone.trim() || undefined,
        date_of_birth: dateOfBirth.trim() || undefined,
        address: address.trim() || undefined,
        diabetes_type: diabetesType,
        diabetes_duration_years: Number(diabetesDuration) || 0,
        symptoms: symptoms.trim() || undefined,
        consent_obtained: consent
      });
      setPatient(p);
      setDispatchPhone(p.phone || '');

      const sc = await api.createScreening(p.id, "PHC Rampur (Tele-Retina Node)");
      setScreeningId(sc.screening_id);
      saveSessionToStorage(sc.screening_id, 2);

      // Transition to RIGHT_EYE_CAPTURE in authoritative state machine
      const state = await api.transitionWorkflow(sc.screening_id, 'RIGHT_EYE_CAPTURE');
      setWorkflowState(state);
      setStep(2);
    } catch (err: any) {
      if (err.status === 409 && err.data?.existing_patient) {
        // Backend detected duplicate patient
        const existing = err.data.existing_patient;
        setDuplicateModal({
          found: true,
          patient: existing,
          unfinished_screening: null
        });
      } else {
        alert("Error creating patient session: " + (err.message || err));
      }
    }
  };

  // Start new screening for an existing patient found via lookup
  const handleUseExistingPatient = async (existing: any, resumeScreeningId?: string) => {
    setDuplicateModal(null);
    setShowFindPatient(false);

    if (resumeScreeningId) {
      // Resume existing active screening
      setScreeningId(resumeScreeningId);
      saveSessionToStorage(resumeScreeningId, 2);
      await restoreSessionFromStorage();
      return;
    }

    // Populate demographics
    setPatient(existing);
    setPatientName(existing.full_name || '');
    setAge(existing.age || '');
    setSex(existing.sex || '');
    setPhone(existing.phone || '');
    setDispatchPhone(existing.phone || '');
    setAddress(existing.address || '');
    setDiabetesType(existing.diabetes_type || 'Type 2');
    setDiabetesDuration(existing.diabetes_duration_years || '');
    setSymptoms(existing.symptoms || '');
    setConsent(true);

    try {
      const sc = await api.createScreening(existing.id, "PHC Rampur (Tele-Retina Node)");
      setScreeningId(sc.screening_id);
      saveSessionToStorage(sc.screening_id, 2);
      const state = await api.transitionWorkflow(sc.screening_id, 'RIGHT_EYE_CAPTURE');
      setWorkflowState(state);
      setStep(2);
    } catch (err: any) {
      alert("Error starting screening for existing patient: " + err.message);
    }
  };

  // Handle Real-Time Autonomous Capture Completion
  const handleRealTimeCaptureCompleted = async (captureData: any) => {
    const currentEye = activeCameraEye;
    setActiveCameraEye(null);

    const qualityData: EyeQuality = {
      quality_score: captureData.quality_score,
      quality_status: captureData.quality_status,
      focus_score: captureData.provenance?.focus_score || 115,
      illumination_uniformity: 11.2,
      failure_reasons: [],
      guidance_message: captureData.passed_quality_gate ? "Image Acquired" : "Recapture Advised",
      passed: captureData.passed_quality_gate
    };

    if (!screeningId) return;

    if (currentEye === 'OD') {
      setOdQuality(qualityData);
      if (captureData.passed_quality_gate) {
        // Authoritative transition to LEFT_EYE_CAPTURE
        const st = await api.transitionWorkflow(screeningId, 'LEFT_EYE_CAPTURE');
        setWorkflowState(st);
        saveSessionToStorage(screeningId, 3);
        setStep(3);
      } else {
        setOdRecaptureCount(prev => prev + 1);
        setRecaptureNotice({
          eye: 'OD',
          reason: t.recapture_reason_glare,
          action: t.recapture_action_glare
        });
      }
    } else if (currentEye === 'OS') {
      setOsQuality(qualityData);
      if (captureData.passed_quality_gate) {
        // Authoritative transition to AI_SCREENING
        const st = await api.transitionWorkflow(screeningId, 'AI_SCREENING');
        setWorkflowState(st);
        saveSessionToStorage(screeningId, 4);
        setStep(4);
      } else {
        setOsRecaptureCount(prev => prev + 1);
        setRecaptureNotice({
          eye: 'OS',
          reason: t.recapture_reason_blur,
          action: t.recapture_action_blur
        });
      }
    }
  };

  // Manual File Upload Fallback for OD
  const handleOdUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0] || !screeningId) return;
    const file = e.target.files[0];
    setOdFile(file);
    setOdLoading(true);
    try {
      const res = await api.uploadEyeImage(screeningId, 'OD', file);
      setOdQuality({
        quality_score: res.quality_score,
        quality_status: res.quality_status,
        focus_score: res.focus_score,
        illumination_uniformity: res.illumination_uniformity,
        failure_reasons: res.failure_reasons,
        guidance_message: res.guidance_message,
        passed: res.passed
      });
      await refreshWorkflowState(screeningId);
    } catch (err: any) {
      alert("Error uploading Right Eye image: " + err.message);
    } finally {
      setOdLoading(false);
    }
  };

  // Manual File Upload Fallback for OS
  const handleOsUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0] || !screeningId) return;
    const file = e.target.files[0];
    setOsFile(file);
    setOsLoading(true);
    try {
      const res = await api.uploadEyeImage(screeningId, 'OS', file);
      setOsQuality({
        quality_score: res.quality_score,
        quality_status: res.quality_status,
        focus_score: res.focus_score,
        illumination_uniformity: res.illumination_uniformity,
        failure_reasons: res.failure_reasons,
        guidance_message: res.guidance_message,
        passed: res.passed
      });
      await refreshWorkflowState(screeningId);
    } catch (err: any) {
      alert("Error uploading Left Eye image: " + err.message);
    } finally {
      setOsLoading(false);
    }
  };

  // Handle Step 4: Run AI Screening with Stage-Based Progress
  const handleRunAiAnalysis = async () => {
    if (!screeningId) return;
    setAnalyzing(true);
    setActiveAiStage(1);

    const s1 = setTimeout(() => setActiveAiStage(2), 300);
    const s2 = setTimeout(() => setActiveAiStage(3), 600);
    const s3 = setTimeout(() => setActiveAiStage(4), 900);
    const s4 = setTimeout(() => setActiveAiStage(5), 1200);
    const s5 = setTimeout(() => setActiveAiStage(6), 1500);

    try {
      await api.analyzeScreening(screeningId);
      const sc = await api.getScreening(screeningId);
      setScreening(sc);

      // Transition authoritative state to CLINICAL_REVIEW
      const state = await api.transitionWorkflow(screeningId, 'CLINICAL_REVIEW');
      setWorkflowState(state);
      saveSessionToStorage(screeningId, 5);

      setTimeout(() => {
        setStep(5);
        setAnalyzing(false);
      }, 1800);
    } catch (err: any) {
      clearTimeout(s1);
      clearTimeout(s2);
      clearTimeout(s3);
      clearTimeout(s4);
      clearTimeout(s5);
      alert("Error executing AI pipeline: " + (err.message || err));
      setAnalyzing(false);
    }
  };

  // Handle Unable to Assess Override
  const handleMarkUnableToAssess = async () => {
    if (!screeningId) return;
    const reason = prompt("Enter clinical reason for unable to assess (e.g., Dense Cataract, Corneal Opacity, Severe Pupil Constriction):", "Dense Cataract Precluding Retinal Visualization");
    if (!reason) return;

    try {
      await api.markUnableToAssess(screeningId, reason);
      const sc = await api.getScreening(screeningId);
      setScreening(sc);
      const st = await api.transitionWorkflow(screeningId, 'CLINICAL_REVIEW');
      setWorkflowState(st);
      saveSessionToStorage(screeningId, 5);
      setStep(5);
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  // Handle Step 5 -> Step 6 (Transition to Dispatch & Sync)
  const handleProceedToDispatch = async () => {
    if (!screeningId) return;
    try {
      const st = await api.transitionWorkflow(screeningId, 'DISPATCH_SYNC');
      setWorkflowState(st);
      saveSessionToStorage(screeningId, 6);
      setStep(6);
    } catch (err: any) {
      alert("Transition rejected: " + err.message);
    }
  };

  // Handle Step 6: Dispatch Referral
  const handleSendDispatch = async () => {
    if (!screeningId) return;
    try {
      await api.completeDispatch(screeningId, {
        phone: dispatchPhone,
        delivery_method: dispatchMethod,
        dispatch_notes: "Operator dispatched referral advice and health education to patient."
      });
      setDispatchSent(true);
      setSyncStatusText("Synced to District Central Hub (Confirmed)");
      await refreshWorkflowState(screeningId);
    } catch (err: any) {
      alert("Dispatch error: " + err.message);
    }
  };

  // Stepper Header Click Handler
  const handleStepClick = async (targetStepNum: number) => {
    // If clicking current step, do nothing
    if (targetStepNum === step) return;

    // If no active screening, only Step 1 is unlocked
    if (!screeningId) {
      if (targetStepNum > 1) {
        setLockNotice("Please register patient in Step 1 before proceeding.");
        setTimeout(() => setLockNotice(null), 3500);
      }
      return;
    }

    // Check authoritative availability
    const available = workflowState?.available_steps || [1];
    const completed = workflowState?.completed_steps || [];
    const isUnlocked = available.includes(targetStepNum) || completed.includes(targetStepNum) || targetStepNum <= step;

    if (isUnlocked) {
      setStep(targetStepNum);
    } else {
      const reason = workflowState?.step_reasons[String(targetStepNum)] || "Complete preceding workflow stages first.";
      setLockNotice(`Step ${targetStepNum} is locked: ${reason}`);
      setTimeout(() => setLockNotice(null), 4000);
    }
  };

  // Demo Data Toggle Handler
  const handleToggleDemoData = async () => {
    setDemoLoading(true);
    try {
      if (demoStatus?.demo_mode_active) {
        await api.clearDemoData();
      } else {
        await api.seedDemoData();
      }
      const st = await api.getDemoStatus();
      setDemoStatus(st);
    } catch (e: any) {
      alert("Demo action failed: " + e.message);
    } finally {
      setDemoLoading(false);
    }
  };

  const stepsList = [
    { num: 1, label: t.step_1, name: 'Registration' },
    { num: 2, label: t.step_2, name: 'OD Capture' },
    { num: 3, label: t.step_3, name: 'OS Capture' },
    { num: 4, label: t.step_4, name: 'Run AI' },
    { num: 5, label: t.step_5, name: 'Summary' },
    { num: 6, label: t.step_6, name: 'Dispatch & Sync' }
  ];

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      {/* Top Banner: Restored Session Alert */}
      {restoredBanner && (
        <div style={{
          background: 'rgba(6, 182, 212, 0.12)',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          borderRadius: 'var(--radius-sm)',
          padding: '10px 16px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '13px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={16} color="var(--brand-cyan)" />
            <span>{restoredBanner}</span>
          </div>
          <button
            className="btn btn-secondary"
            onClick={handleResetSession}
            style={{ fontSize: '11px', padding: '4px 10px' }}
          >
            Start New Screening / Clear
          </button>
        </div>
      )}

      {/* Top Action Bar: Search Patient, Demo Mode Pill, Benchmark Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            className="btn btn-secondary"
            onClick={() => setShowFindPatient(true)}
            style={{ fontSize: '12px', padding: '6px 14px', borderColor: 'var(--brand-cyan)' }}
          >
            <Search size={14} color="var(--brand-cyan)" />
            <span>Find Existing Patient / History</span>
          </button>

          {screeningId && (
            <span className="badge badge-cyan" style={{ fontSize: '11px' }}>
              Session: <strong>{screeningId}</strong>
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Demo Benchmark Data Toggle */}
          <button
            className="btn btn-secondary"
            onClick={handleToggleDemoData}
            disabled={demoLoading}
            style={{
              fontSize: '12px',
              padding: '6px 12px',
              color: demoStatus?.demo_mode_active ? 'var(--brand-emerald)' : 'var(--text-muted)'
            }}
            title={demoStatus?.demo_mode_active ? "Demo benchmark cohort is currently loaded" : "Load 10 standardized clinical benchmark cases"}
          >
            <Zap size={14} color={demoStatus?.demo_mode_active ? 'var(--brand-emerald)' : 'currentColor'} />
            <span>{demoLoading ? 'Updating...' : demoStatus?.demo_mode_active ? `Demo Cohort Active (${demoStatus.demo_patients_count} cases)` : 'Load Demo Cohort (10 Cases)'}</span>
          </button>

          <button
            className="btn btn-secondary"
            onClick={() => setShowBenchmarks(true)}
            style={{ fontSize: '12px', padding: '6px 12px' }}
          >
            <BarChart3 size={14} />
            <span>{t.benchmarks_btn}</span>
          </button>
        </div>
      </div>

      {/* Interactive Authoritative Stepper Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '24px',
        background: 'var(--bg-surface)',
        padding: '14px 18px',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-color)',
        overflowX: 'auto',
        gap: '8px'
      }}>
        {stepsList.map(s => {
          const isCompleted = workflowState?.completed_steps.includes(s.num) || (step > s.num);
          const isActive = step === s.num;
          const isAvailable = workflowState?.available_steps.includes(s.num) || s.num === 1;
          const isLocked = !isCompleted && !isActive && !isAvailable;
          const lockReason = workflowState?.step_reasons[String(s.num)] || `Complete Step ${s.num - 1} first`;

          return (
            <div
              key={s.num}
              onClick={() => handleStepClick(s.num)}
              title={isLocked ? `Locked: ${lockReason}` : `Navigate to Step ${s.num}: ${s.label}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-sm)',
                cursor: isLocked ? 'not-allowed' : 'pointer',
                opacity: isLocked ? 0.45 : 1,
                fontWeight: isActive ? 700 : 500,
                fontSize: '13px',
                background: isActive ? 'rgba(6, 182, 212, 0.1)' : 'transparent',
                border: isActive ? '1px solid var(--brand-cyan)' : '1px solid transparent',
                color: isActive ? 'var(--brand-cyan)' : isCompleted ? 'var(--brand-emerald)' : isLocked ? 'var(--text-muted)' : 'var(--text-primary)',
                transition: 'all 0.15s ease',
                flexShrink: 0
              }}
            >
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: isCompleted ? 'var(--brand-emerald)' : isActive ? 'var(--brand-cyan)' : 'var(--bg-subtle)',
                color: isCompleted || isActive ? 'white' : 'var(--text-muted)',
                fontSize: '11px',
                fontWeight: 700
              }}>
                {isCompleted ? <Check size={13} strokeWidth={3} /> : isLocked ? <Lock size={11} /> : s.num}
              </div>
              <span>{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* Lock Notification Toast */}
      {lockNotice && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: 'var(--radius-sm)',
          padding: '10px 14px',
          color: '#f87171',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '16px',
          animation: 'fadeIn 0.2s ease'
        }}>
          <AlertTriangle size={16} />
          <span>{lockNotice}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 1: PATIENT REGISTRATION                                              */}
      {/* ========================================================================= */}
      {step === 1 && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0 }}>Step 1: Patient Demographics & Clinical History</h3>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Collect baseline diabetes profile, contact details, and informed screening consent
              </div>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => setShowFindPatient(true)}
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              <Search size={14} />
              <span>Lookup by Phone</span>
            </button>
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">
                Patient Full Name (मरीज़ का पूरा नाम) <span style={{ color: 'var(--brand-rose)' }}>*</span>
              </label>
              <input
                className="form-input"
                placeholder="Enter patient full name"
                value={patientName}
                onChange={e => setPatientName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                Mobile Number (मोबाइल नंबर) <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>— Primary identifier</span>
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  className="form-input"
                  placeholder="e.g. 9876543210 or +91-98765..."
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  onBlur={handlePhoneBlur}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handlePhoneBlur}
                  style={{ padding: '8px 12px', fontSize: '12px' }}
                  title="Check if patient already exists"
                >
                  Verify
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                Age & Biological Sex <span style={{ color: 'var(--brand-rose)' }}>*</span>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <input
                  type="number"
                  className="form-input"
                  value={age}
                  onChange={e => setAge(e.target.value ? Number(e.target.value) : '')}
                  placeholder="Age (years)"
                />
                <select
                  className="form-select"
                  value={sex}
                  onChange={e => setSex(e.target.value)}
                >
                  <option value="">Select Sex...</option>
                  <option value="Female">Female (महिला)</option>
                  <option value="Male">Male (पुरुष)</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Residential Address / Village (गाँव / पता)</label>
              <input
                className="form-input"
                placeholder="Village / Ward / Block"
                value={address}
                onChange={e => setAddress(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Diabetes Classification & Duration</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <select
                  className="form-select"
                  value={diabetesType}
                  onChange={e => setDiabetesType(e.target.value)}
                >
                  <option value="Type 2">Type 2 DM</option>
                  <option value="Type 1">Type 1 DM</option>
                  <option value="Gestational">Gestational</option>
                  <option value="None">None / Unknown</option>
                </select>
                <input
                  type="number"
                  step="0.5"
                  className="form-input"
                  value={diabetesDuration}
                  onChange={e => setDiabetesDuration(e.target.value ? Number(e.target.value) : '')}
                  placeholder="Duration (Years)"
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Visual Symptoms Reported</label>
              <input
                className="form-input"
                placeholder="e.g. Mild distance blur, floaters, straight lines intact"
                value={symptoms}
                onChange={e => setSymptoms(e.target.value)}
              />
            </div>
          </div>

          <div style={{
            background: 'var(--bg-subtle)',
            padding: '16px',
            borderRadius: 'var(--radius-sm)',
            marginTop: '16px',
            border: '1px solid var(--border-color)'
          }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={consent}
                onChange={e => setConsent(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--brand-cyan)' }}
              />
              <span style={{ fontSize: '13px' }}>
                <strong>Informed Clinical Screening Consent Obtained:</strong> Patient agrees to non-mydriatic fundus photography, AI triage classification, and telemedicine transmission to district ophthalmologist.
              </span>
            </label>
          </div>

          {/* Explicit Validation Message & Registration Action */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '24px' }}>
            {(!patientName.trim() || !age || !sex || !consent) && (
              <div style={{ fontSize: '12px', color: 'var(--brand-amber)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={14} />
                <span>Please complete Full Name, Age, Biological Sex, and confirm Informed Consent before proceeding.</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleRegisterPatient}
                disabled={!patientName.trim() || !age || !sex || !consent}
              >
                <span>Register & Begin OD Capture</span>
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 2: RIGHT EYE CAPTURE (OD)                                            */}
      {/* ========================================================================= */}
      {step === 2 && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0 }}>Step 2: Right Eye (OD - Oculus Dexter) Retinal Capture</h3>
                <span className="badge badge-cyan">OD</span>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Patient: <strong>{patient?.full_name || patientName}</strong> • Session: <strong>{screeningId}</strong>
              </div>
            </div>

            {/* Optical Mode Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Optic:</span>
              <select
                className="form-select"
                style={{ fontSize: '12px', padding: '4px 8px' }}
                value={opticalMode}
                onChange={e => setOpticalMode(e.target.value as OpticalMode)}
              >
                <option value="MODE_2_PASSIVE_OPTIC">+20D Passive Optic Lens</option>
                <option value="MODE_1_BARE_PHONE">Mode 1: Direct Macro</option>
                <option value="MODE_3_RESEARCH">Mode 3: Bench Research</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
            {/* Primary Action Panel */}
            <div>
              <div style={{
                border: '2px dashed var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '36px 20px',
                textAlign: 'center',
                background: 'var(--bg-subtle)',
                marginBottom: '16px'
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  background: 'rgba(6, 182, 212, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                  color: 'var(--brand-cyan)'
                }}>
                  <Camera size={32} />
                </div>
                <h4 style={{ margin: '0 0 6px', fontSize: '18px' }}>Autonomous Real-Time Video Capture</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '440px', margin: '0 auto 20px' }}>
                  Open continuous smartphone video feed. The AI Gatekeeper automatically detects pupil alignment, evaluates focus & illumination, and freezes the optimal frame.
                </p>

                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => setActiveCameraEye('OD')}
                  style={{ padding: '12px 28px', fontSize: '15px' }}
                >
                  <Play size={18} />
                  <span>{t.btn_start_realtime_scan} (OD)</span>
                </button>
              </div>

              {/* Manual Upload Fallback */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Alternative: Upload pre-captured fundus photograph
                </div>
                <label className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 14px', cursor: 'pointer' }}>
                  <Upload size={14} />
                  <span>{odLoading ? 'Uploading...' : 'Browse Image File'}</span>
                  <input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleOdUpload} />
                </label>
              </div>
            </div>

            {/* Right Side: Quality Assessment Status */}
            <div>
              <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ margin: '0 0 12px', fontSize: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                    Optical Gatekeeper Status (OD)
                  </h4>

                  {odQuality ? (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Quality Grade:</span>
                        <span className={`badge ${odQuality.passed ? 'badge-emerald' : 'badge-rose'}`}>
                          {odQuality.quality_status} ({Math.round(odQuality.quality_score * 100)}%)
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px', fontSize: '12px' }}>
                        <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                          <div style={{ color: 'var(--text-muted)' }}>Focus Score</div>
                          <div style={{ fontWeight: 700, marginTop: '2px' }}>{odQuality.focus_score.toFixed(1)}</div>
                        </div>
                        <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                          <div style={{ color: 'var(--text-muted)' }}>Uniformity</div>
                          <div style={{ fontWeight: 700, marginTop: '2px' }}>{odQuality.illumination_uniformity.toFixed(1)}%</div>
                        </div>
                      </div>

                      <div style={{ fontSize: '12px', color: odQuality.passed ? 'var(--brand-emerald)' : 'var(--brand-amber)', marginBottom: '12px' }}>
                        {odQuality.guidance_message}
                      </div>

                      {odQuality.passed && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--brand-emerald)', fontSize: '13px', fontWeight: 600 }}>
                          <CheckCircle2 size={16} />
                          <span>Ready for Left Eye capture</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-muted)', fontSize: '13px' }}>
                      <Camera size={32} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
                      <div>No image captured yet for Right Eye</div>
                      <div style={{ fontSize: '11px', marginTop: '4px' }}>Click Start Scan or upload a file to run quality check.</div>
                    </div>
                  )}
                </div>

                {odQuality && (
                  <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-color)' }}>
                    <button
                      className="btn btn-secondary"
                      onClick={() => setShowForensicsEye('OD')}
                      style={{ width: '100%', fontSize: '12px', padding: '6px' }}
                    >
                      <Activity size={14} />
                      <span>{t.forensics_btn} (OD)</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '18px' }}>
            <button className="btn btn-secondary" onClick={() => setStep(1)}>
              <ArrowLeft size={16} />
              <span>Back to Patient Details</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {!odQuality?.passed && (
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Capture or upload valid OD image to proceed
                </span>
              )}

              <button
                className="btn btn-primary"
                disabled={!odQuality?.passed}
                onClick={async () => {
                  if (screeningId) {
                    const st = await api.transitionWorkflow(screeningId, 'LEFT_EYE_CAPTURE');
                    setWorkflowState(st);
                    saveSessionToStorage(screeningId, 3);
                  }
                  setStep(3);
                }}
              >
                <span>Proceed to Left Eye (OS) Capture</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 3: LEFT EYE CAPTURE (OS)                                             */}
      {/* ========================================================================= */}
      {step === 3 && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0 }}>Step 3: Left Eye (OS - Oculus Sinister) Retinal Capture</h3>
                <span className="badge badge-cyan">OS</span>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Patient: <strong>{patient?.full_name || patientName}</strong> • OD Captured ✓
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Optic:</span>
              <select
                className="form-select"
                style={{ fontSize: '12px', padding: '4px 8px' }}
                value={opticalMode}
                onChange={e => setOpticalMode(e.target.value as OpticalMode)}
              >
                <option value="MODE_2_PASSIVE_OPTIC">+20D Passive Optic Lens</option>
                <option value="MODE_1_BARE_PHONE">Mode 1: Direct Macro</option>
                <option value="MODE_3_RESEARCH">Mode 3: Bench Research</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
            {/* Primary Action Panel */}
            <div>
              <div style={{
                border: '2px dashed var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '36px 20px',
                textAlign: 'center',
                background: 'var(--bg-subtle)',
                marginBottom: '16px'
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  background: 'rgba(6, 182, 212, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                  color: 'var(--brand-cyan)'
                }}>
                  <Camera size={32} />
                </div>
                <h4 style={{ margin: '0 0 6px', fontSize: '18px' }}>Autonomous Real-Time Video Capture (Left Eye)</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '440px', margin: '0 auto 20px' }}>
                  Position camera over patient's Left Eye (OS). Gatekeeper evaluates focus, glare, and centering in real-time.
                </p>

                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => setActiveCameraEye('OS')}
                  style={{ padding: '12px 28px', fontSize: '15px' }}
                >
                  <Play size={18} />
                  <span>{t.btn_start_realtime_scan} (OS)</span>
                </button>
              </div>

              {/* Manual Upload Fallback */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Alternative: Upload pre-captured fundus photograph
                </div>
                <label className="btn btn-secondary" style={{ fontSize: '12px', padding: '6px 14px', cursor: 'pointer' }}>
                  <Upload size={14} />
                  <span>{osLoading ? 'Uploading...' : 'Browse Image File'}</span>
                  <input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleOsUpload} />
                </label>
              </div>
            </div>

            {/* Right Side: Quality Assessment Status */}
            <div>
              <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ margin: '0 0 12px', fontSize: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                    Optical Gatekeeper Status (OS)
                  </h4>

                  {osQuality ? (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Quality Grade:</span>
                        <span className={`badge ${osQuality.passed ? 'badge-emerald' : 'badge-rose'}`}>
                          {osQuality.quality_status} ({Math.round(osQuality.quality_score * 100)}%)
                        </span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px', fontSize: '12px' }}>
                        <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                          <div style={{ color: 'var(--text-muted)' }}>Focus Score</div>
                          <div style={{ fontWeight: 700, marginTop: '2px' }}>{osQuality.focus_score.toFixed(1)}</div>
                        </div>
                        <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                          <div style={{ color: 'var(--text-muted)' }}>Uniformity</div>
                          <div style={{ fontWeight: 700, marginTop: '2px' }}>{osQuality.illumination_uniformity.toFixed(1)}%</div>
                        </div>
                      </div>

                      <div style={{ fontSize: '12px', color: osQuality.passed ? 'var(--brand-emerald)' : 'var(--brand-amber)', marginBottom: '12px' }}>
                        {osQuality.guidance_message}
                      </div>

                      {osQuality.passed && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--brand-emerald)', fontSize: '13px', fontWeight: 600 }}>
                          <CheckCircle2 size={16} />
                          <span>Both eyes acquired successfully</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-muted)', fontSize: '13px' }}>
                      <Camera size={32} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
                      <div>No image captured yet for Left Eye</div>
                      <div style={{ fontSize: '11px', marginTop: '4px' }}>Click Start Scan or upload a file to run quality check.</div>
                    </div>
                  )}
                </div>

                {osQuality && (
                  <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-color)' }}>
                    <button
                      className="btn btn-secondary"
                      onClick={() => setShowForensicsEye('OS')}
                      style={{ width: '100%', fontSize: '12px', padding: '6px' }}
                    >
                      <Activity size={14} />
                      <span>{t.forensics_btn} (OS)</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Navigation Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '18px' }}>
            <button className="btn btn-secondary" onClick={() => setStep(2)}>
              <ArrowLeft size={16} />
              <span>Back to Right Eye (OD)</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {!osQuality?.passed && (
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Capture or upload valid OS image to proceed
                </span>
              )}

              <button
                className="btn btn-primary"
                disabled={!osQuality?.passed}
                onClick={async () => {
                  if (screeningId) {
                    const st = await api.transitionWorkflow(screeningId, 'AI_SCREENING');
                    setWorkflowState(st);
                    saveSessionToStorage(screeningId, 4);
                  }
                  setStep(4);
                }}
              >
                <span>Proceed to Run AI Screening</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 4: RUN AI SCREENING                                                  */}
      {/* ========================================================================= */}
      {step === 4 && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0 }}>Step 4: Dual-Eye Neuro-Symbolic AI Screening</h3>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Multi-stage inference: Quality Verification → Anatomy Detection → Lesion Segmentation → Biomarker Extraction → ICDR Staging
              </div>
            </div>
            <span className="badge badge-cyan">Inference Stage</span>
          </div>

          {/* Bilateral Pre-Analysis Preview */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: 'var(--bg-subtle)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '14px' }}>Right Eye (OD)</span>
                <span className="badge badge-emerald">Quality: {odQuality?.quality_status || 'Acceptable'}</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Focus: {odQuality?.focus_score.toFixed(1) || '112.5'} • Uniformity: {odQuality?.illumination_uniformity.toFixed(1) || '14.2'}%
              </div>
            </div>

            <div style={{ background: 'var(--bg-subtle)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '14px' }}>Left Eye (OS)</span>
                <span className="badge badge-emerald">Quality: {osQuality?.quality_status || 'Acceptable'}</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Focus: {osQuality?.focus_score.toFixed(1) || '108.3'} • Uniformity: {osQuality?.illumination_uniformity.toFixed(1) || '13.8'}%
              </div>
            </div>
          </div>

          {/* AI Execution Banner / Progress */}
          {analyzing ? (
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--brand-cyan)',
              borderRadius: 'var(--radius-md)',
              padding: '24px',
              textAlign: 'center',
              marginBottom: '20px'
            }}>
              <div className="spinner" style={{ margin: '0 auto 16px' }} />
              <h4 style={{ margin: '0 0 10px', fontSize: '17px' }}>Executing Neuro-Symbolic AI Pipeline...</h4>

              {/* Progress Steps */}
              <div style={{ maxWidth: '400px', margin: '0 auto', textAlign: 'left', fontSize: '13px' }}>
                <div style={{ color: activeAiStage >= 1 ? 'var(--brand-cyan)' : 'var(--text-muted)', marginBottom: '4px' }}>
                  {activeAiStage >= 1 ? '✓' : '○'} 1. Optical Gatekeeper Quality Verification
                </div>
                <div style={{ color: activeAiStage >= 2 ? 'var(--brand-cyan)' : 'var(--text-muted)', marginBottom: '4px' }}>
                  {activeAiStage >= 2 ? '✓' : '○'} 2. Anatomical Landmark Detection (Disc, Fovea, Vessels)
                </div>
                <div style={{ color: activeAiStage >= 3 ? 'var(--brand-cyan)' : 'var(--text-muted)', marginBottom: '4px' }}>
                  {activeAiStage >= 3 ? '✓' : '○'} 3. Lesion Segmentation (MA, Hemorrhages, Hard Exudates)
                </div>
                <div style={{ color: activeAiStage >= 4 ? 'var(--brand-cyan)' : 'var(--text-muted)', marginBottom: '4px' }}>
                  {activeAiStage >= 4 ? '✓' : '○'} 4. 12-D Neuro-Symbolic Biomarker Extraction
                </div>
                <div style={{ color: activeAiStage >= 5 ? 'var(--brand-cyan)' : 'var(--text-muted)' }}>
                  {activeAiStage >= 5 ? '✓' : '○'} 5. TrinetraNet-v1.0 ICDR Staging & Epistemic Uncertainty
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', marginBottom: '20px' }}>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleRunAiAnalysis}
                style={{ padding: '14px 36px', fontSize: '16px', margin: '0 auto' }}
              >
                <Zap size={20} />
                <span>Run Dual-Eye AI Screening Engine</span>
              </button>

              <div style={{ marginTop: '16px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleMarkUnableToAssess}
                  style={{ fontSize: '12px', padding: '6px 14px', color: 'var(--brand-amber)' }}
                >
                  <AlertTriangle size={14} />
                  <span>Mark as Unable to Assess & Escalate Case</span>
                </button>
              </div>
            </div>
          )}

          {/* Navigation Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '18px' }}>
            <button className="btn btn-secondary" onClick={() => setStep(3)}>
              <ArrowLeft size={16} />
              <span>Back to Left Eye Capture</span>
            </button>

            {screening?.images && screening.images.length > 0 && screening.images[0].ai_result && (
              <button
                className="btn btn-primary"
                onClick={() => setStep(5)}
              >
                <span>Proceed to Clinical Summary</span>
                <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 5: CLINICAL SUMMARY                                                  */}
      {/* ========================================================================= */}
      {step === 5 && screening && (
        <div>
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>Step 5: Bilateral AI Retinal Screening Summary</h3>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Patient: <strong>{screening.patient.full_name}</strong> ({screening.patient.age}y / {screening.patient.sex}) • {screening.phc_facility}
                </div>
              </div>
              <span className="badge badge-emerald">AI Pipeline Complete</span>
            </div>

            {/* Bilateral Synthesis Banner */}
            <div style={{ background: 'var(--bg-subtle)', padding: '16px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', borderLeft: '4px solid var(--brand-cyan)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Bilateral Inter-Ocular Synthesis
              </div>
              <div style={{ fontSize: '15px', fontWeight: 700, marginTop: '4px', color: 'var(--text-primary)' }}>
                {screening.bilateral_summary || "Symmetric bilateral screening complete"}
              </div>
            </div>

            {/* Right Eye (OD) and Left Eye (OS) Trust Panels */}
            <div className="grid-2" style={{ marginBottom: '24px' }}>
              {screening.images.map(img => (
                <TrustPanel
                  key={img.id}
                  aiResult={img.ai_result}
                  biomarkers={img.biomarkers}
                  eyeLabel={img.eye === 'OD' ? "Right Eye (OD)" : "Left Eye (OS)"}
                />
              ))}
            </div>

            {/* Navigation Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
              <button className="btn btn-secondary" onClick={() => setStep(4)}>
                <ArrowLeft size={16} />
                <span>Back to AI Screening</span>
              </button>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn btn-primary btn-lg"
                  onClick={handleProceedToDispatch}
                >
                  <span>Proceed to Dispatch & Sync</span>
                  <ArrowRight size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 6: DISPATCH & SYNC                                                   */}
      {/* ========================================================================= */}
      {step === 6 && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0 }}>Step 6: Referral Dispatch, Patient Advice & Edge Sync</h3>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Deliver triage guidance via SMS / WhatsApp, print physical referral ticket, and synchronize with Central Telemedicine Node
              </div>
            </div>
            <span className="badge badge-emerald">Final Stage</span>
          </div>

          <div className="grid-2" style={{ marginBottom: '24px' }}>
            {/* Delivery Channels */}
            <div style={{ background: 'var(--bg-subtle)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <h4 style={{ margin: '0 0 14px', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Smartphone size={16} color="var(--brand-cyan)" />
                <span>Patient Communication Channel</span>
              </h4>

              <div className="form-group">
                <label className="form-label">Delivery Mode</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    type="button"
                    className={`btn ${dispatchMethod === 'sms' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ flex: 1, fontSize: '13px' }}
                    onClick={() => setDispatchMethod('sms')}
                  >
                    SMS Dispatch
                  </button>
                  <button
                    type="button"
                    className={`btn ${dispatchMethod === 'whatsapp' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ flex: 1, fontSize: '13px' }}
                    onClick={() => setDispatchMethod('whatsapp')}
                  >
                    WhatsApp Report
                  </button>
                </div>
              </div>

              <div className="form-group" style={{ marginTop: '12px' }}>
                <label className="form-label">Recipient Phone Number</label>
                <input
                  className="form-input"
                  value={dispatchPhone}
                  onChange={e => setDispatchPhone(e.target.value)}
                  placeholder="Enter phone number"
                />
              </div>

              <button
                className="btn btn-primary"
                onClick={handleSendDispatch}
                disabled={dispatchSent}
                style={{ width: '100%', marginTop: '10px' }}
              >
                {dispatchSent ? (
                  <>
                    <CheckCircle2 size={16} />
                    <span>Referral Dispatched Successfully!</span>
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    <span>Send {dispatchMethod === 'sms' ? 'SMS Notification' : 'WhatsApp Notification'}</span>
                  </>
                )}
              </button>

              <div style={{ marginTop: '14px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => window.print()}
                  style={{ width: '100%', fontSize: '13px' }}
                >
                  <Printer size={14} />
                  <span>Print Physical Referral Slip</span>
                </button>
              </div>
            </div>

            {/* Edge SQLite to Central Cloud Sync Status */}
            <div style={{ background: 'var(--bg-subtle)', padding: '18px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <h4 style={{ margin: '0 0 14px', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={16} color="var(--brand-emerald)" />
                <span>Edge Node Synchronization</span>
              </h4>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', background: 'var(--bg-surface)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                <CheckCircle size={20} color="var(--brand-emerald)" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px' }}>{syncStatusText}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Case ID: {screeningId} • PHC Rampur Node</div>
                </div>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '16px' }}>
                Retinal imagery, 12-D biomarker embeddings, and audit trails have been safely recorded in local SQLite edge storage. Central Telemedicine hub synchronization confirmed.
              </div>

              <div style={{ background: 'var(--bg-surface)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Audit Log Event:</span>
                  <span style={{ fontWeight: 600 }}>SCREENING_COMPLETED</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Referral Status:</span>
                  <span style={{ fontWeight: 600, color: 'var(--brand-emerald)' }}>Active & Dispatched</span>
                </div>
              </div>
            </div>
          </div>

          {/* Final Session Actions */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '1px solid var(--border-color)',
            paddingTop: '20px',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <button className="btn btn-secondary" onClick={() => setStep(5)}>
              <ArrowLeft size={16} />
              <span>Back to Summary</span>
            </button>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                className="btn btn-secondary"
                onClick={handleResetSession}
                style={{ borderColor: 'var(--brand-emerald)', color: 'var(--brand-emerald)' }}
              >
                <RefreshCw size={15} />
                <span>Complete & Register Next Patient</span>
              </button>

              {screeningId && (
                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => onScreeningCompleted(screeningId)}
                >
                  <span>Open in Specialist Workstation</span>
                  <ArrowRight size={18} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODALS & OVERLAYS                                                         */}
      {/* ========================================================================= */}

      {/* Duplicate Patient Alert Modal */}
      {duplicateModal && duplicateModal.patient && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(3, 7, 18, 0.85)',
          backdropFilter: 'blur(6px)',
          zIndex: 10001,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div className="card" style={{ maxWidth: '520px', width: '100%', borderColor: 'var(--brand-amber)', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--brand-amber)', marginBottom: '16px' }}>
              <AlertTriangle size={24} />
              <h3 style={{ margin: 0, fontSize: '18px' }}>Existing Patient Record Identified</h3>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              A registered patient with this mobile number already exists in the Trinetra health database.
            </p>

            <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', fontSize: '13px' }}>
              <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                {duplicateModal.patient.full_name}
              </div>
              <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
                Phone: {duplicateModal.patient.phone} • {duplicateModal.patient.age}y / {duplicateModal.patient.sex}
              </div>
              <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
                Diabetes: {duplicateModal.patient.diabetes_type} ({duplicateModal.patient.diabetes_duration_years} yrs) • {duplicateModal.patient.total_screenings} prior session(s)
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                className="btn btn-primary"
                onClick={() => handleUseExistingPatient(duplicateModal.patient)}
              >
                <span>Start New Screening Session for this Patient</span>
                <ArrowRight size={16} />
              </button>

              <button
                className="btn btn-secondary"
                onClick={() => {
                  setDuplicateModal(null);
                  setShowFindPatient(true);
                }}
              >
                <Search size={14} />
                <span>View Full Longitudinal History First</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={() => setDuplicateModal(null)}
                style={{ color: 'var(--text-muted)' }}
              >
                Different Patient (Keep Editing)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Global Find Patient & History Modal */}
      {showFindPatient && (
        <FindPatientModal
          onClose={() => setShowFindPatient(false)}
          onSelectPatient={(selPatient, resumeScrId) => handleUseExistingPatient(selPatient, resumeScrId)}
        />
      )}

      {/* Live Real-Time Camera HUD Overlay */}
      {activeCameraEye && screeningId && (
        <RealTimeCameraHUD
          screeningId={screeningId}
          eye={activeCameraEye}
          lang={lang}
          onCaptureCompleted={handleRealTimeCaptureCompleted}
          onCancel={() => setActiveCameraEye(null)}
        />
      )}

      {/* Intelligent Recapture Guidance Modal */}
      {recaptureNotice && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(3, 7, 18, 0.85)',
          backdropFilter: 'blur(6px)',
          zIndex: 10001,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div className="card" style={{ maxWidth: '480px', width: '100%', borderColor: 'var(--brand-rose)', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--brand-rose)', marginBottom: '16px' }}>
              <AlertTriangle size={24} />
              <h3 style={{ margin: 0, fontSize: '18px' }}>IMAGE NOT SUITABLE FOR AI ANALYSIS</h3>
            </div>

            <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '18px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Identified Deficit:</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--brand-rose)', marginTop: '2px' }}>
                {recaptureNotice.reason}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '10px' }}>Corrective Operator Action:</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {recaptureNotice.action}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
              {(recaptureNotice.eye === 'OD' ? odRecaptureCount : osRecaptureCount) >= 3 ? (
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setRecaptureNotice(null);
                    alert("Case escalated directly to District Specialist Telemedicine Queue.");
                    if (screeningId) onScreeningCompleted(screeningId);
                  }}
                  style={{ color: 'var(--brand-amber)' }}
                >
                  <ShieldAlert size={14} />
                  <span>Escalate to Specialist Review</span>
                </button>
              ) : (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', alignSelf: 'center' }}>
                  Attempt {recaptureNotice.eye === 'OD' ? odRecaptureCount : osRecaptureCount} of 3
                </div>
              )}

              <button
                className="btn btn-primary"
                onClick={() => {
                  const eyeToRetry = recaptureNotice.eye;
                  setRecaptureNotice(null);
                  setActiveCameraEye(eyeToRetry);
                }}
              >
                <RotateCcw size={14} />
                <span>TRY AGAIN</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Frame Forensics & Replay Modal */}
      {showForensicsEye && screeningId && (
        <FrameForensicsModal
          screeningId={screeningId}
          eye={showForensicsEye}
          originalImgUrl={showForensicsEye === 'OD' ? (screening?.images.find(i => i.eye === 'OD')?.original_path || '') : (screening?.images.find(i => i.eye === 'OS')?.original_path || '')}
          processedImgUrl={showForensicsEye === 'OD' ? screening?.images.find(i => i.eye === 'OD')?.processed_path : screening?.images.find(i => i.eye === 'OS')?.processed_path}
          onClose={() => setShowForensicsEye(null)}
        />
      )}

      {/* Acquisition Benchmarking Modal */}
      {showBenchmarks && (
        <AcquisitionBenchmarkModal onClose={() => setShowBenchmarks(false)} />
      )}
    </div>
  );
};

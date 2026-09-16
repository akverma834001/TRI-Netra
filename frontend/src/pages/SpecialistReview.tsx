import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { ScreeningSession, EyeImage } from '../types';
import { LayerViewer } from '../components/LayerViewer';
import { TrustPanel } from '../components/TrustPanel';
import { FrameForensicsModal } from '../components/FrameForensicsModal';
import { Eye, ShieldCheck, Check, Edit3, RotateCcw, AlertTriangle, FileText, Activity, Camera, Sliders } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  screeningId: string;
  onReferralGenerated: (referralId: string) => void;
  lang: Language;
}

export const SpecialistReview: React.FC<Props> = ({
  screeningId,
  onReferralGenerated,
  lang
}) => {
  const t = translations[lang];
  const [screening, setScreening] = useState<ScreeningSession | null>(null);
  const [activeEye, setActiveEye] = useState<'OD' | 'OS'>('OD');
  const [loading, setLoading] = useState(true);

  // Clinician Action Form State
  const [decision, setDecision] = useState<'CONFIRM' | 'MODIFY' | 'REQUEST_RECAPTURE' | 'ESCALATE' | 'UNABLE_TO_ASSESS'>('CONFIRM');
  const [overrideGrade, setOverrideGrade] = useState('2');
  const [overrideReason, setOverrideReason] = useState('Peripheral hemorrhage burden exceeds automated detector boundary.');
  const [specialistNotes, setSpecialistNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);
  const [showForensics, setShowForensics] = useState(false);

  useEffect(() => {
    const fetchCase = async () => {
      try {
        const sc = await api.getScreening(screeningId);
        setScreening(sc);
      } catch (err) {
        console.error("Error fetching screening:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchCase();
  }, [screeningId]);

  if (loading) {
    return <div className="card" style={{ textAlign: 'center', padding: '60px' }}>Loading Specialist Workstation...</div>;
  }

  if (!screening) {
    return <div className="card" style={{ textAlign: 'center', padding: '60px' }}>Screening record not found: {screeningId}</div>;
  }

  const activeImage = screening.images.find(img => img.eye === activeEye) || screening.images[0];

  const handleSubmitReview = async () => {
    setSubmitting(true);
    try {
      await api.submitReview(screening.id, {
        decision,
        override_grade: decision === 'MODIFY' ? overrideGrade : undefined,
        override_reason: decision === 'MODIFY' ? overrideReason : undefined,
        specialist_notes: specialistNotes
      });
      setReviewSubmitted(true);
      alert(`Clinician review recorded: ${decision}`);
      // Refresh case
      const updated = await api.getScreening(screening.id);
      setScreening(updated);
    } catch (err) {
      alert("Error submitting review: " + err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateReferral = async () => {
    try {
      const ref = await api.generateReferral(screening.id);
      onReferralGenerated(ref.id);
    } catch (err) {
      alert("Error generating referral: " + err);
    }
  };

  return (
    <div>
      {/* Patient Header Banner */}
      <div className="card" style={{ marginBottom: '18px', padding: '16px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
              TRINETRA | District Tele-Ophthalmology Review Console
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)', marginTop: '2px' }}>
              Patient: {screening.patient.full_name}
              <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-muted)', marginLeft: '10px' }}>
                ({screening.patient.age}y / {screening.patient.sex}) • ID: {screening.patient.id}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {screening.phc_facility} • Diabetes: {screening.patient.diabetes_type} ({screening.patient.diabetes_duration_years} yrs) • Symptoms: {screening.patient.symptoms}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary btn-sm" onClick={handleCreateReferral}>
              <FileText size={14} />
              <span>Generate Structured Referral</span>
            </button>
          </div>
        </div>
      </div>

      {/* Bilateral Eye Selector Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button
          className={`btn ${activeEye === 'OD' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveEye('OD')}
        >
          <Eye size={16} />
          <span>Right Eye (OD)</span>
          {screening.images.find(i => i.eye === 'OD')?.ai_result && (
            <span style={{ background: 'rgba(255,255,255,0.2)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>
              Grade {screening.images.find(i => i.eye === 'OD')?.ai_result?.predicted_grade}
            </span>
          )}
        </button>

        <button
          className={`btn ${activeEye === 'OS' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveEye('OS')}
        >
          <Eye size={16} />
          <span>Left Eye (OS)</span>
          {screening.images.find(i => i.eye === 'OS')?.ai_result && (
            <span style={{ background: 'rgba(255,255,255,0.2)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>
              Grade {screening.images.find(i => i.eye === 'OS')?.ai_result?.predicted_grade}
            </span>
          )}
        </button>
      </div>

      {/* Optical Acquisition Provenance Banner */}
      {activeImage && (
        <div style={{
          background: 'var(--bg-subtle)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 18px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Acquisition Mode:</span>{' '}
              <strong style={{ color: 'var(--brand-cyan)' }}>
                {activeImage.optical_mode === 'MODE_1_BARE_PHONE' ? 'Mode 1: Bare Phone Screening' : activeImage.optical_mode === 'MODE_3_RESEARCH' ? 'Mode 3: Research Geometry' : 'Mode 2: Passive Optic (+20D)'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Optic:</span>{' '}
              <strong>{activeImage.lens_power || '+20D Condensing Optic'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Method:</span>{' '}
              <span className="badge badge-emerald" style={{ fontSize: '10px' }}>
                {activeImage.capture_method || 'AUTONOMOUS BEST-FRAME'}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Quality Index:</span>{' '}
              <strong style={{ color: activeImage.quality_score >= 70 ? 'var(--brand-emerald)' : 'var(--brand-amber)' }}>
                {activeImage.quality_score} / 100
              </strong>
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowForensics(true)}
            style={{ fontSize: '12px', padding: '5px 12px' }}
          >
            <Activity size={14} color="var(--brand-cyan)" />
            <span>Frame Forensics & Replay</span>
          </button>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '20px' }}>
        {/* Left: Retinal Image Canvas */}
        <div>
          <LayerViewer
            image={activeImage}
            eyeLabel={activeEye === 'OD' ? "Right Eye (OD)" : "Left Eye (OS)"}
          />

          {/* 12-D Retinal Biomarker Vector Table */}
          {activeImage?.biomarkers && (
            <div className="card" style={{ marginTop: '20px', padding: '16px' }}>
              <h4 style={{ fontSize: '14px', marginBottom: '12px' }}>
                Extracted 12-Dimensional Retinal Biomarker Vector
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', fontSize: '12px' }}>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f1 (MAs):</strong> {activeImage.biomarkers.f1_ma_count}
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f2 (Exudates):</strong> {activeImage.biomarkers.f2_exudate_area} px
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f3 (Foveal Dist):</strong> {activeImage.biomarkers.f3_foveal_dist.toFixed(2)} DD
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f4 (Hemorrhages):</strong> {activeImage.biomarkers.f4_hemorrhage_count}
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f5 (Hemo/Vessel):</strong> {activeImage.biomarkers.f5_hemo_vessel_ratio.toFixed(3)}
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f6 (Tortuosity):</strong> {activeImage.biomarkers.f6_tortuosity.toFixed(3)}
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f7 (Branch Density):</strong> {activeImage.biomarkers.f7_branch_density.toFixed(3)}
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f8-f11 (Quadrants):</strong> [{activeImage.biomarkers.f8_quad1}, {activeImage.biomarkers.f9_quad2}, {activeImage.biomarkers.f10_quad3}, {activeImage.biomarkers.f11_quad4}]
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: '8px', borderRadius: '4px' }}>
                  <strong>f12 (Sharpness Φ):</strong> {activeImage.biomarkers.f12_sharpness.toFixed(1)}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Trust Panel & Human-in-the-Loop Actions */}
        <div>
          <TrustPanel
            aiResult={activeImage?.ai_result}
            biomarkers={activeImage?.biomarkers}
            eyeLabel={activeEye === 'OD' ? "Right Eye (OD)" : "Left Eye (OS)"}
          />

          {/* Clinician Decision Console */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} color="var(--brand-cyan)" />
                <h4 style={{ margin: 0 }}>Human-in-the-Loop Clinician Action</h4>
              </div>
              <span className="badge badge-purple">Specialist Authority</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
              <button
                className={`btn ${decision === 'CONFIRM' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setDecision('CONFIRM')}
                style={{ fontSize: '12px' }}
              >
                <Check size={14} /> Confirm Finding
              </button>
              <button
                className={`btn ${decision === 'MODIFY' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setDecision('MODIFY')}
                style={{ fontSize: '12px' }}
              >
                <Edit3 size={14} /> Override Grade
              </button>
              <button
                className={`btn ${decision === 'REQUEST_RECAPTURE' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setDecision('REQUEST_RECAPTURE')}
                style={{ fontSize: '12px' }}
              >
                <RotateCcw size={14} /> Recapture
              </button>
              <button
                className={`btn ${decision === 'ESCALATE' ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => setDecision('ESCALATE')}
                style={{ fontSize: '12px' }}
              >
                <AlertTriangle size={14} /> Escalate
              </button>
            </div>

            {decision === 'MODIFY' && (
              <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
                <div className="form-group">
                  <label className="form-label">Specialist Grade Assignment</label>
                  <select className="form-select" value={overrideGrade} onChange={e => setOverrideGrade(e.target.value)}>
                    <option value="0">Grade 0 — No apparent DR</option>
                    <option value="1">Grade 1 — Mild NPDR</option>
                    <option value="2">Grade 2 — Moderate NPDR</option>
                    <option value="3">Grade 3 — Severe NPDR</option>
                    <option value="4">Grade 4 — Proliferative DR</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Mandatory Clinical Override Rationale</label>
                  <input
                    className="form-input"
                    value={overrideReason}
                    onChange={e => setOverrideReason(e.target.value)}
                    placeholder="Document clinical justification for audit log"
                  />
                </div>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Specialist Consultation Notes</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={specialistNotes}
                onChange={e => setSpecialistNotes(e.target.value)}
                placeholder="Enter notes for primary care operator or patient referral note..."
              />
            </div>

              <button
                className="btn btn-primary"
                onClick={handleSubmitReview}
                disabled={submitting}
                style={{ width: '100%' }}
              >
                {submitting ? "Recording Audit & Disposition..." : "Submit Clinician Assessment"}
              </button>
            </div>
          </div>
        </div>

        {/* Forensics Modal */}
        {showForensics && activeImage && (
          <FrameForensicsModal
            screeningId={screening.id}
            eye={activeEye}
            originalImgUrl={activeImage.original_path}
            processedImgUrl={activeImage.processed_path}
            onClose={() => setShowForensics(false)}
          />
        )}
      </div>
    );
  };

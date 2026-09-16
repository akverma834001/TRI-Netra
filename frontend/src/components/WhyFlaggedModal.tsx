import React from 'react';
import { AIResult, BiomarkerVector } from '../types';
import { X, AlertCircle, Info, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  aiResult: AIResult;
  biomarkers?: BiomarkerVector;
  eyeLabel: string;
}

export const WhyFlaggedModal: React.FC<Props> = ({
  isOpen,
  onClose,
  aiResult,
  biomarkers,
  eyeLabel
}) => {
  if (!isOpen) return null;

  const getEvidenceList = () => {
    const list: string[] = [];
    if (biomarkers) {
      if (biomarkers.f1_ma_count > 0) {
        list.push(`Detected ${biomarkers.f1_ma_count} microaneurysm candidates in inverted green channel`);
      }
      if (biomarkers.f4_hemorrhage_count > 0) {
        list.push(`Detected ${biomarkers.f4_hemorrhage_count} intraretinal blot/flame hemorrhages (Total Area: ${biomarkers.f2_exudate_area} px)`);
      }
      if (aiResult.macular_risk_flag) {
        list.push(`Hard exudate cluster located within 1.0 Optic Disc Diameter from the foveal avascular center (${biomarkers.f3_foveal_dist.toFixed(2)} DD)`);
      }
      if (biomarkers.f6_tortuosity > 1.40) {
        list.push(`Elevated vascular tortuosity index (${biomarkers.f6_tortuosity.toFixed(2)} vs normal 1.05-1.25)`);
      }
      if (aiResult.pdr_evidence_flag) {
        list.push(`Fine irregular vessel proliferation candidates detected (potential neovascularization)`);
      }
    }
    if (list.length === 0) {
      list.push("No significant microvascular lesions detected. Homogeneous retinal reflectance.");
    }
    return list;
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--bg-surface)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-color)',
        maxWidth: '680px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '24px',
        boxShadow: 'var(--shadow-lg)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '14px', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Info size={20} color="var(--brand-cyan)" />
            <h3 style={{ margin: 0 }}>Clinical Rationale & Evidence Breakdown ({eyeLabel})</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            AI Screening Assessment
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>
            Grade {aiResult.predicted_grade}: {aiResult.predicted_label}
          </div>
        </div>

        {/* Detected Biomarkers List */}
        <div style={{ background: 'var(--bg-subtle)', padding: '16px', borderRadius: 'var(--radius-md)', marginBottom: '20px' }}>
          <h4 style={{ fontSize: '14px', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertCircle size={16} color="var(--brand-amber)" /> Contributing Clinical Biomarkers Detected:
          </h4>
          <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: 'var(--text-primary)' }}>
            {getEvidenceList().map((item, idx) => (
              <li key={idx} style={{ marginBottom: '6px' }}>{item}</li>
            ))}
          </ul>
        </div>

        {/* Probabilities Distribution */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
            Model Softmax Class Probabilities (Calibrated T=1.15):
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {['0 — No DR', '1 — Mild', '2 — Moderate', '3 — Severe', '4 — PDR'].map((label, idx) => {
              const prob = (aiResult.probabilities[idx] || 0) * 100;
              return (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', fontSize: '12px', gap: '8px' }}>
                  <span style={{ width: '100px', color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
                  <div style={{ flex: 1, height: '8px', background: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${prob}%`,
                      height: '100%',
                      background: idx === Number(aiResult.predicted_grade) ? 'var(--brand-cyan)' : 'var(--text-muted)',
                      borderRadius: '4px'
                    }} />
                  </div>
                  <span style={{ width: '45px', textAlign: 'right', fontWeight: 600 }}>{prob.toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Safety Limitation Notice */}
        <div style={{
          borderLeft: '4px solid var(--brand-amber)',
          background: 'var(--brand-amber-light)',
          padding: '12px 16px',
          borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
          fontSize: '12px',
          color: 'var(--text-primary)',
          lineHeight: '1.5'
        }}>
          <strong>Clinical Verification Imperative:</strong> Highlighted regions and biomarkers contributed to the model's prediction and must be interpreted as AI evidence, not a standalone diagnosis. All findings require confirmation by a licensed ophthalmologist via slit-lamp biomicroscopy.
        </div>

        <div style={{ marginTop: '20px', textAlign: 'right' }}>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            Close Rationale
          </button>
        </div>
      </div>
    </div>
  );
};

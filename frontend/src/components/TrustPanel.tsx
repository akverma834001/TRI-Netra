import React, { useState } from 'react';
import { AIResult, BiomarkerVector } from '../types';
import { ShieldCheck, AlertTriangle, HelpCircle, Activity, Info, AlertOctagon } from 'lucide-react';
import { WhyFlaggedModal } from './WhyFlaggedModal';

interface Props {
  aiResult: AIResult | undefined;
  biomarkers?: BiomarkerVector;
  eyeLabel: string;
}

export const TrustPanel: React.FC<Props> = ({ aiResult, biomarkers, eyeLabel }) => {
  const [showModal, setShowModal] = useState(false);

  if (!aiResult) {
    return (
      <div className="card" style={{ padding: '24px', textAlign: 'center' }}>
        <Activity size={32} color="var(--text-muted)" style={{ margin: '0 auto 10px auto' }} />
        <h4 style={{ color: 'var(--text-secondary)' }}>AI Clinical Trust Panel</h4>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Awaiting retinal analysis execution for {eyeLabel}.
        </p>
      </div>
    );
  }

  const getGradeBadge = () => {
    switch (aiResult.predicted_grade) {
      case '0':
        return <span className="badge badge-emerald">Grade 0 — No Apparent DR</span>;
      case '1':
        return <span className="badge badge-cyan">Grade 1 — Mild NPDR</span>;
      case '2':
        return <span className="badge badge-amber">Grade 2 — Moderate NPDR</span>;
      case '3':
        return <span className="badge badge-rose">Grade 3 — Severe NPDR</span>;
      case '4':
        return <span className="badge badge-purple">Grade 4 — Proliferative DR</span>;
      default:
        return <span className="badge badge-rose">Grade U — Unable to Assess</span>;
    }
  };

  return (
    <div className="card" style={{ borderLeft: '4px solid var(--brand-cyan)' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={20} color="var(--brand-cyan)" />
          <h4 style={{ margin: 0 }}>Clinical Trust Panel — {eyeLabel}</h4>
        </div>
        {getGradeBadge()}
      </div>

      {/* OOD Alert if Withheld */}
      {aiResult.is_ood && (
        <div style={{
          background: 'var(--brand-rose-light)',
          color: 'var(--brand-rose)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: 700,
          fontSize: '13px'
        }}>
          <AlertOctagon size={20} />
          <div>{aiResult.ood_status_message || "AI RESULT WITHHELD — Out of Distribution"}</div>
        </div>
      )}

      {/* Primary Assessment Banner */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
          AI Screening Finding
        </div>
        <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginTop: '2px' }}>
          {aiResult.predicted_label}
        </div>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          {aiResult.recommendation}
        </div>
      </div>

      {/* Clinical Risk Flags */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
        <div style={{
          padding: '10px',
          borderRadius: 'var(--radius-sm)',
          background: aiResult.macular_risk_flag ? 'var(--brand-rose-light)' : 'var(--bg-subtle)',
          border: `1px solid ${aiResult.macular_risk_flag ? 'var(--brand-rose)' : 'var(--border-color)'}`
        }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: aiResult.macular_risk_flag ? 'var(--brand-rose)' : 'var(--text-muted)' }}>
            MACULAR / DME RISK
          </div>
          <div style={{ fontSize: '13px', fontWeight: 700, marginTop: '2px', color: aiResult.macular_risk_flag ? 'var(--brand-rose)' : 'var(--text-primary)' }}>
            {aiResult.macular_risk_flag ? "RISK FLAG DETECTED" : "No Significant Risk"}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {aiResult.macular_risk_reason}
          </div>
        </div>

        <div style={{
          padding: '10px',
          borderRadius: 'var(--radius-sm)',
          background: aiResult.pdr_evidence_flag ? 'var(--brand-purple-light)' : 'var(--bg-subtle)',
          border: `1px solid ${aiResult.pdr_evidence_flag ? 'var(--brand-purple)' : 'var(--border-color)'}`
        }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: aiResult.pdr_evidence_flag ? 'var(--brand-purple)' : 'var(--text-muted)' }}>
            PDR PROLIFERATIVE EVIDENCE
          </div>
          <div style={{ fontSize: '13px', fontWeight: 700, marginTop: '2px', color: aiResult.pdr_evidence_flag ? 'var(--brand-purple)' : 'var(--text-primary)' }}>
            {aiResult.pdr_evidence_flag ? "PROLIFERATIVE EVIDENCE" : "None Detected"}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {aiResult.pdr_evidence_details}
          </div>
        </div>
      </div>

      {/* Uncertainty & Calibration Matrix */}
      <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)', marginBottom: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Calibrated Conf.</div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--brand-cyan)', marginTop: '2px' }}>
              {(aiResult.calibrated_confidence * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Softmax T=1.15</div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>Epistemic Unc.</div>
            <div style={{
              fontSize: '16px',
              fontWeight: 800,
              color: aiResult.epistemic_uncertainty > 0.40 ? 'var(--brand-rose)' : 'var(--brand-emerald)',
              marginTop: '2px'
            }}>
              {aiResult.epistemic_uncertainty.toFixed(3)}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>MC Dropout (T=10)</div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>OOD Metric</div>
            <div style={{
              fontSize: '16px',
              fontWeight: 800,
              color: aiResult.is_ood ? 'var(--brand-rose)' : 'var(--text-primary)',
              marginTop: '2px'
            }}>
              {aiResult.ood_score.toFixed(2)}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Cutoff: 4.20</div>
          </div>
        </div>
      </div>

      {/* Why Flagged & Metadata footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          <span>Model: <strong>{aiResult.model_name}</strong> (v{aiResult.model_version})</span>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setShowModal(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <HelpCircle size={14} color="var(--brand-cyan)" />
          <span>Why was this flagged?</span>
        </button>
      </div>

      <WhyFlaggedModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        aiResult={aiResult}
        biomarkers={biomarkers}
        eyeLabel={eyeLabel}
      />
    </div>
  );
};

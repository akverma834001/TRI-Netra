import React from 'react';
import { Eye, Shield, ArrowRight, Play, CheckCircle2, AlertTriangle, Layers, Cpu, HeartPulse } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  onStartScreening: () => void;
  onSelectDemoCase: (screeningId: string) => void;
  lang: Language;
}

const DEMO_CASES = [
  { id: "SCR-DEMO-01", label: "Case A: Normal Retina", desc: "Grade 0, healthy baseline, low uncertainty", priority: "ROUTINE", tag: "Routine" },
  { id: "SCR-DEMO-02", label: "Case B: Mild NPDR", desc: "Grade 1, microaneurysms detected", priority: "PRIORITY", tag: "Priority" },
  { id: "SCR-DEMO-03", label: "Case C: Moderate NPDR", desc: "Grade 2, hemorrhages & exudates", priority: "URGENT", tag: "Urgent" },
  { id: "SCR-DEMO-04", label: "Case D: Severe NPDR", desc: "Grade 3, 4-quadrant hemorrhages", priority: "URGENT", tag: "Urgent" },
  { id: "SCR-DEMO-05", label: "Case E: Proliferative DR", desc: "Grade 4, neovascularization fronds (NVD)", priority: "EMERGENCY", tag: "Emergency" },
  { id: "SCR-DEMO-06", label: "Case F: Macular / DME Risk", desc: "Hard exudates encroaching onto fovea (< 1 DD)", priority: "EMERGENCY", tag: "DME Risk" },
  { id: "SCR-DEMO-07", label: "Case G: Poor Quality", desc: "Ungradable (defocus blur & shadow occlusion)", priority: "ROUTINE", tag: "Recapture" },
  { id: "SCR-DEMO-08", label: "Case H: High Uncertainty", desc: "Borderline case with high epistemic variance", priority: "PRIORITY", tag: "Uncertainty" },
  { id: "SCR-DEMO-09", label: "Case I: Out-of-Distribution", desc: "Non-retinal target (AI Result Withheld)", priority: "PRIORITY", tag: "OOD Gated" },
  { id: "SCR-DEMO-10", label: "Case J: Other Abnormality", desc: "Chorioretinal scar / drusen confluence", priority: "PRIORITY", tag: "Non-DR Flag" }
];

export const LandingPage: React.FC<Props> = ({ onStartScreening, onSelectDemoCase, lang }) => {
  const t = translations[lang];

  return (
    <div>
      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        padding: '48px 20px 32px 20px',
        maxWidth: '960px',
        margin: '0 auto'
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: 'var(--brand-cyan-light)',
          color: 'var(--brand-cyan)',
          padding: '6px 14px',
          borderRadius: 'var(--radius-full)',
          fontSize: '12px',
          fontWeight: 700,
          letterSpacing: '0.06em',
          marginBottom: '20px'
        }}>
          <Eye size={14} /> {t.tagline}
        </div>

        <h1 style={{ fontSize: '46px', lineHeight: '1.15', marginBottom: '16px', color: 'var(--text-primary)' }}>
          {t.brand_name} <span style={{ color: 'var(--brand-cyan)' }}>({t.brand_hindi})</span>
        </h1>
        <p style={{ fontSize: '18px', color: 'var(--text-secondary)', lineHeight: '1.6', maxWidth: '720px', margin: '0 auto 32px auto' }}>
          {t.subtitle}. Distributed clinical intelligence connecting primary health centers with district tele-retina networks.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <button className="btn btn-primary btn-lg" onClick={onStartScreening}>
            <span>{t.btn_start_screening}</span>
            <ArrowRight size={18} />
          </button>
          <a href="#demo-section" className="btn btn-secondary btn-lg">
            <Play size={16} />
            <span>{t.btn_view_demo}</span>
          </a>
        </div>
      </div>

      {/* Three Eye Pillars */}
      <div className="grid-3" style={{ marginBottom: '48px' }}>
        <div className="card" style={{ borderTop: '4px solid #0284c7' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(2, 132, 199, 0.1)', color: '#0284c7' }}>
              <Eye size={22} />
            </div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>{t.eye_1_title}</h3>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            {t.eye_1_desc}. Dynamic FOV extraction, 8×8 Lab L* illumination heatmap, and Laplacian focus sharpness (Φ ≥ 110) gating.
          </p>
        </div>

        <div className="card" style={{ borderTop: '4px solid #059669' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(5, 150, 105, 0.1)', color: '#059669' }}>
              <Cpu size={22} />
            </div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>{t.eye_2_title}</h3>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            {t.eye_2_desc}. Optic disc Hough/contour, multi-scale Frangi vessels, 12-D biomarker vector, and Monte Carlo Dropout uncertainty (T=10).
          </p>
        </div>

        <div className="card" style={{ borderTop: '4px solid #7c3aed' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(124, 58, 237, 0.1)', color: '#7c3aed' }}>
              <HeartPulse size={22} />
            </div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>{t.eye_3_title}</h3>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            {t.eye_3_desc}. Specialist tele-ophthalmology console, human-in-the-loop review, bilingual referral note generator, and offline sync.
          </p>
        </div>
      </div>

      {/* 10 Clinical Demonstration Cases Matrix */}
      <div id="demo-section" className="card" style={{ marginBottom: '40px' }}>
        <div className="card-header">
          <div>
            <h3 style={{ fontSize: '20px', margin: 0 }}>10 Pre-Staged Ground-Truth Clinical Cases</h3>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Select any benchmark scenario to immediately inspect genuine optical quality, neural inference, and explainability layers.
            </div>
          </div>
          <span className="badge badge-cyan">Full Spectrum Benchmark</span>
        </div>

        <div className="grid-2">
          {DEMO_CASES.map(c => (
            <div
              key={c.id}
              onClick={() => onSelectDemoCase(c.id)}
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--brand-cyan)';
                e.currentTarget.style.transform = 'translateX(4px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.transform = 'none';
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <strong style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{c.label}</strong>
                  <span className={`badge badge-${c.priority === 'EMERGENCY' ? 'rose' : c.priority === 'URGENT' ? 'amber' : 'emerald'}`} style={{ fontSize: '10px' }}>
                    {c.tag}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{c.desc}</div>
              </div>
              <ArrowRight size={16} color="var(--brand-cyan)" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

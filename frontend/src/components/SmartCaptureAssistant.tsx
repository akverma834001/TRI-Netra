import React from 'react';
import { EyeQuality } from '../types';
import { Camera, CheckCircle, AlertTriangle, XCircle, Focus, Sun, Maximize } from 'lucide-react';

interface Props {
  quality: EyeQuality | null;
  eyeLabel: string;
}

export const SmartCaptureAssistant: React.FC<Props> = ({ quality, eyeLabel }) => {
  if (!quality) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '30px', borderStyle: 'dashed' }}>
        <Camera size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px auto' }} />
        <h4 style={{ color: 'var(--text-secondary)' }}>Optical Gatekeeper Ready for {eyeLabel}</h4>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Position the fundus camera aperture. Real-time focus and illumination guidance will appear upon image capture.
        </p>
      </div>
    );
  }

  const getStatusBadge = () => {
    switch (quality.quality_status) {
      case 'Excellent':
        return <span className="badge badge-emerald"><CheckCircle size={12} /> Excellent Quality</span>;
      case 'Acceptable':
        return <span className="badge badge-cyan"><CheckCircle size={12} /> Acceptable Quality</span>;
      case 'Marginal':
        return <span className="badge badge-amber"><AlertTriangle size={12} /> Marginal Quality</span>;
      default:
        return <span className="badge badge-rose"><XCircle size={12} /> Ungradable (Recapture Advised)</span>;
    }
  };

  return (
    <div className="card" style={{ borderColor: quality.passed ? 'var(--brand-emerald)' : 'var(--brand-rose)' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Camera size={18} color="var(--brand-cyan)" />
          <h4 style={{ margin: 0 }}>Smart Capture Gatekeeper — {eyeLabel}</h4>
        </div>
        {getStatusBadge()}
      </div>

      {/* Live Operator Guidance HUD Banner */}
      <div style={{
        padding: '12px 16px',
        borderRadius: 'var(--radius-sm)',
        background: quality.passed ? 'var(--brand-emerald-light)' : 'var(--brand-rose-light)',
        color: quality.passed ? 'var(--brand-emerald)' : 'var(--brand-rose)',
        fontWeight: 700,
        fontSize: '14px',
        textAlign: 'center',
        marginBottom: '16px',
        letterSpacing: '0.04em'
      }}>
        {quality.guidance_message}
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', textAlign: 'center' }}>
        <div style={{ background: 'var(--bg-subtle)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <Focus size={13} /> Focus Sharpness (Φ)
          </div>
          <div style={{ fontSize: '18px', fontWeight: 700, marginTop: '4px', color: quality.focus_score >= 110 ? 'var(--brand-emerald)' : 'var(--brand-rose)' }}>
            {quality.focus_score}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Calibrated Cutoff: ≥ 110.0</div>
        </div>

        <div style={{ background: 'var(--bg-subtle)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <Sun size={13} /> 8×8 Illum Variation
          </div>
          <div style={{ fontSize: '18px', fontWeight: 700, marginTop: '4px', color: quality.illumination_uniformity <= 18 ? 'var(--brand-emerald)' : 'var(--brand-amber)' }}>
            σ = {quality.illumination_uniformity}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Uniformity Limit: ≤ 18.0</div>
        </div>

        <div style={{ background: 'var(--bg-subtle)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
            <Maximize size={13} /> Overall Quality Score
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, marginTop: '4px', color: 'var(--brand-cyan)' }}>
            {quality.quality_score} / 100
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Weighted Optical Index</div>
        </div>
      </div>

      {quality.failure_reasons.length > 0 && (
        <div style={{ marginTop: '14px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <strong>Identified Optical Deficits:</strong>
          <ul style={{ paddingLeft: '20px', marginTop: '4px' }}>
            {quality.failure_reasons.map((r, i) => (
              <li key={i} style={{ color: 'var(--brand-rose)', fontWeight: 500 }}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

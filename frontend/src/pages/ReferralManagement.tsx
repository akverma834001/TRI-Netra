import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Referral } from '../types';
import { FileText, Printer, CheckCircle, Clock, Send, Eye } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  selectedReferralId?: string | null;
  lang: Language;
}

export const ReferralManagement: React.FC<Props> = ({ selectedReferralId, lang }) => {
  const t = translations[lang];
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [selectedRef, setSelectedRef] = useState<Referral | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReferrals = async () => {
      try {
        const list = await api.listReferrals();
        setReferrals(list);
        if (selectedReferralId) {
          const match = list.find(r => r.id === selectedReferralId);
          if (match) setSelectedRef(match);
        } else if (list.length > 0) {
          setSelectedRef(list[0]);
        }
      } catch (err) {
        console.error("Error fetching referrals:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchReferrals();
  }, [selectedReferralId]);

  const handleStatusChange = async (referralId: string, newStatus: string) => {
    try {
      await api.updateReferralStatus(referralId, newStatus);
      const list = await api.listReferrals();
      setReferrals(list);
      const updated = list.find(r => r.id === referralId);
      if (updated) setSelectedRef(updated);
    } catch (err) {
      alert("Error updating status: " + err);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '28px', color: 'var(--text-primary)', margin: 0 }}>
            Referral Logistics & Patient Communication
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Structured Bilingual Tele-Ophthalmology Dispatch Notes & Appointment Tracking
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '24px' }}>
        {/* Left: Referrals List */}
        <div className="card">
          <div className="card-header">
            <h3 style={{ fontSize: '18px', margin: 0 }}>Active Referrals Tracker</h3>
            <span className="badge badge-cyan">{referrals.length} Dispatched</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {referrals.map(r => (
              <div
                key={r.id}
                onClick={() => setSelectedRef(r)}
                style={{
                  background: selectedRef?.id === r.id ? 'var(--brand-cyan-light)' : 'var(--bg-subtle)',
                  border: `1px solid ${selectedRef?.id === r.id ? 'var(--brand-cyan)' : 'var(--border-color)'}`,
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <strong style={{ fontSize: '14px' }}>{r.id}</strong>
                  <span className={`badge badge-${r.priority === 'EMERGENCY' ? 'rose' : r.priority === 'URGENT' ? 'amber' : 'emerald'}`}>
                    {r.priority}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Patient: <strong>{r.patient_id}</strong> • Destination: {r.destination_facility}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                  <span>Status: <strong>{r.status}</strong></span>
                  <span>{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Selected Referral Detail & Note Preview */}
        {selectedRef ? (
          <div className="card">
            <div className="card-header">
              <div>
                <h3 style={{ fontSize: '18px', margin: 0 }}>Structured Referral Document</h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>ID: {selectedRef.id}</div>
              </div>
              <a
                href={api.getPrintableReferralUrl(selectedRef.id)}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary btn-sm"
              >
                <Printer size={14} />
                <span>Print / Save PDF</span>
              </a>
            </div>

            {/* Status Change Control */}
            <div style={{ background: 'var(--bg-subtle)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '12px', fontWeight: 600 }}>Tracking Lifecycle Status:</span>
              <select
                className="form-select"
                style={{ width: 'auto', padding: '4px 8px', fontSize: '12px' }}
                value={selectedRef.status}
                onChange={e => handleStatusChange(selectedRef.id, e.target.value)}
              >
                <option value="APPOINTMENT_REQUESTED">Appointment Requested</option>
                <option value="APPOINTMENT_SCHEDULED">Appointment Scheduled</option>
                <option value="SPECIALIST_REVIEWED">Specialist Reviewed</option>
                <option value="FOLLOW_UP_REQUIRED">Follow-up Required</option>
                <option value="COMPLETED">Completed</option>
              </select>
            </div>

            {/* Bilingual Clinical Notes */}
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                English Clinical Summary:
              </h4>
              <pre style={{
                background: 'var(--bg-subtle)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                whiteSpace: 'pre-wrap',
                fontFamily: 'inherit',
                color: 'var(--text-primary)',
                maxHeight: '180px',
                overflowY: 'auto'
              }}>
                {selectedRef.clinical_summary_en}
              </pre>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Hindi Referral Note (हिंदी सारांश):
              </h4>
              <pre style={{
                background: 'var(--bg-subtle)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                whiteSpace: 'pre-wrap',
                fontFamily: 'inherit',
                color: 'var(--text-primary)',
                maxHeight: '160px',
                overflowY: 'auto'
              }}>
                {selectedRef.clinical_summary_hi}
              </pre>
            </div>

            {/* Patient Friendly SMS / WhatsApp Preview */}
            <div style={{ background: '#0284c715', border: '1px solid #0284c740', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 700, color: 'var(--brand-cyan)', marginBottom: '6px' }}>
                <Send size={14} />
                <span>Patient WhatsApp / SMS Notification Text</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: '1.5' }}>
                {selectedRef.patient_message_hi}
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            Select a referral to view structured notes
          </div>
        )}
      </div>
    </div>
  );
};

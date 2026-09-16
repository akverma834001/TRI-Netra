import React, { useState } from 'react';
import { api } from '../services/api';
import { Patient, PatientLookupResult, PatientHistoryResponse, PatientHistoryScreening } from '../types';
import { Search, Phone, User, Calendar, Clock, Eye, AlertCircle, CheckCircle2, ChevronRight, X, ArrowRight, ShieldCheck, History } from 'lucide-react';

interface Props {
  onClose: () => void;
  onSelectPatient: (patient: Patient, resumeScreeningId?: string) => void;
}

export const FindPatientModal: React.FC<Props> = ({ onClose, onSelectPatient }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<PatientLookupResult | null>(null);
  const [searched, setSearched] = useState(false);

  // Longitudinal History State
  const [historyLoading, setHistoryLoading] = useState(false);
  const [patientHistory, setPatientHistory] = useState<PatientHistoryResponse | null>(null);
  const [selectedScreening, setSelectedScreening] = useState<PatientHistoryScreening | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = phoneNumber.trim();
    if (!query) {
      setError('Please enter a mobile phone number to search.');
      return;
    }
    setError(null);
    setLoading(true);
    setPatientHistory(null);
    setSelectedScreening(null);
    try {
      const res = await api.lookupPatientByPhone(query);
      setLookupResult(res);
      setSearched(true);
    } catch (err: any) {
      setError(err.message || 'Error occurred while searching for patient.');
      setLookupResult(null);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchHistory = async (patientId: string) => {
    setHistoryLoading(true);
    setError(null);
    try {
      const history = await api.getPatientHistory(patientId);
      setPatientHistory(history);
      if (history.screenings && history.screenings.length > 0) {
        setSelectedScreening(history.screenings[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve longitudinal patient history.');
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(3, 7, 18, 0.85)',
      backdropFilter: 'blur(6px)',
      zIndex: 10000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div className="card" style={{
        maxWidth: patientHistory ? '900px' : '620px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto',
        position: 'relative',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-color)',
          paddingBottom: '14px',
          marginBottom: '20px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(6, 182, 212, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--brand-cyan)'
            }}>
              <Search size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px' }}>Patient Lookup & Longitudinal History</h3>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Search by registered phone number across all screenings
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary"
            style={{ padding: '6px', borderRadius: '50%', minWidth: '32px', height: '32px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Search Input Form */}
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Phone size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="form-input"
              style={{ paddingLeft: '38px', fontSize: '14px' }}
              placeholder="Enter mobile number (e.g. 9876543210 or +91 98450 12345)"
              value={phoneNumber}
              onChange={e => setPhoneNumber(e.target.value)}
              autoFocus
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Searching...' : 'Search Patient'}
          </button>
        </form>

        {/* Error Message */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px',
            color: '#f87171',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '16px'
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Search Results */}
        {searched && !loading && (
          <div>
            {lookupResult?.found && lookupResult.patient ? (
              <div style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '18px',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '17px', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {lookupResult.patient.full_name}
                      </span>
                      <span className="badge badge-cyan" style={{ fontSize: '11px' }}>
                        ID: {lookupResult.patient.id}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Phone: <strong>{lookupResult.patient.phone}</strong> • {lookupResult.patient.age}y / {lookupResult.patient.sex}
                    </div>
                  </div>
                  <span className="badge badge-emerald">
                    <CheckCircle2 size={12} style={{ marginRight: '4px' }} />
                    Verified Patient
                  </span>
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '10px',
                  background: 'var(--bg-surface)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '16px',
                  fontSize: '12px'
                }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Diabetes Profile</div>
                    <div style={{ fontWeight: 600, marginTop: '2px' }}>
                      {lookupResult.patient.diabetes_type} ({lookupResult.patient.diabetes_duration_years} yrs)
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Previous Screenings</div>
                    <div style={{ fontWeight: 600, marginTop: '2px' }}>
                      {lookupResult.patient.total_screenings} session(s)
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Last Screened</div>
                    <div style={{ fontWeight: 600, marginTop: '2px' }}>
                      {lookupResult.patient.last_screening_date ? new Date(lookupResult.patient.last_screening_date).toLocaleDateString() : 'Never'}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)' }}>Informed Consent</div>
                    <div style={{ fontWeight: 600, marginTop: '2px', color: lookupResult.patient.consent_obtained ? 'var(--brand-emerald)' : 'var(--brand-amber)' }}>
                      {lookupResult.patient.consent_obtained ? 'Active Consent' : 'Pending'}
                    </div>
                  </div>
                </div>

                {/* Active Unfinished Screening Alert */}
                {lookupResult.unfinished_screening && (
                  <div style={{
                    background: 'rgba(245, 158, 11, 0.12)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px 14px',
                    marginBottom: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--brand-amber)' }}>
                        In-Progress Screening Found: {lookupResult.unfinished_screening.screening_id}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Current Stage: {lookupResult.unfinished_screening.current_step.replace(/_/g, ' ')} (Step {lookupResult.unfinished_screening.current_step_num})
                      </div>
                    </div>
                    <button
                      className="btn btn-primary"
                      style={{ fontSize: '12px', padding: '6px 12px' }}
                      onClick={() => onSelectPatient(lookupResult.patient as any, lookupResult.unfinished_screening?.screening_id)}
                    >
                      <span>Resume Session</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => onSelectPatient(lookupResult.patient as any)}
                  >
                    <PlusIcon />
                    <span>Start New Screening Session</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    onClick={() => handleFetchHistory(lookupResult.patient!.id)}
                    disabled={historyLoading}
                  >
                    <History size={14} />
                    <span>{historyLoading ? 'Loading History...' : 'View Longitudinal History'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '32px 16px',
                background: 'var(--bg-subtle)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-muted)'
              }}>
                <User size={36} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
                <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  No existing patient found with phone {phoneNumber}
                </div>
                <div style={{ fontSize: '13px', marginTop: '4px' }}>
                  You can register this patient as a new screening candidate in Step 1.
                </div>
              </div>
            )}
          </div>
        )}

        {/* Longitudinal Profile View */}
        {patientHistory && (
          <div style={{
            marginTop: '24px',
            borderTop: '1px solid var(--border-color)',
            paddingTop: '20px'
          }}>
            <h4 style={{ margin: '0 0 14px', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={16} color="var(--brand-cyan)" />
              <span>Longitudinal Screening Timeline ({patientHistory.screenings.length} total)</span>
            </h4>

            {patientHistory.screenings.length === 0 ? (
              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                No previous screenings recorded for this patient.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: '16px' }}>
                {/* Timeline List */}
                <div style={{ borderRight: '1px solid var(--border-color)', paddingRight: '12px' }}>
                  {patientHistory.screenings.map((sc, idx) => (
                    <div
                      key={sc.id}
                      onClick={() => setSelectedScreening(sc)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        marginBottom: '8px',
                        background: selectedScreening?.id === sc.id ? 'var(--bg-surface)' : 'transparent',
                        border: selectedScreening?.id === sc.id ? '1px solid var(--brand-cyan)' : '1px solid transparent'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                        <span style={{ fontWeight: 600 }}>{sc.id}</span>
                        <span style={{ color: 'var(--text-muted)' }}>#{patientHistory.screenings.length - idx}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {new Date(sc.created_at).toLocaleDateString()}
                      </div>
                      <div style={{ fontSize: '11px', marginTop: '4px', fontWeight: 600, color: sc.overall_disposition?.includes('Refer') ? 'var(--brand-amber)' : 'var(--brand-emerald)' }}>
                        {sc.overall_disposition || sc.status}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Selected Screening Details */}
                {selectedScreening && (
                  <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <span style={{ fontWeight: 700, fontSize: '14px' }}>Session {selectedScreening.id}</span>
                      <span className="badge badge-cyan">{new Date(selectedScreening.created_at).toLocaleString()}</span>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                      {selectedScreening.bilateral_summary || 'Screening recorded at primary health center.'}
                    </div>

                    {/* Images & AI Grades */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                      {selectedScreening.images.map(img => (
                        <div key={img.id} style={{ background: 'var(--bg-surface)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                          <div style={{ fontSize: '12px', fontWeight: 700, marginBottom: '4px' }}>
                            {img.eye === 'OD' ? 'Right Eye (OD)' : 'Left Eye (OS)'}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Quality: {img.quality_status} ({Math.round(img.quality_score * 100)}%)
                          </div>
                          {img.ai_result && (
                            <div style={{ marginTop: '4px', fontSize: '12px', fontWeight: 600, color: 'var(--brand-cyan)' }}>
                              Grade {img.ai_result.predicted_grade}: {img.ai_result.predicted_label}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Specialist Review if available */}
                    {selectedScreening.review && (
                      <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '10px', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
                        <div style={{ fontWeight: 700, color: 'var(--brand-emerald)' }}>
                          Specialist Endorsement ({selectedScreening.review.specialist_name}):
                        </div>
                        <div style={{ marginTop: '2px' }}>{selectedScreening.review.action_plan}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '4px' }}>
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  </svg>
);

import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { ScreeningSession, SyncStatus } from '../types';
import { Eye, Users, AlertTriangle, FileText, CheckCircle, Clock, ArrowRight, PlusCircle, Activity } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  onStartScreening: () => void;
  onSelectScreening: (id: string) => void;
  setActiveTab: (tab: string) => void;
  lang: Language;
}

export const DashboardPage: React.FC<Props> = ({
  onStartScreening,
  onSelectScreening,
  setActiveTab,
  lang
}) => {
  const [screenings, setScreenings] = useState<any[]>([]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [scList, sync] = await Promise.all([
          api.listScreenings(),
          api.getSyncStatus()
        ]);
        setScreenings(scList);
        setSyncStatus(sync);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const totalPatients = screenings.length;
  const completed = screenings.filter(s => s.status === 'completed' || s.status === 'referred').length;
  const referred = screenings.filter(s => s.status === 'referred').length;
  const ungradable = screenings.filter(s => s.status === 'ungradable').length;

  return (
    <div>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '28px', color: 'var(--text-primary)', margin: 0 }}>
            Operational Screening Overview
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Primary Health Center Node • Real-Time AI Screening & Telemedicine Telemetry
          </div>
        </div>
        <button className="btn btn-primary" onClick={onStartScreening}>
          <PlusCircle size={16} />
          <span>New Patient Screening</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase' }}>Patients Screened</span>
            <Users size={18} color="var(--brand-cyan)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--text-primary)' }}>{totalPatients}</div>
          <div style={{ fontSize: '12px', color: 'var(--brand-emerald)', marginTop: '4px', fontWeight: 600 }}>
            Active Daily Cohort
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase' }}>AI Verified</span>
            <CheckCircle size={18} color="var(--brand-emerald)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--brand-emerald)' }}>{completed}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Bilateral Analysis Complete
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase' }}>Clinical Referrals</span>
            <FileText size={18} color="var(--brand-amber)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--brand-amber)' }}>{referred}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Referred to District Specialist
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase' }}>Ungradable Cases</span>
            <AlertTriangle size={18} color="var(--brand-rose)" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--brand-rose)' }}>{ungradable}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Optical Defocus / Shadow Recapture
          </div>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid-3" style={{ marginBottom: '28px' }}>
        <div className="card" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Activity size={18} color="var(--brand-cyan)" />
            <h4 style={{ margin: 0, fontSize: '14px' }}>AI Inference Core</h4>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
            <strong>TrinetraNet-v1.0</strong> (PyTorch Neuro-Symbolic ResConv + 12-D BioMLP) • CPU Edge Fallback Ready
          </div>
          <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--brand-emerald)', fontWeight: 600 }}>
            Latency: ~1.72s • Calibrated (ECE=2.45%)
          </div>
        </div>

        <div className="card" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Clock size={18} color="var(--brand-emerald)" />
            <h4 style={{ margin: 0, fontSize: '14px' }}>Telemedicine Network</h4>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
            Active Mode: <strong>{syncStatus?.network.mode || "Mode A (4G)"}</strong> ({syncStatus?.network.status || "ONLINE"})
          </div>
          <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
            Sync Queue: {syncStatus?.sync_metrics.pending_count || 0} pending records
          </div>
        </div>

        <div className="card" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Eye size={18} color="var(--brand-purple)" />
            <h4 style={{ margin: 0, fontSize: '14px' }}>Camera Gatekeeper</h4>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
            Remidio FOP NM-v3 (Calibrated Φ=110.0) • Dynamic 8×8 Lab L* Illumination Grid
          </div>
          <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--brand-cyan)', fontWeight: 600 }}>
            Live Optical Guidance HUD Active
          </div>
        </div>
      </div>

      {/* Screenings Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>Recent Patient Screening Sessions</h3>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Real-time audit log of screened patients, quality status, and referral dispositions
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('telemedicine')}>
            <span>Open Triage Queue</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="clinical-table">
            <thead>
              <tr>
                <th>Screening ID</th>
                <th>Patient Name</th>
                <th>Age / Sex</th>
                <th>Facility</th>
                <th>Images</th>
                <th>Disposition / Summary</th>
                <th>Sync Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {screenings.map(sc => (
                <tr key={sc.id}>
                  <td><strong>{sc.id}</strong></td>
                  <td>{sc.patient_name}</td>
                  <td>{sc.patient_age} yrs</td>
                  <td>{sc.phc_facility}</td>
                  <td>
                    <span className="badge badge-cyan">{sc.images_count} Captured</span>
                  </td>
                  <td style={{ maxWidth: '300px', fontSize: '12px' }}>
                    {sc.bilateral_summary || sc.overall_disposition}
                  </td>
                  <td>
                    <span className={`badge badge-${sc.sync_status === 'synced' ? 'emerald' : sc.sync_status === 'pending' ? 'amber' : 'rose'}`}>
                      {sc.sync_status}
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectScreening(sc.id)}
                      style={{ fontSize: '11px' }}
                    >
                      Review Case
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

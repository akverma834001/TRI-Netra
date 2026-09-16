import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { TelemedicineQueueItem } from '../types';
import { AlertCircle, Clock, Eye, Filter, ArrowRight, Activity, ShieldAlert } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  onSelectCase: (screeningId: string) => void;
  lang: Language;
}

export const TelemedicineQueue: React.FC<Props> = ({ onSelectCase, lang }) => {
  const t = translations[lang];
  const [queue, setQueue] = useState<TelemedicineQueueItem[]>([]);
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const data = await api.getTelemedicineQueue(filterPriority === 'ALL' ? undefined : filterPriority);
        setQueue(data);
      } catch (err) {
        console.error("Error fetching telemedicine queue:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchQueue();
  }, [filterPriority]);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '28px', color: 'var(--text-primary)', margin: 0 }}>
            District Tele-Ophthalmology Triage Queue
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Central Hub Priority Queue • Triage sorted by Proliferative & Macular Risk Urgency
          </div>
        </div>

        {/* Priority Filter Tabs */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-surface)', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
          {['ALL', 'EMERGENCY', 'URGENT', 'PRIORITY', 'ROUTINE'].map(p => (
            <button
              key={p}
              className={`btn btn-sm ${filterPriority === p ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilterPriority(p)}
              style={{ fontSize: '11px' }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Queue Table */}
      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="clinical-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Case ID</th>
                <th>Patient Details</th>
                <th>Origin PHC</th>
                <th>AI Stage</th>
                <th>Risk Flags</th>
                <th>Uncertainty</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {queue.map(item => (
                <tr key={item.case_id}>
                  <td>
                    <span className={`badge badge-${item.priority === 'EMERGENCY' ? 'rose' : item.priority === 'URGENT' ? 'amber' : item.priority === 'PRIORITY' ? 'cyan' : 'emerald'}`}>
                      {item.priority}
                    </span>
                  </td>
                  <td><strong>{item.case_id}</strong></td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.patient_name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{item.patient_age}y • ID: {item.patient_id}</div>
                  </td>
                  <td>{item.phc_facility}</td>
                  <td>
                    <span style={{ fontWeight: 700 }}>{item.ai_stage}</span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      {item.macular_risk && (
                        <span style={{ fontSize: '10px', color: 'var(--brand-rose)', fontWeight: 700 }}>
                          ⚠ Macular / DME Risk
                        </span>
                      )}
                      {item.pdr_evidence && (
                        <span style={{ fontSize: '10px', color: 'var(--brand-purple)', fontWeight: 700 }}>
                          ⚠ PDR Neovascularization
                        </span>
                      )}
                      {!item.macular_risk && !item.pdr_evidence && (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Standard</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span style={{
                      fontWeight: 700,
                      color: item.epistemic_uncertainty > 0.40 ? 'var(--brand-rose)' : 'var(--brand-emerald)'
                    }}>
                      {item.epistemic_uncertainty.toFixed(2)}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-cyan">{item.status}</span>
                  </td>
                  <td>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => onSelectCase(item.case_id)}
                      style={{ fontSize: '11px' }}
                    >
                      <span>Review</span>
                      <ArrowRight size={12} />
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

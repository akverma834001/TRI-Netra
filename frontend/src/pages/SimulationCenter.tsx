import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { OperationalSimResults } from '../types';
import { Activity, Users, Clock, Database, BarChart2, ShieldCheck, Play, RefreshCcw } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const SimulationCenter: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [numPhcs, setNumPhcs] = useState(20);
  const [ptsPerPhc, setPtsPerPhc] = useState(25);
  const [specialists, setSpecialists] = useState(4);
  const [reviewMin, setReviewMin] = useState(3.5);
  const [bandwidth, setBandwidth] = useState(5000);

  const [simResults, setSimResults] = useState<OperationalSimResults | null>(null);
  const [loading, setLoading] = useState(false);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const res = await api.runOperationalSimulation({
        num_phcs: numPhcs,
        patients_per_day_per_phc: ptsPerPhc,
        specialist_count: specialists,
        avg_specialist_review_min: reviewMin,
        network_bandwidth_kbps: bandwidth
      });
      setSimResults(res);
    } catch (err) {
      alert("Error running operational simulation: " + err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '28px', color: 'var(--text-primary)', margin: 0 }}>
            Healthcare Operations & Telemedicine Simulation Center
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Multi-Center Monte Carlo Queue Modeling • Baseline: 20 PHCs × 25 Patients/Day • Non-Homogeneous Poisson Arrivals
          </div>
        </div>

        <button className="btn btn-primary" onClick={runSimulation} disabled={loading}>
          <RefreshCcw size={16} className={loading ? 'pulse-glow' : ''} />
          <span>{loading ? "Simulating Network..." : "Re-Run Simulation"}</span>
        </button>
      </div>

      {/* Configurable Simulation Controls */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '15px', marginBottom: '16px' }}>Configurable Simulation Parameters</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px' }}>
          <div>
            <label className="form-label">PHC Nodes Count</label>
            <input
              type="number"
              className="form-input"
              value={numPhcs}
              onChange={e => setNumPhcs(Number(e.target.value))}
            />
          </div>

          <div>
            <label className="form-label">Pts / Day / PHC</label>
            <input
              type="number"
              className="form-input"
              value={ptsPerPhc}
              onChange={e => setPtsPerPhc(Number(e.target.value))}
            />
          </div>

          <div>
            <label className="form-label">District Specialists</label>
            <input
              type="number"
              className="form-input"
              value={specialists}
              onChange={e => setSpecialists(Number(e.target.value))}
            />
          </div>

          <div>
            <label className="form-label">Review Time (min)</label>
            <input
              type="number"
              step="0.5"
              className="form-input"
              value={reviewMin}
              onChange={e => setReviewMin(Number(e.target.value))}
            />
          </div>

          <div>
            <label className="form-label">Bandwidth (kbps)</label>
            <input
              type="number"
              step="500"
              className="form-input"
              value={bandwidth}
              onChange={e => setBandwidth(Number(e.target.value))}
            />
          </div>
        </div>
      </div>

      {simResults && (
        <>
          {/* Operational KPIs */}
          <div className="grid-4" style={{ marginBottom: '24px' }}>
            <div className="card">
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Cohort Throughput
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '4px', color: 'var(--text-primary)' }}>
                {simResults.operational_results.total_patients_screened} / {simResults.operational_results.total_patients_registered}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--brand-emerald)', marginTop: '2px' }}>
                Completed 8-Hour Screenings
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Edge Recapture Rate
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '4px', color: 'var(--brand-amber)' }}>
                {simResults.operational_results.edge_recapture_rate_pct}%
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {simResults.operational_results.total_edge_recaptures} optical gatekeeper retakes
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Referral Volume
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, marginTop: '4px', color: 'var(--brand-purple)' }}>
                {simResults.operational_results.total_referrals_generated}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {simResults.operational_results.referral_rate_pct}% referable DR / macular risk
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Specialist Utilization
              </div>
              <div style={{
                fontSize: '28px',
                fontWeight: 800,
                marginTop: '4px',
                color: simResults.operational_results.specialist_system_utilization_pct > 85 ? 'var(--brand-rose)' : 'var(--brand-cyan)'
              }}>
                {simResults.operational_results.specialist_system_utilization_pct}%
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Queue Delay: ~{simResults.operational_results.avg_specialist_wait_min} min
              </div>
            </div>
          </div>

          {/* Hourly Screening Volume Histogram */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <h4 style={{ fontSize: '15px', marginBottom: '16px' }}>Hourly Screening Arrivals (Peak Morning Distribution)</h4>
            <div style={{ display: 'flex', alignItems: 'flex-end', height: '140px', gap: '16px', paddingBottom: '20px', borderBottom: '1px solid var(--border-color)' }}>
              {simResults.operational_results.hourly_screenings.map((count, idx) => {
                const maxCount = Math.max(...simResults.operational_results.hourly_screenings);
                const heightPct = (count / maxCount) * 100;
                const hours = ['9-10 AM', '10-11 AM', '11-12 PM', '12-1 PM', '1-2 PM', '2-3 PM', '3-4 PM', '4-5 PM'];
                return (
                  <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>{count}</span>
                    <div style={{
                      width: '100%',
                      height: `${heightPct}%`,
                      background: 'linear-gradient(180deg, var(--brand-cyan), #0369a1)',
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.3s ease'
                    }} />
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '6px', whiteSpace: 'nowrap' }}>
                      {hours[idx]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sample PHCs Breakdown Table */}
          <div className="card">
            <h4 style={{ fontSize: '15px', marginBottom: '14px' }}>Primary Health Center Node Breakdown (Sample)</h4>
            <div style={{ overflowX: 'auto' }}>
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>PHC Node</th>
                    <th>Registered</th>
                    <th>Screened</th>
                    <th>Recaptures</th>
                    <th>Referrals</th>
                    <th>Avg Capture Time</th>
                  </tr>
                </thead>
                <tbody>
                  {simResults.phc_breakdown.map(node => (
                    <tr key={node.phc_id}>
                      <td><strong>{node.phc_id}</strong></td>
                      <td>{node.registered}</td>
                      <td>{node.completed}</td>
                      <td>{node.recaptures}</td>
                      <td><span className="badge badge-amber">{node.referrals}</span></td>
                      <td>{node.avg_capture_min} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

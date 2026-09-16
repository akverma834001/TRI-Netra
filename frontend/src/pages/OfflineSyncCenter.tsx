import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { SyncStatus } from '../types';
import { Wifi, WifiOff, RefreshCw, Server, AlertTriangle, CheckCircle, Database } from 'lucide-react';
import { Language, translations } from '../i18n/translations';

interface Props {
  lang: Language;
}

export const OfflineSyncCenter: React.FC<Props> = ({ lang }) => {
  const t = translations[lang];
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [queueItems, setQueueItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const fetchSyncData = async () => {
    try {
      const [status, q] = await Promise.all([
        api.getSyncStatus(),
        api.getSyncQueue()
      ]);
      setSyncStatus(status);
      setQueueItems(q);
    } catch (err) {
      console.error("Error loading sync center:", err);
    }
  };

  useEffect(() => {
    fetchSyncData();
  }, []);

  const handleSwitchNetworkMode = async (mode: string) => {
    let bandwidth = 5000.0;
    let packetLoss = 0.005;
    let latency = 45.0;

    if (mode === 'Mode B') {
      bandwidth = 128.0;
      packetLoss = 0.08;
      latency = 320.0;
    } else if (mode === 'Mode C') {
      bandwidth = 0.0;
      packetLoss = 1.0;
      latency = 9999.0;
    }

    try {
      await api.configureNetwork({
        mode,
        bandwidth_kbps: bandwidth,
        packet_loss_rate: packetLoss,
        latency_ms: latency
      });
      await fetchSyncData();
    } catch (err) {
      alert("Error switching network mode: " + err);
    }
  };

  const handleTriggerSync = async () => {
    setLoading(true);
    setSyncMessage(null);
    try {
      const res = await api.triggerSync();
      setSyncMessage(res.message);
      await fetchSyncData();
    } catch (err) {
      setSyncMessage("Sync error: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '28px', color: 'var(--text-primary)', margin: 0 }}>
            Offline-First Architecture & Network Simulation Center
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Simulate realistic rural edge conditions: 4G/Fiber, 2G/3G limited bandwidth, and complete blackout buffering.
          </div>
        </div>

        <button className="btn btn-primary" onClick={handleTriggerSync} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'pulse-glow' : ''} />
          <span>{loading ? "Synchronizing Queue..." : "Trigger Synchronization"}</span>
        </button>
      </div>

      {syncMessage && (
        <div style={{
          padding: '14px 18px',
          borderRadius: 'var(--radius-sm)',
          background: syncMessage.includes('failed') ? 'var(--brand-rose-light)' : 'var(--brand-emerald-light)',
          color: syncMessage.includes('failed') ? 'var(--brand-rose)' : 'var(--brand-emerald)',
          fontWeight: 600,
          fontSize: '13px',
          marginBottom: '20px'
        }}>
          {syncMessage}
        </div>
      )}

      {/* Network Mode Cards */}
      <div className="grid-3" style={{ marginBottom: '28px' }}>
        <div
          className="card"
          onClick={() => handleSwitchNetworkMode('Mode A')}
          style={{
            cursor: 'pointer',
            border: syncStatus?.network.mode === 'Mode A' ? '2px solid var(--brand-emerald)' : '1px solid var(--border-color)',
            background: syncStatus?.network.mode === 'Mode A' ? 'var(--brand-emerald-light)' : 'var(--bg-surface)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-emerald)' }}>MODE A: 4G / FIBER</span>
            <Wifi size={18} color="var(--brand-emerald)" />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800 }}>Online Broadband</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Bandwidth: 5,000 kbps • Latency: 45ms • Packet Loss: 0.5%
          </div>
        </div>

        <div
          className="card"
          onClick={() => handleSwitchNetworkMode('Mode B')}
          style={{
            cursor: 'pointer',
            border: syncStatus?.network.mode === 'Mode B' ? '2px solid var(--brand-amber)' : '1px solid var(--border-color)',
            background: syncStatus?.network.mode === 'Mode B' ? 'var(--brand-amber-light)' : 'var(--bg-surface)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-amber)' }}>MODE B: 2G / 3G</span>
            <Wifi size={18} color="var(--brand-amber)" />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800 }}>Limited Connectivity</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            Bandwidth: 128 kbps • Latency: 320ms • Packet Loss: 8.0%
          </div>
        </div>

        <div
          className="card"
          onClick={() => handleSwitchNetworkMode('Mode C')}
          style={{
            cursor: 'pointer',
            border: syncStatus?.network.mode === 'Mode C' ? '2px solid var(--brand-rose)' : '1px solid var(--border-color)',
            background: syncStatus?.network.mode === 'Mode C' ? 'var(--brand-rose-light)' : 'var(--bg-surface)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brand-rose)' }}>MODE C: BLACKOUT</span>
            <WifiOff size={18} color="var(--brand-rose)" />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800 }}>Offline Local Store</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
            No link (0 kbps) • All screenings safely buffered in local SQLite store
          </div>
        </div>
      </div>

      {/* Sync Queue Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 style={{ fontSize: '18px', margin: 0 }}>SQLite Local Sync Queue</h3>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Pending and synchronized object records buffered for central hub transmission
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="badge badge-amber">{syncStatus?.sync_metrics.pending_count || 0} Pending</span>
            <span className="badge badge-emerald">{syncStatus?.sync_metrics.synced_count || 0} Synced</span>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="clinical-table">
            <thead>
              <tr>
                <th>Queue Item ID</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th>Status</th>
                <th>Retry Count</th>
                <th>Error Log / Diagnostic</th>
                <th>Enqueued At</th>
              </tr>
            </thead>
            <tbody>
              {queueItems.map(it => (
                <tr key={it.id}>
                  <td><strong>Q-{it.id}</strong></td>
                  <td><span className="badge badge-cyan">{it.entity_type}</span></td>
                  <td>{it.entity_id}</td>
                  <td>
                    <span className={`badge badge-${it.status === 'SYNCED' ? 'emerald' : it.status === 'PENDING' ? 'amber' : 'rose'}`}>
                      {it.status}
                    </span>
                  </td>
                  <td>{it.retry_count} retries</td>
                  <td style={{ fontSize: '11px', color: it.error_log ? 'var(--brand-rose)' : 'var(--text-muted)', maxWidth: '300px' }}>
                    {it.error_log || "No errors recorded. Link nominal."}
                  </td>
                  <td>{new Date(it.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
              {queueItems.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px' }}>
                    Sync queue is clean. All local records are synchronized.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

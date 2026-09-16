import React from 'react';
import { Eye, Shield, Wifi, WifiOff, Globe, Moon, Sun, Activity } from 'lucide-react';
import { Language, translations } from '../i18n/translations';
import { User, SyncStatus } from '../types';

interface Props {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  lang: Language;
  setLang: (lang: Language) => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  currentUser: User;
  onSwitchRole: (role: string) => void;
  syncStatus: SyncStatus | null;
}

export const Navbar: React.FC<Props> = ({
  activeTab,
  setActiveTab,
  lang,
  setLang,
  theme,
  toggleTheme,
  currentUser,
  onSwitchRole,
  syncStatus
}) => {
  const t = translations[lang];

  const getNetworkBadge = () => {
    if (!syncStatus) return null;
    const mode = syncStatus.network.mode;
    if (mode === 'Mode C' || syncStatus.network.status === 'OFFLINE') {
      return (
        <span className="badge badge-rose" title="Local offline mode. Cases safely buffered in SQLite.">
          <WifiOff size={12} /> Blackout (Offline)
        </span>
      );
    }
    if (mode === 'Mode B' || syncStatus.network.status === 'LIMITED') {
      return (
        <span className="badge badge-amber" title="Limited 2G/3G connectivity.">
          <Wifi size={12} /> 2G/3G (Limited)
        </span>
      );
    }
    return (
      <span className="badge badge-emerald" title="4G / Broadband connection active.">
        <Wifi size={12} /> 4G / Online
      </span>
    );
  };

  return (
    <header className="navbar">
      <div className="nav-left">
        <div className="brand-badge" onClick={() => setActiveTab('landing')}>
          <div className="brand-icon">
            <Eye size={22} />
          </div>
          <div>
            <div className="brand-name">
              {t.brand_name}
              <span className="brand-name-hi">({t.brand_hindi})</span>
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.04em' }}>
              {t.tagline}
            </div>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            {t.nav_dashboard}
          </button>
          <button
            className={`nav-link ${activeTab === 'operator' ? 'active' : ''}`}
            onClick={() => setActiveTab('operator')}
          >
            {t.nav_operator}
          </button>
          <button
            className={`nav-link ${activeTab === 'specialist' ? 'active' : ''}`}
            onClick={() => setActiveTab('specialist')}
          >
            {t.nav_specialist}
          </button>
          <button
            className={`nav-link ${activeTab === 'telemedicine' ? 'active' : ''}`}
            onClick={() => setActiveTab('telemedicine')}
          >
            {t.nav_telemedicine}
          </button>
          <button
            className={`nav-link ${activeTab === 'referrals' ? 'active' : ''}`}
            onClick={() => setActiveTab('referrals')}
          >
            {t.nav_referrals}
          </button>
          <button
            className={`nav-link ${activeTab === 'sync' ? 'active' : ''}`}
            onClick={() => setActiveTab('sync')}
          >
            {t.nav_sync}
            {syncStatus && syncStatus.sync_metrics.pending_count > 0 && (
              <span style={{ fontSize: '10px', background: 'var(--brand-amber)', color: 'white', padding: '1px 5px', borderRadius: '10px' }}>
                {syncStatus.sync_metrics.pending_count}
              </span>
            )}
          </button>
          <button
            className={`nav-link ${activeTab === 'simulation' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulation')}
          >
            {t.nav_simulation}
          </button>
          <button
            className={`nav-link ${activeTab === 'validation' ? 'active' : ''}`}
            onClick={() => setActiveTab('validation')}
          >
            {t.nav_validation}
          </button>
        </nav>
      </div>

      <div className="nav-right">
        {getNetworkBadge()}

        {/* Role Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Shield size={14} color="var(--brand-cyan)" />
          <select
            className="form-select"
            style={{ padding: '4px 8px', fontSize: '11px', fontWeight: 600, width: 'auto' }}
            value={currentUser.role}
            onChange={(e) => onSwitchRole(e.target.value)}
            title="Switch User Role for Live Testing"
          >
            <option value="phc_operator">PHC Operator (सुनीता देवी)</option>
            <option value="ophthalmologist">Specialist (Dr. Sharma)</option>
            <option value="district_admin">District Admin (राजेश कुमार)</option>
            <option value="ml_admin">ML / Research Admin (Dr. Verma)</option>
            <option value="sysadmin">System Admin (V. K. Meena)</option>
          </select>
        </div>

        {/* Language Toggle */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
          title="Toggle Language / भाषा बदलें"
        >
          <Globe size={14} />
          <span>{lang === 'en' ? 'हिंदी' : 'English'}</span>
        </button>

        {/* Theme Toggle */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Clinical Theme' : 'Switch to Dark Eye Review Theme'}
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </header>
  );
};

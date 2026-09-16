import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { User, SyncStatus } from './types';
import { Language } from './i18n/translations';

// Components
import { Navbar } from './components/Navbar';
import { DisclaimerBanner } from './components/DisclaimerBanner';

// Pages
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { OperatorWorkflow } from './pages/OperatorWorkflow';
import { SpecialistReview } from './pages/SpecialistReview';
import { TelemedicineQueue } from './pages/TelemedicineQueue';
import { ReferralManagement } from './pages/ReferralManagement';
import { OfflineSyncCenter } from './pages/OfflineSyncCenter';
import { SimulationCenter } from './pages/SimulationCenter';
import { ValidationCenter } from './pages/ValidationCenter';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('landing');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [lang, setLang] = useState<Language>('en');
  const [selectedScreeningId, setSelectedScreeningId] = useState<string>('SCR-DEMO-03');
  const [selectedReferralId, setSelectedReferralId] = useState<string | null>(null);

  const [currentUser, setCurrentUser] = useState<User>({
    id: 1,
    username: 'operator_rampur',
    full_name: 'Sunita Devi (PHC Operator)',
    role: 'phc_operator',
    facility: 'PHC Rampur (Block A)',
    language: 'hi'
  });

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);

  // Sync theme attribute on root element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  // Initial user fetch & sync status
  useEffect(() => {
    const init = async () => {
      try {
        const u = await api.getMe();
        if (u && u.username) setCurrentUser(u);
      } catch {
        // Fallback user initialized
      }
      try {
        const sync = await api.getSyncStatus();
        setSyncStatus(sync);
      } catch (err) {
        console.warn("Initial sync status check:", err);
      }
    };
    init();

    const interval = setInterval(async () => {
      try {
        const sync = await api.getSyncStatus();
        setSyncStatus(sync);
      } catch {
        // network silent
      }
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSwitchRole = async (role: string) => {
    try {
      const res = await api.switchRole(role);
      setCurrentUser(res.user);
    } catch (err) {
      alert("Error switching role: " + err);
    }
  };

  const handleStartScreening = () => {
    setActiveTab('operator');
  };

  const handleSelectDemoCase = (screeningId: string) => {
    setSelectedScreeningId(screeningId);
    setActiveTab('specialist');
  };

  const handleSelectScreening = (screeningId: string) => {
    setSelectedScreeningId(screeningId);
    setActiveTab('specialist');
  };

  const handleScreeningCompleted = (screeningId: string) => {
    setSelectedScreeningId(screeningId);
    setActiveTab('specialist');
  };

  const handleReferralGenerated = (referralId: string) => {
    setSelectedReferralId(referralId);
    setActiveTab('referrals');
  };

  return (
    <div className="app-container">
      {/* Top Clinical Safety Position Banner */}
      <DisclaimerBanner />

      {/* Main Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        lang={lang}
        setLang={setLang}
        theme={theme}
        toggleTheme={toggleTheme}
        currentUser={currentUser}
        onSwitchRole={handleSwitchRole}
        syncStatus={syncStatus}
      />

      {/* Main Content Router */}
      <main className="main-content">
        {activeTab === 'landing' && (
          <LandingPage
            onStartScreening={handleStartScreening}
            onSelectDemoCase={handleSelectDemoCase}
            lang={lang}
          />
        )}

        {activeTab === 'dashboard' && (
          <DashboardPage
            onStartScreening={handleStartScreening}
            onSelectScreening={handleSelectScreening}
            setActiveTab={setActiveTab}
            lang={lang}
          />
        )}

        {activeTab === 'operator' && (
          <OperatorWorkflow
            onScreeningCompleted={handleScreeningCompleted}
            lang={lang}
          />
        )}

        {activeTab === 'specialist' && (
          <SpecialistReview
            screeningId={selectedScreeningId}
            onReferralGenerated={handleReferralGenerated}
            lang={lang}
          />
        )}

        {activeTab === 'telemedicine' && (
          <TelemedicineQueue
            onSelectCase={handleSelectScreening}
            lang={lang}
          />
        )}

        {activeTab === 'referrals' && (
          <ReferralManagement
            selectedReferralId={selectedReferralId}
            lang={lang}
          />
        )}

        {activeTab === 'sync' && (
          <OfflineSyncCenter
            lang={lang}
          />
        )}

        {activeTab === 'simulation' && (
          <SimulationCenter
            lang={lang}
          />
        )}

        {activeTab === 'validation' && (
          <ValidationCenter
            lang={lang}
          />
        )}
      </main>
    </div>
  );
};

export default App;

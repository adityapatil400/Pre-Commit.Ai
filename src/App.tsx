import React, { useState, useEffect } from 'react';
import { HomePage } from './pages/HomePage';
import { AnalysisPage } from './pages/AnalysisPage';
import { PlaygroundPage } from './pages/PlaygroundPage';
import { SettingsModal } from './components/SettingsModal';
import { ScanHistoryModal } from './components/ScanHistoryModal';
import { NewScanModal } from './components/NewScanModal';
import { AnalysisResult } from './types/analysis';

const STORAGE_KEY_HISTORY = 'precommit_ai_scan_history_v1';

export const App: React.FC = () => {
  // Navigation & View Routing
  const [nav, setNav] = useState<'dashboard' | 'playground'>(() => {
    return window.location.pathname.startsWith('/playground') ? 'playground' : 'dashboard';
  });
  const [currentView, setCurrentView] = useState<'home' | 'analysis'>('home');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  // Global Modals State
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [isNewScanOpen, setIsNewScanOpen] = useState<boolean>(false);

  // Scan History
  const [scanHistory, setScanHistory] = useState<AnalysisResult[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_HISTORY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Sync with browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      if (window.location.pathname.startsWith('/playground')) {
        setNav('playground');
      } else {
        setNav('dashboard');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Update history from localStorage whenever modal opens
  useEffect(() => {
    if (isHistoryOpen) {
      try {
        const stored = localStorage.getItem(STORAGE_KEY_HISTORY);
        if (stored) {
          setScanHistory(JSON.parse(stored));
        }
      } catch {
        // ignore
      }
    }
  }, [isHistoryOpen]);

  const handleNavigate = (destination: 'dashboard' | 'playground') => {
    setNav(destination);
    if (destination === 'playground') {
      window.history.pushState({}, '', '/playground');
    } else {
      window.history.pushState({}, '', '/');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAnalysisComplete = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setCurrentView('analysis');
    setNav('dashboard');
    window.history.pushState({}, '', '/');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleReset = () => {
    setCurrentView('home');
    setAnalysisResult(null);
    setNav('dashboard');
    window.history.pushState({}, '', '/');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectHistoryScan = (scan: AnalysisResult) => {
    setAnalysisResult(scan);
    setCurrentView('analysis');
    setNav('dashboard');
    setIsHistoryOpen(false);
    window.history.pushState({}, '', '/');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleClearHistory = () => {
    localStorage.removeItem(STORAGE_KEY_HISTORY);
    setScanHistory([]);
  };

  const handleNewScanComplete = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setCurrentView('analysis');
    setNav('dashboard');
    setIsNewScanOpen(false);
    window.history.pushState({}, '', '/');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="w-full min-h-screen text-[#050505] font-sans">
      {nav === 'playground' ? (
        <PlaygroundPage
          onNavigateDashboard={() => handleNavigate('dashboard')}
          onOpenHistory={() => setIsHistoryOpen(true)}
          onOpenNewScan={() => setIsNewScanOpen(true)}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />
      ) : currentView === 'home' || !analysisResult ? (
        <HomePage
          onAnalysisComplete={handleAnalysisComplete}
          onNavigatePlayground={() => handleNavigate('playground')}
          onOpenHistory={() => setIsHistoryOpen(true)}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />
      ) : (
        <AnalysisPage
          result={analysisResult}
          onReset={handleReset}
          onNavigatePlayground={() => handleNavigate('playground')}
        />
      )}

      {/* Global Modals */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      <ScanHistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={scanHistory}
        onSelectScan={handleSelectHistoryScan}
        onClearHistory={handleClearHistory}
      />

      <NewScanModal
        isOpen={isNewScanOpen}
        onClose={() => setIsNewScanOpen(false)}
        onScanComplete={handleNewScanComplete}
      />
    </div>
  );
};

export default App;

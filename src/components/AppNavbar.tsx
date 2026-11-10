import React from 'react';
import { BrandLogo } from './BrandLogo';
import {
  LayoutDashboard,
  Plus,
  Clock,
  Terminal,
  Settings,
  Sparkles,
  ExternalLink,
} from 'lucide-react';

export type NavItem = 'dashboard' | 'new-scan' | 'history' | 'playground' | 'settings';

interface AppNavbarProps {
  currentNav: 'dashboard' | 'playground';
  onNavigate: (item: 'dashboard' | 'playground') => void;
  onOpenNewScan?: () => void;
  onOpenHistory?: () => void;
  onOpenSettings?: () => void;
}

export const AppNavbar: React.FC<AppNavbarProps> = ({
  currentNav,
  onNavigate,
  onOpenNewScan,
  onOpenHistory,
  onOpenSettings,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-neutral-200/80 bg-white/95 backdrop-blur-md shadow-xs transition-all">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Brand Logo */}
        <div className="flex items-center gap-6 min-w-0">
          <BrandLogo onClick={() => onNavigate('dashboard')} />

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5" aria-label="Main Navigation">
            {/* 1. Dashboard */}
            <button
              type="button"
              onClick={() => onNavigate('dashboard')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] text-[13px] font-medium transition-all ${
                currentNav === 'dashboard'
                  ? 'bg-neutral-900 text-white font-semibold shadow-xs'
                  : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Dashboard</span>
            </button>

            {/* 2. Playground (NEW) */}
            <button
              type="button"
              onClick={() => onNavigate('playground')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] text-[13px] font-medium transition-all relative ${
                currentNav === 'playground'
                  ? 'bg-neutral-900 text-white font-semibold shadow-xs'
                  : 'text-neutral-700 hover:text-neutral-900 hover:bg-neutral-100'
              }`}
            >
              <Terminal className="w-3.5 h-3.5 text-blue-500" />
              <span>Playground</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700 uppercase tracking-wider ml-0.5">
                NEW
              </span>
            </button>
          </nav>
        </div>

        {/* Right: Quick Actions (New Scan, Scan History, Settings) */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Mobile Playground button */}
          <button
            type="button"
            onClick={() => onNavigate(currentNav === 'playground' ? 'dashboard' : 'playground')}
            className="md:hidden inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[9px] border border-neutral-200 text-neutral-700 text-[12px] font-medium"
          >
            <Terminal className="w-3.5 h-3.5 text-blue-500" />
            <span>{currentNav === 'playground' ? 'Dashboard' : 'Playground'}</span>
          </button>

          {/* Scan History Button */}
          {onOpenHistory && (
            <button
              type="button"
              onClick={onOpenHistory}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] border border-neutral-200/90 bg-white hover:bg-neutral-50 text-neutral-700 text-[13px] font-medium transition-all shadow-2xs hover:border-neutral-300"
              title="View past code scans"
            >
              <Clock className="w-3.5 h-3.5 text-neutral-500" />
              <span className="hidden sm:inline">Scan History</span>
            </button>
          )}

          {/* New Scan Button */}
          {onOpenNewScan && (
            <button
              type="button"
              onClick={onOpenNewScan}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-[9px] bg-[#050505] hover:bg-neutral-800 text-white text-[13px] font-semibold transition-all shadow-xs hover:shadow"
              title="Upload code or scan GitHub repo"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">New Scan</span>
            </button>
          )}

          {/* Settings Button */}
          {onOpenSettings && (
            <button
              type="button"
              onClick={onOpenSettings}
              className="p-2 rounded-[9px] border border-neutral-200/90 bg-white hover:bg-neutral-50 text-neutral-600 hover:text-neutral-900 transition-colors shadow-2xs"
              title="Application Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};


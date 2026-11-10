import React from 'react';
import { BrandLogo } from './BrandLogo';
import {
  GitBranch,
  Clock,
  Plus,
  CheckCircle2,
  FolderGit2,
  ChevronDown,
  Sparkles,
  Terminal,
} from 'lucide-react';

interface DashboardHeaderProps {
  projectName: string;
  sourceType: 'file' | 'zip' | 'github';
  sourceReference: string;
  branch?: string;
  onNewScan: () => void;
  onOpenHistory: () => void;
  onNavigatePlayground?: () => void;
  onLogoClick?: () => void;
  status?: string;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  projectName,
  sourceType,
  sourceReference,
  branch = 'main',
  onNewScan,
  onOpenHistory,
  onNavigatePlayground,
  onLogoClick,
  status = 'completed',
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-neutral-200/80 bg-white/95 backdrop-blur-md shadow-xs transition-all">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left Section: Logo & Project/Repo Metadata */}
        <div className="flex items-center gap-4 sm:gap-6 min-w-0">
          <BrandLogo onClick={onLogoClick} />

          <div className="hidden sm:block h-5 w-[1px] bg-neutral-200" aria-hidden="true" />

          {/* Repo / Project Name Badge */}
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] bg-neutral-100/80 border border-neutral-200 text-neutral-800 text-[13px] font-medium truncate">
              <FolderGit2 className="w-3.5 h-3.5 text-neutral-500 flex-shrink-0" />
              <span className="truncate max-w-[140px] sm:max-w-[220px]" title={sourceReference || projectName}>
                {projectName}
              </span>
            </div>

            {/* Git Branch Selector */}
            <div className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] bg-neutral-50 border border-neutral-200 text-neutral-600 text-[12.5px] font-mono hover:bg-neutral-100 hover:text-neutral-900 transition-colors cursor-pointer">
              <GitBranch className="w-3.5 h-3.5 text-neutral-400" />
              <span className="font-semibold text-neutral-800">{branch}</span>
              <ChevronDown className="w-3 h-3 text-neutral-400 ml-0.5" />
            </div>

            {/* Analysis Status Badge */}
            <div className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] bg-emerald-50 border border-emerald-200/70 text-emerald-800 text-[12px] font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>{status === 'completed' ? 'Scan Complete' : 'Analysis In Progress'}</span>
            </div>
          </div>
        </div>

        {/* Right Section: Actions */}
        <div className="flex items-center gap-2.5 sm:gap-3 flex-shrink-0">
          {/* Playground Button */}
          {onNavigatePlayground && (
            <button
              type="button"
              onClick={onNavigatePlayground}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] border border-neutral-200/90 bg-white hover:bg-neutral-50 text-neutral-700 text-[13px] font-medium transition-all shadow-2xs hover:border-neutral-300"
              title="Open Python Playground"
            >
              <Terminal className="w-3.5 h-3.5 text-blue-500" />
              <span className="hidden sm:inline">Playground</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700 uppercase tracking-wider">
                NEW
              </span>
            </button>
          )}

          {/* Scan History Button */}
          <button
            type="button"
            onClick={onOpenHistory}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] border border-neutral-200/90 bg-white hover:bg-neutral-50 text-neutral-700 text-[13px] font-medium transition-all shadow-2xs hover:border-neutral-300"
            title="View recent code scans"
          >
            <Clock className="w-3.5 h-3.5 text-neutral-500" />
            <span className="hidden sm:inline">Scan History</span>
          </button>

          {/* New Scan Primary Button */}
          <button
            type="button"
            onClick={onNewScan}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-[10px] bg-[#050505] hover:bg-neutral-800 text-white text-[13px] font-semibold transition-all shadow-xs hover:shadow hover:scale-[1.01]"
          >
            <Plus className="w-4 h-4" />
            <span>New Scan</span>
          </button>
        </div>
      </div>
    </header>
  );
};


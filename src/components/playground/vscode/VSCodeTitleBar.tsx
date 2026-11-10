import React from 'react';
import {
  Play,
  ShieldCheck,
  Download,
  GitCommit,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Settings,
  ChevronRight,
  Loader2,
  ExternalLink,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { BrandLogo } from '../../BrandLogo';

interface VSCodeTitleBarProps {
  activeFileName: string;
  isModified: boolean;
  pythonVersion?: string;
  ollamaConnected: boolean;
  ollamaModel?: string;
  isRunning: boolean;
  isAnalyzing: boolean;
  onRun: () => void;
  onAnalyze: () => void;
  onDownload: () => void;
  onCommitGitHub: () => void;
  onOpenSettings: () => void;
  onNavigateDashboard?: () => void;
}

export const VSCodeTitleBar: React.FC<VSCodeTitleBarProps> = ({
  activeFileName,
  isModified,
  pythonVersion = 'Python 3.13',
  ollamaConnected,
  ollamaModel = 'llama3.2:latest',
  isRunning,
  isAnalyzing,
  onRun,
  onAnalyze,
  onDownload,
  onCommitGitHub,
  onOpenSettings,
  onNavigateDashboard,
}) => {
  return (
    <header className="h-10 bg-[#1e1e1e] border-b border-[#2d2d2d] flex items-center justify-between px-3 text-[12px] text-[#cccccc] select-none z-30">
      {/* Left: Brand & File Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Brand / Logo */}
        <div
          onClick={onNavigateDashboard}
          className="flex items-center gap-2 cursor-pointer hover:opacity-90 transition-opacity"
          title="Return to PreCommit AI Dashboard"
        >
          <div className="w-5 h-5 rounded-[5px] bg-[#007acc] text-white flex items-center justify-center font-bold text-[11px] shadow-xs">
            P
          </div>
          <span className="font-semibold text-white tracking-tight hidden sm:inline text-[12.5px]">
            PreCommit AI
          </span>
        </div>

        <div className="h-4 w-[1px] bg-[#333333]" />

        {/* Breadcrumbs */}
        <div className="flex items-center gap-1.5 text-[#858585] min-w-0">
          <span className="hidden md:inline hover:text-[#cccccc] transition-colors">playground</span>
          <ChevronRight className="w-3 h-3 text-[#555555] hidden md:inline" />
          <div className="flex items-center gap-1 text-[#e1e1e1] font-medium font-mono text-[12px]">
            <span>{activeFileName}</span>
            {isModified ? (
              <span
                className="w-2 h-2 rounded-full bg-[#e2c08d]"
                title="Unsaved changes"
              />
            ) : (
              <span title="All changes saved" className="flex items-center">
                <CheckCircle2 className="w-3 h-3 text-[#73c991]" />
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Center: System Indicators */}
      <div className="hidden lg:flex items-center gap-2.5">
        {/* Python Version Pill */}
        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[5px] bg-[#252526] border border-[#333333] text-[11px] text-[#a0a0a0]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#4B8BBE]" />
          <span>{pythonVersion} (Isolated)</span>
        </div>

        {/* Ollama Status Pill */}
        <div
          onClick={onOpenSettings}
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[5px] border text-[11px] cursor-pointer transition-colors ${
            ollamaConnected
              ? 'bg-[#1b2b1d] border-[#254628] text-[#89d185] hover:bg-[#203623]'
              : 'bg-[#2b1f1f] border-[#462828] text-[#f48771] hover:bg-[#382424]'
          }`}
          title={`Ollama LLM Provider (${ollamaModel}) - Click to configure`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              ollamaConnected ? 'bg-[#89d185] animate-pulse' : 'bg-[#f48771]'
            }`}
          />
          <span className="truncate max-w-[150px]">
            {ollamaConnected ? `Ollama (${ollamaModel})` : 'Ollama Offline'}
          </span>
        </div>
      </div>

      {/* Right: Core Action Buttons */}
      <div className="flex items-center gap-1.5">
        {/* Run Code Button */}
        <button
          type="button"
          onClick={onRun}
          disabled={isRunning}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[4px] bg-[#1a7f37] hover:bg-[#1f883d] text-white text-[11.5px] font-semibold transition-all disabled:opacity-50 shadow-2xs"
          title="Run Python code in safe isolated sandbox (Ctrl+Enter)"
        >
          {isRunning ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Play className="w-3 h-3 fill-current" />
          )}
          <span>Run</span>
        </button>

        {/* Analyze Code Button */}
        <button
          type="button"
          onClick={onAnalyze}
          disabled={isAnalyzing}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[4px] bg-[#0e639c] hover:bg-[#1177bb] text-white text-[11.5px] font-semibold transition-all disabled:opacity-50 shadow-2xs"
          title="Statically analyze code with Python AST (Ctrl+Shift+Enter)"
        >
          {isAnalyzing ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <ShieldCheck className="w-3.5 h-3.5" />
          )}
          <span className="hidden sm:inline">Analyze</span>
        </button>

        {/* Download .py Button */}
        <button
          type="button"
          onClick={onDownload}
          className="inline-flex items-center gap-1 px-2 py-1 rounded-[4px] bg-[#2d2d2d] hover:bg-[#383838] text-[#cccccc] hover:text-white text-[11.5px] transition-colors"
          title="Download current file as .py (Ctrl+S)"
        >
          <Download className="w-3.5 h-3.5 text-[#858585]" />
          <span className="hidden md:inline">Download</span>
        </button>

        {/* Commit to GitHub Button */}
        <button
          type="button"
          onClick={onCommitGitHub}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[4px] bg-[#21262d] hover:bg-[#30363d] border border-[#30363d] text-[#e6edf3] text-[11.5px] font-medium transition-colors"
          title="Review changes & commit to GitHub branch"
        >
          <GitCommit className="w-3.5 h-3.5 text-[#58a6ff]" />
          <span className="hidden sm:inline">Commit</span>
        </button>

        {/* Settings Button */}
        <button
          type="button"
          onClick={onOpenSettings}
          className="p-1 rounded-[4px] text-[#858585] hover:text-[#cccccc] hover:bg-[#2d2d2d] transition-colors ml-1"
          title="Playground & Model Settings"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};

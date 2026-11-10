import React from 'react';
import {
  GitBranch,
  XCircle,
  AlertTriangle,
  Check,
  Loader2,
  Sparkles,
  PanelBottom,
  Bell,
} from 'lucide-react';

interface VSCodeStatusBarProps {
  branch?: string;
  errorCount: number;
  warningCount: number;
  isAnalyzing: boolean;
  ollamaConnected: boolean;
  ollamaModel?: string;
  cursorLine: number;
  cursorColumn: number;
  pythonVersion?: string;
  onOpenProblems: () => void;
  onToggleBottomPanel: () => void;
  onToggleAssistant: () => void;
  onOpenSettings: () => void;
}

export const VSCodeStatusBar: React.FC<VSCodeStatusBarProps> = ({
  branch = 'main',
  errorCount,
  warningCount,
  isAnalyzing,
  ollamaConnected,
  ollamaModel = 'llama3.2',
  cursorLine,
  cursorColumn,
  pythonVersion = 'Python 3.13',
  onOpenProblems,
  onToggleBottomPanel,
  onToggleAssistant,
  onOpenSettings,
}) => {
  return (
    <footer className="h-[22px] bg-[#007acc] text-white flex items-center justify-between px-2 text-[11px] font-sans select-none z-30 shrink-0">
      {/* Left Items */}
      <div className="flex items-center space-x-3">
        {/* Branch */}
        <div
          className="flex items-center gap-1 hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-pointer transition-colors"
          title={`Git repository branch: ${branch}`}
        >
          <GitBranch className="w-3 h-3" />
          <span>{branch}</span>
        </div>

        {/* Problems Counter (Clickable -> Opens Problems tab) */}
        <div
          onClick={onOpenProblems}
          className="flex items-center gap-2 hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-pointer transition-colors"
          title="Click to view detected issues in Problems panel"
        >
          <div className="flex items-center gap-0.5">
            <XCircle className="w-3 h-3 text-white" />
            <span>{errorCount}</span>
          </div>
          <div className="flex items-center gap-0.5">
            <AlertTriangle className="w-3 h-3 text-[#ffcc00]" />
            <span>{warningCount}</span>
          </div>
        </div>

        {/* AST Status */}
        <div className="flex items-center gap-1 px-1.5 py-0.5" title="PreCommit AI AST Static Analyzer">
          {isAnalyzing ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Analyzing AST...</span>
            </>
          ) : (
            <>
              <Check className="w-3 h-3" />
              <span>AST Ready</span>
            </>
          )}
        </div>

        {/* Ollama Status */}
        <div
          onClick={onOpenSettings}
          className="hidden md:flex items-center gap-1 hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-pointer transition-colors"
          title={`Ollama LLM Provider: ${ollamaModel} (Click to configure)`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              ollamaConnected ? 'bg-[#89d185]' : 'bg-[#f48771]'
            }`}
          />
          <span className="truncate max-w-[140px]">
            {ollamaConnected ? `Ollama (${ollamaModel})` : 'Ollama Offline'}
          </span>
        </div>
      </div>

      {/* Right Items */}
      <div className="flex items-center space-x-3">
        {/* Line & Column Coordinates */}
        <div className="hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-default font-mono">
          Ln {cursorLine}, Col {cursorColumn}
        </div>

        {/* Spaces Indentation */}
        <div className="hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-default hidden sm:inline">
          Spaces: 4
        </div>

        {/* Encoding */}
        <div className="hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-default hidden md:inline">
          UTF-8
        </div>

        {/* Python Version */}
        <div className="hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded cursor-default">
          {pythonVersion}
        </div>

        {/* Toggle AI Assistant */}
        <button
          type="button"
          onClick={onToggleAssistant}
          className="hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded transition-colors flex items-center gap-1"
          title="Toggle PreCommit AI Assistant"
        >
          <Sparkles className="w-3 h-3" />
        </button>

        {/* Toggle Bottom Panel */}
        <button
          type="button"
          onClick={onToggleBottomPanel}
          className="hover:bg-[#1f8ad2] px-1.5 py-0.5 rounded transition-colors flex items-center gap-1"
          title="Toggle Output & Problems Panel"
        >
          <PanelBottom className="w-3 h-3" />
        </button>
      </div>
    </footer>
  );
};


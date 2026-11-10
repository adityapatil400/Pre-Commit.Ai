import React, { useState } from 'react';
import {
  Terminal,
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle2,
  Trash2,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  X,
  Sparkles,
  RotateCcw,
  ShieldCheck,
  FileCode,
  Clock,
  ArrowRight,
} from 'lucide-react';
import {
  PlaygroundExecutionResult,
  PlaygroundAnalysisResult,
  PlaygroundIssue,
  PlaygroundFixResponse,
  TerminalLog,
} from '../../../types/playground';

export type BottomPanelTab = 'output' | 'problems' | 'terminal' | 'explanation';

interface VSCodeBottomPanelProps {
  activeTab: BottomPanelTab;
  onSelectTab: (tab: BottomPanelTab) => void;
  executionResult: PlaygroundExecutionResult | null;
  analysisResult: PlaygroundAnalysisResult | null;
  selectedIssue: PlaygroundIssue | null;
  fixResponse: PlaygroundFixResponse | null;
  isFixing: boolean;
  terminalLogs: TerminalLog[];
  onSelectIssue: (issue: PlaygroundIssue) => void;
  onFixIssueWithAi: (issue?: PlaygroundIssue) => void;
  onAcceptFix: (suggestedCode: string) => void;
  onRejectFix: () => void;
  onRegenerateFix: () => void;
  onClearOutput: () => void;
  onClearTerminal: () => void;
  onClosePanel: () => void;
  activeFileName: string;
}

export const VSCodeBottomPanel: React.FC<VSCodeBottomPanelProps> = ({
  activeTab,
  onSelectTab,
  executionResult,
  analysisResult,
  selectedIssue,
  fixResponse,
  isFixing,
  terminalLogs,
  onSelectIssue,
  onFixIssueWithAi,
  onAcceptFix,
  onRejectFix,
  onRegenerateFix,
  onClearOutput,
  onClearTerminal,
  onClosePanel,
  activeFileName,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  // Issues count
  const issues = analysisResult?.issues || [];
  const errorCount = issues.filter((i) => i.severity === 'Critical' || i.severity === 'High').length;
  const warningCount = issues.filter((i) => i.severity === 'Medium' || i.severity === 'Low').length;

  const handleCopyCode = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className={`bg-[#1e1e1e] border-t border-[#2d2d2d] flex flex-col text-[#cccccc] font-sans select-none transition-all ${
        isExpanded ? 'h-[460px]' : 'h-[250px]'
      }`}
    >
      {/* Panel Tab Header */}
      <div className="h-9 px-3 bg-[#1e1e1e] border-b border-[#2d2d2d] flex items-center justify-between text-[11.5px] shrink-0">
        {/* Left Tabs */}
        <div className="flex items-center h-full space-x-4">
          {/* 1. Output Tab */}
          <button
            type="button"
            onClick={() => onSelectTab('output')}
            className={`h-full flex items-center gap-1.5 uppercase tracking-wider font-semibold border-b-2 transition-colors ${
              activeTab === 'output'
                ? 'text-white border-[#007acc]'
                : 'text-[#858585] border-transparent hover:text-[#cccccc]'
            }`}
          >
            <span>Output</span>
          </button>

          {/* 2. Problems Tab with Count Badges */}
          <button
            type="button"
            onClick={() => onSelectTab('problems')}
            className={`h-full flex items-center gap-1.5 uppercase tracking-wider font-semibold border-b-2 transition-colors ${
              activeTab === 'problems'
                ? 'text-white border-[#007acc]'
                : 'text-[#858585] border-transparent hover:text-[#cccccc]'
            }`}
          >
            <span>Problems</span>
            {issues.length > 0 && (
              <span className="flex items-center gap-1 ml-0.5">
                {errorCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-[#f14c4c] text-white">
                    {errorCount}
                  </span>
                )}
                {warningCount > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-[#cca700] text-black">
                    {warningCount}
                  </span>
                )}
              </span>
            )}
          </button>

          {/* 3. Terminal Tab */}
          <button
            type="button"
            onClick={() => onSelectTab('terminal')}
            className={`h-full flex items-center gap-1.5 uppercase tracking-wider font-semibold border-b-2 transition-colors ${
              activeTab === 'terminal'
                ? 'text-white border-[#007acc]'
                : 'text-[#858585] border-transparent hover:text-[#cccccc]'
            }`}
          >
            <span>Terminal</span>
          </button>

          {/* 4. AI Explanation Tab */}
          <button
            type="button"
            onClick={() => onSelectTab('explanation')}
            className={`h-full flex items-center gap-1.5 uppercase tracking-wider font-semibold border-b-2 transition-colors ${
              activeTab === 'explanation'
                ? 'text-[#007acc] border-[#007acc]'
                : 'text-[#858585] border-transparent hover:text-[#cccccc]'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Explanation</span>
            {fixResponse && (
              <span className="w-1.5 h-1.5 rounded-full bg-[#89d185]" />
            )}
          </button>
        </div>

        {/* Right Panel Actions */}
        <div className="flex items-center gap-1">
          {activeTab === 'output' && (
            <button
              type="button"
              onClick={onClearOutput}
              className="p-1 rounded text-[#858585] hover:text-[#cccccc] hover:bg-[#2d2d2d]"
              title="Clear Output"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          {activeTab === 'terminal' && (
            <button
              type="button"
              onClick={onClearTerminal}
              className="p-1 rounded text-[#858585] hover:text-[#cccccc] hover:bg-[#2d2d2d]"
              title="Clear Terminal"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="p-1 rounded text-[#858585] hover:text-[#cccccc] hover:bg-[#2d2d2d]"
            title={isExpanded ? 'Minimize Panel' : 'Maximize Panel'}
          >
            {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

          <button
            type="button"
            onClick={onClosePanel}
            className="p-1 rounded text-[#858585] hover:text-[#cccccc] hover:bg-[#2d2d2d]"
            title="Close Panel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tab 1: Output */}
      {activeTab === 'output' && (
        <div className="flex-1 overflow-y-auto p-3 font-mono text-[12.5px] leading-relaxed bg-[#181818] text-[#cccccc]">
          {!executionResult ? (
            <div className="text-[#858585] italic flex flex-col justify-center items-center h-full py-8 text-center">
              <Terminal className="w-6 h-6 text-[#555555] mb-2" />
              <p>No program output yet.</p>
              <p className="text-[11px] text-[#666666] mt-0.5">
                Press <span className="text-[#007acc] font-semibold">Run Code</span> (Ctrl+Enter) to safely execute in the isolated sandbox.
              </p>
              <p className="text-[10.5px] text-[#555555] mt-2 max-w-md">
                Safety Note: PreCommit AI strictly prevents arbitrary automatic code execution. Code only runs upon explicit user request inside an ephemeral sandbox.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Output metadata bar */}
              <div className="flex items-center justify-between text-[11px] font-sans pb-1.5 border-b border-[#2d2d2d] text-[#858585]">
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1 font-semibold ${
                      executionResult.success && executionResult.exit_code === 0
                        ? 'text-[#89d185]'
                        : 'text-[#f14c4c]'
                    }`}
                  >
                    {executionResult.success && executionResult.exit_code === 0 ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : (
                      <AlertCircle className="w-3 h-3" />
                    )}
                    {executionResult.success && executionResult.exit_code === 0
                      ? 'Process Completed'
                      : executionResult.status === 'timeout'
                      ? 'Execution Timed Out'
                      : 'Process Failed'}
                  </span>
                  <span>Exit code: {executionResult.exit_code}</span>
                </div>
                <span>Duration: {executionResult.execution_time_ms.toFixed(1)} ms</span>
              </div>

              {/* Stdout */}
              {executionResult.stdout && (
                <pre className="whitespace-pre-wrap text-[#d4d4d4] selection:bg-[#264f78]">
                  {executionResult.stdout}
                </pre>
              )}

              {/* Stderr / Traceback */}
              {(executionResult.stderr || executionResult.traceback) && (
                <pre className="whitespace-pre-wrap text-[#f48771] selection:bg-[#5a1d1d] font-semibold">
                  {executionResult.traceback || executionResult.stderr}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Problems */}
      {activeTab === 'problems' && (
        <div className="flex-1 overflow-y-auto bg-[#181818]">
          {issues.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-8 text-center text-[#858585]">
              <CheckCircle2 className="w-6 h-6 text-[#89d185] mb-2" />
              <p className="font-medium text-[#cccccc]">No problems have been detected in the workspace.</p>
              <p className="text-[11.5px] text-[#666666] mt-0.5">
                AST syntax parsing and resource management rules verified 0 issues.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#262626] font-mono text-[12px]">
              {issues.map((issue) => {
                const isSelected = selectedIssue?.id === issue.id;
                const isError = issue.severity === 'Critical' || issue.severity === 'High';

                return (
                  <div
                    key={issue.id}
                    onClick={() => onSelectIssue(issue)}
                    className={`px-3 py-2 flex items-center justify-between gap-3 cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[#04395e] text-white'
                        : 'hover:bg-[#222222] text-[#cccccc]'
                    }`}
                  >
                    {/* Left: Icon & Description */}
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      {isError ? (
                        <AlertCircle className="w-4 h-4 text-[#f14c4c] shrink-0" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-[#cca700] shrink-0" />
                      )}

                      <span className="font-sans font-medium truncate text-[#e1e1e1]">
                        {issue.description}
                      </span>

                      {issue.rule_id && (
                        <span className="text-[10.5px] px-1 py-0.2 rounded bg-[#2b2b2b] text-[#9cdcfe] shrink-0">
                          {issue.rule_id}
                        </span>
                      )}
                    </div>

                    {/* Right: File & Coordinate + Quick Fix button */}
                    <div className="flex items-center gap-3 shrink-0 font-sans text-[11px]">
                      <span className="text-[#858585]">
                        {activeFileName} [{issue.line}, {issue.column}]
                      </span>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIssue(issue);
                          onFixIssueWithAi(issue);
                        }}
                        disabled={isFixing}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#007acc] hover:bg-[#0062a3] text-white font-medium text-[11px] transition-colors"
                        title="Generate AI Fix for this issue"
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>Quick Fix</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Terminal */}
      {activeTab === 'terminal' && (
        <div className="flex-1 overflow-y-auto p-3 font-mono text-[12px] bg-[#141414] text-[#cccccc] space-y-1">
          <div className="text-[#858585] pb-2 border-b border-[#222222]">
            PreCommit AI Subprocess Terminal [Version 2.4.0]
            <br />
            (c) PreCommit AI Team. Safe sandbox active.
          </div>

          <div className="space-y-1 py-1">
            {terminalLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-2">
                <span className="text-[#555555] shrink-0 select-none">[{log.timestamp}]</span>
                <span
                  className={
                    log.type === 'error'
                      ? 'text-[#f14c4c]'
                      : log.type === 'warn'
                      ? 'text-[#cca700]'
                      : log.type === 'success'
                      ? 'text-[#89d185]'
                      : 'text-[#9cdcfe]'
                  }
                >
                  {log.message}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2 text-[#858585] pt-1">
            <span className="text-[#89d185]">playground@precommit-ai</span>
            <span>:</span>
            <span className="text-[#58a6ff]">~</span>
            <span>$</span>
            <span className="w-2 h-4 bg-[#cccccc] animate-pulse inline-block" />
          </div>
        </div>
      )}

      {/* Tab 4: AI Explanation */}
      {activeTab === 'explanation' && (
        <div className="flex-1 overflow-y-auto p-4 bg-[#1e1e1e] space-y-4 text-[12.5px]">
          {!fixResponse ? (
            <div className="flex flex-col items-center justify-center h-full py-8 text-center text-[#858585]">
              <Sparkles className="w-6 h-6 text-[#007acc] mb-2" />
              <p className="font-medium text-[#cccccc]">No AI fix generated yet.</p>
              <p className="text-[11.5px] text-[#666666] mt-0.5">
                Select an issue in Problems and click &quot;Quick Fix&quot; or click &quot;Fix with AI&quot;.
              </p>
              <button
                type="button"
                onClick={() => onFixIssueWithAi(selectedIssue || undefined)}
                disabled={isFixing}
                className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#007acc] hover:bg-[#0062a3] text-white text-[12px] font-medium transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generate AI Fix with Ollama</span>
              </button>
            </div>
          ) : (
            <div className="space-y-3 font-sans">
              {/* Header with status and Actions */}
              <div className="flex items-center justify-between pb-2 border-b border-[#2d2d2d]">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white text-[13px]">
                    Ollama Suggested Fix ({fixResponse.ai_model})
                  </span>
                  {fixResponse.is_valid && (
                    <span className="px-1.5 py-0.2 rounded text-[10.5px] font-semibold bg-[#1b2b1d] text-[#89d185]">
                      ✓ AST Validated
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleCopyCode(fixResponse.suggested_code)}
                    className="px-2 py-1 rounded bg-[#2d2d2d] hover:bg-[#383838] text-[11px] text-[#cccccc] flex items-center gap-1"
                  >
                    {copied ? <Check className="w-3 h-3 text-[#89d185]" /> : <Copy className="w-3 h-3" />}
                    <span>{copied ? 'Copied' : 'Copy Code'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={onRegenerateFix}
                    disabled={isFixing}
                    className="px-2 py-1 rounded bg-[#2d2d2d] hover:bg-[#383838] text-[11px] text-[#cccccc] flex items-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Regenerate</span>
                  </button>

                  <button
                    type="button"
                    onClick={onRejectFix}
                    className="px-2.5 py-1 rounded bg-[#333333] hover:bg-[#444444] text-[11px] text-[#cccccc]"
                  >
                    Reject
                  </button>

                  <button
                    type="button"
                    onClick={() => onAcceptFix(fixResponse.suggested_code)}
                    className="px-3 py-1 rounded bg-[#1a7f37] hover:bg-[#1f883d] text-white text-[11.5px] font-semibold flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Accept Fix</span>
                  </button>
                </div>
              </div>

              {/* 6-Part Structured Explanation Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* 1. What is the error */}
                <div className="p-3 rounded bg-[#252526] border border-[#333333] space-y-1">
                  <div className="text-[11px] font-bold text-[#f14c4c] uppercase tracking-wider">
                    1. What is the error?
                  </div>
                  <p className="text-[12px] text-[#cccccc]">
                    {fixResponse.explanation.what_is_error}
                  </p>
                </div>

                {/* 2. Why does it happen */}
                <div className="p-3 rounded bg-[#252526] border border-[#333333] space-y-1">
                  <div className="text-[11px] font-bold text-[#cca700] uppercase tracking-wider">
                    2. Why does it happen?
                  </div>
                  <p className="text-[12px] text-[#cccccc]">
                    {fixResponse.explanation.side_effects || 'Resource handle left without guaranteed cleanup or syntax constraint violated.'}
                  </p>
                </div>

                {/* 3. How can it be fixed */}
                <div className="p-3 rounded bg-[#252526] border border-[#333333] space-y-1">
                  <div className="text-[11px] font-bold text-[#58a6ff] uppercase tracking-wider">
                    3. How can it be fixed?
                  </div>
                  <p className="text-[12px] text-[#cccccc]">
                    {fixResponse.explanation.how_it_is_fixed}
                  </p>
                </div>

                {/* 4. Why is suggested code correct */}
                <div className="p-3 rounded bg-[#252526] border border-[#333333] space-y-1">
                  <div className="text-[11px] font-bold text-[#89d185] uppercase tracking-wider">
                    4. Why is this fix correct?
                  </div>
                  <p className="text-[12px] text-[#cccccc]">
                    {fixResponse.explanation.why_it_is_correct}
                  </p>
                </div>
              </div>

              {/* Suggested Code Preview */}
              <div className="space-y-1">
                <div className="text-[11px] font-bold text-[#858585] uppercase tracking-wider">
                  Corrected Code Preview
                </div>
                <div className="p-2.5 rounded bg-[#181818] border border-[#2d2d2d] font-mono text-[11.5px] max-h-40 overflow-y-auto text-[#d4d4d4]">
                  <pre className="whitespace-pre-wrap">{fixResponse.suggested_code}</pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};


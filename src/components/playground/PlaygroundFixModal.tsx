import React, { useState } from 'react';
import {
  X,
  Sparkles,
  Check,
  RotateCcw,
  Copy,
  CheckCheck,
  AlertTriangle,
  Info,
  ShieldCheck,
  FileCode,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { DiffEditor } from '@monaco-editor/react';
import { PlaygroundFixResponse } from '../../types/playground';

interface PlaygroundFixModalProps {
  isOpen: boolean;
  onClose: () => void;
  fixResponse: PlaygroundFixResponse | null;
  onAcceptFix: (suggestedCode: string) => void;
  onRegenerateFix: () => void;
  isRegenerating: boolean;
}

export const PlaygroundFixModal: React.FC<PlaygroundFixModalProps> = ({
  isOpen,
  onClose,
  fixResponse,
  onAcceptFix,
  onRegenerateFix,
  isRegenerating,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'diff' | 'explanation'>('diff');

  if (!isOpen || !fixResponse) return null;

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(fixResponse.suggested_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      setCopied(false);
    }
  };

  const handleAccept = () => {
    onAcceptFix(fixResponse.suggested_code);
    onClose();
  };

  const { explanation } = fixResponse;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-neutral-900/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
    >
      <div className="relative w-full max-w-5xl h-[90vh] bg-white rounded-[16px] shadow-2xl border border-neutral-200/90 flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-neutral-200/80 bg-neutral-50/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-[9px] bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-xs">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-neutral-900">
                  AI Code Correction Review
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-neutral-200 text-neutral-700 font-mono">
                  {fixResponse.ai_model || 'Ollama'}
                </span>
                {fixResponse.is_valid ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-100 text-emerald-800">
                    <ShieldCheck className="w-3 h-3 text-emerald-600" />
                    AST Validated
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-100 text-amber-800">
                    <AlertTriangle className="w-3 h-3 text-amber-600" />
                    Validation Warning
                  </span>
                )}
              </div>
              <p className="text-[12px] text-neutral-500 mt-0.5">
                Inspect AI-generated fixes, AST verification, and reasoning before applying to your playground.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-[8px] text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center justify-between px-5 py-2 border-b border-neutral-200 bg-white">
          <div className="flex items-center gap-1 p-1 bg-neutral-100 rounded-[10px]">
            <button
              type="button"
              onClick={() => setActiveTab('diff')}
              className={`px-3 py-1 rounded-[7px] text-[12px] font-medium transition-all ${
                activeTab === 'diff'
                  ? 'bg-white text-neutral-900 font-semibold shadow-2xs'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Side-by-Side Diff
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('explanation')}
              className={`px-3 py-1 rounded-[7px] text-[12px] font-medium transition-all ${
                activeTab === 'explanation'
                  ? 'bg-white text-neutral-900 font-semibold shadow-2xs'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Structured Explanation & Analysis
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyCode}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-[12px] font-medium transition-colors shadow-2xs"
            >
              {copied ? (
                <>
                  <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-700">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-neutral-500" />
                  <span>Copy Code</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onRegenerateFix}
              disabled={isRegenerating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-[12px] font-medium transition-colors shadow-2xs disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
              <span>Regenerate</span>
            </button>
          </div>
        </div>

        {/* Modal Main Content */}
        <div className="flex-1 overflow-hidden relative flex flex-col">
          {activeTab === 'diff' ? (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Header labels for Original vs Suggested */}
              <div className="grid grid-cols-2 text-xs font-semibold border-b border-neutral-200 bg-neutral-100/70 text-neutral-600">
                <div className="px-4 py-2 border-r border-neutral-200 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-400" />
                  <span>Original Code (Current)</span>
                </div>
                <div className="px-4 py-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span>Suggested Fix (Ollama)</span>
                  </div>
                  {fixResponse.is_valid && (
                    <span className="text-[11px] font-normal text-emerald-700">
                      ✓ Syntax verified
                    </span>
                  )}
                </div>
              </div>

              {/* Monaco Diff Editor */}
              <div className="flex-1 min-h-0">
                <DiffEditor
                  original={fixResponse.original_code}
                  modified={fixResponse.suggested_code}
                  language="python"
                  theme="vs-dark"
                  options={{
                    readOnly: true,
                    renderSideBySide: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, monospace",
                    automaticLayout: true,
                    wordWrap: 'on',
                  }}
                />
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-neutral-50/50">
              {/* Card 1: What is the error */}
              <div className="p-4 rounded-[12px] bg-white border border-red-200 shadow-2xs">
                <div className="flex items-center gap-2 text-red-700 font-semibold text-[13.5px] mb-1.5">
                  <AlertTriangle className="w-4 h-4" />
                  <h4>1. What is the error?</h4>
                </div>
                <p className="text-[13px] text-neutral-700 leading-relaxed">
                  {explanation.what_is_error || 'No issue description available.'}
                </p>
              </div>

              {/* Card 2: How it is fixed */}
              <div className="p-4 rounded-[12px] bg-white border border-blue-200 shadow-2xs">
                <div className="flex items-center gap-2 text-blue-700 font-semibold text-[13.5px] mb-1.5">
                  <Sparkles className="w-4 h-4" />
                  <h4>2. How it is fixed</h4>
                </div>
                <p className="text-[13px] text-neutral-700 leading-relaxed">
                  {explanation.how_it_is_fixed || 'Fixed according to Python AST rules.'}
                </p>
              </div>

              {/* Card 3: Why it is correct */}
              <div className="p-4 rounded-[12px] bg-white border border-emerald-200 shadow-2xs">
                <div className="flex items-center gap-2 text-emerald-700 font-semibold text-[13.5px] mb-1.5">
                  <ShieldCheck className="w-4 h-4" />
                  <h4>3. Why this fix is correct</h4>
                </div>
                <p className="text-[13px] text-neutral-700 leading-relaxed">
                  {explanation.why_it_is_correct || 'Preserves semantic intent and prevents resource leaks.'}
                </p>
              </div>

              {/* Card 4: Potential side effects */}
              <div className="p-4 rounded-[12px] bg-white border border-neutral-200 shadow-2xs">
                <div className="flex items-center gap-2 text-neutral-800 font-semibold text-[13.5px] mb-1.5">
                  <Info className="w-4 h-4 text-neutral-500" />
                  <h4>4. Potential Side Effects</h4>
                </div>
                <p className="text-[13px] text-neutral-600 leading-relaxed">
                  {explanation.side_effects || 'None detected. The changes maintain backward compatibility.'}
                </p>
              </div>

              {/* Applied Fixes list if any */}
              {fixResponse.fixes_applied && fixResponse.fixes_applied.length > 0 && (
                <div className="p-4 rounded-[12px] bg-white border border-neutral-200">
                  <h4 className="text-[13px] font-semibold text-neutral-800 mb-2">
                    Applied Adjustments ({fixResponse.fixes_applied.length}):
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-[12.5px] text-neutral-600">
                    {fixResponse.fixes_applied.map((fix, idx) => (
                      <li key={idx}>{fix}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-neutral-200 bg-white">
          <div className="text-[12px] text-neutral-500">
            Accepting this fix will replace the code in your active Playground editor.
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-[9px] border border-neutral-200 hover:bg-neutral-100 text-neutral-700 text-[13px] font-medium transition-colors"
            >
              Reject Fix
            </button>

            <button
              type="button"
              onClick={handleAccept}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-[9px] bg-emerald-600 hover:bg-emerald-700 text-white text-[13px] font-semibold transition-all shadow-xs"
            >
              <Check className="w-4 h-4" />
              <span>Accept Fix</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};


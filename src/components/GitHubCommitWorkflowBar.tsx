import React, { useState } from 'react';
import { ValidationResult } from '../types/analysis';
import {
  GitCommit,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  ShieldCheck,
  Download,
  Loader2,
  ArrowRight,
  GitPullRequest,
  Sparkles,
} from 'lucide-react';

interface GitHubCommitWorkflowBarProps {
  totalFindings: number;
  approvedCount: number;
  sourceType: 'file' | 'zip' | 'github';
  branchName: string;
  commitMessage: string;
  onCommitMessageChange: (msg: string) => void;
  isValidating: boolean;
  validationResult: ValidationResult | null;
  onValidate: () => Promise<void>;
  onOpenCommitModal: () => void;
  onDownloadPatchedZip: () => void;
}

export const GitHubCommitWorkflowBar: React.FC<GitHubCommitWorkflowBarProps> = ({
  totalFindings,
  approvedCount,
  sourceType,
  branchName,
  commitMessage,
  onCommitMessageChange,
  isValidating,
  validationResult,
  onValidate,
  onOpenCommitModal,
  onDownloadPatchedZip,
}) => {
  // Determine current active workflow step (1 to 4)
  let activeStep = 1;
  if (approvedCount > 0) activeStep = 2;
  if (validationResult?.isValid) activeStep = 3;
  if (validationResult?.isValid && approvedCount > 0) activeStep = 4;

  const steps = [
    { number: 1, title: 'Review Fixes', detail: `${approvedCount}/${totalFindings} approved` },
    { number: 2, title: 'Apply Changes', detail: approvedCount > 0 ? 'Fixes staged' : 'Approval needed' },
    { number: 3, title: 'Validate Code', detail: validationResult?.isValid ? '0 syntax errors' : 'AST re-parse' },
    { number: 4, title: 'Commit to GitHub', detail: 'Dedicated branch' },
  ];

  const addedLinesEstimate = approvedCount * 2;
  const removedLinesEstimate = approvedCount * 1;
  const changedFilesCount = approvedCount > 0 ? Math.min(approvedCount, 3) : 0;

  return (
    <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs space-y-4">
      {/* Step Header Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-100 pb-3">
        <div className="flex items-center gap-2">
          <GitPullRequest className="w-4 h-4 text-neutral-800" />
          <h3 className="text-[15px] font-bold text-neutral-900 tracking-tight">
            Remediation &amp; GitHub Commit Pipeline
          </h3>
        </div>

        <div className="flex items-center gap-2 text-[12px] font-medium text-neutral-500">
          <span>Pipeline Progress:</span>
          <span className="font-semibold text-neutral-800">
            Step {activeStep} of 4 ({Math.round((activeStep / 4) * 100)}%)
          </span>
        </div>
      </div>

      {/* Horizontal Four-Step Stepper */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {steps.map((s) => {
          const isDone = activeStep > s.number || (s.number === 3 && validationResult?.isValid);
          const isCurrent = activeStep === s.number;

          return (
            <div
              key={s.number}
              className={`p-3 rounded-[11px] border transition-all ${
                isDone
                  ? 'bg-emerald-50/50 border-emerald-200/90 text-emerald-950'
                  : isCurrent
                  ? 'bg-neutral-900 text-white border-neutral-900 shadow-xs'
                  : 'bg-neutral-50/60 border-neutral-200/70 text-neutral-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`w-5 h-5 rounded-full text-[11px] font-bold flex items-center justify-center font-mono ${
                  isDone
                    ? 'bg-emerald-600 text-white'
                    : isCurrent
                    ? 'bg-white text-neutral-900'
                    : 'bg-neutral-200 text-neutral-600'
                }`}>
                  {isDone ? '✓' : s.number}
                </span>

                <span className={`text-[11px] font-medium ${
                  isCurrent ? 'text-neutral-300' : 'text-neutral-400'
                }`}>
                  {s.detail}
                </span>
              </div>

              <div className="font-semibold text-[13px]">{s.title}</div>
            </div>
          );
        })}
      </div>

      {/* Workflow Controls & Configuration Bar */}
      <div className="pt-2 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-neutral-50/70 p-4 rounded-[12px] border border-neutral-200/70">
        {/* Left: Commit inputs */}
        <div className="flex-1 space-y-2.5 max-w-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2">
            {/* Target Branch Badge */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[9px] bg-white border border-neutral-300/80 text-[12.5px] font-mono font-medium text-neutral-700 flex-shrink-0">
              <GitBranch className="w-3.5 h-3.5 text-neutral-500" />
              <span>Target:</span>
              <span className="font-bold text-neutral-900">
                precommit-ai/fix-{branchName.slice(0, 8)}
              </span>
            </div>

            {/* Metrics Badges: Changed Files, Lines Added, Lines Removed */}
            <div className="flex items-center gap-1.5 text-[12px] font-mono">
              <span className="px-2 py-1 rounded-[7px] bg-neutral-200/70 text-neutral-800">
                {changedFilesCount} {changedFilesCount === 1 ? 'file' : 'files'}
              </span>
              <span className="px-2 py-1 rounded-[7px] bg-emerald-100 text-emerald-800 font-semibold">
                +{addedLinesEstimate}
              </span>
              <span className="px-2 py-1 rounded-[7px] bg-red-100 text-red-800 font-semibold">
                -{removedLinesEstimate}
              </span>
            </div>
          </div>

          {/* Editable Commit Message Input */}
          <div className="relative">
            <input
              type="text"
              value={commitMessage}
              onChange={(e) => onCommitMessageChange(e.target.value)}
              placeholder="Commit message: fix: resolve syntax and resource management issues"
              className="w-full px-3 py-2 text-[13px] border border-neutral-300 rounded-[9px] bg-white text-neutral-900 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 transition-all font-sans"
            />
          </div>

          {/* Validation Status Indicator */}
          {validationResult && (
            <div className={`p-2.5 rounded-[8px] text-[12.5px] flex items-center gap-2 border ${
              validationResult.isValid
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-red-50 text-red-800 border-red-200'
            }`}>
              {validationResult.isValid ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>
                    <strong>AST Validation Passed:</strong> All patched files compile cleanly with 0 syntax errors. ({validationResult.fixedCount} issues resolved)
                  </span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <span>
                    <strong>Validation Failed:</strong> Syntax regressions detected during re-parse.
                  </span>
                </>
              )}
            </div>
          )}
        </div>

        {/* Right: Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap lg:flex-nowrap flex-shrink-0">
          {/* Step 3: Run Validation Button */}
          <button
            type="button"
            onClick={onValidate}
            disabled={isValidating || approvedCount === 0}
            className="px-3.5 py-2 rounded-[10px] border border-neutral-300 bg-white hover:bg-neutral-100 text-neutral-800 text-[13px] font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 disabled:opacity-50"
            title="Re-parse code with AST to check for regressions"
          >
            {isValidating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Validating AST...</span>
              </>
            ) : (
              <>
                <FileCheck className="w-3.5 h-3.5 text-neutral-600" />
                <span>Validate Code</span>
              </>
            )}
          </button>

          {/* Download Patched ZIP (Always available for local/offline export) */}
          <button
            type="button"
            onClick={onDownloadPatchedZip}
            disabled={approvedCount === 0}
            className="px-3.5 py-2 rounded-[10px] border border-neutral-300 bg-white hover:bg-neutral-100 text-neutral-800 text-[13px] font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 disabled:opacity-50"
            title="Download corrected code archive as ZIP"
          >
            <Download className="w-3.5 h-3.5 text-neutral-600" />
            <span>Download ZIP</span>
          </button>

          {/* Step 4: Commit to GitHub Primary Action */}
          <button
            type="button"
            onClick={onOpenCommitModal}
            disabled={approvedCount === 0}
            className="px-4 py-2 rounded-[10px] bg-[#050505] hover:bg-neutral-800 text-white text-[13px] font-semibold transition-all shadow-xs inline-flex items-center gap-2 hover:shadow disabled:opacity-50"
          >
            <GitCommit className="w-4 h-4 text-emerald-400" />
            <span>Commit to GitHub</span>
          </button>
        </div>
      </div>
    </div>
  );
};


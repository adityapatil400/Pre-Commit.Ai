import React, { useState } from 'react';
import { Finding, ApprovalStatus } from '../types/analysis';
import { DiffViewer } from './DiffViewer';
import {
  AlertTriangle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
  FileCode,
  CheckCircle,
  Copy,
  Check,
  ShieldAlert,
  Wrench,
  CheckCheck,
  X,
} from 'lucide-react';

interface FindingCardProps {
  finding: Finding;
  onStatusChange?: (id: string, status: ApprovalStatus) => void;
  onEditFix?: (id: string, editedCode: string) => void;
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding, onStatusChange, onEditFix }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const getSeverityBadge = () => {
    switch (finding.severity) {
      case 'error':
        return {
          icon: XCircle,
          label: 'Error',
          className: 'bg-red-50 text-red-700 border-red-200',
          iconColor: 'text-red-600',
        };
      case 'warning':
        return {
          icon: AlertTriangle,
          label: 'Warning',
          className: 'bg-amber-50 text-amber-800 border-amber-200',
          iconColor: 'text-amber-600',
        };
      case 'information':
      default:
        return {
          icon: Info,
          label: 'Information',
          className: 'bg-blue-50 text-blue-700 border-blue-200',
          iconColor: 'text-blue-600',
        };
    }
  };

  const badge = getSeverityBadge();
  const Icon = badge.icon;

  const handleCopyFix = () => {
    navigator.clipboard.writeText(finding.suggestedFix);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const approval = finding.approvalStatus || 'pending';

  return (
    <article className="rounded-[16px] border border-neutral-200 bg-white shadow-sm overflow-hidden transition-all duration-200 hover:border-neutral-300">
      {/* Card Header / Summary Line */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer bg-neutral-50/40 hover:bg-neutral-50 transition-colors select-none"
      >
        <div className="flex items-start sm:items-center gap-3">
          <div className="mt-0.5 sm:mt-0 flex-shrink-0">
            <Icon className={`w-5 h-5 ${badge.iconColor}`} />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2.5 flex-wrap">
            <span className="font-mono text-[12px] font-bold text-neutral-600 bg-neutral-100 border border-neutral-200 px-2 py-0.5 rounded">
              {finding.ruleId}
            </span>

            <span className={`text-[12px] font-semibold px-2 py-0.5 rounded-full border ${badge.className}`}>
              {badge.label}
            </span>

            {/* Approval Status Badge */}
            {finding.fixable && (
              <span
                className={`text-[11.5px] font-medium px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                  approval === 'accepted'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                    : approval === 'rejected'
                    ? 'bg-neutral-100 text-neutral-600 border-neutral-300'
                    : approval === 'edited'
                    ? 'bg-blue-50 text-blue-700 border-blue-300'
                    : approval === 'stale'
                    ? 'bg-red-50 text-red-700 border-red-300'
                    : 'bg-amber-50 text-amber-700 border-amber-300'
                }`}
              >
                {approval === 'accepted' && <Check className="w-3 h-3 stroke-[2.5]" />}
                {approval === 'rejected' && <X className="w-3 h-3" />}
                {approval === 'edited' && <CheckCheck className="w-3 h-3 text-blue-600" />}
                {approval === 'pending' && <Wrench className="w-3 h-3" />}
                <span>
                  {approval === 'accepted'
                    ? 'Fix Accepted'
                    : approval === 'rejected'
                    ? 'Fix Rejected'
                    : approval === 'edited'
                    ? 'Fix Edited'
                    : approval === 'stale'
                    ? 'Stale Fix'
                    : 'Approval Needed'}
                </span>
              </span>
            )}

            <h4 className="text-[15px] sm:text-[16px] font-bold text-[#050505]">
              {finding.title}
            </h4>
          </div>
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-3 text-neutral-500 text-[13px]">
          <div className="flex items-center gap-1.5 font-mono text-[12px] sm:text-[13px] text-neutral-700 bg-white px-2.5 py-1 rounded-md border border-neutral-200">
            <FileCode className="w-3.5 h-3.5 text-neutral-500" />
            <span className="truncate max-w-[200px] sm:max-w-[280px]">
              {finding.filePath}:{finding.line}
            </span>
          </div>

          <button
            type="button"
            className="p-1 rounded-md hover:bg-neutral-200/60 text-neutral-600"
            aria-label={isExpanded ? 'Collapse finding details' : 'Expand finding details'}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4 sm:p-6 border-t border-neutral-100 space-y-4">
          {/* Static analysis vs runtime distinction alert */}
          {finding.isPotentialWarning && (
            <div className="flex items-start gap-2.5 p-3 rounded-[10px] bg-amber-50/60 border border-amber-200/80 text-[13px] text-amber-900">
              <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Static Analysis Heuristic:</span> This pattern suggests a potential leak or resource mismanagement based on AST pattern matching. It is not a confirmed runtime crash, but violates deterministic resource-handling standards.
              </div>
            </div>
          )}

          {/* Description */}
          <div>
            <h5 className="text-[12px] font-semibold text-neutral-500 uppercase tracking-wider mb-1">
              Description
            </h5>
            <p className="text-[14px] text-neutral-800 leading-relaxed">
              {finding.description}
            </p>
          </div>

          {/* Interactive Code Diff Viewer (Steps 5 & 6) */}
          {(finding.proposedCode || finding.unifiedDiff || finding.originalCode) && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[12px] font-semibold text-neutral-500 uppercase tracking-wider">
                  Code Comparison &amp; Approval
                </span>
                {finding.fixable && onStatusChange && (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onStatusChange(finding.id, 'accepted')}
                      className={`text-[12px] font-semibold px-2.5 py-0.5 rounded border transition-colors ${
                        approval === 'accepted'
                          ? 'bg-emerald-600 text-white border-emerald-600'
                          : 'bg-white text-emerald-700 border-emerald-300 hover:bg-emerald-50'
                      }`}
                    >
                      ✓ Accept Fix
                    </button>
                    <button
                      type="button"
                      onClick={() => onStatusChange(finding.id, 'rejected')}
                      className={`text-[12px] font-semibold px-2.5 py-0.5 rounded border transition-colors ${
                        approval === 'rejected'
                          ? 'bg-neutral-800 text-white border-neutral-800'
                          : 'bg-white text-neutral-600 border-neutral-300 hover:bg-neutral-100'
                      }`}
                    >
                      ✕ Reject
                    </button>
                  </div>
                )}
              </div>

              <DiffViewer
                originalCode={finding.originalCode || finding.codeSnippet || ''}
                proposedCode={finding.proposedCode || finding.suggestedFix || ''}
                unifiedDiff={finding.unifiedDiff}
                approvalStatus={approval}
                fixable={finding.fixable}
                onApprove={() => onStatusChange?.(finding.id, 'accepted')}
                onReject={() => onStatusChange?.(finding.id, 'rejected')}
                onEdit={onEditFix ? (newCode) => onEditFix(finding.id, newCode) : undefined}
              />
            </div>
          )}

          {/* Suggested Remediation Text Box */}
          <div className="rounded-[12px] bg-emerald-50/50 border border-emerald-200/80 p-3.5 sm:p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-emerald-800 font-semibold text-[13.5px]">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                <span>Suggested Remediation</span>
              </div>
              <button
                type="button"
                onClick={handleCopyFix}
                className="inline-flex items-center gap-1 text-[12px] font-medium text-emerald-800 hover:text-emerald-900 bg-white/80 hover:bg-white border border-emerald-300 px-2 py-1 rounded focus-ring transition-colors"
                title="Copy suggested fix to clipboard"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy Fix'}</span>
              </button>
            </div>
            <div className="font-mono text-[13px] text-emerald-950 bg-white/70 p-2.5 rounded-[8px] border border-emerald-200/60 whitespace-pre-wrap">
              {finding.suggestedFix}
            </div>
          </div>

          {/* Additional Technical Explanation */}
          {finding.explanation && (
            <div className="text-[13px] text-neutral-600 italic">
              <strong>Technical rationale:</strong> {finding.explanation}
            </div>
          )}
        </div>
      )}
    </article>
  );
};

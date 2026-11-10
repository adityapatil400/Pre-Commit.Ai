import React, { useState } from 'react';
import { Check, X, FileCode, Edit3, Save, RotateCcw } from 'lucide-react';
import { ApprovalStatus } from '../types/analysis';

interface DiffViewerProps {
  originalCode: string;
  proposedCode: string;
  unifiedDiff?: string;
  approvalStatus: ApprovalStatus;
  fixable?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: (newCode: string) => void;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  originalCode,
  proposedCode,
  unifiedDiff,
  approvalStatus,
  fixable = false,
  onApprove,
  onReject,
  onEdit,
}) => {
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split');
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(proposedCode);

  const origTrimmed = originalCode.trim();
  const propTrimmed = (isEditing ? editValue : proposedCode).trim();

  const handleSaveEdit = () => {
    if (onEdit) {
      onEdit(editValue);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditValue(proposedCode);
    setIsEditing(false);
  };

  return (
    <div className="rounded-[12px] border border-neutral-200 bg-neutral-900 overflow-hidden text-neutral-100 font-mono text-[12.5px] sm:text-[13px] shadow-sm">
      {/* Diff Header Bar */}
      <div className="bg-neutral-800/90 px-3.5 py-2 flex items-center justify-between border-b border-neutral-700/80 text-[12px] text-neutral-300 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-neutral-400" />
          <span className="font-semibold text-neutral-200">Code Diff &amp; Remediation</span>
          {fixable && (
            <span className="bg-emerald-950/90 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[11px] font-sans font-medium">
              Auto-Fixable
            </span>
          )}
          {approvalStatus === 'edited' && (
            <span className="bg-blue-950/90 text-blue-300 border border-blue-800 px-2 py-0.5 rounded text-[11px] font-sans font-medium">
              Edited by User
            </span>
          )}
          {approvalStatus === 'stale' && (
            <span className="bg-red-950/90 text-red-300 border border-red-800 px-2 py-0.5 rounded text-[11px] font-sans font-medium">
              Stale Fix
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* View mode toggle */}
          <div className="inline-flex rounded-md bg-neutral-950 p-0.5 border border-neutral-700">
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`px-2 py-0.5 rounded text-[11px] font-sans transition-colors ${
                viewMode === 'split' ? 'bg-neutral-700 text-white font-medium' : 'text-neutral-400 hover:text-white'
              }`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              onClick={() => setViewMode('unified')}
              className={`px-2 py-0.5 rounded text-[11px] font-sans transition-colors ${
                viewMode === 'unified' ? 'bg-neutral-700 text-white font-medium' : 'text-neutral-400 hover:text-white'
              }`}
            >
              Unified Diff
            </button>
          </div>

          {/* User Approval Actions: 1. Accept, 2. Reject, 3. Edit */}
          {fixable && (
            <div className="flex items-center gap-1.5 ml-2">
              <button
                type="button"
                onClick={onApprove}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11.5px] font-sans font-semibold transition-all ${
                  approvalStatus === 'accepted'
                    ? 'bg-emerald-600 text-white ring-1 ring-emerald-400 shadow-xs'
                    : 'bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700/60'
                }`}
                title="Accept this fix"
              >
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>{approvalStatus === 'accepted' ? 'Accepted' : 'Accept Fix'}</span>
              </button>

              <button
                type="button"
                onClick={onReject}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11.5px] font-sans font-semibold transition-all ${
                  approvalStatus === 'rejected'
                    ? 'bg-red-600 text-white ring-1 ring-red-400 shadow-xs'
                    : 'bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-neutral-700'
                }`}
                title="Reject this fix"
              >
                <X className="w-3.5 h-3.5" />
                <span>{approvalStatus === 'rejected' ? 'Rejected' : 'Reject Fix'}</span>
              </button>

              {onEdit && (
                <button
                  type="button"
                  onClick={() => setIsEditing(!isEditing)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11.5px] font-sans font-semibold transition-all ${
                    isEditing || approvalStatus === 'edited'
                      ? 'bg-blue-600 text-white ring-1 ring-blue-400'
                      : 'bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-neutral-700'
                  }`}
                  title="Edit suggested code snippet"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>{isEditing ? 'Editing' : 'Edit Fix'}</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Inline Code Editor Mode */}
      {isEditing && (
        <div className="p-3 bg-neutral-950 border-b border-neutral-800 space-y-2">
          <div className="flex items-center justify-between text-[11.5px] text-neutral-400 font-sans">
            <span className="font-medium text-blue-300">Edit Suggested Code:</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSaveEdit}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[11.5px] transition-colors cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Edit</span>
              </button>
              <button
                type="button"
                onClick={handleCancelEdit}
                className="inline-flex items-center gap-1 px-2 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-[11.5px] transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Cancel</span>
              </button>
            </div>
          </div>
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            rows={5}
            className="w-full bg-neutral-900 text-emerald-300 font-mono text-[12.5px] p-2.5 rounded border border-neutral-700 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
            placeholder="Enter customized Python replacement code..."
          />
        </div>
      )}

      {/* Diff Content View */}
      {viewMode === 'split' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-neutral-800">
          {/* Left: Original Code */}
          <div className="p-3.5 bg-red-950/20">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-red-400 mb-1.5 flex items-center gap-1">
              <span>Original Code (Issue Detected)</span>
            </div>
            <pre className="overflow-x-auto text-red-200/90 whitespace-pre leading-relaxed">
              <code>{origTrimmed || '# No original line'}</code>
            </pre>
          </div>

          {/* Right: Suggested Code */}
          <div className="p-3.5 bg-emerald-950/25">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-emerald-400 mb-1.5 flex items-center gap-1">
              <span>Suggested Code (AST Corrected)</span>
            </div>
            <pre className="overflow-x-auto text-emerald-200/95 whitespace-pre leading-relaxed">
              <code>{propTrimmed || '# No automated change'}</code>
            </pre>
          </div>
        </div>
      ) : (
        /* Unified View */
        <div className="p-3.5 bg-neutral-950 overflow-x-auto">
          {unifiedDiff ? (
            <pre className="leading-relaxed whitespace-pre font-mono text-[12px]">
              {unifiedDiff.split('\n').map((line, idx) => {
                let colorClass = 'text-neutral-300';
                if (line.startsWith('+') && !line.startsWith('+++')) {
                  colorClass = 'text-emerald-400 bg-emerald-950/40 px-1 rounded block';
                } else if (line.startsWith('-') && !line.startsWith('---')) {
                  colorClass = 'text-red-400 bg-red-950/40 px-1 rounded block';
                } else if (line.startsWith('@@')) {
                  colorClass = 'text-blue-400 opacity-80';
                }
                return (
                  <span key={idx} className={colorClass}>
                    {line}
                    {'\n'}
                  </span>
                );
              })}
            </pre>
          ) : (
            <div className="space-y-1">
              <div className="text-red-400 bg-red-950/40 px-2 py-0.5 rounded">
                - {origTrimmed}
              </div>
              <div className="text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded">
                + {propTrimmed}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

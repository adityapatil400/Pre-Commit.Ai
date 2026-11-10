import React from 'react';
import { Finding, ApprovalStatus } from '../types/analysis';
import {
  Check,
  X,
  Edit3,
  RotateCcw,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  CheckCheck,
  Loader2,
} from 'lucide-react';

interface FixActionBarProps {
  finding: Finding | null;
  onApprove: (findingId: string) => void;
  onReject: (findingId: string) => void;
  onEdit: (findingId: string) => void;
  onUndo: (findingId: string) => void;
  onFixAll?: () => void;
  isFixingAll?: boolean;
  totalFindingsCount?: number;
}

export const FixActionBar: React.FC<FixActionBarProps> = ({
  finding,
  onApprove,
  onReject,
  onEdit,
  onUndo,
  onFixAll,
  isFixingAll = false,
  totalFindingsCount = 0,
}) => {
  if (!finding) return null;

  const status = finding.approvalStatus || 'pending';
  const isFixable = finding.fixable !== false;

  return (
    <div className="rounded-[14px] border border-neutral-200/90 bg-white p-3.5 sm:p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
      {/* Left: Status & Safety Notice */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-neutral-600">
            Fix Decision:
          </span>
          <span
            className={`text-[12px] font-semibold px-2.5 py-0.5 rounded-full border inline-flex items-center gap-1.5 ${
              status === 'accepted'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : status === 'rejected'
                ? 'bg-neutral-100 text-neutral-700 border-neutral-300'
                : status === 'edited'
                ? 'bg-blue-50 text-blue-700 border-blue-300'
                : 'bg-amber-50 text-amber-800 border-amber-300'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                status === 'accepted'
                  ? 'bg-emerald-500'
                  : status === 'rejected'
                  ? 'bg-neutral-500'
                  : status === 'edited'
                  ? 'bg-blue-500'
                  : 'bg-amber-500'
              }`}
            />
            <span className="capitalize">{status === 'pending' ? 'Pending Review' : status}</span>
          </span>
        </div>

        <div className="hidden lg:flex items-center gap-1 text-[12px] text-neutral-400">
          <ShieldCheck className="w-3.5 h-3.5 text-neutral-400" />
          <span>Files remain untouched until commit confirmation</span>
        </div>
      </div>

      {/* Right: Actions (Fix Selected & Fix All) */}
      <div className="flex items-center gap-2 flex-wrap">
        {status !== 'pending' && (
          <button
            type="button"
            onClick={() => onUndo(finding.id)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-[12.5px] font-medium transition-colors shadow-2xs"
            title="Undo approval decision"
          >
            <RotateCcw className="w-3.5 h-3.5 text-neutral-500" />
            <span>Undo</span>
          </button>
        )}

        {isFixable && (
          <>
            {/* Edit Fix */}
            <button
              type="button"
              onClick={() => onEdit(finding.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-[12.5px] font-medium transition-colors shadow-2xs"
            >
              <Edit3 className="w-3.5 h-3.5 text-neutral-500" />
              <span>Edit Fix</span>
            </button>

            {/* Reject Fix */}
            <button
              type="button"
              onClick={() => onReject(finding.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] text-[12.5px] font-medium transition-all ${
                status === 'rejected'
                  ? 'bg-neutral-800 text-white font-semibold'
                  : 'border border-neutral-300 bg-white hover:bg-neutral-100 text-neutral-700'
              }`}
            >
              <X className="w-3.5 h-3.5" />
              <span>Reject Fix</span>
            </button>

            {/* Fix Selected (Accept Selected Finding) */}
            <button
              type="button"
              onClick={() => onApprove(finding.id)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-[9px] text-[12.5px] font-semibold transition-all shadow-xs ${
                status === 'accepted'
                  ? 'bg-emerald-700 text-white ring-2 ring-emerald-400/50'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white hover:shadow'
              }`}
            >
              <Check className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>{status === 'accepted' ? 'Selected Fixed' : 'Fix Selected'}</span>
            </button>
          </>
        )}

        {/* Fix All Button (Step 7 Specification) */}
        {onFixAll && (
          <button
            type="button"
            onClick={onFixAll}
            disabled={isFixingAll}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-[9px] bg-[#050505] hover:bg-neutral-800 text-white text-[12.5px] font-semibold transition-all shadow-xs disabled:opacity-50 ring-1 ring-neutral-700"
            title="Generate corrected code addressing ALL supported detected issues"
          >
            {isFixingAll ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Fixing All Issues...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span>Fix All ({totalFindingsCount})</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

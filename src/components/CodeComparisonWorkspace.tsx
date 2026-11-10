import React, { useState, useMemo } from 'react';
import { Finding } from '../types/analysis';
import {
  FileCode,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  Sparkles,
  Columns,
  AlignLeft,
  AlertCircle,
  Loader2,
} from 'lucide-react';

interface CodeComparisonWorkspaceProps {
  finding: Finding | null;
  isLoadingFix?: boolean;
  onRegenerateFix?: () => void;
  aiModel?: string;
}

interface SplitDiffRow {
  leftLineNumber: number | null;
  leftText: string | null;
  leftType: 'normal' | 'removed' | 'problem' | 'empty';
  rightLineNumber: number | null;
  rightText: string | null;
  rightType: 'normal' | 'added' | 'empty';
}

interface UnifiedDiffRow {
  oldLineNumber: number | null;
  newLineNumber: number | null;
  text: string;
  type: 'normal' | 'removed' | 'added' | 'header';
}

/**
 * Compute Longest Common Subsequence matrix for line diffing
 */
function computeLCS(a: string[], b: string[]): number[][] {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < n; j++) {
      if (a[i] === b[j]) {
        dp[i + 1][j + 1] = dp[i][j] + 1;
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }
  return dp;
}

/**
 * Computes aligned side-by-side split rows and unified diff rows
 */
function computeDiffRows(
  origLines: string[],
  suggLines: string[],
  problemLine?: number
): { splitRows: SplitDiffRow[]; unifiedRows: UnifiedDiffRow[] } {
  if (origLines.length === 0 && suggLines.length === 0) {
    return { splitRows: [], unifiedRows: [] };
  }

  // If one side is empty, treat as complete addition/removal
  if (origLines.length === 0) {
    const splitRows: SplitDiffRow[] = suggLines.map((line, idx) => ({
      leftLineNumber: null,
      leftText: null,
      leftType: 'empty',
      rightLineNumber: idx + 1,
      rightText: line,
      rightType: 'added',
    }));
    const unifiedRows: UnifiedDiffRow[] = suggLines.map((line, idx) => ({
      oldLineNumber: null,
      newLineNumber: idx + 1,
      text: line,
      type: 'added',
    }));
    return { splitRows, unifiedRows };
  }

  if (suggLines.length === 0) {
    const splitRows: SplitDiffRow[] = origLines.map((line, idx) => ({
      leftLineNumber: idx + 1,
      leftText: line,
      leftType: idx + 1 === problemLine ? 'problem' : 'removed',
      rightLineNumber: null,
      rightText: null,
      rightType: 'empty',
    }));
    const unifiedRows: UnifiedDiffRow[] = origLines.map((line, idx) => ({
      oldLineNumber: idx + 1,
      newLineNumber: null,
      text: line,
      type: 'removed',
    }));
    return { splitRows, unifiedRows };
  }

  const m = origLines.length;
  const n = suggLines.length;
  const dp = computeLCS(origLines, suggLines);

  let i = m;
  let j = n;
  const splitRowsRev: SplitDiffRow[] = [];
  const unifiedRowsRev: UnifiedDiffRow[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && origLines[i - 1] === suggLines[j - 1]) {
      const isProblem = i === problemLine;
      splitRowsRev.push({
        leftLineNumber: i,
        leftText: origLines[i - 1],
        leftType: isProblem ? 'problem' : 'normal',
        rightLineNumber: j,
        rightText: suggLines[j - 1],
        rightType: 'normal',
      });
      unifiedRowsRev.push({
        oldLineNumber: i,
        newLineNumber: j,
        text: origLines[i - 1],
        type: 'normal',
      });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      splitRowsRev.push({
        leftLineNumber: null,
        leftText: null,
        leftType: 'empty',
        rightLineNumber: j,
        rightText: suggLines[j - 1],
        rightType: 'added',
      });
      unifiedRowsRev.push({
        oldLineNumber: null,
        newLineNumber: j,
        text: suggLines[j - 1],
        type: 'added',
      });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      const isProblem = i === problemLine;
      splitRowsRev.push({
        leftLineNumber: i,
        leftText: origLines[i - 1],
        leftType: isProblem ? 'problem' : 'removed',
        rightLineNumber: null,
        rightText: null,
        rightType: 'empty',
      });
      unifiedRowsRev.push({
        oldLineNumber: i,
        newLineNumber: null,
        text: origLines[i - 1],
        type: 'removed',
      });
      i--;
    }
  }

  return {
    splitRows: splitRowsRev.reverse(),
    unifiedRows: unifiedRowsRev.reverse(),
  };
}

export const CodeComparisonWorkspace: React.FC<CodeComparisonWorkspaceProps> = ({
  finding,
  isLoadingFix = false,
  onRegenerateFix,
  aiModel = 'Ollama',
}) => {
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split');
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  if (!finding) {
    return (
      <div className="flex-1 rounded-[14px] border border-neutral-200/90 bg-white p-12 text-center flex flex-col items-center justify-center min-h-[480px] shadow-xs">
        <FileCode className="w-12 h-12 text-neutral-300 mb-3" />
        <h4 className="text-[16px] font-bold text-neutral-700">No Issue Selected</h4>
        <p className="text-[13px] text-neutral-500 max-w-sm mt-1">
          Select an issue from the list on the left to inspect the original code and review AI suggested corrections.
        </p>
      </div>
    );
  }

  const originalCode = (finding.originalCode || '').trim() !== ''
    ? finding.originalCode!
    : (finding.codeSnippet || '');

  const suggestedCode = (finding.proposedCode || '').trim() !== ''
    ? finding.proposedCode!
    : (finding.suggestedFix && !finding.suggestedFix.startsWith('Consider') && !finding.suggestedFix.startsWith('Correct')
        ? finding.suggestedFix
        : originalCode);

  const hasOriginalCode = originalCode.trim().length > 0;
  const origLines = useMemo(() => hasOriginalCode ? originalCode.split('\n') : [], [originalCode, hasOriginalCode]);
  const suggLines = useMemo(() => suggestedCode ? suggestedCode.split('\n') : [], [suggestedCode]);

  const { splitRows, unifiedRows } = useMemo(() => {
    return computeDiffRows(origLines, suggLines, finding.line);
  }, [origLines, suggLines, finding.line]);

  const handleCopySuggested = () => {
    navigator.clipboard.writeText(suggestedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`flex-1 flex flex-col rounded-[14px] border border-neutral-200/90 bg-white shadow-xs overflow-hidden transition-all duration-200 ${
        isExpanded ? 'min-h-[680px]' : 'min-h-[480px]'
      }`}
    >
      {/* Workspace Top Toolbar */}
      <div className="px-4 py-2.5 border-b border-neutral-200/80 bg-neutral-50/70 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="w-4 h-4 text-neutral-500 flex-shrink-0" />
          <span className="font-mono text-[13px] font-bold text-neutral-900 truncate" title={finding.filePath}>
            {finding.filePath}
          </span>
          <span className="px-2 py-0.5 rounded-md bg-neutral-200/80 text-neutral-700 font-mono text-[11.5px] font-semibold flex-shrink-0">
            Line {finding.line}
          </span>
          <span className="hidden sm:inline-flex px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200/70 font-mono text-[11px] font-bold flex-shrink-0">
            {finding.ruleId}
          </span>
        </div>

        {/* Action Toggles */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Split / Unified Toggle */}
          <div className="inline-flex rounded-lg bg-neutral-200/60 p-0.5 border border-neutral-300/60 text-[12px]">
            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-[6px] font-medium transition-colors ${
                viewMode === 'split'
                  ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Split View</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('unified')}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-[6px] font-medium transition-colors ${
                viewMode === 'unified'
                  ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              <AlignLeft className="w-3.5 h-3.5" />
              <span>Unified Diff</span>
            </button>
          </div>

          {/* Regenerate with Ollama Button */}
          {onRegenerateFix && (
            <button
              type="button"
              onClick={onRegenerateFix}
              disabled={isLoadingFix}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[8px] border border-blue-200 bg-blue-50/70 hover:bg-blue-100 text-blue-700 text-[12px] font-semibold shadow-2xs transition-colors disabled:opacity-50"
              title="Generate complete corrected Python code using Ollama"
            >
              {isLoadingFix ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Generating Fix...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  <span>Regenerate Fix</span>
                </>
              )}
            </button>
          )}

          {/* Copy Suggested Code */}
          <button
            type="button"
            onClick={handleCopySuggested}
            disabled={!suggestedCode}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[8px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-[12px] font-medium shadow-2xs transition-colors disabled:opacity-50"
            title="Copy AI suggested complete code"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700 font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-neutral-500" />
                <span>Copy Code</span>
              </>
            )}
          </button>

          {/* Expand / Minimize Height */}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded-[8px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-500 hover:text-neutral-800 shadow-2xs transition-colors"
            title={isExpanded ? 'Minimize editor' : 'Expand editor'}
            aria-label="Toggle editor size"
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Loading Overlay */}
      {isLoadingFix && (
        <div className="bg-blue-50/90 border-b border-blue-200 px-4 py-2 text-[12.5px] text-blue-900 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600 flex-shrink-0" />
            <span>Analyzing AST context &amp; generating complete corrected Python code with Ollama...</span>
          </div>
          <span className="font-mono text-[11px] text-blue-600 font-semibold">llama3.2</span>
        </div>
      )}

      {/* Missing Original Code Error Notice */}
      {!hasOriginalCode && (
        <div className="p-4 bg-amber-50 border-b border-amber-200 text-amber-900 text-[13px] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>
            <strong>Source Code Unavailable:</strong> The complete original source code for <code>{finding.filePath}</code> could not be located in the current workspace.
          </span>
        </div>
      )}

      {/* Code Editor Body */}
      {viewMode === 'split' ? (
        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-neutral-800 bg-[#0d1117] font-mono text-[13px] leading-relaxed overflow-hidden">
          {/* Panel 1: Current Code (Original) */}
          <div className="flex flex-col overflow-hidden">
            <div className="px-4 py-2 bg-[#161b22] border-b border-neutral-800 flex items-center justify-between text-[11.5px] font-sans">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                <span className="font-semibold text-neutral-300">Current Code (Original)</span>
                <span className="text-[11px] text-neutral-500 font-mono">({origLines.length} lines)</span>
              </div>
              <span className="text-neutral-400 font-mono text-[11px]">Unmodified Source</span>
            </div>

            <div
              className={`p-3 overflow-auto scrollbar-thin text-neutral-200 select-text ${
                isExpanded ? 'max-h-[580px]' : 'max-h-[380px]'
              }`}
            >
              {hasOriginalCode ? (
                <table className="w-full border-collapse">
                  <tbody>
                    {splitRows.map((row, idx) => {
                      const isProblem = row.leftType === 'problem';
                      const isRemoved = row.leftType === 'removed';
                      const isEmpty = row.leftType === 'empty';

                      return (
                        <tr
                          key={`left-${idx}`}
                          className={`${
                            isProblem
                              ? 'bg-red-950/60 border-l-2 border-red-500 text-red-200 font-medium'
                              : isRemoved
                              ? 'bg-red-950/35 border-l-2 border-red-500/70 text-red-200'
                              : isEmpty
                              ? 'bg-neutral-900/30 text-transparent select-none'
                              : 'hover:bg-neutral-800/40 text-neutral-300'
                          }`}
                        >
                          {/* Line Number */}
                          <td className="w-10 pr-3 text-right text-neutral-600 select-none text-[12px] font-mono align-top">
                            {row.leftLineNumber ?? ''}
                          </td>
                          {/* Diff Marker */}
                          <td className="w-4 text-center select-none text-[12px] font-mono text-red-400 align-top">
                            {isProblem || isRemoved ? '-' : ''}
                          </td>
                          {/* Code Content */}
                          <td className="whitespace-pre pl-2 font-mono text-[12.5px] leading-relaxed">
                            {isEmpty ? '\u00A0' : row.leftText || '\u00A0'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="p-8 text-center text-neutral-500 text-[13px] font-sans">
                  Original source code is unavailable for preview.
                </div>
              )}
            </div>
          </div>

          {/* Panel 2: AI Suggested Fix (Ollama) */}
          <div className="flex flex-col overflow-hidden">
            <div className="px-4 py-2 bg-[#161b22] border-b border-neutral-800 flex items-center justify-between text-[11.5px] font-sans">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="font-semibold text-neutral-200">AI Suggested Fix</span>
                <span className="inline-flex items-center gap-1 text-[10.5px] bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 px-1.5 py-0.2 rounded">
                  <Sparkles className="w-2.5 h-2.5" /> {aiModel}
                </span>
                <span className="text-[11px] text-neutral-500 font-mono">({suggLines.length} lines)</span>
              </div>
              <span className="text-emerald-400 font-mono text-[11px]">Corrected Python</span>
            </div>

            <div
              className={`p-3 overflow-auto scrollbar-thin text-neutral-200 select-text ${
                isExpanded ? 'max-h-[580px]' : 'max-h-[380px]'
              }`}
            >
              <table className="w-full border-collapse">
                <tbody>
                  {splitRows.map((row, idx) => {
                    const isAdded = row.rightType === 'added';
                    const isEmpty = row.rightType === 'empty';

                    return (
                      <tr
                        key={`right-${idx}`}
                        className={`${
                          isAdded
                            ? 'bg-emerald-950/45 border-l-2 border-emerald-500 text-emerald-200 font-medium'
                            : isEmpty
                            ? 'bg-neutral-900/30 text-transparent select-none'
                            : 'hover:bg-neutral-800/40 text-neutral-300'
                        }`}
                      >
                        {/* Line Number */}
                        <td className="w-10 pr-3 text-right text-neutral-600 select-none text-[12px] font-mono align-top">
                          {row.rightLineNumber ?? ''}
                        </td>
                        {/* Diff Marker */}
                        <td className="w-4 text-center select-none text-[12px] font-mono text-emerald-400 align-top">
                          {isAdded ? '+' : ''}
                        </td>
                        {/* Code Content */}
                        <td className="whitespace-pre pl-2 font-mono text-[12.5px] leading-relaxed">
                          {isEmpty ? '\u00A0' : row.rightText || '\u00A0'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Unified Diff View */
        <div className="flex-1 bg-[#0d1117] font-mono text-[13px] leading-relaxed p-4 overflow-auto scrollbar-thin">
          <div className="text-neutral-400 text-[12px] mb-2 font-sans flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-neutral-300">Unified Diff</span>
              <span>({finding.filePath})</span>
            </div>
            <span className="text-[11px] text-neutral-500 font-mono">{aiModel}</span>
          </div>

          <div className="bg-[#161b22] rounded-[8px] p-3 border border-neutral-800 text-[12.5px] overflow-x-auto">
            <table className="w-full border-collapse">
              <tbody>
                {unifiedRows.map((row, idx) => {
                  const isAdded = row.type === 'added';
                  const isRemoved = row.type === 'removed';

                  return (
                    <tr
                      key={`uni-${idx}`}
                      className={`${
                        isAdded
                          ? 'bg-emerald-950/45 text-emerald-200'
                          : isRemoved
                          ? 'bg-red-950/45 text-red-200'
                          : 'text-neutral-300 hover:bg-neutral-800/30'
                      }`}
                    >
                      <td className="w-8 pr-2 text-right text-neutral-600 select-none text-[11px] font-mono align-top">
                        {row.oldLineNumber ?? ''}
                      </td>
                      <td className="w-8 pr-3 text-right text-neutral-600 select-none text-[11px] font-mono align-top">
                        {row.newLineNumber ?? ''}
                      </td>
                      <td className="w-4 text-center select-none text-[12px] font-mono align-top">
                        {isAdded ? '+' : isRemoved ? '-' : ' '}
                      </td>
                      <td className="whitespace-pre pl-2 font-mono text-[12.5px]">
                        {row.text || ' '}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

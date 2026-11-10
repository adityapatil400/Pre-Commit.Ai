import React, { useState, useMemo, useEffect } from 'react';
import {
  AnalysisResult,
  ApprovalStatus,
  ValidationResult,
  CommitResult,
  Finding,
} from '../types/analysis';
import { DashboardHeader } from '../components/DashboardHeader';
import { AnalysisSummaryCards } from '../components/AnalysisSummaryCards';
import { DetectedIssuesSidebar } from '../components/DetectedIssuesSidebar';
import { CodeComparisonWorkspace } from '../components/CodeComparisonWorkspace';
import { FixActionBar } from '../components/FixActionBar';
import { IssueExplanationSection } from '../components/IssueExplanationSection';
import { GitHubCommitWorkflowBar } from '../components/GitHubCommitWorkflowBar';
import { CommitModal } from '../components/CommitModal';
import { EditFixModal } from '../components/EditFixModal';
import { ScanHistoryModal } from '../components/ScanHistoryModal';
import { NewScanModal } from '../components/NewScanModal';
import { validateFixes, downloadPatchedZipUrl, generateFileFix } from '../services/analysisService';
import { Sparkles, Check, AlertCircle } from 'lucide-react';

interface AnalysisPageProps {
  result: AnalysisResult;
  onReset: () => void;
  onNavigatePlayground?: () => void;
}

const STORAGE_KEY_HISTORY = 'precommit_ai_scan_history_v1';

export const AnalysisPage: React.FC<AnalysisPageProps> = ({ result, onReset, onNavigatePlayground }) => {
  const [currentResult, setCurrentResult] = useState<AnalysisResult>(result);
  const [findings, setFindings] = useState<Finding[]>(result.findings);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(
    result.findings[0]?.id || null
  );

  // Validation State (Step 3/7)
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Commit Pipeline State
  const [commitMessage, setCommitMessage] = useState(
    'fix: resolve syntax and resource management issues'
  );
  const [isCommitModalOpen, setIsCommitModalOpen] = useState<boolean>(false);
  const [commitResult, setCommitResult] = useState<CommitResult | null>(null);

  // Additional Modals & AI State
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState<boolean>(false);
  const [isNewScanModalOpen, setIsNewScanModalOpen] = useState<boolean>(false);
  const [isFixGenerating, setIsFixGenerating] = useState<boolean>(false);
  const [isFixingAll, setIsFixingAll] = useState<boolean>(false);
  const [fixAllResult, setFixAllResult] = useState<{
    fixesApplied: string[];
    unresolvedIssues: any[];
  } | null>(null);
  const [aiModelUsed, setAiModelUsed] = useState<string>('Ollama');

  // Scan History
  const [scanHistory, setScanHistory] = useState<AnalysisResult[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_HISTORY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Could not read scan history from localStorage:', e);
    }
    return [result];
  });

  // Save current scan to history on mount or scan change
  useEffect(() => {
    setScanHistory((prev) => {
      const exists = prev.some(
        (s) => s.sessionId === currentResult.sessionId || s.projectName === currentResult.projectName
      );
      const updated = exists ? prev : [currentResult, ...prev].slice(0, 20);
      try {
        localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(updated));
      } catch (e) {
        console.warn('Could not write scan history to localStorage:', e);
      }
      return updated;
    });
  }, [currentResult]);

  // Synchronize when active finding changes or is deleted
  const selectedFinding = useMemo(() => {
    return findings.find((f) => f.id === selectedFindingId) || findings[0] || null;
  }, [findings, selectedFindingId]);

  // Approved finding IDs
  const approvedFindingIds = useMemo(() => {
    return findings
      .filter((f) => f.approvalStatus === 'accepted' || f.approvalStatus === 'edited')
      .map((f) => f.id);
  }, [findings]);

  // Fix Action Handlers
  const handleApprove = (id: string) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === id ? { ...f, approvalStatus: 'accepted' } : f))
    );
    setValidationResult(null);
  };

  const handleReject = (id: string) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === id ? { ...f, approvalStatus: 'rejected' } : f))
    );
    setValidationResult(null);
  };

  const handleUndo = (id: string) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === id ? { ...f, approvalStatus: 'pending' } : f))
    );
    setValidationResult(null);
  };

  const handleSaveEdit = (id: string, newCode: string) => {
    setFindings((prev) =>
      prev.map((f) =>
        f.id === id
          ? {
              ...f,
              proposedCode: newCode,
              suggestedFix: newCode,
              approvalStatus: 'edited',
            }
          : f
      )
    );
    setValidationResult(null);
  };

  // Generate complete corrected code with Ollama (Step 3 & 5)
  const handleRegenerateFix = async () => {
    if (!selectedFinding) return;
    setIsFixGenerating(true);
    try {
      const res = await generateFileFix({
        sessionId: currentResult.sessionId,
        filePath: selectedFinding.filePath,
        findingId: selectedFinding.id,
        originalCode: selectedFinding.originalCode,
      });

      setFindings((prev) =>
        prev.map((f) =>
          f.filePath === selectedFinding.filePath
            ? {
                ...f,
                originalCode: res.originalCode,
                proposedCode: res.suggestedCode,
                unifiedDiff: res.diff,
                explanation: res.explanation.howItIsFixed || f.explanation,
              }
            : f
        )
      );
      setAiModelUsed(res.aiModel);
    } catch (err: any) {
      console.warn('Ollama fix generation error:', err);
    } finally {
      setIsFixGenerating(false);
    }
  };

  // Fix All: Generates corrected version addressing all supported detected issues
  const handleFixAll = async () => {
    setIsFixingAll(true);
    setFixAllResult(null);
    try {
      const filesMap: Record<string, Finding[]> = {};
      findings.forEach((f) => {
        filesMap[f.filePath] = filesMap[f.filePath] || [];
        filesMap[f.filePath].push(f);
      });

      const allFixesApplied: string[] = [];
      const allUnresolved: any[] = [];

      for (const [filePath, fileFindings] of Object.entries(filesMap)) {
        const first = fileFindings[0];
        const res = await generateFileFix({
          sessionId: currentResult.sessionId,
          filePath,
          findingId: first.id,
          originalCode: first.originalCode,
        });

        // Update all findings for this file with complete corrected code & diff
        setFindings((prev) =>
          prev.map((f) => {
            if (f.filePath === filePath) {
              return {
                ...f,
                originalCode: res.originalCode,
                proposedCode: res.suggestedCode,
                unifiedDiff: res.diff,
                approvalStatus: 'accepted',
                explanation: res.explanation.howItIsFixed || f.explanation,
              };
            }
            return f;
          })
        );

        if (res.fixesApplied && res.fixesApplied.length > 0) {
          allFixesApplied.push(...res.fixesApplied);
        } else {
          fileFindings.forEach((f) => {
            allFixesApplied.push(`Resolved [${f.ruleId}] at line ${f.line}: ${f.title}`);
          });
        }

        if (res.unresolvedIssues && res.unresolvedIssues.length > 0) {
          allUnresolved.push(...res.unresolvedIssues);
        }
        if (res.remainingIssues && res.remainingIssues.length > 0) {
          allUnresolved.push(...res.remainingIssues);
        }

        setAiModelUsed(res.aiModel);
      }

      setFixAllResult({
        fixesApplied: Array.from(new Set(allFixesApplied)),
        unresolvedIssues: allUnresolved,
      });
    } catch (err: any) {
      console.warn('Fix All execution error:', err);
    } finally {
      setIsFixingAll(false);
    }
  };

  // Run Code Validation (Step 3)
  const handleValidateFixes = async () => {
    if (!currentResult.sessionId) return;
    if (approvedFindingIds.length === 0) {
      setValidationError('Please accept at least one fix to validate.');
      return;
    }

    setIsValidating(true);
    setValidationError(null);

    try {
      const val = await validateFixes(currentResult.sessionId, approvedFindingIds);
      setValidationResult(val);
    } catch (err: any) {
      setValidationError(err.message || 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  };

  // Download Patched ZIP
  const handleDownloadPatchedZip = () => {
    if (!currentResult.sessionId) return;
    const url = downloadPatchedZipUrl(currentResult.sessionId, approvedFindingIds);
    window.location.href = url;
  };

  // Switch to another scan from history or new scan modal
  const handleSelectNewScan = (newScan: AnalysisResult) => {
    setCurrentResult(newScan);
    setFindings(newScan.findings);
    setSelectedFindingId(newScan.findings[0]?.id || null);
    setValidationResult(null);
    setCommitResult(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleClearHistory = () => {
    setScanHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY_HISTORY);
    } catch (e) {
      // ignore
    }
  };

  return (
    <div className="min-h-screen bg-atmospheric text-[#050505] flex flex-col font-sans">
      {/* 1. Dashboard Header */}
      <DashboardHeader
        projectName={currentResult.projectName}
        sourceType={currentResult.sourceType}
        sourceReference={currentResult.sourceReference}
        branch="main"
        status={currentResult.status}
        onNewScan={() => setIsNewScanModalOpen(true)}
        onOpenHistory={() => setIsHistoryModalOpen(true)}
        onNavigatePlayground={onNavigatePlayground}
        onLogoClick={onReset}
      />

      {/* Main Dashboard Container */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        {/* 2. Analysis Summary Cards (4 Cards) */}
        <section aria-label="Analysis Summary">
          <AnalysisSummaryCards
            metrics={currentResult.metrics}
            findings={findings}
          />
        </section>

        {/* 3. Main Analysis Workspace: Left Sidebar + Right Workspace */}
        <section aria-label="Main Analysis Workspace" className="flex flex-col lg:flex-row gap-5 items-start">
          {/* Left Sidebar: Detected Issues List */}
          <DetectedIssuesSidebar
            findings={findings}
            selectedFindingId={selectedFinding?.id || null}
            onSelectFinding={(f) => setSelectedFindingId(f.id)}
          />

          {/* Right Workspace: Code Comparison & Actions & Explanations */}
          <div className="flex-1 flex flex-col gap-4 min-w-0 w-full">
            {/* Fix All Summary Banner if Fix All was run */}
            {fixAllResult && (
              <div className="rounded-[12px] border border-emerald-200 bg-emerald-50/90 p-4 shadow-2xs space-y-2.5 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-600" />
                    <h4 className="text-[14px] font-bold text-emerald-950">
                      Fix All Applied: {fixAllResult.fixesApplied.length} Issues Resolved
                    </h4>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFixAllResult(null)}
                    className="text-[12px] text-emerald-700 hover:text-emerald-900 font-semibold px-2 py-0.5 rounded hover:bg-emerald-100 transition-colors"
                  >
                    Dismiss
                  </button>
                </div>
                <div className="text-[12.5px] text-emerald-900 space-y-1">
                  {fixAllResult.fixesApplied.map((fixText, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 font-mono">
                      <Check className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                      <span>{fixText}</span>
                    </div>
                  ))}
                </div>
                {fixAllResult.unresolvedIssues.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-emerald-200/80 text-[12px] text-amber-800">
                    <span className="font-semibold block mb-1">
                      Unresolved Issues ({fixAllResult.unresolvedIssues.length}):
                    </span>
                    {fixAllResult.unresolvedIssues.map((unres, idx) => (
                      <div key={idx} className="font-mono text-[11.5px]">
                        Line {unres.line}: {unres.description}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Side-by-Side Code Comparison */}
            <CodeComparisonWorkspace
              finding={selectedFinding}
              isLoadingFix={isFixGenerating || isFixingAll}
              onRegenerateFix={handleRegenerateFix}
              aiModel={aiModelUsed}
            />

            {/* AI Fix Actions Bar (Accept / Reject / Edit / Undo / Fix All) */}
            <FixActionBar
              finding={selectedFinding}
              onApprove={handleApprove}
              onReject={handleReject}
              onEdit={() => setIsEditModalOpen(true)}
              onUndo={handleUndo}
              onFixAll={handleFixAll}
              isFixingAll={isFixingAll}
              totalFindingsCount={findings.length}
            />

            {/* 4. Issue Explanation Section (Directly BELOW Code Comparison & Actions) */}
            <IssueExplanationSection finding={selectedFinding} />
          </div>
        </section>

        {/* 5. GitHub Commit Workflow (At the bottom of the dashboard) */}
        <section aria-label="Commit Pipeline">
          <GitHubCommitWorkflowBar
            totalFindings={findings.length}
            approvedCount={approvedFindingIds.length}
            sourceType={currentResult.sourceType}
            branchName={currentResult.sessionId || 'fix-patch'}
            commitMessage={commitMessage}
            onCommitMessageChange={setCommitMessage}
            isValidating={isValidating}
            validationResult={validationResult}
            onValidate={handleValidateFixes}
            onOpenCommitModal={() => setIsCommitModalOpen(true)}
            onDownloadPatchedZip={handleDownloadPatchedZip}
          />
        </section>
      </main>

      {/* Modals */}
      {/* GitHub Commit Modal */}
      <CommitModal
        isOpen={isCommitModalOpen}
        onClose={() => setIsCommitModalOpen(false)}
        sessionId={currentResult.sessionId || ''}
        repoUrl={currentResult.sourceReference || currentResult.projectName}
        approvedFindingIds={approvedFindingIds}
        onCommitSuccess={(res) => setCommitResult(res)}
      />

      {/* Edit Fix Modal */}
      <EditFixModal
        isOpen={isEditModalOpen}
        finding={selectedFinding}
        onClose={() => setIsEditModalOpen(false)}
        onSave={handleSaveEdit}
      />

      {/* Scan History Modal */}
      <ScanHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        history={scanHistory}
        onSelectScan={handleSelectNewScan}
        onClearHistory={handleClearHistory}
      />

      {/* New Scan Modal */}
      <NewScanModal
        isOpen={isNewScanModalOpen}
        onClose={() => setIsNewScanModalOpen(false)}
        onScanComplete={handleSelectNewScan}
      />
    </div>
  );
};

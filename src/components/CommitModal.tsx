import React, { useState } from 'react';
import { X, GitBranch, GitCommit, ExternalLink, Loader2, CheckCircle2, AlertCircle, KeyRound } from 'lucide-react';
import { CommitResult } from '../types/analysis';
import { commitFixesToGitHub } from '../services/analysisService';

interface CommitModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  repoUrl: string;
  approvedFindingIds: string[];
  onCommitSuccess: (result: CommitResult) => void;
}

export const CommitModal: React.FC<CommitModalProps> = ({
  isOpen,
  onClose,
  sessionId,
  repoUrl,
  approvedFindingIds,
  onCommitSuccess,
}) => {
  const [githubToken, setGithubToken] = useState('');
  const [commitMessage, setCommitMessage] = useState(
    'fix: resolve syntax and resource management issues'
  );
  const [createPr, setCreatePr] = useState(true);
  const [isCommitting, setIsCommitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [commitResult, setCommitResult] = useState<CommitResult | null>(null);

  if (!isOpen) return null;

  const handleCommit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubToken.trim()) {
      setErrorMessage('Please provide a GitHub Personal Access Token with repo write permissions.');
      return;
    }

    setIsCommitting(true);
    setErrorMessage(null);

    try {
      const res = await commitFixesToGitHub(
        sessionId,
        approvedFindingIds,
        githubToken.trim(),
        commitMessage.trim() || undefined,
        createPr
      );

      if (res.success) {
        setCommitResult(res);
        onCommitSuccess(res);
      } else {
        setErrorMessage(res.message || 'GitHub commit failed');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred while communicating with GitHub API');
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="relative w-full max-w-lg bg-white rounded-[18px] border border-neutral-300 shadow-2xl p-6 sm:p-7 overflow-hidden text-left">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 p-1.5 rounded-full text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>

        {commitResult ? (
          /* Step 8/9 Success Screen */
          <div className="space-y-5 animate-fadeIn">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 stroke-[2.2]" />
            </div>

            <div>
              <h3 className="text-[20px] font-bold text-[#050505]">
                Branch Created &amp; Changes Committed!
              </h3>
              <p className="text-[14px] text-neutral-600 mt-1">
                Your approved static analysis fixes were committed to a dedicated branch.
              </p>
            </div>

            <div className="p-4 rounded-[12px] bg-neutral-50 border border-neutral-200 space-y-2.5 font-mono text-[13px]">
              <div className="flex items-center justify-between">
                <span className="text-neutral-500 font-sans">Branch:</span>
                <span className="font-semibold text-neutral-900">{commitResult.branchName}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-neutral-500 font-sans">Commit SHA:</span>
                <span className="font-semibold text-neutral-900">{commitResult.commitSha}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-neutral-500 font-sans">Files Remediated:</span>
                <span className="font-semibold text-neutral-900">{commitResult.committedFiles.length} file(s)</span>
              </div>
              {commitResult.pullRequestNumber && (
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500 font-sans">Pull Request:</span>
                  <span className="font-semibold text-neutral-900">#{commitResult.pullRequestNumber}</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 pt-2">
              {commitResult.pullRequestUrl ? (
                <a
                  href={commitResult.pullRequestUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 py-2.5 px-4 rounded-[10px] bg-[#000000] text-white font-semibold text-[14px] inline-flex items-center justify-center gap-2 hover:bg-neutral-800 transition-colors"
                >
                  <span>Open Pull Request</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              ) : (
                <a
                  href={commitResult.commitUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 py-2.5 px-4 rounded-[10px] bg-[#000000] text-white font-semibold text-[14px] inline-flex items-center justify-center gap-2 hover:bg-neutral-800 transition-colors"
                >
                  <span>View on GitHub</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
              {commitResult.pullRequestUrl && commitResult.commitUrl && (
                <a
                  href={commitResult.commitUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="py-2.5 px-3 rounded-[10px] border border-neutral-300 text-neutral-700 font-semibold text-[14px] inline-flex items-center justify-center hover:bg-neutral-100 transition-colors"
                  title="View Commit Details"
                >
                  <GitCommit className="w-4 h-4" />
                </a>
              )}
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-[10px] bg-neutral-100 text-neutral-800 font-semibold text-[14px] hover:bg-neutral-200 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          /* Input Form */
          <form onSubmit={handleCommit} className="space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-900">
                <GitBranch className="w-4 h-4 stroke-[2]" />
              </div>
              <div>
                <h3 className="text-[19px] font-bold text-[#050505]">
                  Commit Approved Fixes to GitHub
                </h3>
                <p className="text-[13px] text-neutral-500">
                  Target repo: <span className="font-mono text-neutral-800">{repoUrl}</span>
                </p>
              </div>
            </div>

            <div className="p-3 rounded-[10px] bg-blue-50/70 border border-blue-200 text-[13px] text-blue-900">
              A dedicated branch <code className="bg-blue-100 px-1 py-0.5 rounded font-mono text-[12px]">precommit-ai/fixes-*</code> will be created so your default branch remains untouched until reviewed.
            </div>

            <div>
              <label htmlFor="github-token-input" className="block text-[13px] font-semibold text-neutral-700 mb-1">
                GitHub Personal Access Token (PAT)
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  id="github-token-input"
                  type="password"
                  required
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-[14px] border border-neutral-300 rounded-[10px] focus-ring placeholder-neutral-400"
                />
              </div>
              <p className="text-[12px] text-neutral-500 mt-1">
                Requires <code className="font-mono text-neutral-700">contents:write</code> permission on the target repository.
              </p>
            </div>

            <div>
              <label htmlFor="commit-msg-input" className="block text-[13px] font-semibold text-neutral-700 mb-1">
                Commit Message
              </label>
              <input
                id="commit-msg-input"
                type="text"
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                className="w-full px-3 py-2 text-[14px] border border-neutral-300 rounded-[10px] focus-ring"
              />
            </div>

            <div className="flex items-center gap-2 pt-0.5">
              <input
                id="create-pr-checkbox"
                type="checkbox"
                checked={createPr}
                onChange={(e) => setCreatePr(e.target.checked)}
                className="w-4 h-4 rounded border-neutral-300 text-black focus:ring-black cursor-pointer"
              />
              <label htmlFor="create-pr-checkbox" className="text-[13px] text-neutral-700 font-medium cursor-pointer select-none">
                Create a Pull Request automatically
              </label>
            </div>

            <div className="text-[12.5px] text-neutral-500">
              Approved fixes to commit: <strong>{approvedFindingIds.length}</strong>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-[10px] bg-red-50 border border-red-200 text-red-700 text-[13px] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isCommitting}
                className="px-4 py-2 text-[14px] font-semibold text-neutral-700 hover:bg-neutral-100 rounded-[10px] transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCommitting || approvedFindingIds.length === 0}
                className="px-5 py-2 text-[14px] font-semibold text-white bg-[#000000] hover:bg-neutral-800 disabled:opacity-50 rounded-[10px] inline-flex items-center gap-2 transition-colors"
              >
                {isCommitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Committing...</span>
                  </>
                ) : (
                  <>
                    <GitCommit className="w-4 h-4" />
                    <span>Create Branch &amp; Commit</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};


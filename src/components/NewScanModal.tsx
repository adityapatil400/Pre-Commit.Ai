import React, { useState } from 'react';
import { X, Upload, Github, FileCode, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { ProjectUpload } from './ProjectUpload';
import { GitHubRepositoryInput } from './GitHubRepositoryInput';
import { AnalyzeButton } from './AnalyzeButton';
import { analyzeProject } from '../services/analysisService';
import { AnalysisResult } from '../types/analysis';

interface NewScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScanComplete: (result: AnalysisResult) => void;
}

export const NewScanModal: React.FC<NewScanModalProps> = ({
  isOpen,
  onClose,
  onScanComplete,
}) => {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState<'upload' | 'github'>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);

  const canAnalyze = (activeTab === 'upload' && selectedFile !== null) || (activeTab === 'github' && githubUrl.trim() !== '');

  const handleStartScan = async () => {
    if (!canAnalyze) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setProgressMessage('Connecting to AST analysis engine...');

    try {
      const result = await analyzeProject({
        file: activeTab === 'upload' ? selectedFile : null,
        githubUrl: activeTab === 'github' ? githubUrl.trim() : undefined,
        githubToken: activeTab === 'github' && githubToken.trim() ? githubToken.trim() : undefined,
        onProgress: (step) => setProgressMessage(step),
      });

      onScanComplete(result);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Analysis failed. Please check your project and try again.');
    } finally {
      setIsAnalyzing(false);
      setProgressMessage(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="relative w-full max-w-xl bg-white rounded-[18px] border border-neutral-300 shadow-2xl p-6 sm:p-7 overflow-hidden text-left space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div>
            <h3 className="text-[18px] font-bold text-neutral-900 tracking-tight">
              Start New Code Scan
            </h3>
            <p className="text-[12.5px] text-neutral-500 mt-0.5">
              Analyze a Python file, project ZIP, or GitHub repository without code execution.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-full text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selection */}
        <div className="flex items-center gap-1 p-1 bg-neutral-100 rounded-[10px] text-[13px] font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('upload')}
            className={`flex-1 py-1.5 rounded-[8px] transition-all flex items-center justify-center gap-2 ${
              activeTab === 'upload'
                ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload ZIP or File</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('github')}
            className={`flex-1 py-1.5 rounded-[8px] transition-all flex items-center justify-center gap-2 ${
              activeTab === 'github'
                ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <Github className="w-3.5 h-3.5" />
            <span>GitHub Repository</span>
          </button>
        </div>

        {/* Tab Contents */}
        {activeTab === 'upload' ? (
          <div>
            <ProjectUpload
              selectedFile={selectedFile}
              onFileSelect={(file) => {
                setSelectedFile(file);
                if (errorMessage) setErrorMessage(null);
              }}
              disabled={isAnalyzing}
            />
          </div>
        ) : (
          <div className="space-y-3">
            <GitHubRepositoryInput
              value={githubUrl}
              onChange={(val) => {
                setGithubUrl(val);
                if (errorMessage) setErrorMessage(null);
              }}
              disabled={isAnalyzing}
            />
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                GitHub Token (Optional for private repos or high rate limits)
              </label>
              <input
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                disabled={isAnalyzing}
                className="w-full px-3.5 py-2 text-[13px] bg-slate-50 border border-slate-200 rounded-[10px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono placeholder:font-sans"
              />
            </div>
          </div>
        )}

        {/* Progress feedback */}
        {isAnalyzing && progressMessage && (
          <div className="p-3 rounded-[10px] bg-blue-50/80 border border-blue-200 text-blue-900 text-[13px] flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600 flex-shrink-0" />
            <span>{progressMessage}</span>
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <div className="p-3 rounded-[10px] bg-red-50 border border-red-200 text-red-700 text-[13px] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isAnalyzing}
            className="px-4 py-2 text-[13px] font-semibold text-neutral-600 hover:bg-neutral-100 rounded-[9px] transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleStartScan}
            disabled={!canAnalyze || isAnalyzing}
            className="px-5 py-2 text-[13px] font-semibold text-white bg-[#050505] hover:bg-neutral-800 disabled:opacity-50 rounded-[9px] transition-all shadow-xs inline-flex items-center gap-2"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Scanning AST...</span>
              </>
            ) : (
              <>
                <span>Analyze Code</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

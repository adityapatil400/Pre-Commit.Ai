import React, { useState } from 'react';
import { AppNavbar } from '../components/AppNavbar';
import { HeroSection } from '../components/HeroSection';
import { ProjectUpload } from '../components/ProjectUpload';
import { OrDivider } from '../components/OrDivider';
import { GitHubRepositoryInput } from '../components/GitHubRepositoryInput';
import { AnalyzeButton } from '../components/AnalyzeButton';
import { analyzeProject } from '../services/analysisService';
import { AnalysisResult } from '../types/analysis';
import { AlertCircle, ShieldCheck, Cpu, Code2 } from 'lucide-react';

interface HomePageProps {
  onAnalysisComplete: (result: AnalysisResult) => void;
  onNavigatePlayground?: () => void;
  onOpenHistory?: () => void;
  onOpenSettings?: () => void;
}

// GitHub repo regex validation
const GITHUB_REPO_REGEX = /^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/;

export const HomePage: React.FC<HomePageProps> = ({
  onAnalysisComplete,
  onNavigatePlayground,
  onOpenHistory,
  onOpenSettings,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [loadingText, setLoadingText] = useState<string>('Analyzing Project...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [githubValidationError, setGithubValidationError] = useState<string | null>(null);

  // Clear GitHub URL when file is selected
  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
    setErrorMessage(null);
    if (file) {
      setGithubUrl('');
      setGithubValidationError(null);
    }
  };

  // Clear file when GitHub URL is entered
  const handleGithubUrlChange = (url: string) => {
    setGithubUrl(url);
    setErrorMessage(null);
    setGithubValidationError(null);
    if (url.trim() !== '') {
      setSelectedFile(null);
    }
  };

  const handleClearOtherForFile = () => {
    setGithubUrl('');
    setGithubValidationError(null);
  };

  const handleClearOtherForGithub = () => {
    setSelectedFile(null);
  };

  // Determine if Analyze button should be enabled
  const hasFile = selectedFile !== null;
  const hasGithub = githubUrl.trim() !== '';
  const isInputProvided = hasFile || hasGithub;

  const handleAnalyzeClick = async () => {
    setErrorMessage(null);
    setGithubValidationError(null);

    // Validation
    if (!hasFile && !hasGithub) {
      setErrorMessage('Please upload a project ZIP file or provide a GitHub repository URL.');
      return;
    }

    if (hasGithub && !hasFile) {
      const trimmed = githubUrl.trim();
      if (!GITHUB_REPO_REGEX.test(trimmed)) {
        setGithubValidationError('Please enter a valid GitHub repository URL (e.g. https://github.com/username/repository)');
        return;
      }
    }

    setIsAnalyzing(true);
    setLoadingText('Initializing Python AST parser...');

    try {
      const result = await analyzeProject({
        file: selectedFile,
        githubUrl: githubUrl.trim(),
        onProgress: (step) => {
          setLoadingText(step);
        },
      });

      onAnalysisComplete(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred during static analysis.';
      setErrorMessage(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-atmospheric flex flex-col justify-between selection:bg-neutral-200 overflow-x-hidden">
      {/* Main App Navigation Bar */}
      <AppNavbar
        currentNav="dashboard"
        onNavigate={(item) => {
          if (item === 'playground') {
            onNavigatePlayground?.();
          }
        }}
        onOpenHistory={onOpenHistory}
        onOpenSettings={onOpenSettings}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-3 sm:py-6 w-full">
        <div className="w-full max-w-[780px] mx-auto flex flex-col items-center">
          {/* Hero Section */}
          <HeroSection />

          {/* Core Analysis Form Container */}
          <div className="w-full mt-1 sm:mt-2">
            {/* Project Upload Section */}
            <ProjectUpload
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
              disabled={isAnalyzing}
              onClearOther={handleClearOtherForFile}
            />

            {/* OR Divider */}
            <OrDivider />

            {/* GitHub Repository Input */}
            <GitHubRepositoryInput
              value={githubUrl}
              onChange={handleGithubUrlChange}
              disabled={isAnalyzing}
              onClearOther={handleClearOtherForGithub}
              externalError={githubValidationError}
            />

            {/* General Submission Error Alert */}
            {errorMessage && (
              <div
                role="alert"
                className="mt-3.5 flex items-center gap-2.5 text-[14px] text-red-700 bg-red-50/90 border border-red-200 p-3 rounded-[12px] animate-fadeIn"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-600" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Primary Action Button */}
            <div className="mt-4 sm:mt-5">
              <AnalyzeButton
                onClick={handleAnalyzeClick}
                disabled={!isInputProvided || isAnalyzing}
                isLoading={isAnalyzing}
                loadingText={loadingText}
              />
            </div>

            {/* Subtle Security & Architecture Trust Badges */}
            <div className="mt-4 sm:mt-5 flex flex-wrap items-center justify-center gap-2.5 sm:gap-6 text-[11.5px] sm:text-[13px] text-neutral-500 font-medium text-center">
              <span className="flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-neutral-400" />
                AST Syntax &amp; Leakage Heuristics
              </span>
              <span className="hidden sm:inline text-neutral-300">•</span>
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-neutral-400" />
                Zero Source Code Execution
              </span>
              <span className="hidden sm:inline text-neutral-300">•</span>
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-neutral-400" />
                Secure Static Analysis
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="w-full py-4 px-4 sm:px-12 text-center text-[11px] sm:text-[13px] text-neutral-400 border-t border-neutral-100/60 bg-white/40">
        <p>PreCommit AI &copy; {new Date().getFullYear()} — Python AST-based static code analysis platform.</p>
      </footer>
    </div>
  );
};

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  PlaygroundExecutionResult,
  PlaygroundAnalysisResult,
  PlaygroundIssue,
  PlaygroundFixResponse,
  PlaygroundFile,
  TerminalLog,
  ChatMessage,
  PlaygroundOllamaStatusResponse,
} from '../types/playground';
import {
  runPlaygroundCode,
  analyzePlaygroundCode,
  fixPlaygroundCode,
  checkPlaygroundOllamaStatus,
  askPlaygroundAssistant,
} from '../services/playgroundService';
import { VSCodeTitleBar } from '../components/playground/vscode/VSCodeTitleBar';
import { VSCodeActivityBar, ActivityBarTab } from '../components/playground/vscode/VSCodeActivityBar';
import { VSCodeSidebar } from '../components/playground/vscode/VSCodeSidebar';
import { VSCodeTabBar } from '../components/playground/vscode/VSCodeTabBar';
import { VSCodeBottomPanel, BottomPanelTab } from '../components/playground/vscode/VSCodeBottomPanel';
import { VSCodeAIAssistant } from '../components/playground/vscode/VSCodeAIAssistant';
import { VSCodeStatusBar } from '../components/playground/vscode/VSCodeStatusBar';
import { PlaygroundEditor, WELCOME_COMMENT } from '../components/playground/PlaygroundEditor';
import { PlaygroundFixModal } from '../components/playground/PlaygroundFixModal';
import { CommitModal } from '../components/CommitModal';

const STORAGE_KEY_FILES = 'precommit_playground_files_v3';

const isSampleOrHello = (code: string): boolean => {
  const trimmed = code.trim();
  if (!trimmed || trimmed === WELCOME_COMMENT) return true;
  const lower = trimmed.toLowerCase();
  return (
    lower.includes('quicksort') ||
    lower.includes('read_config_file') ||
    lower.includes('hello') ||
    lower === 'print("hello")' ||
    lower === "print('hello')" ||
    lower === 'print("hello!")' ||
    lower === "print('hello!')"
  );
};

const createDefaultFiles = (): PlaygroundFile[] => [
  {
    id: 'file-main',
    name: 'main.py',
    language: 'python',
    content: WELCOME_COMMENT,
    initialContent: '',
    isModified: false,
  },
  {
    id: 'file-utils',
    name: 'utils.py',
    language: 'python',
    content: '',
    initialContent: '',
    isModified: false,
  },
  {
    id: 'file-reqs',
    name: 'requirements.txt',
    language: 'plaintext',
    content: '',
    initialContent: '',
    isModified: false,
  },
];

const loadInitialFiles = (): PlaygroundFile[] => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_FILES);
    if (saved) {
      const parsed: PlaygroundFile[] = JSON.parse(saved);
      const main = parsed.find((f) => f.name === 'main.py');
      const utils = parsed.find((f) => f.name === 'utils.py');
      const reqs = parsed.find((f) => f.name === 'requirements.txt');
      if (main && utils && reqs) {
        // Strip any previously auto-inserted sample programs or hello code
        const cleanUtils = utils.content.includes('quicksort') ? '' : utils.content;
        const cleanReqs = reqs.content.includes('pytest>=8.0.0') ? '' : reqs.content;
        const cleanMain = isSampleOrHello(main.content) ? WELCOME_COMMENT : main.content;

        return [
          { ...main, content: cleanMain, isModified: cleanMain !== WELCOME_COMMENT && !!main.isModified },
          { ...utils, content: cleanUtils },
          { ...reqs, content: cleanReqs },
          ...parsed.filter((f) => !['main.py', 'utils.py', 'requirements.txt'].includes(f.name)),
        ];
      }
    }
  } catch {
    // fallback
  }
  return createDefaultFiles();
};

interface PlaygroundPageProps {
  onNavigateDashboard?: () => void;
  onOpenHistory?: () => void;
  onOpenNewScan?: () => void;
  onOpenSettings?: () => void;
}

export const PlaygroundPage: React.FC<PlaygroundPageProps> = ({
  onNavigateDashboard,
  onOpenSettings,
}) => {
  // Welcome comment state (active only when main.py holds the welcome comment)
  const [isWelcomeActive, setIsWelcomeActive] = useState<boolean>(() => {
    const mainFile = loadInitialFiles().find((f) => f.name === 'main.py');
    return mainFile ? mainFile.content.trim() === WELCOME_COMMENT : true;
  });

  // Multi-File Project State: preserve existing files without sample Python code
  const [files, setFiles] = useState<PlaygroundFile[]>(loadInitialFiles);
  const [activeFileId, setActiveFileId] = useState<string>('file-main');

  // Persist files in localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_FILES, JSON.stringify(files));
    } catch {
      // ignore storage errors
    }
  }, [files]);

  // Active file reference
  const activeFile = useMemo(() => {
    return files.find((f) => f.id === activeFileId) || files[0];
  }, [files, activeFileId]);

  // UI Panels state
  const [activeActivityTab, setActiveActivityTab] = useState<ActivityBarTab | null>('explorer');
  const [isBottomPanelOpen, setIsBottomPanelOpen] = useState<boolean>(true);
  const [bottomPanelTab, setBottomPanelTab] = useState<BottomPanelTab>('problems');
  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false);

  // Cursor coordinates
  const [cursorLine, setCursorLine] = useState<number>(1);
  const [cursorColumn, setCursorColumn] = useState<number>(1);

  // Terminal Logs
  const [terminalLogs, setTerminalLogs] = useState<TerminalLog[]>([
    {
      id: 'log-1',
      timestamp: new Date().toLocaleTimeString(),
      type: 'info',
      message: 'PreCommit AI VS Code environment initialized.',
    },
    {
      id: 'log-2',
      timestamp: new Date().toLocaleTimeString(),
      type: 'info',
      message: 'Static AST Engine active. Subprocess sandbox ready.',
    },
  ]);

  // AI Assistant Chat Messages
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isAssistantGenerating, setIsAssistantGenerating] = useState<boolean>(false);

  // Ollama Connection State
  const [ollamaStatus, setOllamaStatus] = useState<PlaygroundOllamaStatusResponse>({
    connected: true,
    model: 'llama3.2:latest',
    base_url: 'http://localhost:11434',
  });

  // Execution & Analysis States
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isFixing, setIsFixing] = useState<boolean>(false);

  const [executionResult, setExecutionResult] = useState<PlaygroundExecutionResult | null>(null);
  const [analysisResult, setAnalysisResult] = useState<PlaygroundAnalysisResult | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<PlaygroundIssue | null>(null);
  const [targetLine, setTargetLine] = useState<number | null>(null);

  // AI Fix Response & Modals
  const [fixResponse, setFixResponse] = useState<PlaygroundFixResponse | null>(null);
  const [isFixModalOpen, setIsFixModalOpen] = useState<boolean>(false);
  const [isCommitModalOpen, setIsCommitModalOpen] = useState<boolean>(false);

  // Append a message to terminal logs
  const appendLog = useCallback((message: string, type: TerminalLog['type'] = 'info') => {
    setTerminalLogs((prev) => [
      ...prev,
      {
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
        timestamp: new Date().toLocaleTimeString(),
        type,
        message,
      },
    ]);
  }, []);

  // Check Ollama status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await checkPlaygroundOllamaStatus();
        setOllamaStatus(res);
        if (res.connected) {
          appendLog(`Ollama connected successfully (${res.model}).`, 'success');
        } else {
          appendLog('Ollama service offline. AI fixes will use local AST fallback.', 'warn');
        }
      } catch {
        setOllamaStatus({ connected: false, model: 'llama3.2:latest', base_url: 'http://localhost:11434' });
      }
    };
    checkStatus();
  }, [appendLog]);

  // Real-time Static AST Analysis
  const performAnalysis = useCallback(
    async (codeToAnalyze: string, filename: string) => {
      // Do not include the welcome comment in AST code analysis
      if (
        !codeToAnalyze.trim() ||
        codeToAnalyze.trim() === WELCOME_COMMENT ||
        (isWelcomeActive && filename === 'main.py')
      ) {
        setAnalysisResult({
          total_issues: 0,
          metrics: { total_issues: 0, syntax_errors: 0, potential_bugs: 0, resource_leaks: 0, risk_score: 100 },
          issues: [],
        });
        return;
      }

      setIsAnalyzing(true);
      try {
        const result = await analyzePlaygroundCode(codeToAnalyze);
        setAnalysisResult(result);

        if (result.issues.length > 0) {
          setSelectedIssue(result.issues[0]);
          appendLog(
            `[AST Engine] Found ${result.total_issues} issue(s) in ${filename} (Risk score: ${result.metrics.risk_score}/100).`,
            result.metrics.syntax_errors > 0 ? 'error' : 'warn'
          );
        } else {
          appendLog(`[AST Engine] ${filename} verified clean. Zero issues detected.`, 'success');
        }
      } catch (err: unknown) {
        console.error('Real-time analysis error:', err);
      } finally {
        setIsAnalyzing(false);
      }
    },
    [isWelcomeActive, appendLog]
  );

  // Debounced real-time analysis whenever active Python code changes (800ms)
  useEffect(() => {
    if (activeFile.language !== 'python') return;

    const timer = setTimeout(() => {
      performAnalysis(activeFile.content, activeFile.name);
    }, 800);

    return () => clearTimeout(timer);
  }, [activeFile.content, activeFile.name, activeFile.language, performAnalysis]);

  // Clear welcome comment and transition to normal editing
  const handleWelcomeClear = useCallback(() => {
    setIsWelcomeActive(false);
    setFiles((prev) =>
      prev.map((f) =>
        f.id === 'file-main' && f.content.trim() === WELCOME_COMMENT
          ? { ...f, content: '', initialContent: '', isModified: false }
          : f
      )
    );
  }, []);

  // Code change handler
  const handleCodeChange = (newCode: string) => {
    if (isWelcomeActive && newCode !== WELCOME_COMMENT) {
      setIsWelcomeActive(false);
    }

    setFiles((prev) =>
      prev.map((f) =>
        f.id === activeFileId
          ? {
              ...f,
              content: newCode,
              isModified: newCode.trim() !== WELCOME_COMMENT && newCode !== f.initialContent,
            }
          : f
      )
    );
  };

  // Run Code
  const handleRunCode = useCallback(async () => {
    if (isRunning) return;

    // Only execute Python source files
    if (activeFile.language !== 'python') {
      appendLog(`[Sandbox] ${activeFile.name} is not a Python source file. Switch to main.py or a .py file to execute.`, 'warn');
      setIsBottomPanelOpen(true);
      setBottomPanelTab('output');
      return;
    }

    // Do not run welcome comment - treat as visual placeholder, not executable source code
    if (!activeFile.content.trim() || activeFile.content.trim() === WELCOME_COMMENT || (isWelcomeActive && activeFile.id === 'file-main')) {
      appendLog(`[Sandbox] ${activeFile.name} is currently empty. Enter Python code to execute.`, 'warn');
      setExecutionResult({
        success: false,
        stdout: '',
        stderr: 'Workspace is empty.\nThe welcome comment is a visual placeholder, not executable source code.\nEnter Python code in main.py and click Run.',
        exit_code: 1,
        execution_time_ms: 0,
        status: 'error',
        error_message: 'Workspace is empty (welcome placeholder)',
      });
      setIsBottomPanelOpen(true);
      setBottomPanelTab('output');
      return;
    }

    setIsRunning(true);
    setExecutionResult(null);
    appendLog(`[Sandbox] Executing ${activeFile.name} in isolated subprocess (Python 3.13 -I)...`, 'info');

    try {
      const result = await runPlaygroundCode(activeFile.content, 5.0);
      setExecutionResult(result);
      setIsBottomPanelOpen(true);

      if (result.status === 'completed' && result.exit_code === 0) {
        appendLog(`[Sandbox] Finished in ${result.execution_time_ms.toFixed(1)}ms with exit code 0.`, 'success');
        setBottomPanelTab('output');
      } else if (result.status === 'timeout') {
        appendLog(`[Sandbox] Execution timed out after 5.0s limit.`, 'error');
        setBottomPanelTab('output');
      } else {
        appendLog(`[Sandbox] Process exited with code ${result.exit_code}. Traceback captured.`, 'error');
        setBottomPanelTab('output');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Execution failed';
      setExecutionResult({
        success: false,
        stdout: '',
        stderr: msg,
        exit_code: 1,
        execution_time_ms: 0,
        status: 'error',
        error_message: msg,
      });
      appendLog(`[Sandbox Error] ${msg}`, 'error');
      setBottomPanelTab('output');
    } finally {
      setIsRunning(false);
    }
  }, [activeFile.content, activeFile.name, activeFile.language, activeFile.id, isRunning, isWelcomeActive, appendLog]);

  // Manual Analyze Trigger
  const handleManualAnalyze = useCallback(() => {
    appendLog(`[AST Engine] Manually triggered full scan for ${activeFile.name}...`, 'info');
    performAnalysis(activeFile.content, activeFile.name);
    setIsBottomPanelOpen(true);
    setBottomPanelTab('problems');
  }, [activeFile.content, activeFile.name, performAnalysis, appendLog]);

  // Generate AI Fix with Ollama
  const handleFixWithAi = useCallback(
    async (issue?: PlaygroundIssue) => {
      setIsFixing(true);
      const targetIssue = issue || selectedIssue;
      appendLog(
        `[Ollama AI] Generating code repair suggestion for ${activeFile.name}${
          targetIssue ? ` (Issue: ${targetIssue.type})` : ''
        }...`,
        'info'
      );

      try {
        const response = await fixPlaygroundCode(activeFile.content, targetIssue?.id);
        setFixResponse(response);
        setIsBottomPanelOpen(true);
        setBottomPanelTab('explanation');
        appendLog(
          `[Ollama AI] Proposed fix ready. AST Syntax Valid: ${response.is_valid}. Reviewing explanation.`,
          'success'
        );
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Fix generation failed';
        appendLog(`[Ollama AI Error] ${errorMsg}`, 'error');
        alert(`AI Fix Error: ${errorMsg}`);
      } finally {
        setIsFixing(false);
      }
    },
    [activeFile.content, activeFile.name, selectedIssue, appendLog]
  );

  // Accept Fix (Updates editor code & immediately verifies)
  const handleAcceptFix = useCallback(
    (suggestedCode: string) => {
      handleCodeChange(suggestedCode);
      setFixResponse(null);
      appendLog(
        `[PreCommit AI] Accepted AI fix. Overwrote ${activeFile.name}. Triggering verification scan...`,
        'success'
      );

      // Instant re-analysis
      setTimeout(() => {
        performAnalysis(suggestedCode, activeFile.name);
      }, 50);
    },
    [activeFile.name, performAnalysis, appendLog]
  );

  // Reject Fix
  const handleRejectFix = useCallback(() => {
    setFixResponse(null);
    appendLog(`[PreCommit AI] Rejected proposed fix. Original code retained.`, 'info');
  }, [appendLog]);

  // Download File (.py) - Excludes welcome comment
  const handleDownload = useCallback(() => {
    const contentToDownload =
      activeFile.content.trim() === WELCOME_COMMENT ? '' : activeFile.content;
    const blob = new Blob([contentToDownload], { type: 'text/x-python;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = activeFile.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    appendLog(`[Workspace] Downloaded ${activeFile.name} locally.`, 'info');
  }, [activeFile.content, activeFile.name, appendLog]);

  // AI Assistant Question - Excludes welcome comment from context
  const handleSendMessage = useCallback(
    async (prompt: string) => {
      if (isAssistantGenerating) return;
      setIsAssistantGenerating(true);

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: prompt,
        timestamp: new Date().toLocaleTimeString(),
      };
      setChatMessages((prev) => [...prev, userMsg]);

      try {
        const historyPayload = chatMessages.slice(-4).map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const codeContext =
          activeFile.content.trim() === WELCOME_COMMENT ? '' : activeFile.content;

        const res = await askPlaygroundAssistant(prompt, codeContext, activeFile.name, historyPayload);

        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          timestamp: new Date().toLocaleTimeString(),
          model: res.model,
        };
        setChatMessages((prev) => [...prev, aiMsg]);
      } catch (err: unknown) {
        const errText = err instanceof Error ? err.message : 'Failed to reach AI assistant.';
        setChatMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `Error: ${errText}`,
            timestamp: new Date().toLocaleTimeString(),
            model: 'Error',
          },
        ]);
      } finally {
        setIsAssistantGenerating(false);
      }
    },
    [activeFile.content, activeFile.name, chatMessages, isAssistantGenerating]
  );

  // File Management
  const CORE_FILE_NAMES = ['main.py', 'utils.py', 'requirements.txt'];

  const handleCreateFile = (fileName: string) => {
    const newId = `file-${Date.now()}`;
    const newFile: PlaygroundFile = {
      id: newId,
      name: fileName,
      language: fileName.endsWith('.py') ? 'python' : 'plaintext',
      content: fileName.endsWith('.py') ? `# ${fileName}\n\n` : '',
      initialContent: fileName.endsWith('.py') ? `# ${fileName}\n\n` : '',
      isModified: false,
    };
    setFiles((prev) => [...prev, newFile]);
    setActiveFileId(newId);
    appendLog(`[Workspace] Created file ${fileName}.`, 'info');
  };

  const handleRenameFile = (fileId: string, newName: string) => {
    setFiles((prev) =>
      prev.map((f) => {
        if (f.id === fileId && !CORE_FILE_NAMES.includes(f.name)) {
          return {
            ...f,
            name: newName,
            language: newName.endsWith('.py') ? 'python' : 'plaintext',
          };
        }
        return f;
      })
    );
    appendLog(`[Workspace] Renamed file to ${newName}.`, 'info');
  };

  const handleDeleteFile = (fileId: string) => {
    const fileToDelete = files.find((f) => f.id === fileId);
    if (fileToDelete && CORE_FILE_NAMES.includes(fileToDelete.name)) {
      return; // Core files main.py, utils.py, requirements.txt cannot be deleted
    }
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
    if (activeFileId === fileId) {
      const remaining = files.filter((f) => f.id !== fileId);
      if (remaining.length > 0) {
        setActiveFileId(remaining[0].id);
      }
    }
    appendLog(`[Workspace] Deleted file.`, 'info');
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;
      if (isCmdOrCtrl && e.key === 'Enter') {
        e.preventDefault();
        if (e.shiftKey) {
          handleManualAnalyze();
        } else {
          handleRunCode();
        }
      }
      if (isCmdOrCtrl && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleDownload();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleRunCode, handleManualAnalyze, handleDownload]);

  // Modified files count for Activity Bar badge
  const modifiedCount = files.filter(
    (f) => f.content.trim() !== WELCOME_COMMENT && f.isModified
  ).length;

  const issuesList = analysisResult?.issues || [];
  const errorCount = issuesList.filter((i) => i.severity === 'Critical' || i.severity === 'High').length;
  const warningCount = issuesList.filter((i) => i.severity === 'Medium' || i.severity === 'Low').length;

  return (
    <div className="h-screen w-screen bg-[#1e1e1e] text-[#cccccc] flex flex-col font-sans overflow-hidden select-none">
      {/* 1. Top Title Bar (VS Code Header) */}
      <VSCodeTitleBar
        activeFileName={activeFile.name}
        isModified={activeFile.content.trim() !== WELCOME_COMMENT && !!activeFile.isModified}
        pythonVersion="Python 3.13"
        ollamaConnected={ollamaStatus.connected}
        ollamaModel={ollamaStatus.model}
        isRunning={isRunning}
        isAnalyzing={isAnalyzing}
        onRun={handleRunCode}
        onAnalyze={handleManualAnalyze}
        onDownload={handleDownload}
        onCommitGitHub={() => setIsCommitModalOpen(true)}
        onOpenSettings={() => onOpenSettings?.()}
        onNavigateDashboard={onNavigateDashboard}
      />

      {/* 2. Middle Main Workspace Layout */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative">
        {/* A. Left Activity Bar */}
        <VSCodeActivityBar
          activeTab={activeActivityTab}
          onSelectTab={(tab) => {
            if (activeActivityTab === tab) {
              setActiveActivityTab(null); // toggle close
            } else {
              setActiveActivityTab(tab);
            }
          }}
          modifiedFilesCount={modifiedCount}
          onOpenSettings={() => onOpenSettings?.()}
        />

        {/* B. Secondary Sidebar (Explorer, Search, Git, Extensions) */}
        {activeActivityTab && (
          <VSCodeSidebar
            activeTab={activeActivityTab}
            files={files}
            activeFileId={activeFileId}
            onSelectFile={setActiveFileId}
            onCreateFile={handleCreateFile}
            onRenameFile={handleRenameFile}
            onDeleteFile={handleDeleteFile}
            onCommitGitHub={() => setIsCommitModalOpen(true)}
            onJumpToLine={(fId, line) => {
              setActiveFileId(fId);
              setTargetLine(line);
            }}
            onCloseSidebar={() => setActiveActivityTab(null)}
          />
        )}

        {/* C. Center: Code Editor Area + Bottom Panel */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#1e1e1e] overflow-hidden">
          {/* File Tabs Bar */}
          <VSCodeTabBar
            files={files}
            activeFileId={activeFileId}
            onSelectFile={setActiveFileId}
            onCloseFile={handleDeleteFile}
            onRun={handleRunCode}
            isAssistantOpen={isAssistantOpen}
            onToggleAssistant={() => setIsAssistantOpen((prev) => !prev)}
          />

          {/* Monaco Editor Component with Welcome Comment Handler */}
          <div className="flex-1 min-h-0 overflow-hidden relative">
            <PlaygroundEditor
              code={activeFile.content}
              onChange={handleCodeChange}
              language={activeFile.language}
              path={activeFile.name}
              theme="vs-dark"
              issues={issuesList}
              targetLine={targetLine}
              onCursorChange={(line, col) => {
                setCursorLine(line);
                setCursorColumn(col);
              }}
              isWelcomeActive={
                isWelcomeActive &&
                activeFile.id === 'file-main' &&
                activeFile.content.trim() === WELCOME_COMMENT
              }
              onWelcomeClear={handleWelcomeClear}
            />
          </div>

          {/* Bottom Panel (Output, Problems, Terminal, AI Explanation) */}
          {isBottomPanelOpen && (
            <VSCodeBottomPanel
              activeTab={bottomPanelTab}
              onSelectTab={setBottomPanelTab}
              executionResult={executionResult}
              analysisResult={analysisResult}
              selectedIssue={selectedIssue}
              fixResponse={fixResponse}
              isFixing={isFixing}
              terminalLogs={terminalLogs}
              onSelectIssue={(issue) => {
                setSelectedIssue(issue);
                setTargetLine(issue.line);
              }}
              onFixIssueWithAi={handleFixWithAi}
              onAcceptFix={handleAcceptFix}
              onRejectFix={handleRejectFix}
              onRegenerateFix={() => handleFixWithAi(selectedIssue || undefined)}
              onClearOutput={() => setExecutionResult(null)}
              onClearTerminal={() => setTerminalLogs([])}
              onClosePanel={() => setIsBottomPanelOpen(false)}
              activeFileName={activeFile.name}
            />
          )}
        </div>

        {/* D. Right Collapsible AI Assistant */}
        <VSCodeAIAssistant
          isOpen={isAssistantOpen}
          onClose={() => setIsAssistantOpen(false)}
          messages={chatMessages}
          onSendMessage={handleSendMessage}
          isGenerating={isAssistantGenerating}
          activeFileName={activeFile.name}
        />
      </div>

      {/* 3. Bottom Status Bar */}
      <VSCodeStatusBar
        branch="main"
        errorCount={errorCount}
        warningCount={warningCount}
        isAnalyzing={isAnalyzing}
        ollamaConnected={ollamaStatus.connected}
        ollamaModel={ollamaStatus.model}
        cursorLine={cursorLine}
        cursorColumn={cursorColumn}
        pythonVersion="Python 3.13"
        onOpenProblems={() => {
          setIsBottomPanelOpen(true);
          setBottomPanelTab('problems');
        }}
        onToggleBottomPanel={() => setIsBottomPanelOpen((prev) => !prev)}
        onToggleAssistant={() => setIsAssistantOpen((prev) => !prev)}
        onOpenSettings={() => onOpenSettings?.()}
      />

      {/* Full Screen AI Fix Review Modal if triggered */}
      <PlaygroundFixModal
        isOpen={isFixModalOpen}
        onClose={() => setIsFixModalOpen(false)}
        fixResponse={fixResponse}
        onAcceptFix={handleAcceptFix}
        onRegenerateFix={() => handleFixWithAi(selectedIssue || undefined)}
        isRegenerating={isFixing}
      />

      {/* GitHub Commit Workflow Modal */}
      <CommitModal
        isOpen={isCommitModalOpen}
        onClose={() => setIsCommitModalOpen(false)}
        sessionId="playground-session"
        repoUrl="https://github.com/developer/python-playground"
        approvedFindingIds={issuesList.map((i) => i.id)}
        onCommitSuccess={(res) => {
          appendLog(`[GitHub] Successfully committed approved changes: ${res.commitSha}`, 'success');
          setIsCommitModalOpen(false);
        }}
      />
    </div>
  );
};

export default PlaygroundPage;

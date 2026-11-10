import React, { useState } from 'react';
import {
  FilePlus,
  RotateCcw,
  MoreHorizontal,
  ChevronDown,
  ChevronRight,
  FileCode,
  FileText,
  Trash2,
  Edit2,
  Check,
  X,
  Search,
  GitBranch,
  GitCommit,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Layers,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { PlaygroundFile } from '../../../types/playground';
import { ActivityBarTab } from './VSCodeActivityBar';

interface VSCodeSidebarProps {
  activeTab: ActivityBarTab;
  files: PlaygroundFile[];
  activeFileId: string;
  onSelectFile: (fileId: string) => void;
  onCreateFile: (fileName: string) => void;
  onRenameFile: (fileId: string, newName: string) => void;
  onDeleteFile: (fileId: string) => void;
  onCommitGitHub: () => void;
  onJumpToLine?: (fileId: string, line: number) => void;
  onCloseSidebar: () => void;
}

export const VSCodeSidebar: React.FC<VSCodeSidebarProps> = ({
  activeTab,
  files,
  activeFileId,
  onSelectFile,
  onCreateFile,
  onRenameFile,
  onDeleteFile,
  onCommitGitHub,
  onJumpToLine,
  onCloseSidebar,
}) => {
  // Explorer state
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // Git state
  const [commitMessage, setCommitMessage] = useState('fix: resolve detected AST syntax and resource issues');

  // Handle new file submit
  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = newFileName.trim();
    if (cleanName) {
      onCreateFile(cleanName.endsWith('.py') || cleanName.includes('.') ? cleanName : `${cleanName}.py`);
      setNewFileName('');
      setIsCreatingFile(false);
    }
  };

  // Handle rename submit
  const handleRenameSubmit = (fileId: string) => {
    const cleanName = renameValue.trim();
    if (cleanName) {
      onRenameFile(fileId, cleanName);
    }
    setRenamingFileId(null);
  };

  // File icon helper
  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.py')) {
      return <FileCode className="w-4 h-4 text-[#4B8BBE] shrink-0" />;
    }
    if (fileName.endsWith('.txt')) {
      return <FileText className="w-4 h-4 text-[#858585] shrink-0" />;
    }
    return <FileText className="w-4 h-4 text-[#e2c08d] shrink-0" />;
  };

  // Search matches computed across files
  const searchResults = React.useMemo(() => {
    if (!searchQuery.trim()) return [];
    const queryLower = searchQuery.toLowerCase();
    const matches: Array<{ file: PlaygroundFile; lineNum: number; lineText: string }> = [];

    files.forEach((file) => {
      const lines = file.content.split('\n');
      lines.forEach((lineText, idx) => {
        if (lineText.toLowerCase().includes(queryLower)) {
          matches.push({
            file,
            lineNum: idx + 1,
            lineText: lineText.trim(),
          });
        }
      });
    });

    return matches;
  }, [files, searchQuery]);

  // Modified files for Git
  const modifiedFiles = files.filter((f) => f.isModified);

  return (
    <div className="w-64 bg-[#252526] border-r border-[#1e1e1e] flex flex-col text-[13px] text-[#cccccc] select-none h-full z-10 shrink-0">
      {/* Sidebar Header */}
      <div className="h-9 px-3 flex items-center justify-between border-b border-[#2d2d2d] bg-[#252526] text-[11px] font-bold tracking-wider text-[#bbbbbb] uppercase">
        <span className="truncate">
          {activeTab === 'explorer' && 'Explorer: Python Playground'}
          {activeTab === 'search' && 'Search'}
          {activeTab === 'git' && 'Source Control: Git'}
          {activeTab === 'extensions' && 'Extensions: Marketplace'}
          {activeTab === 'assistant' && 'AI Assistant (PreCommit)'}
        </span>

        <button
          type="button"
          onClick={onCloseSidebar}
          className="p-1 rounded text-[#858585] hover:text-white hover:bg-[#333333] transition-colors"
          title="Hide Sidebar"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* View: Explorer */}
      {activeTab === 'explorer' && (
        <div className="flex-1 overflow-y-auto flex flex-col">
          {/* Section: Project Root */}
          <div className="px-2 py-1.5 flex items-center justify-between text-[#aaaaaa] hover:text-[#cccccc] text-[11px] font-semibold">
            <div className="flex items-center gap-1">
              <ChevronDown className="w-3.5 h-3.5" />
              <span>WORKSPACE</span>
            </div>

            <div className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => {
                  setIsCreatingFile(true);
                  setNewFileName('');
                }}
                className="p-1 rounded text-[#858585] hover:text-white hover:bg-[#333333] transition-colors"
                title="New File..."
              >
                <FilePlus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* New file input form */}
          {isCreatingFile && (
            <form onSubmit={handleCreateSubmit} className="px-3 py-1 flex items-center gap-1.5 bg-[#1e1e1e] border-y border-[#333333]">
              <FileCode className="w-3.5 h-3.5 text-[#4B8BBE] shrink-0" />
              <input
                type="text"
                autoFocus
                placeholder="filename.py"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') setIsCreatingFile(false);
                }}
                className="w-full bg-[#3c3c3c] text-white text-[12px] px-1.5 py-0.5 rounded outline-none border border-[#007acc]"
              />
              <button type="submit" className="text-[#89d185] hover:text-white">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setIsCreatingFile(false)}
                className="text-[#f48771] hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </form>
          )}

          {/* Files List */}
          <div className="flex-1 py-1 space-y-0.5">
            {files.map((file) => {
              const isActive = file.id === activeFileId;
              const isRenaming = renamingFileId === file.id;
              const isCore = ['main.py', 'utils.py', 'requirements.txt'].includes(file.name);

              return (
                <div
                  key={file.id}
                  onClick={() => onSelectFile(file.id)}
                  className={`group px-3 py-1.5 flex items-center justify-between cursor-pointer transition-colors ${
                    isActive
                      ? 'bg-[#37373d] text-white font-medium'
                      : 'hover:bg-[#2a2d2e] text-[#cccccc]'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {getFileIcon(file.name)}

                    {isRenaming ? (
                      <input
                        type="text"
                        autoFocus
                        value={renameValue}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => handleRenameSubmit(file.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRenameSubmit(file.id);
                          if (e.key === 'Escape') setRenamingFileId(null);
                        }}
                        className="w-full bg-[#3c3c3c] text-white text-[12px] px-1 py-0.5 rounded outline-none border border-[#007acc]"
                      />
                    ) : (
                      <span className="truncate text-[12.5px]">{file.name}</span>
                    )}
                  </div>

                  {/* Right: Modified dot or hover actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    {file.isModified && !isRenaming && (
                      <span
                        className="w-2 h-2 rounded-full bg-[#e2c08d] mr-1 group-hover:hidden"
                        title="Modified"
                      />
                    )}

                    {/* Hover actions: preserve core files from rename or deletion */}
                    {!isCore && (
                      <div className="hidden group-hover:flex items-center gap-1">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setRenamingFileId(file.id);
                            setRenameValue(file.name);
                          }}
                          className="p-1 rounded text-[#858585] hover:text-[#cccccc] hover:bg-[#333333]"
                          title="Rename"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`Delete ${file.name}?`)) {
                              onDeleteFile(file.id);
                            }
                          }}
                          className="p-1 rounded text-[#858585] hover:text-[#f48771] hover:bg-[#333333]"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* View: Search */}
      {activeTab === 'search' && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#858585]" />
            <input
              type="text"
              placeholder="Search across files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#3c3c3c] text-white text-[12.5px] pl-8 pr-2 py-1.5 rounded outline-none border border-transparent focus:border-[#007acc]"
            />
          </div>

          <div className="text-[11.5px] text-[#858585]">
            {searchQuery ? `${searchResults.length} results found` : 'Type a query to search workspace'}
          </div>

          <div className="space-y-1.5">
            {searchResults.map((res, i) => (
              <div
                key={i}
                onClick={() => {
                  onSelectFile(res.file.id);
                  onJumpToLine?.(res.file.id, res.lineNum);
                }}
                className="p-2 rounded bg-[#1e1e1e] hover:bg-[#2a2d2e] cursor-pointer border border-[#333333] transition-colors"
              >
                <div className="flex items-center justify-between text-[11px] text-[#4B8BBE] mb-0.5">
                  <span className="font-semibold">{res.file.name}</span>
                  <span className="font-mono text-[#858585]">Line {res.lineNum}</span>
                </div>
                <p className="text-[12px] font-mono text-[#cccccc] truncate">{res.lineText}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View: Source Control (Git) */}
      {activeTab === 'git' && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 flex flex-col">
          <div className="flex items-center justify-between text-[11.5px] text-[#858585]">
            <div className="flex items-center gap-1.5">
              <GitBranch className="w-3.5 h-3.5 text-[#58a6ff]" />
              <span className="font-medium text-white">Branch: main</span>
            </div>
            <span>{modifiedFiles.length} changes</span>
          </div>

          {/* Commit Message Box */}
          <div className="space-y-1.5">
            <textarea
              rows={3}
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder="Message (Press Ctrl+Enter to commit)"
              className="w-full bg-[#3c3c3c] text-white text-[12px] p-2 rounded outline-none border border-transparent focus:border-[#007acc] resize-none"
            />

            <button
              type="button"
              onClick={onCommitGitHub}
              className="w-full py-1.5 rounded bg-[#007acc] hover:bg-[#0062a3] text-white font-medium text-[12.5px] flex items-center justify-center gap-1.5 transition-colors shadow-xs"
            >
              <GitCommit className="w-3.5 h-3.5" />
              <span>Commit to GitHub</span>
            </button>
          </div>

          {/* Changed Files List */}
          <div className="space-y-1 pt-2">
            <div className="text-[11px] font-bold text-[#858585] uppercase tracking-wider">
              Changes ({modifiedFiles.length})
            </div>

            {modifiedFiles.length === 0 ? (
              <p className="text-[12px] text-[#777777] italic py-2">
                No modified files. Clean working tree.
              </p>
            ) : (
              modifiedFiles.map((file) => (
                <div
                  key={file.id}
                  onClick={() => onSelectFile(file.id)}
                  className="px-2 py-1.5 rounded flex items-center justify-between hover:bg-[#2a2d2e] cursor-pointer"
                >
                  <div className="flex items-center gap-2 truncate">
                    {getFileIcon(file.name)}
                    <span className="text-[12.5px] text-[#cccccc] truncate">{file.name}</span>
                  </div>
                  <span className="text-[11px] font-bold text-[#e2c08d]">M</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* View: Extensions */}
      {activeTab === 'extensions' && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          <div className="text-[11px] font-bold text-[#858585] uppercase tracking-wider">
            Installed Built-In Tools
          </div>

          <div className="space-y-2">
            <div className="p-2.5 rounded bg-[#1e1e1e] border border-[#333333] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white text-[12px]">PreCommit AST Engine</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#1b2b1d] text-[#89d185]">
                  Active
                </span>
              </div>
              <p className="text-[11px] text-[#858585]">
                Static AST visitor detecting multi-syntax errors, memory leaks, and unclosed resources without execution.
              </p>
            </div>

            <div className="p-2.5 rounded bg-[#1e1e1e] border border-[#333333] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white text-[12px]">Ollama AI Fix Engine</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#1b2b1d] text-[#89d185]">
                  Active
                </span>
              </div>
              <p className="text-[11px] text-[#858585]">
                Local LLM repair model (`llama3.2:latest`) with AST syntax validation and unified diff explanations.
              </p>
            </div>

            <div className="p-2.5 rounded bg-[#1e1e1e] border border-[#333333] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white text-[12px]">Isolated Subprocess Sandbox</span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#1b2b1d] text-[#89d185]">
                  Active
                </span>
              </div>
              <p className="text-[11px] text-[#858585]">
                Ephemeral subprocess environment running Python 3.13 in isolated mode (`-I`) with strict timeout & 200 KB cap.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


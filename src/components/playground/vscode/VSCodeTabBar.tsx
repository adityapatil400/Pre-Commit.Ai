import React from 'react';
import {
  FileCode,
  FileText,
  X,
  Play,
  Sparkles,
  Columns,
  PanelRightOpen,
  PanelRightClose,
} from 'lucide-react';
import { PlaygroundFile } from '../../../types/playground';

interface VSCodeTabBarProps {
  files: PlaygroundFile[];
  activeFileId: string;
  onSelectFile: (fileId: string) => void;
  onCloseFile?: (fileId: string) => void;
  onRun: () => void;
  onFormat?: () => void;
  isAssistantOpen: boolean;
  onToggleAssistant: () => void;
}

const CORE_FILES = ['main.py', 'utils.py', 'requirements.txt'];

export const VSCodeTabBar: React.FC<VSCodeTabBarProps> = ({
  files,
  activeFileId,
  onSelectFile,
  onCloseFile,
  onRun,
  onFormat,
  isAssistantOpen,
  onToggleAssistant,
}) => {
  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.py')) {
      return <FileCode className="w-3.5 h-3.5 text-[#4B8BBE] shrink-0" />;
    }
    return <FileText className="w-3.5 h-3.5 text-[#858585] shrink-0" />;
  };

  return (
    <div className="h-9 bg-[#252526] border-b border-[#1e1e1e] flex items-center justify-between select-none overflow-x-auto overflow-y-hidden z-10 shrink-0">
      {/* File Tabs */}
      <div className="flex items-center h-full min-w-0">
        {files.map((file) => {
          const isActive = file.id === activeFileId;
          const isCore = CORE_FILES.includes(file.name);

          return (
            <div
              key={file.id}
              onClick={() => onSelectFile(file.id)}
              className={`group h-full px-3 flex items-center gap-2 border-r border-[#1e1e1e] cursor-pointer text-[12.5px] font-mono transition-colors min-w-[120px] max-w-[200px] ${
                isActive
                  ? 'bg-[#1e1e1e] text-white border-t-2 border-t-[#007acc] font-medium'
                  : 'bg-[#2d2d2d] text-[#969696] hover:bg-[#282828] hover:text-[#cccccc]'
              }`}
            >
              {getFileIcon(file.name)}
              <span className="truncate flex-1">{file.name}</span>

              {/* Dirty Indicator or Close Button */}
              {file.isModified ? (
                <span
                  className="w-2 h-2 rounded-full bg-[#e2c08d] group-hover:hidden"
                  title="Unsaved changes"
                />
              ) : null}

              {/* Preserve existing core files: only allow closing custom non-core files */}
              {onCloseFile && !isCore && files.length > 1 && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseFile(file.id);
                  }}
                  className={`p-0.5 rounded hover:bg-[#444444] text-[#858585] hover:text-white ${
                    file.isModified ? 'hidden group-hover:block' : 'opacity-0 group-hover:opacity-100'
                  }`}
                  title="Close Tab"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Right Tab Bar Actions */}
      <div className="flex items-center gap-1 px-2 shrink-0">
        <button
          type="button"
          onClick={onRun}
          className="p-1.5 rounded hover:bg-[#333333] text-[#89d185] hover:text-white transition-colors"
          title="Run Active File (Ctrl+Enter)"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
        </button>

        {onFormat && (
          <button
            type="button"
            onClick={onFormat}
            className="p-1.5 rounded hover:bg-[#333333] text-[#858585] hover:text-white transition-colors"
            title="Format Document (Shift+Alt+F)"
          >
            <Sparkles className="w-3.5 h-3.5" />
          </button>
        )}

        <button
          type="button"
          onClick={onToggleAssistant}
          className={`p-1.5 rounded transition-colors ${
            isAssistantOpen
              ? 'bg-[#007acc] text-white'
              : 'hover:bg-[#333333] text-[#858585] hover:text-white'
          }`}
          title={isAssistantOpen ? 'Close AI Assistant' : 'Open AI Assistant'}
        >
          {isAssistantOpen ? (
            <PanelRightClose className="w-3.5 h-3.5" />
          ) : (
            <PanelRightOpen className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  );
};


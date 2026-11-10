import React from 'react';
import {
  Files,
  Search,
  GitBranch,
  LayoutGrid,
  Sparkles,
  Settings,
  HelpCircle,
} from 'lucide-react';

export type ActivityBarTab = 'explorer' | 'search' | 'git' | 'extensions' | 'assistant';

interface VSCodeActivityBarProps {
  activeTab: ActivityBarTab | null;
  onSelectTab: (tab: ActivityBarTab) => void;
  modifiedFilesCount?: number;
  onOpenSettings: () => void;
}

export const VSCodeActivityBar: React.FC<VSCodeActivityBarProps> = ({
  activeTab,
  onSelectTab,
  modifiedFilesCount = 0,
  onOpenSettings,
}) => {
  const topTabs: Array<{ id: ActivityBarTab; label: string; icon: React.FC<{ className?: string }>; badge?: number }> = [
    { id: 'explorer', label: 'Explorer (Ctrl+Shift+E)', icon: Files },
    { id: 'search', label: 'Search (Ctrl+Shift+F)', icon: Search },
    {
      id: 'git',
      label: 'Source Control (Ctrl+Shift+G)',
      icon: GitBranch,
      badge: modifiedFilesCount > 0 ? modifiedFilesCount : undefined,
    },
    { id: 'extensions', label: 'Extensions (Ctrl+Shift+X)', icon: LayoutGrid },
    { id: 'assistant', label: 'AI Assistant (Ctrl+Shift+A)', icon: Sparkles },
  ];

  return (
    <div className="w-12 bg-[#333333] border-r border-[#252526] flex flex-col justify-between items-center py-2 select-none z-20 shrink-0">
      {/* Top Activity Icons */}
      <div className="flex flex-col items-center w-full space-y-1">
        {topTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onSelectTab(tab.id)}
              className={`relative w-full h-11 flex items-center justify-center transition-colors group ${
                isActive
                  ? 'text-white border-l-2 border-[#007acc] bg-[#252526]'
                  : 'text-[#858585] hover:text-[#cccccc] hover:bg-[#2a2a2a]'
              }`}
              title={tab.label}
            >
              <Icon
                className={`w-5 h-5 transition-transform ${
                  tab.id === 'assistant' && isActive ? 'text-[#007acc]' : ''
                }`}
              />

              {/* Badge for changed files or items */}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="absolute top-2 right-2 min-w-[15px] h-[15px] px-1 bg-[#007acc] text-white text-[9.5px] font-bold rounded-full flex items-center justify-center">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom Icons (Settings) */}
      <div className="flex flex-col items-center w-full space-y-1">
        <button
          type="button"
          onClick={onOpenSettings}
          className="w-full h-10 flex items-center justify-center text-[#858585] hover:text-[#cccccc] hover:bg-[#2a2a2a] transition-colors"
          title="Manage Settings"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};


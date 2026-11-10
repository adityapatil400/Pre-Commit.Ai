import React, { useState, useEffect } from 'react';
import { X, Settings, Cpu, ShieldCheck, Check, Sparkles, Sliders } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [ollamaUrl, setOllamaUrl] = useState<string>(() => {
    return localStorage.getItem('precommit_ollama_url') || 'http://localhost:11434';
  });
  const [ollamaModel, setOllamaModel] = useState<string>(() => {
    return localStorage.getItem('precommit_ollama_model') || 'llama3.2:latest';
  });
  const [timeoutSecs, setTimeoutSecs] = useState<number>(() => {
    return Number(localStorage.getItem('precommit_timeout_secs') || 5);
  });
  const [editorTheme, setEditorTheme] = useState<string>(() => {
    return localStorage.getItem('precommit_editor_theme') || 'vs-dark';
  });
  const [savedToast, setSavedToast] = useState<boolean>(false);

  useEffect(() => {
    if (savedToast) {
      const timer = setTimeout(() => setSavedToast(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [savedToast]);

  if (!isOpen) return null;

  const handleSave = () => {
    localStorage.setItem('precommit_ollama_url', ollamaUrl);
    localStorage.setItem('precommit_ollama_model', ollamaModel);
    localStorage.setItem('precommit_timeout_secs', String(timeoutSecs));
    localStorage.setItem('precommit_editor_theme', editorTheme);
    setSavedToast(true);
    setTimeout(() => {
      onClose();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-white rounded-[16px] shadow-2xl border border-neutral-200/90 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200/80 bg-neutral-50/70 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-neutral-900 text-white flex items-center justify-center shadow-xs">
              <Settings className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-neutral-900">Application Settings</h3>
              <p className="text-[12px] text-neutral-500">Configure AI models, playground execution, and editor preferences</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-5 overflow-y-auto max-h-[75vh]">
          {/* AI Settings */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-[13px] font-bold text-neutral-900">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>Ollama AI Engine</span>
            </div>
            <div className="space-y-3 pl-6 border-l-2 border-purple-100">
              <div>
                <label className="block text-[12px] font-semibold text-neutral-700 mb-1">
                  Ollama Base URL
                </label>
                <input
                  type="text"
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                  className="w-full px-3 py-1.5 text-[13px] font-mono border border-neutral-300 rounded-[8px] bg-neutral-50/50 focus:bg-white focus:outline-none focus:border-neutral-900"
                  placeholder="http://localhost:11434"
                />
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-neutral-700 mb-1">
                  Installed Model
                </label>
                <input
                  type="text"
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  className="w-full px-3 py-1.5 text-[13px] font-mono border border-neutral-300 rounded-[8px] bg-neutral-50/50 focus:bg-white focus:outline-none focus:border-neutral-900"
                  placeholder="llama3.2:latest"
                />
              </div>
            </div>
          </div>

          {/* Sandbox Execution Settings */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-[13px] font-bold text-neutral-900">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Playground Sandbox Security</span>
            </div>
            <div className="space-y-3 pl-6 border-l-2 border-emerald-100">
              <div>
                <label className="block text-[12px] font-semibold text-neutral-700 mb-1">
                  Execution Timeout (Seconds)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="0.5"
                    value={timeoutSecs}
                    onChange={(e) => setTimeoutSecs(Number(e.target.value))}
                    className="flex-1 accent-neutral-900 cursor-pointer"
                  />
                  <span className="w-12 text-center px-2 py-0.5 rounded bg-neutral-100 border text-[12.5px] font-mono font-bold text-neutral-800">
                    {timeoutSecs}s
                  </span>
                </div>
                <p className="text-[11.5px] text-neutral-400 mt-1">
                  Subprocess is automatically killed if execution exceeds this limit.
                </p>
              </div>
            </div>
          </div>

          {/* Code Editor Theme */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-[13px] font-bold text-neutral-900">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>Editor Appearance</span>
            </div>
            <div className="pl-6 border-l-2 border-blue-100 flex items-center gap-3">
              <button
                type="button"
                onClick={() => setEditorTheme('vs-dark')}
                className={`flex-1 p-2.5 rounded-[9px] border text-left text-[12.5px] transition-all ${
                  editorTheme === 'vs-dark'
                    ? 'border-neutral-900 bg-neutral-900 text-white font-semibold shadow-xs'
                    : 'border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700'
                }`}
              >
                Dark Theme (vs-dark)
              </button>
              <button
                type="button"
                onClick={() => setEditorTheme('vs')}
                className={`flex-1 p-2.5 rounded-[9px] border text-left text-[12.5px] transition-all ${
                  editorTheme === 'vs'
                    ? 'border-neutral-900 bg-neutral-900 text-white font-semibold shadow-xs'
                    : 'border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700'
                }`}
              >
                Light Theme (vs)
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-neutral-200/80 bg-neutral-50/50 flex items-center justify-between">
          <span className="text-[11.5px] text-neutral-400">Settings saved in local workspace cache</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-[9px] border border-neutral-200 bg-white hover:bg-neutral-50 text-neutral-700 text-[13px] font-medium"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-[9px] bg-[#050505] hover:bg-neutral-800 text-white text-[13px] font-semibold shadow-xs"
            >
              {savedToast ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Saved!</span>
                </>
              ) : (
                <span>Save Changes</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};


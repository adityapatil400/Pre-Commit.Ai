import React, { useState } from 'react';
import { X, Code2, Check, AlertCircle } from 'lucide-react';
import { Finding } from '../types/analysis';

interface EditFixModalProps {
  isOpen: boolean;
  finding: Finding | null;
  onClose: () => void;
  onSave: (findingId: string, newCode: string) => void;
}

export const EditFixModal: React.FC<EditFixModalProps> = ({
  isOpen,
  finding,
  onClose,
  onSave,
}) => {
  if (!isOpen || !finding) return null;

  const [code, setCode] = useState(finding.proposedCode || finding.suggestedFix || '');
  const [error, setError] = useState<string | null>(null);

  const handleSave = () => {
    if (!code.trim()) {
      setError('Code snippet cannot be empty.');
      return;
    }
    // Basic syntax heuristic check before sending
    if (code.includes('def ') && !code.includes(':')) {
      setError('Function definition missing closing colon (:).');
      return;
    }
    setError(null);
    onSave(finding.id, code);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-white rounded-[18px] border border-neutral-300 shadow-2xl p-6 overflow-hidden text-left space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5 text-neutral-800" />
            <h3 className="text-[17px] font-bold text-neutral-900">
              Edit Suggested Fix
            </h3>
            <span className="text-[12px] font-mono text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded">
              {finding.filePath}:{finding.line}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-full text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Info */}
        <p className="text-[13px] text-neutral-600">
          Modify the AI-suggested Python code before accepting it. Your code will be validated by the AST static parser.
        </p>

        {/* Code Editor Textarea */}
        <div className="space-y-1.5">
          <label htmlFor="edit-code-textarea" className="block text-[12px] font-semibold text-neutral-500 uppercase tracking-wider">
            Replacement Python Code
          </label>
          <textarea
            id="edit-code-textarea"
            rows={8}
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              if (error) setError(null);
            }}
            className="w-full p-3 font-mono text-[13px] bg-[#0d1117] text-neutral-100 border border-neutral-700 rounded-[10px] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            placeholder="Enter replacement Python code..."
          />
        </div>

        {error && (
          <div className="p-3 rounded-[9px] bg-red-50 border border-red-200 text-red-700 text-[12.5px] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2.5 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-[13px] font-semibold text-neutral-600 hover:bg-neutral-100 rounded-[9px] transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 text-[13px] font-semibold text-white bg-[#050505] hover:bg-neutral-800 rounded-[9px] transition-colors inline-flex items-center gap-1.5 shadow-xs"
          >
            <Check className="w-4 h-4" />
            <span>Save &amp; Apply Changes</span>
          </button>
        </div>
      </div>
    </div>
  );
};


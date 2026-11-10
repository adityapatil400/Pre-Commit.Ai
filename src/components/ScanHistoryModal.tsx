import React from 'react';
import { X, Clock, FolderGit2, Trash2, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { AnalysisResult } from '../types/analysis';

interface ScanHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  history: AnalysisResult[];
  onSelectScan: (scan: AnalysisResult) => void;
  onClearHistory: () => void;
}

export const ScanHistoryModal: React.FC<ScanHistoryModalProps> = ({
  isOpen,
  onClose,
  history,
  onSelectScan,
  onClearHistory,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
      <div className="relative w-full max-w-xl bg-white rounded-[18px] border border-neutral-300 shadow-2xl p-6 overflow-hidden text-left space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-neutral-800" />
            <h3 className="text-[17px] font-bold text-neutral-900">
              Analysis Scan History
            </h3>
            <span className="text-[12px] font-mono text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded">
              {history.length} scans
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

        {/* History List */}
        <div className="max-h-[360px] overflow-y-auto divide-y divide-neutral-100 pr-1 space-y-1">
          {history.length === 0 ? (
            <div className="py-12 text-center text-neutral-500 text-[13px]">
              <Clock className="w-8 h-8 mx-auto text-neutral-300 mb-2" />
              <p className="font-semibold text-neutral-700">No scan history recorded</p>
              <p className="text-[12px] text-neutral-400 mt-1">
                Completed project scans will appear here for instant review.
              </p>
            </div>
          ) : (
            history.map((scan, idx) => (
              <div
                key={scan.sessionId || idx}
                onClick={() => {
                  onSelectScan(scan);
                  onClose();
                }}
                className="group p-3.5 rounded-[12px] hover:bg-neutral-50 transition-all cursor-pointer border border-transparent hover:border-neutral-200 flex items-center justify-between gap-3 text-left"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4 text-neutral-500 flex-shrink-0" />
                    <h4 className="text-[14px] font-bold text-neutral-900 group-hover:text-blue-600 transition-colors truncate">
                      {scan.projectName}
                    </h4>
                    <span className="text-[11px] font-mono uppercase bg-neutral-100 px-1.5 py-0.2 rounded text-neutral-600">
                      {scan.sourceType}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[12px] text-neutral-500">
                    <span>{scan.scannedAt}</span>
                    <span>•</span>
                    <span>{scan.filesScanned} file(s)</span>
                    <span>•</span>
                    <span className="font-medium text-neutral-700">
                      {scan.metrics.totalIssues} issue(s)
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 text-neutral-400 group-hover:text-neutral-900 transition-colors">
                  <span className="text-[12px] font-medium hidden sm:inline">Load</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-neutral-100 text-[13px]">
          {history.length > 0 ? (
            <button
              type="button"
              onClick={onClearHistory}
              className="inline-flex items-center gap-1.5 text-neutral-500 hover:text-red-600 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear History</span>
            </button>
          ) : (
            <div />
          )}

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 font-semibold text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-[9px] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};


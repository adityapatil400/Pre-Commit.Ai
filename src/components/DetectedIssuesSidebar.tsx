import React, { useState, useMemo } from 'react';
import { Finding, ApprovalStatus } from '../types/analysis';
import {
  Search,
  Filter,
  AlertCircle,
  AlertTriangle,
  Info,
  Check,
  X,
  Wrench,
  CheckCheck,
  FileCode,
  SlidersHorizontal,
  Layers,
  Bug,
  Flame,
  Zap,
} from 'lucide-react';

export type CategoryFilter = 'all' | 'syntax' | 'resource_leak' | 'bug';
export type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low';

interface DetectedIssuesSidebarProps {
  findings: Finding[];
  selectedFindingId: string | null;
  onSelectFinding: (finding: Finding) => void;
}

export const DetectedIssuesSidebar: React.FC<DetectedIssuesSidebarProps> = ({
  findings,
  selectedFindingId,
  onSelectFinding,
}) => {
  const [activeCategory, setActiveCategory] = useState<CategoryFilter>('all');
  const [activeSeverity, setActiveSeverity] = useState<SeverityFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Helper to normalize finding severity into Critical, High, Medium, Low
  const getMappedSeverity = (f: Finding): 'critical' | 'high' | 'medium' | 'low' => {
    if (f.category === 'syntax' || (f.severity === 'error' && (f.ruleId?.includes('RES') || f.ruleId?.includes('SYN')))) {
      return 'critical';
    }
    if (f.severity === 'error') {
      return 'high';
    }
    if (f.severity === 'warning') {
      return 'medium';
    }
    return 'low';
  };

  // Issue counts for the top Counter Box
  const summaryCounters = useMemo(() => {
    let syntaxCount = 0;
    let resourceLeakCount = 0;
    let fixedCount = 0;

    findings.forEach((f) => {
      if (f.category === 'syntax') syntaxCount += 1;
      if (f.category === 'resource_leak') resourceLeakCount += 1;
      if (f.approvalStatus === 'accepted' || f.approvalStatus === 'edited') fixedCount += 1;
    });

    return {
      total: findings.length,
      syntax: syntaxCount,
      resource: resourceLeakCount,
      fixed: fixedCount,
    };
  }, [findings]);

  // Counts by severity
  const severityCounts = useMemo(() => {
    const c = { all: findings.length, critical: 0, high: 0, medium: 0, low: 0 };
    findings.forEach((f) => {
      const mapped = getMappedSeverity(f);
      c[mapped] += 1;
    });
    return c;
  }, [findings]);

  // Filtered findings based on category, severity, and search text
  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      // Category filter
      if (activeCategory !== 'all') {
        if (activeCategory === 'syntax' && f.category !== 'syntax') return false;
        if (activeCategory === 'resource_leak' && f.category !== 'resource_leak') return false;
        if (activeCategory === 'bug' && f.category !== 'bug' && f.category !== 'memory') return false;
      }

      // Severity filter
      if (activeSeverity !== 'all') {
        const mapped = getMappedSeverity(f);
        if (mapped !== activeSeverity) return false;
      }

      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesTitle = (f.title || '').toLowerCase().includes(query);
        const matchesFile = (f.filePath || '').toLowerCase().includes(query);
        const matchesRule = (f.ruleId || '').toLowerCase().includes(query);
        const matchesDesc = (f.description || '').toLowerCase().includes(query);
        const matchesSnippet = (f.codeSnippet || f.problematic_code || '').toLowerCase().includes(query);
        return matchesTitle || matchesFile || matchesRule || matchesDesc || matchesSnippet;
      }

      return true;
    });
  }, [findings, activeCategory, activeSeverity, searchQuery]);

  const getSeverityBadge = (mapped: 'critical' | 'high' | 'medium' | 'low') => {
    switch (mapped) {
      case 'critical':
        return {
          label: 'Critical',
          badgeClass: 'bg-red-50 text-red-700 border-red-200/80',
          dotClass: 'bg-red-500',
        };
      case 'high':
        return {
          label: 'High',
          badgeClass: 'bg-orange-50 text-orange-800 border-orange-200/80',
          dotClass: 'bg-orange-500',
        };
      case 'medium':
        return {
          label: 'Medium',
          badgeClass: 'bg-amber-50 text-amber-800 border-amber-200/80',
          dotClass: 'bg-amber-500',
        };
      case 'low':
      default:
        return {
          label: 'Low',
          badgeClass: 'bg-blue-50 text-blue-700 border-blue-200/80',
          dotClass: 'bg-blue-500',
        };
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'syntax':
        return { label: 'Syntax Error', badgeClass: 'bg-purple-50 text-purple-700 border-purple-200' };
      case 'resource_leak':
        return { label: 'Resource Leak', badgeClass: 'bg-rose-50 text-rose-700 border-rose-200' };
      case 'bug':
        return { label: 'Bug', badgeClass: 'bg-amber-50 text-amber-800 border-amber-200' };
      case 'memory':
      case 'memory_leak':
        return { label: 'Memory', badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200' };
      default:
        return { label: 'Issue', badgeClass: 'bg-neutral-100 text-neutral-700 border-neutral-200' };
    }
  };

  const getStatusBadge = (status?: ApprovalStatus) => {
    switch (status) {
      case 'accepted':
        return {
          label: 'Accepted',
          className: 'bg-emerald-50 text-emerald-700 border-emerald-300',
          icon: Check,
        };
      case 'rejected':
        return {
          label: 'Rejected',
          className: 'bg-neutral-100 text-neutral-600 border-neutral-300',
          icon: X,
        };
      case 'edited':
        return {
          label: 'Edited',
          className: 'bg-blue-50 text-blue-700 border-blue-300',
          icon: CheckCheck,
        };
      case 'stale':
        return {
          label: 'Stale',
          className: 'bg-red-50 text-red-700 border-red-300',
          icon: AlertCircle,
        };
      case 'pending':
      default:
        return {
          label: 'Pending',
          className: 'bg-amber-50 text-amber-700 border-amber-300',
          icon: Wrench,
        };
    }
  };

  return (
    <aside className="w-full lg:w-[400px] xl:w-[430px] flex-shrink-0 flex flex-col bg-white rounded-[14px] border border-neutral-200/90 shadow-xs overflow-hidden h-[820px]">
      {/* 1. Sidebar Header */}
      <div className="p-4 border-b border-neutral-200/80 bg-neutral-50/50 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-neutral-700" />
            <h3 className="text-[15px] font-bold text-neutral-900 tracking-tight">
              Detected Issues
            </h3>
            <span className="px-2 py-0.5 rounded-full bg-neutral-200/80 text-neutral-800 text-[11.5px] font-mono font-semibold">
              {filteredFindings.length} of {findings.length}
            </span>
          </div>
        </div>

        {/* 2. Issue Counter Box (Step 6 Specification) */}
        <div className="grid grid-cols-4 gap-2 bg-white p-2.5 rounded-[10px] border border-neutral-200/90 text-center shadow-2xs">
          <div className="p-1 rounded bg-neutral-50 border border-neutral-100">
            <span className="block text-[10px] uppercase tracking-wider text-neutral-500 font-bold">Total</span>
            <span className="text-[15px] font-bold text-neutral-900 font-mono">{summaryCounters.total}</span>
          </div>
          <div className="p-1 rounded bg-purple-50/60 border border-purple-100">
            <span className="block text-[10px] uppercase tracking-wider text-purple-700 font-bold">Syntax</span>
            <span className="text-[15px] font-bold text-purple-900 font-mono">{summaryCounters.syntax}</span>
          </div>
          <div className="p-1 rounded bg-rose-50/60 border border-rose-100">
            <span className="block text-[10px] uppercase tracking-wider text-rose-700 font-bold">Leaks</span>
            <span className="text-[15px] font-bold text-rose-900 font-mono">{summaryCounters.resource}</span>
          </div>
          <div className="p-1 rounded bg-emerald-50/60 border border-emerald-100">
            <span className="block text-[10px] uppercase tracking-wider text-emerald-700 font-bold">Fixed</span>
            <span className="text-[15px] font-bold text-emerald-900 font-mono">{summaryCounters.fixed}</span>
          </div>
        </div>

        {/* 3. Search Bar */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search errors by file, line, code, or rule..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-[12.5px] border border-neutral-300/80 rounded-[9px] bg-white placeholder-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 transition-all"
          />
        </div>

        {/* 4. Category Filter Buttons (All Issues, Syntax Errors, Resource Leaks, Bugs) */}
        <div>
          <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider mb-1 block">Category</span>
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-none text-[11.5px]">
            {[
              { id: 'all', label: 'All Issues' },
              { id: 'syntax', label: 'Syntax Errors' },
              { id: 'resource_leak', label: 'Resource Leaks' },
              { id: 'bug', label: 'Bugs' },
            ].map((cat) => {
              const isActive = activeCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setActiveCategory(cat.id as CategoryFilter)}
                  className={`px-2.5 py-1 rounded-[7px] font-medium transition-all whitespace-nowrap inline-flex items-center gap-1 ${
                    isActive
                      ? 'bg-[#050505] text-white shadow-2xs font-semibold'
                      : 'bg-white hover:bg-neutral-100 text-neutral-600 border border-neutral-200/80'
                  }`}
                >
                  {cat.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 5. Severity Filter Pills (Critical, High, Medium, Low) */}
        <div>
          <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider mb-1 block">Severity</span>
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-none text-[11.5px]">
            {(['all', 'critical', 'high', 'medium', 'low'] as SeverityFilter[]).map((filter) => {
              const count = severityCounts[filter];
              const isActive = activeSeverity === filter;
              return (
                <button
                  key={filter}
                  type="button"
                  onClick={() => setActiveSeverity(filter)}
                  className={`px-2 py-0.5 rounded-[6px] font-medium transition-all whitespace-nowrap capitalize inline-flex items-center gap-1 ${
                    isActive
                      ? 'bg-neutral-800 text-white shadow-2xs font-semibold'
                      : 'bg-white hover:bg-neutral-100 text-neutral-600 border border-neutral-200/80'
                  }`}
                >
                  <span>{filter === 'all' ? 'All' : filter}</span>
                  <span className={`text-[10px] font-mono px-1 rounded ${
                    isActive ? 'bg-neutral-700 text-neutral-200' : 'bg-neutral-100 text-neutral-500'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 6. Issues List Container */}
      <div className="flex-1 overflow-y-auto divide-y divide-neutral-100 p-2 space-y-1.5">
        {filteredFindings.length === 0 ? (
          <div className="py-16 px-4 text-center text-neutral-500 text-[13px]">
            <Check className="w-8 h-8 mx-auto text-emerald-500 mb-2 opacity-80" />
            <p className="font-semibold text-neutral-800">No issues found</p>
            <p className="text-[12px] text-neutral-400 mt-1">
              Adjust filters or search query to view issues.
            </p>
          </div>
        ) : (
          filteredFindings.map((finding) => {
            const isSelected = finding.id === selectedFindingId;
            const mappedSev = getMappedSeverity(finding);
            const sevBadge = getSeverityBadge(mappedSev);
            const catBadge = getCategoryLabel(finding.category);
            const statusBadge = getStatusBadge(finding.approvalStatus);
            const StatusIcon = statusBadge.icon;
            const snippet = finding.problematic_code || finding.codeSnippet || '';

            return (
              <div
                key={finding.id}
                onClick={() => onSelectFinding(finding)}
                className={`group p-3 rounded-[11px] cursor-pointer transition-all duration-150 border text-left space-y-2 ${
                  isSelected
                    ? 'bg-blue-50/60 border-blue-500 shadow-xs ring-1 ring-blue-500/30'
                    : 'bg-white hover:bg-neutral-50/80 border-neutral-200/60 hover:border-neutral-300'
                }`}
              >
                {/* Line 1: Issue ID + Category + Severity + Fix Status */}
                <div className="flex items-center justify-between gap-1.5 flex-wrap">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-mono text-[11px] font-bold text-neutral-800 bg-neutral-100 px-1.5 py-0.5 rounded border border-neutral-200">
                      {finding.ruleId || 'ISSUE'}
                    </span>
                    <span className={`text-[10.5px] font-semibold px-2 py-0.5 rounded-full border ${catBadge.badgeClass}`}>
                      {catBadge.label}
                    </span>
                    <span className={`text-[10.5px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${sevBadge.badgeClass}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${sevBadge.dotClass}`} />
                      {sevBadge.label}
                    </span>
                  </div>

                  {/* Fix Status Badge */}
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full border flex items-center gap-1 ${statusBadge.className}`}>
                    <StatusIcon className="w-2.5 h-2.5" />
                    <span>{statusBadge.label}</span>
                  </span>
                </div>

                {/* Line 2: Finding Title / Short Description */}
                <div>
                  <h4 className="text-[13px] font-bold text-neutral-900 group-hover:text-blue-900 transition-colors line-clamp-1">
                    {finding.title || finding.message || 'Issue detected'}
                  </h4>
                  {finding.description && finding.description !== finding.title && (
                    <p className="text-[11.5px] text-neutral-500 line-clamp-1 mt-0.5">
                      {finding.description}
                    </p>
                  )}
                </div>

                {/* Line 3: Problematic Code Preview if available */}
                {snippet && (
                  <div className="px-2 py-1 rounded bg-[#0d1117] text-neutral-300 font-mono text-[11px] truncate border border-neutral-800">
                    <span className="text-red-400 mr-1 select-none font-bold">Line {finding.line}:</span>
                    <span>{snippet}</span>
                  </div>
                )}

                {/* Line 4: File Path & Line Number */}
                <div className="flex items-center justify-between text-[11.5px] font-mono text-neutral-500 pt-0.5">
                  <div className="flex items-center gap-1 truncate" title={`${finding.filePath}:${finding.line}`}>
                    <FileCode className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0" />
                    <span className="truncate">{finding.filePath}</span>
                  </div>
                  <span className="text-neutral-600 font-semibold bg-neutral-100 px-1.5 py-0.2 rounded border border-neutral-200">
                    L{finding.line}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};

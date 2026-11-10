import React from 'react';
import { SummaryMetrics, Finding } from '../types/analysis';
import {
  AlertCircle,
  Flame,
  CheckCircle2,
  FileCode2,
  TrendingUp,
  Activity,
  Layers,
} from 'lucide-react';

interface AnalysisSummaryCardsProps {
  metrics: SummaryMetrics;
  findings: Finding[];
}

export const AnalysisSummaryCards: React.FC<AnalysisSummaryCardsProps> = ({ metrics, findings }) => {
  // Count approved / fixed issues
  const fixedCount = findings.filter(
    (f) => f.approvalStatus === 'accepted' || f.approvalStatus === 'edited'
  ).length;

  const totalIssues = metrics.totalIssues || findings.length;
  const syntaxErrors = metrics.syntaxErrors || findings.filter((f) => f.category === 'syntax').length;
  const resourceLeaks =
    (metrics.resourceLeakWarnings || 0) + (metrics.memoryWarnings || 0) ||
    findings.filter((f) => f.category === 'resource_leak' || f.category === 'memory').length;

  // Compute dynamic Risk Score (out of 10)
  // Base 10 - deductions for unresolved issues + recovery for approved fixes
  let rawScore = 10.0;
  rawScore -= syntaxErrors * 2.5;
  rawScore -= (metrics.resourceLeakWarnings || 0) * 1.5;
  rawScore -= (metrics.memoryWarnings || 0) * 1.2;
  rawScore -= (metrics.bugWarnings || 0) * 0.8;
  rawScore += fixedCount * 1.0;

  // Bound between 1.0 and 10.0
  const riskScore = Math.max(1.0, Math.min(10.0, Math.round(rawScore * 10) / 10));

  // Determine Severity Level
  let severityLevel: 'Critical' | 'High' | 'Medium' | 'Low' = 'Low';
  let severityBadgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  let ringColor = '#10b981'; // emerald-500

  if (syntaxErrors > 0 || riskScore < 4.0) {
    severityLevel = 'Critical';
    severityBadgeClass = 'bg-red-50 text-red-700 border-red-200';
    ringColor = '#ef4444'; // red-500
  } else if (riskScore < 6.5) {
    severityLevel = 'High';
    severityBadgeClass = 'bg-orange-50 text-orange-800 border-orange-200';
    ringColor = '#f97316'; // orange-500
  } else if (riskScore < 8.5) {
    severityLevel = 'Medium';
    severityBadgeClass = 'bg-amber-50 text-amber-800 border-amber-200';
    ringColor = '#f59e0b'; // amber-500
  }

  // Circular gauge calculations (radius 22 -> circumference ~138.2)
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (riskScore / 10) * circumference;

  const resolutionPercent = totalIssues > 0 ? Math.round((fixedCount / totalIssues) * 100) : 100;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
      {/* 1. Risk Score Card with Circular Indicator */}
      <div className="relative rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 overflow-hidden group">
        <div className="flex items-center justify-between gap-3 mb-2">
          <span className="text-[13px] font-semibold text-neutral-500 uppercase tracking-wider">
            Risk Score
          </span>
          <span className={`text-[11.5px] font-semibold px-2 py-0.5 rounded-full border ${severityBadgeClass}`}>
            {severityLevel} Risk
          </span>
        </div>

        <div className="flex items-center justify-between mt-1">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-[32px] sm:text-[36px] font-bold text-neutral-900 tracking-tight leading-none">
                {riskScore.toFixed(1)}
              </span>
              <span className="text-[16px] font-medium text-neutral-400">/ 10</span>
            </div>
            <p className="text-[12.5px] text-neutral-500 mt-2 font-medium">
              {riskScore >= 8.5
                ? 'Safe to commit'
                : riskScore >= 6.5
                ? 'Review recommended'
                : 'Remediation required'}
            </p>
          </div>

          {/* Clean SVG Circular Indicator */}
          <div className="relative w-16 h-16 flex items-center justify-center flex-shrink-0">
            <svg className="w-16 h-16 -rotate-90 transform" viewBox="0 0 60 60">
              {/* Background ring */}
              <circle
                cx="30"
                cy="30"
                r={radius}
                className="stroke-neutral-100"
                strokeWidth="5"
                fill="none"
              />
              {/* Foreground progress ring */}
              <circle
                cx="30"
                cy="30"
                r={radius}
                stroke={ringColor}
                strokeWidth="5.5"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="none"
                className="transition-all duration-700 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Activity className="w-4 h-4 text-neutral-500" />
            </div>
          </div>
        </div>
      </div>

      {/* 2. Syntax Errors Card */}
      <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 group">
        <div className="flex items-center justify-between gap-3 mb-2">
          <span className="text-[13px] font-semibold text-neutral-500 uppercase tracking-wider">
            Syntax Errors
          </span>
          <div className={`w-8 h-8 rounded-[10px] flex items-center justify-center ${
            syntaxErrors > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'
          }`}>
            {syntaxErrors > 0 ? (
              <AlertCircle className="w-4 h-4" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
          </div>
        </div>

        <div className="mt-1">
          <div className="text-[32px] sm:text-[36px] font-bold text-neutral-900 tracking-tight leading-none">
            {syntaxErrors}
          </div>
          <p className="text-[12.5px] text-neutral-500 mt-2 font-medium">
            {syntaxErrors > 0
              ? `${syntaxErrors} file(s) failed AST compilation`
              : '0 blocking parser syntax errors'}
          </p>
        </div>
      </div>

      {/* 3. Resource Leaks Card */}
      <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 group">
        <div className="flex items-center justify-between gap-3 mb-2">
          <span className="text-[13px] font-semibold text-neutral-500 uppercase tracking-wider">
            Resource Leaks
          </span>
          <div className={`w-8 h-8 rounded-[10px] flex items-center justify-center ${
            resourceLeaks > 0 ? 'bg-amber-50 text-amber-600' : 'bg-neutral-50 text-neutral-400'
          }`}>
            <Flame className="w-4 h-4" />
          </div>
        </div>

        <div className="mt-1">
          <div className="text-[32px] sm:text-[36px] font-bold text-neutral-900 tracking-tight leading-none">
            {resourceLeaks}
          </div>
          <p className="text-[12.5px] text-neutral-500 mt-2 font-medium">
            {resourceLeaks > 0
              ? 'Unclosed files, sockets, & connections'
              : 'Clean resource management detected'}
          </p>
        </div>
      </div>

      {/* 4. Total Issues & Fixed Progress Card */}
      <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 group">
        <div className="flex items-center justify-between gap-3 mb-2">
          <span className="text-[13px] font-semibold text-neutral-500 uppercase tracking-wider">
            Total Issues
          </span>
          <span className="text-[12px] font-medium text-neutral-600 bg-neutral-100 px-2 py-0.5 rounded-md font-mono">
            {fixedCount} / {totalIssues} Fixed
          </span>
        </div>

        <div className="mt-1">
          <div className="flex items-baseline justify-between">
            <span className="text-[32px] sm:text-[36px] font-bold text-neutral-900 tracking-tight leading-none">
              {totalIssues}
            </span>
            <span className="text-[13px] font-semibold text-emerald-600">
              {resolutionPercent}% Resolved
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-neutral-100 rounded-full h-2 mt-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${resolutionPercent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

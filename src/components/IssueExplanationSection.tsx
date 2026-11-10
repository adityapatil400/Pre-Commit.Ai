import React from 'react';
import { Finding } from '../types/analysis';
import { getIssueExplanation } from '../utils/explanationHelper';
import {
  AlertCircle,
  Wrench,
  ShieldCheck,
  AlertTriangle,
  ExternalLink,
  BookOpen,
  Code2,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

interface IssueExplanationSectionProps {
  finding: Finding | null;
}

export const IssueExplanationSection: React.FC<IssueExplanationSectionProps> = ({ finding }) => {
  if (!finding) return null;

  const explanation = getIssueExplanation(finding);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-1">
        <Sparkles className="w-4 h-4 text-blue-600" />
        <h3 className="text-[15px] font-bold text-neutral-900 tracking-tight">
          Issue Explanation &amp; Remediation Architecture
        </h3>
        <span className="text-[12px] text-neutral-500 font-mono">
          [{finding.ruleId}]
        </span>
      </div>

      {/* 4 Clean Explanation Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1 – What is the Error? */}
        <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-7 h-7 rounded-[8px] bg-red-50 text-red-600 flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-4 h-4" />
              </div>
              <h4 className="text-[14px] font-bold text-neutral-900">
                1. What is the Error?
              </h4>
            </div>

            <p className="text-[13px] text-neutral-700 leading-relaxed mb-3">
              {explanation.whatIsTheError.summary}
            </p>

            {/* Problematic code snippet quote */}
            <div className="mb-3">
              <span className="text-[11.5px] font-semibold text-neutral-500 uppercase tracking-wider block mb-1">
                Problematic Source Pattern:
              </span>
              <pre className="p-2.5 rounded-[8px] bg-red-50/60 border border-red-200/70 text-red-950 font-mono text-[12px] overflow-x-auto whitespace-pre-wrap">
                {explanation.whatIsTheError.problematicSnippet}
              </pre>
            </div>

            <div>
              <span className="text-[11.5px] font-semibold text-neutral-500 uppercase tracking-wider block mb-1">
                Why It Is a Problem:
              </span>
              <p className="text-[12.5px] text-neutral-600 leading-relaxed bg-neutral-50 p-2.5 rounded-[8px] border border-neutral-200/60">
                {explanation.whatIsTheError.whyItIsAProblem}
              </p>
            </div>
          </div>
        </div>

        {/* Card 2 – How Is It Fixed? */}
        <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-7 h-7 rounded-[8px] bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
                <Wrench className="w-4 h-4" />
              </div>
              <h4 className="text-[14px] font-bold text-neutral-900">
                2. How Is It Fixed?
              </h4>
            </div>

            <p className="text-[13px] text-neutral-700 leading-relaxed mb-3">
              {explanation.howIsItFixed.correction}
            </p>

            {/* Programming Concept */}
            <div className="mb-3">
              <span className="text-[11.5px] font-semibold text-neutral-500 uppercase tracking-wider block mb-1">
                Programming Concept Used:
              </span>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[8px] bg-emerald-50/80 border border-emerald-200 text-emerald-900 font-medium text-[12px]">
                <Code2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>{explanation.howIsItFixed.programmingConcept}</span>
              </div>
            </div>

            <div>
              <span className="text-[11.5px] font-semibold text-neutral-500 uppercase tracking-wider block mb-1">
                Changes Made:
              </span>
              <ul className="space-y-1.5 text-[12.5px] text-neutral-600">
                {explanation.howIsItFixed.changesMade.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Card 3 – Why Is the Suggested Code Correct? */}
        <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-[8px] bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <h4 className="text-[14px] font-bold text-neutral-900">
                  3. Why Is the Suggested Code Correct?
                </h4>
              </div>

              {/* Confidence Score Pill */}
              {explanation.whyItIsCorrect.confidenceScore > 0 && (
                <span className="text-[11.5px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {explanation.whyItIsCorrect.confidenceScore}% Confidence
                </span>
              )}
            </div>

            <p className="text-[13px] text-neutral-700 leading-relaxed mb-3">
              {explanation.whyItIsCorrect.reasoning}
            </p>

            <div className="p-3 rounded-[9px] bg-neutral-50 border border-neutral-200/80">
              <span className="text-[11.5px] font-semibold text-neutral-500 uppercase tracking-wider block mb-1">
                Static AST Verification:
              </span>
              <div className="flex items-center gap-2 text-[12.5px] text-neutral-700 font-mono">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{explanation.whyItIsCorrect.validationStatus}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 4 – Possible Side Effects */}
        <div className="rounded-[14px] border border-neutral-200/90 bg-white p-5 shadow-xs hover:shadow-sm transition-all duration-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-7 h-7 rounded-[8px] bg-amber-50 text-amber-700 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <h4 className="text-[14px] font-bold text-neutral-900">
                4. Possible Side Effects &amp; References
              </h4>
            </div>

            <div className="space-y-2.5 text-[12.5px] text-neutral-700 mb-3">
              <div>
                <strong className="text-neutral-900">Behavior Changes: </strong>
                <span>{explanation.sideEffects.behaviorChanges}</span>
              </div>
              <div>
                <strong className="text-neutral-900">Compatibility: </strong>
                <span>{explanation.sideEffects.compatibility}</span>
              </div>
              <div>
                <strong className="text-neutral-900">Risks &amp; Mitigations: </strong>
                <span>{explanation.sideEffects.risksAndMitigations}</span>
              </div>
            </div>

            {/* Official References & PEPs */}
            {explanation.sideEffects.references.length > 0 && (
              <div>
                <span className="text-[11.5px] font-semibold text-neutral-500 uppercase tracking-wider block mb-1.5">
                  Official Documentation &amp; Standards:
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  {explanation.sideEffects.references.map((ref, idx) => (
                    <a
                      key={idx}
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[7px] bg-neutral-100 hover:bg-neutral-200/70 text-neutral-800 text-[12px] font-medium transition-colors border border-neutral-200"
                    >
                      <BookOpen className="w-3 h-3 text-neutral-500" />
                      <span>{ref.title}</span>
                      <ExternalLink className="w-3 h-3 text-neutral-400" />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


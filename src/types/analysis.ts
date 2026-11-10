export type Severity = 'error' | 'warning' | 'information';

export type IssueCategory = 'syntax' | 'resource_leak' | 'memory' | 'bug' | 'other';

export type ApprovalStatus = 'pending' | 'accepted' | 'rejected' | 'edited' | 'stale';

export interface FixDiff {
  fixId: string;
  analysisId: string;
  findingId?: string;
  filePath: string;
  line: number;
  issue: string;
  explanation: string;
  originalCode: string;
  suggestedCode: string;
  diff: string;
  status: ApprovalStatus;
  isStale: boolean;
}

export interface FixProposal {
  fixId: string;
  analysisId: string;
  findingId?: string;
  filePath: string;
  line: number;
  issue: string;
  originalCode: string;
  suggestedCode: string;
  explanation: string;
  status: ApprovalStatus;
  diff?: string;
  modelUsed?: string;
  isStale?: boolean;
}

export interface Finding {
  id: string;
  ruleId: string;
  title: string;
  severity: Severity;
  category: IssueCategory;
  filePath: string;
  line: number;
  column?: number;
  endLine?: number;
  endColumn?: number;
  description: string;
  codeSnippet?: string;
  problematic_code?: string;
  message?: string;
  suggestion?: string;
  suggestedFix: string;
  explanation?: string;
  isPotentialWarning?: boolean;
  fixable?: boolean;
  originalCode?: string;
  proposedCode?: string;
  unifiedDiff?: string;
  approvalStatus?: ApprovalStatus;
}

export interface SummaryMetrics {
  totalIssues: number;
  syntaxErrors: number;
  resourceLeakWarnings: number;
  memoryWarnings: number;
  bugWarnings?: number;
  informationCount: number;
  fixableCount?: number;
  fixedIssues?: number;
}

export interface AnalysisResult {
  sessionId?: string;
  projectName: string;
  sourceType: 'file' | 'zip' | 'github';
  sourceReference: string;
  status: 'completed' | 'failed';
  scannedAt: string;
  durationSeconds: number;
  filesScanned: number;
  totalLinesAnalyzed: number;
  metrics: SummaryMetrics;
  findings: Finding[];
  filesManifest?: string[];
  filesSource?: Record<string, string>;
  filesSuggested?: Record<string, string>;
  isMockData?: boolean;
}

export interface IssueItem {
  type: string;
  severity: string;
  line: number;
  description: string;
  suggestion: string;
  ruleId?: string;
}

export interface FileFixExplanation {
  whatIsError: string;
  howItIsFixed: string;
  whyItIsCorrect: string;
  sideEffects: string;
}

export interface FileFixResponse {
  filename: string;
  filePath?: string;
  originalCode: string;
  suggestedCode: string;
  correctedCode?: string;
  fixesApplied?: string[];
  unresolvedIssues?: IssueItem[];
  issues: IssueItem[];
  explanation: FileFixExplanation;
  aiModel: string;
  diff: string;
  isValid: boolean;
  validationErrors?: string[];
  remainingIssues?: IssueItem[];
}

export interface ValidationResult {
  isValid: boolean;
  validatedFiles: string[];
  syntaxErrors: string[];
  fixedCount: number;
  remainingCount: number;
  remainingFindings: Finding[];
}

export interface CommitResult {
  commitId?: string;
  success: boolean;
  branchName: string;
  commitSha: string;
  commitUrl: string;
  pullRequestUrl?: string;
  pullRequestNumber?: number;
  committedFiles: string[];
  message: string;
}

export type FilterSeverity = 'all' | 'error' | 'warning' | 'information';

export interface PlaygroundExecutionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
  execution_time_ms: number;
  status: 'completed' | 'error' | 'timeout' | 'blocked';
  error_message?: string | null;
  traceback?: string | null;
}

export interface PlaygroundIssue {
  id: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  type: string;
  line: number;
  column: number;
  problematic_code: string;
  description: string;
  suggestion: string;
  rule_id?: string | null;
}

export interface PlaygroundMetrics {
  total_issues: number;
  syntax_errors: number;
  potential_bugs: number;
  resource_leaks: number;
  risk_score: number;
}

export interface PlaygroundAnalysisResult {
  total_issues: number;
  metrics: PlaygroundMetrics;
  issues: PlaygroundIssue[];
}

export interface PlaygroundFixExplanation {
  what_is_error: string;
  how_it_is_fixed: string;
  why_it_is_correct: string;
  side_effects: string;
}

export interface PlaygroundFixResponse {
  original_code: string;
  suggested_code: string;
  corrected_code: string;
  diff: string;
  ai_model: string;
  is_valid: boolean;
  validation_errors: string[];
  explanation: PlaygroundFixExplanation;
  fixes_applied: string[];
  unresolved_issues: PlaygroundIssue[];
}

export interface PlaygroundRunAndAnalyzeResponse {
  execution: PlaygroundExecutionResult;
  analysis: PlaygroundAnalysisResult;
}


export interface PlaygroundAssistantResponse {
  answer: string;
  model: string;
}

export interface PlaygroundOllamaStatusResponse {
  connected: boolean;
  model: string;
  base_url: string;
}

export interface PlaygroundFile {
  id: string;
  name: string;
  language: string;
  content: string;
  isModified?: boolean;
  initialContent?: string;
}

export interface TerminalLog {
  id: string;
  timestamp: string;
  type: 'info' | 'error' | 'success' | 'warn';
  message: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
}

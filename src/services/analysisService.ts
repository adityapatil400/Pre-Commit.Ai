import { AnalysisResult, Finding, ValidationResult, CommitResult, FileFixResponse } from '../types/analysis';

/**
 * PreCommit AI Analysis Service
 * Connects directly to the FastAPI AST static analysis backend pipeline.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export interface AnalyzeOptions {
  file?: File | null;
  githubUrl?: string;
  githubToken?: string;
  onProgress?: (step: string) => void;
}

// Map backend snake_case Finding to frontend Finding
function mapBackendFinding(f: any): Finding {
  return {
    id: f.id,
    ruleId: f.rule_id || f.ruleId,
    title: f.title,
    severity: f.severity,
    category: f.category,
    filePath: f.file_path || f.filePath,
    line: f.line,
    column: f.column,
    endLine: f.end_line || f.endLine,
    endColumn: f.end_column || f.endColumn,
    description: f.description,
    codeSnippet: f.code_snippet || f.codeSnippet,
    suggestedFix: f.suggested_fix || f.suggestedFix,
    explanation: f.explanation,
    isPotentialWarning: f.is_potential_warning ?? f.isPotentialWarning ?? true,
    fixable: f.fixable ?? false,
    originalCode: f.original_code || f.originalCode || '',
    proposedCode: f.proposed_code || f.proposedCode || '',
    unifiedDiff: f.unified_diff || f.unifiedDiff || '',
    approvalStatus: f.approval_status || 'pending',
  };
}

export async function analyzeProject(options: AnalyzeOptions): Promise<AnalysisResult> {
  const { file, githubUrl, githubToken, onProgress } = options;

  if (!file && !githubUrl) {
    throw new Error('Please provide either a Python file, a ZIP project, or a GitHub repository URL.');
  }

  onProgress?.('Connecting to PreCommit AI AST Backend Engine...');

  try {
    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    if (githubUrl) {
      formData.append('github_url', githubUrl);
    }
    if (githubToken) {
      formData.append('github_token', githubToken);
    }

    onProgress?.('Parsing Python AST tree & scanning resource descriptors...');
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Analysis failed' }));
      throw new Error(err.detail || `Server returned error status ${response.status}`);
    }

    const data = await response.json();
    onProgress?.('Processing findings & generating fix recommendations...');

    const filesSource = data.files_source || {};
    const filesSuggested = data.files_suggested || {};

    const findings = (data.findings || []).map((f: any) => {
      const mapped = mapBackendFinding(f);
      // Guarantee complete original code
      if (!mapped.originalCode && filesSource[mapped.filePath]) {
        mapped.originalCode = filesSource[mapped.filePath];
      }
      // Guarantee complete suggested code
      if (!mapped.proposedCode && filesSuggested[mapped.filePath]) {
        mapped.proposedCode = filesSuggested[mapped.filePath];
      }
      return mapped;
    });

    return {
      sessionId: data.session_id,
      projectName: data.project_name,
      sourceType: data.source_type,
      sourceReference: data.source_reference,
      status: data.status,
      scannedAt: data.scanned_at,
      durationSeconds: data.duration_seconds,
      filesScanned: data.files_scanned,
      totalLinesAnalyzed: data.total_lines_analyzed,
      metrics: {
        totalIssues: data.metrics.total_issues,
        syntaxErrors: data.metrics.syntax_errors,
        resourceLeakWarnings: data.metrics.resource_leak_warnings,
        memoryWarnings: data.metrics.memory_warnings,
        bugWarnings: data.metrics.bug_warnings || 0,
        informationCount: data.metrics.information_count,
        fixableCount: data.metrics.fixable_count || 0,
      },
      findings,
      filesManifest: data.files_manifest || [],
      filesSource,
      filesSuggested,
      isMockData: false,
    };
  } catch (err: any) {
    console.warn('Backend API connection failed or unavailable, using fallback AST simulation:', err);

    // Fallback development AST simulation if backend is not started
    onProgress?.('Executing fallback static AST scanner...');
    await new Promise((r) => setTimeout(r, 600));

    const projectName = file
      ? file.name.replace(/\.(zip|py)$/i, '')
      : githubUrl?.split('/').filter(Boolean).slice(-2).join('/') || 'python-project';

    return {
      sessionId: 'dev-session-' + Date.now(),
      projectName,
      sourceType: file ? (file.name.endsWith('.py') ? 'file' : 'zip') : 'github',
      sourceReference: file ? file.name : (githubUrl || ''),
      status: 'completed',
      scannedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' + new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      durationSeconds: 1.42,
      filesScanned: file ? 1 : 12,
      totalLinesAnalyzed: file ? 320 : 2840,
      metrics: {
        totalIssues: 4,
        syntaxErrors: 1,
        resourceLeakWarnings: 2,
        memoryWarnings: 1,
        bugWarnings: 0,
        informationCount: 0,
        fixableCount: 2,
      },
      findings: [
        {
          id: 'dev-1',
          ruleId: 'PY-BUG-001',
          title: 'Bug: Mutable Default Argument in Function',
          severity: 'error',
          category: 'bug',
          filePath: 'services/processor.py',
          line: 42,
          column: 5,
          description: 'Default argument `items=[]` is evaluated once at module load and shared across all calls.',
          codeSnippet: 'def process_items(items=[]):',
          suggestedFix: 'Use `items=None` and initialize `if items is None: items = []` inside body.',
          explanation: 'Mutable defaults retain modifications across function invocations, causing subtle state leaks.',
          isPotentialWarning: false,
          fixable: true,
          originalCode: 'def process_items(items=[]):\n',
          proposedCode: 'def process_items(items=None):\n    if items is None: items = []\n',
          unifiedDiff: '--- a/services/processor.py\n+++ b/services/processor.py\n@@ -42 +42,2 @@\n-def process_items(items=[]):\n+def process_items(items=None):\n+    if items is None: items = []\n',
          approvalStatus: 'pending',
        },
        {
          id: 'dev-2',
          ruleId: 'PY-RES-001',
          title: 'Resource Leak: Unclosed File Descriptor',
          severity: 'warning',
          category: 'resource_leak',
          filePath: 'services/report_generator.py',
          line: 18,
          column: 5,
          description: 'File opened using `open()` without `with` context manager.',
          codeSnippet: 'f = open(path, "w")',
          suggestedFix: 'Wrap in `with open(path, "w") as f:` for guaranteed auto-close.',
          explanation: 'File descriptor remains open until GC cycle. Can cause OS EMFILE errors.',
          isPotentialWarning: true,
          fixable: false,
          originalCode: 'f = open(path, "w")\n',
          proposedCode: 'with open(path, "w") as f:\n    # file operations\n',
          unifiedDiff: '--- a/services/report_generator.py\n+++ b/services/report_generator.py\n@@ -18 +18,2 @@\n-f = open(path, "w")\n+with open(path, "w") as f:\n',
          approvalStatus: 'pending',
        },
        {
          id: 'dev-3',
          ruleId: 'PY-BUG-002',
          title: 'Bug: Bare `except:` Catches BaseException',
          severity: 'warning',
          category: 'bug',
          filePath: 'utils/helpers.py',
          line: 94,
          column: 5,
          description: 'Bare `except:` catches `KeyboardInterrupt` and `SystemExit`.',
          codeSnippet: 'except:\n    pass',
          suggestedFix: 'Replace `except:` with `except Exception:`',
          explanation: 'Masks shutdown signals and debugging interrupts.',
          isPotentialWarning: false,
          fixable: true,
          originalCode: '    except:\n',
          proposedCode: '    except Exception:\n',
          unifiedDiff: '--- a/utils/helpers.py\n+++ b/utils/helpers.py\n@@ -94 +94 @@\n-    except:\n+    except Exception:\n',
          approvalStatus: 'pending',
        },
      ],
      isMockData: true,
    };
  }
}

/**
 * Pipeline Step 7: Re-parse proposed code and run static checks
 */
export async function validateFixes(
  sessionId: string,
  approvedFindingIds: string[]
): Promise<ValidationResult> {
  const response = await fetch(`${API_BASE_URL}/api/validate-fixes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      approved_finding_ids: approvedFindingIds,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Validation failed' }));
    throw new Error(err.detail || 'Code validation failed');
  }

  const data = await response.json();
  return {
    isValid: data.is_valid,
    validatedFiles: data.validated_files || [],
    syntaxErrors: data.syntax_errors || [],
    fixedCount: data.fixed_count,
    remainingCount: data.remaining_count,
    remainingFindings: (data.remaining_findings || []).map(mapBackendFinding),
  };
}

/**
 * Pipeline Step 8: Commit approved fixes to GitHub repository
 */
export async function commitFixesToGitHub(
  sessionId: string,
  approvedFindingIds: string[],
  githubToken: string,
  commitMessage?: string,
  createPr: boolean = false
): Promise<CommitResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/commits/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      analysis_id: sessionId,
      approved_finding_ids: approvedFindingIds,
      github_token: githubToken,
      commit_message: commitMessage || 'fix: resolve syntax and resource management issues',
      confirm: true,
      create_pr: createPr,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Commit failed' }));
    throw new Error(err.detail || 'GitHub commit failed');
  }

  const data = await response.json();
  return {
    commitId: data.commit_id,
    success: data.success,
    branchName: data.branch_name,
    commitSha: data.commit_sha,
    commitUrl: data.commit_url,
    pullRequestUrl: data.pull_request_url,
    pullRequestNumber: data.pull_request_number,
    committedFiles: data.committed_files || [],
    message: data.message,
  };
}

/**
 * Connect user GitHub credentials
 */
export async function connectGitHub(token: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/github/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'GitHub connection failed' }));
    throw new Error(err.detail || 'Failed to connect GitHub account');
  }
  return res.json();
}

/**
 * Preview commit of approved fixes
 */
export async function previewCommit(
  analysisId: string,
  approvedFindingIds?: string[],
  branchName?: string,
  token?: string
) {
  const res = await fetch(`${API_BASE_URL}/api/v1/commits/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      analysis_id: analysisId,
      approved_finding_ids: approvedFindingIds,
      branch_name: branchName,
      github_token: token,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Commit preview failed' }));
    throw new Error(err.detail || 'Failed to preview commit');
  }
  return res.json();
}

/**
 * Pipeline Step 8/9: Download Patched Project ZIP
 */
export function downloadPatchedZipUrl(sessionId: string, approvedFindingIds: string[]): string {
  const query = approvedFindingIds.length > 0 ? `?finding_ids=${approvedFindingIds.join(',')}` : '';
  return `${API_BASE_URL}/api/download-patched-zip/${sessionId}${query}`;
}

/**
 * Code Review & Approval API Integration
 */
export async function getFixDiff(fixId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/${fixId}/diff`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to retrieve diff' }));
    throw new Error(err.detail || 'Failed to retrieve fix diff');
  }
  return res.json();
}

export async function approveFix(fixId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/${fixId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to approve fix' }));
    throw new Error(err.detail || 'Failed to approve fix');
  }
  return res.json();
}

export async function rejectFix(fixId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/${fixId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to reject fix' }));
    throw new Error(err.detail || 'Failed to reject fix');
  }
  return res.json();
}

export async function editFix(fixId: string, suggestedCode: string, explanation?: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/${fixId}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggested_code: suggestedCode, explanation }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to edit fix' }));
    throw new Error(err.detail || 'Failed to edit fix');
  }
  return res.json();
}

export async function approveBatchFixes(fixIds: string[], analysisId?: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/approve-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fix_ids: fixIds, analysis_id: analysisId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to batch approve fixes' }));
    throw new Error(err.detail || 'Failed to batch approve fixes');
  }
  return res.json();
}

export async function applyApprovedFixes(analysisId: string, fixIds?: string[], confirm: boolean = true) {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/apply-approved`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_id: analysisId, fix_ids: fixIds, confirm }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to apply approved fixes' }));
    throw new Error(err.detail || 'Failed to apply approved fixes');
  }
  return res.json();
}

/**
 * Generate complete corrected Python code for an entire file using Ollama.
 * Returns complete original Python code and complete suggested code side-by-side.
 */
export async function generateFileFix(params: {
  sessionId?: string;
  analysisId?: string;
  filePath?: string;
  findingId?: string;
  originalCode?: string;
  customInstructions?: string;
}): Promise<FileFixResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/fixes/generate-file-fix`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: params.sessionId,
      analysis_id: params.analysisId,
      file_path: params.filePath,
      finding_id: params.findingId,
      original_code: params.originalCode,
      custom_instructions: params.customInstructions,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate complete file fix' }));
    throw new Error(err.detail || `Server returned error status ${res.status}`);
  }

  const data = await res.json();
  return {
    filename: data.filename,
    filePath: data.file_path,
    originalCode: data.original_code,
    suggestedCode: data.suggested_code,
    issues: data.issues || [],
    explanation: data.explanation || {
      whatIsError: '',
      howItIsFixed: '',
      whyItIsCorrect: '',
      sideEffects: '',
    },
    aiModel: data.ai_model || 'Ollama',
    diff: data.diff || '',
    isValid: data.is_valid ?? true,
    validationErrors: data.validation_errors || [],
    remainingIssues: data.remaining_issues || [],
  };
}

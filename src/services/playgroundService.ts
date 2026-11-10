import {
  PlaygroundExecutionResult,
  PlaygroundAnalysisResult,
  PlaygroundFixResponse,
  PlaygroundRunAndAnalyzeResponse,
  PlaygroundAssistantResponse,
  PlaygroundOllamaStatusResponse,
} from '../types/playground';

function getApiBaseUrl(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname || '127.0.0.1';
    return `http://${hostname}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

const API_BASE_URL = getApiBaseUrl();

function handleFetchError(err: unknown, endpoint: string): never {
  if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
    throw new Error(
      `Cannot connect to backend server at ${API_BASE_URL} (${endpoint}). Please verify that the FastAPI backend server is running on port 8000.`
    );
  }
  if (err instanceof Error) {
    throw err;
  }
  throw new Error(`Unexpected error calling ${endpoint}`);
}

export async function runPlaygroundCode(
  code: string,
  timeoutSeconds: number = 5.0,
  stdinInput: string = ''
): Promise<PlaygroundExecutionResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/playground/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        timeout_seconds: timeoutSeconds,
        stdin_input: stdinInput,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Execution request failed' }));
      throw new Error(err.detail || `Server returned error status ${response.status}`);
    }

    return await response.json();
  } catch (err: unknown) {
    handleFetchError(err, '/api/playground/run');
  }
}

export async function analyzePlaygroundCode(code: string): Promise<PlaygroundAnalysisResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/playground/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Analysis request failed' }));
      throw new Error(err.detail || `Server returned error status ${response.status}`);
    }

    return await response.json();
  } catch (err: unknown) {
    handleFetchError(err, '/api/playground/analyze');
  }
}

export async function fixPlaygroundCode(
  code: string,
  issueId?: string,
  customInstructions?: string
): Promise<PlaygroundFixResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/playground/fix`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        issue_id: issueId,
        custom_instructions: customInstructions,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'AI fix generation failed' }));
      throw new Error(err.detail || `Server returned error status ${response.status}`);
    }

    return await response.json();
  } catch (err: unknown) {
    handleFetchError(err, '/api/playground/fix');
  }
}

export async function runAndAnalyzePlayground(
  code: string,
  timeoutSeconds: number = 5.0,
  stdinInput: string = ''
): Promise<PlaygroundRunAndAnalyzeResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/playground/run-and-analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        timeout_seconds: timeoutSeconds,
        stdin_input: stdinInput,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Run & analyze request failed' }));
      throw new Error(err.detail || `Server returned error status ${response.status}`);
    }

    return await response.json();
  } catch (err: unknown) {
    handleFetchError(err, '/api/playground/run-and-analyze');
  }
}

export async function checkPlaygroundOllamaStatus(): Promise<PlaygroundOllamaStatusResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/playground/ollama-status`);
    if (!response.ok) {
      return { connected: false, model: 'unknown', base_url: API_BASE_URL };
    }
    return await response.json();
  } catch {
    return { connected: false, model: 'offline', base_url: API_BASE_URL };
  }
}

export async function askPlaygroundAssistant(
  prompt: string,
  code: string = '',
  filename: string = 'main.py',
  history: Array<{ role: string; content: string }> = []
): Promise<PlaygroundAssistantResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/playground/assistant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        code,
        filename,
        history,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Assistant request failed' }));
      throw new Error(err.detail || `Server returned error status ${response.status}`);
    }

    return await response.json();
  } catch (err: unknown) {
    handleFetchError(err, '/api/playground/assistant');
  }
}

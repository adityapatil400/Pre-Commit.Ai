from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class PlaygroundRunRequest(BaseModel):
    code: str = Field(..., description="Python source code to execute")
    timeout_seconds: float = Field(5.0, ge=0.5, le=10.0, description="Max execution timeout in seconds")
    stdin_input: Optional[str] = Field("", description="Optional stdin data to feed into process")

class PlaygroundExecutionResult(BaseModel):
    success: bool = Field(..., description="True if process exited with code 0")
    stdout: str = Field("", description="Standard output from execution")
    stderr: str = Field("", description="Standard error output from execution")
    exit_code: int = Field(0, description="Process return code (-1 if timed out)")
    execution_time_ms: float = Field(0.0, description="Execution duration in milliseconds")
    status: str = Field("completed", description="Execution status: completed, error, timeout, or blocked")
    error_message: Optional[str] = Field(None, description="Human-readable execution error or timeout description")
    traceback: Optional[str] = Field(None, description="Python traceback lines if runtime exception occurred")

class PlaygroundAnalyzeRequest(BaseModel):
    code: str = Field(..., description="Python source code to analyze")
    filename: Optional[str] = Field("playground.py", description="Virtual filename")

class PlaygroundIssue(BaseModel):
    id: str = Field(..., description="Unique issue identifier")
    severity: str = Field(..., description="Critical, High, Medium, or Low")
    type: str = Field(..., description="Syntax Error, Resource Leak, Memory Leak, Bug, etc.")
    line: int = Field(1, description="Line number of detected issue")
    column: int = Field(1, description="Column offset of detected issue")
    problematic_code: str = Field("", description="Problematic source code line")
    description: str = Field("", description="Detailed explanation of detected issue")
    suggestion: str = Field("", description="Recommended solution or fix")
    rule_id: Optional[str] = Field(None, description="AST rule identifier")

class PlaygroundMetrics(BaseModel):
    total_issues: int = 0
    syntax_errors: int = 0
    potential_bugs: int = 0
    resource_leaks: int = 0
    risk_score: int = Field(100, ge=0, le=100, description="Code health risk score (0-100, higher is safer)")

class PlaygroundAnalysisResult(BaseModel):
    total_issues: int = 0
    metrics: PlaygroundMetrics
    issues: List[PlaygroundIssue] = Field(default_factory=list)

class PlaygroundFixExplanation(BaseModel):
    what_is_error: str = Field(..., description="What was wrong with the code")
    how_it_is_fixed: str = Field(..., description="How the issue was remediated")
    why_it_is_correct: str = Field(..., description="Why the fix is appropriate")
    side_effects: str = Field(..., description="Possible side effects or limitations")

class PlaygroundFixRequest(BaseModel):
    code: str = Field(..., description="Original Python source code")
    issue_id: Optional[str] = Field(None, description="Optional specific issue ID to address")
    custom_instructions: Optional[str] = Field(None, description="Optional custom user prompt")

class PlaygroundFixResponse(BaseModel):
    original_code: str = Field(..., description="Original source code")
    suggested_code: str = Field(..., description="Complete corrected Python code")
    corrected_code: str = Field(..., description="Synonym for suggested_code")
    diff: str = Field("", description="Unified diff between original and suggested code")
    ai_model: str = Field("Ollama", description="Model or remediation engine used")
    is_valid: bool = Field(True, description="Whether corrected code compiles cleanly with AST")
    validation_errors: List[str] = Field(default_factory=list, description="Any syntax errors found in corrected code")
    explanation: PlaygroundFixExplanation
    fixes_applied: List[str] = Field(default_factory=list, description="List of all fixes applied")
    unresolved_issues: List[PlaygroundIssue] = Field(default_factory=list, description="List of unresolved issues")

class PlaygroundRunAndAnalyzeResponse(BaseModel):
    execution: PlaygroundExecutionResult
    analysis: PlaygroundAnalysisResult


class PlaygroundAssistantRequest(BaseModel):
    prompt: str = Field(..., description="Developer question or instruction")
    code: str = Field("", description="Current editor Python code context")
    filename: Optional[str] = Field("main.py", description="Current file name")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Chat message history")

class PlaygroundAssistantResponse(BaseModel):
    answer: str = Field(..., description="AI response to developer question")
    model: str = Field("Ollama", description="Model used for response")

class PlaygroundOllamaStatusResponse(BaseModel):
    connected: bool = Field(..., description="Whether Ollama server is responsive")
    model: str = Field(..., description="Current configured model")
    base_url: str = Field(..., description="Configured Ollama base URL")

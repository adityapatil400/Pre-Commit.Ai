from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.analysis_schema import FindingSchema

class ValidateFixesRequest(BaseModel):
    session_id: str = Field(..., description="Active analysis session UUID")
    approved_finding_ids: List[str] = Field(..., description="List of finding IDs accepted by user")

class ValidationResultResponse(BaseModel):
    is_valid: bool = Field(..., description="True if code re-parses with AST with zero syntax errors")
    validated_files: List[str] = Field(default_factory=list, description="List of file paths validated")
    syntax_errors: List[str] = Field(default_factory=list, description="Any syntax errors found during re-parsing")
    fixed_count: int = Field(0, description="Number of issues successfully resolved")
    remaining_count: int = Field(0, description="Number of remaining issues")
    remaining_findings: List[FindingSchema] = Field(default_factory=list, description="Remaining finding objects")

class FixProposalResponse(BaseModel):
    """
    Standardized LLM-generated code remediation proposal.
    Matches the required PreCommit AI structured response schema.
    """
    fix_id: str = Field(..., description="Unique fix proposal ID")
    analysis_id: str = Field(..., description="Analysis ID from which the issue originated")
    finding_id: Optional[str] = Field(None, description="Finding ID from analysis report")
    file_path: str = Field(..., description="Relative path of the target file")
    line_number: int = Field(1, description="Starting line number of the detected issue")
    issue: str = Field(..., description="Short title or description of the issue")
    original_code: str = Field(..., description="Original problematic code snippet")
    suggested_code: str = Field(..., description="Corrected code proposed by the LLM or user")
    explanation: str = Field(..., description="Technical rationale for the proposed fix")
    status: str = Field("pending_review", description="Fix status: pending_review, accepted, rejected, edited, stale, applied")
    diff: Optional[str] = Field(None, description="Unified diff between original and suggested code")
    model_used: Optional[str] = Field(None, description="LLM model identifier used to generate the fix")
    source_hash: Optional[str] = Field(None, description="SHA-256 hash of original file content at generation time")
    is_stale: bool = Field(False, description="True if source file content has changed since analysis")
    created_at: Optional[str] = Field(None, description="ISO timestamp of fix creation")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last update")

class GenerateFixRequest(BaseModel):
    """
    Request payload to generate a single LLM fix proposal.
    """
    analysis_id: str = Field(..., description="Active analysis ID")
    finding_id: Optional[str] = Field(None, description="Finding ID from analysis report")
    file_path: Optional[str] = Field(None, description="Optional target file path if finding_id not provided")
    rule_id: Optional[str] = Field(None, description="Optional rule ID if finding_id not provided")
    line_number: Optional[int] = Field(None, description="Optional line number if finding_id not provided")
    custom_instructions: Optional[str] = Field(None, description="Optional custom user instructions for the LLM")

class BatchGenerateFixRequest(BaseModel):
    """
    Request payload to generate fixes in batch for multiple findings.
    """
    analysis_id: str = Field(..., description="Active analysis ID")
    finding_ids: Optional[List[str]] = Field(None, description="Optional subset of finding IDs (all if omitted)")
    custom_instructions: Optional[str] = Field(None, description="Optional custom user instructions")

class BatchFixResponse(BaseModel):
    """
    Response returned by POST /api/v1/fixes/generate-batch.
    """
    analysis_id: str
    total_requested: int
    total_generated: int
    fixes: List[FixProposalResponse]

class LLMFixPromptRequest(BaseModel):
    rule_id: str
    code_snippet: str
    file_path: str
    context: Optional[str] = None
    custom_instructions: Optional[str] = None

class LLMFixResponse(BaseModel):
    rule_id: str
    explanation: str
    suggested_code: str
    diff: str
    model_used: str

class FixDiffResponse(BaseModel):
    """
    Detailed response for GET /api/v1/fixes/{fix_id}/diff.
    Contains original code, suggested code, file path, line number, issue description,
    LLM explanation, and unified diff.
    """
    fix_id: str = Field(..., description="Fix proposal identifier")
    analysis_id: str = Field(..., description="Analysis report ID")
    finding_id: Optional[str] = Field(None, description="Finding ID from analysis report")
    file_path: str = Field(..., description="Relative file path")
    line_number: int = Field(1, description="Line number of the issue")
    issue: str = Field(..., description="Issue title or description")
    explanation: str = Field(..., description="LLM explanation of remediation")
    original_code: str = Field(..., description="Original source code snippet")
    suggested_code: str = Field(..., description="Suggested corrected code")
    diff: str = Field(..., description="Unified diff formatted output")
    status: str = Field(..., description="Current approval status: pending_review, accepted, rejected, edited, stale, applied")
    is_stale: bool = Field(False, description="Whether source file was modified since analysis")

class EditFixRequest(BaseModel):
    """
    Request payload to edit a proposed code fix.
    """
    suggested_code: str = Field(..., description="User-modified corrected Python code")
    explanation: Optional[str] = Field(None, description="Optional updated technical explanation")

class BatchApproveRequest(BaseModel):
    """
    Request payload to batch-approve multiple proposed fixes.
    """
    fix_ids: List[str] = Field(..., description="List of fix proposal IDs to approve")
    analysis_id: Optional[str] = Field(None, description="Optional analysis ID context")

class BatchApproveResponse(BaseModel):
    """
    Response returned by POST /api/v1/fixes/approve-batch.
    """
    total_requested: int
    total_approved: int
    approved_fixes: List[FixProposalResponse]
    rejected_stale_fixes: List[dict] = Field(default_factory=list, description="Fixes rejected because source was modified")

class ApplyApprovedFixesRequest(BaseModel):
    """
    Request payload to apply approved fixes to workspace source files.
    Requires explicit user confirmation.
    """
    analysis_id: str = Field(..., description="Target analysis ID")
    fix_ids: Optional[List[str]] = Field(None, description="Optional specific approved fix IDs to apply")
    confirm: bool = Field(False, description="Explicit confirmation required to modify workspace files")

class ApplyApprovedFixesResponse(BaseModel):
    """
    Response returned when approved fixes are safely applied with explicit confirmation.
    """
    success: bool
    message: str
    applied_count: int
    modified_files: List[str]
    remaining_findings_count: int

# ---------------------------------------------------------------------------
# Structured File-Level Complete Remediation Schemas (Step 4 & Step 5)
# ---------------------------------------------------------------------------

class IssueItemSchema(BaseModel):
    type: str = Field(..., description="Category: Resource Leak, Syntax Error, Bug, Memory Leak")
    severity: str = Field(..., description="Critical, High, Medium, Low")
    line: int = Field(..., description="Line number of detected issue")
    description: str = Field(..., description="Issue description")
    suggestion: str = Field(..., description="Remediation suggestion")
    rule_id: Optional[str] = Field(None, description="AST rule identifier")

class ExplanationSchema(BaseModel):
    what_is_error: str = Field(..., description="What the error is")
    how_it_is_fixed: str = Field(..., description="How it is fixed")
    why_it_is_correct: str = Field(..., description="Why the suggested code is correct")
    side_effects: str = Field(..., description="Possible side effects or behavioral differences")

class FileFixResponse(BaseModel):
    """
    Structured file-level complete code fix response.
    Returns complete original Python code and complete Ollama-corrected Python code.
    """
    filename: str = Field(..., description="Target file name")
    file_path: Optional[str] = Field(None, description="Relative file path")
    original_code: str = Field(..., description="Complete original Python source code")
    suggested_code: str = Field(..., description="Complete corrected Python source code")
    corrected_code: Optional[str] = Field(None, description="Synonym for suggested_code")
    fixes_applied: List[str] = Field(default_factory=list, description="Descriptions of all fixes applied")
    unresolved_issues: List[IssueItemSchema] = Field(default_factory=list, description="List of unresolved issues")
    issues: List[IssueItemSchema] = Field(default_factory=list, description="All detected issues in this file")
    explanation: ExplanationSchema = Field(..., description="Structured explanation of error and fix")
    ai_model: str = Field("Ollama", description="AI model or engine used")
    diff: str = Field("", description="Unified diff between complete original and suggested code")
    is_valid: bool = Field(True, description="Whether generated code passes AST validation")
    validation_errors: List[str] = Field(default_factory=list, description="Any syntax errors found during AST check")
    remaining_issues: List[IssueItemSchema] = Field(default_factory=list, description="Remaining issues after fix")

class GenerateFileFixRequest(BaseModel):
    """
    Request to generate complete corrected Python code for a file using Ollama.
    """
    session_id: Optional[str] = Field(None, description="Analysis session ID")
    analysis_id: Optional[str] = Field(None, description="Analysis report ID (alternative to session_id)")
    file_path: Optional[str] = Field(None, description="Relative file path to fix")
    finding_id: Optional[str] = Field(None, description="Specific finding ID to fix file for")
    original_code: Optional[str] = Field(None, description="Optional raw original source code")
    custom_instructions: Optional[str] = Field(None, description="Optional custom user prompt instructions")



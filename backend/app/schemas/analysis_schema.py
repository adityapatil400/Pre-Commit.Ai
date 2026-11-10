from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

class SeverityEnum(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"

class CategoryEnum(str, Enum):
    SYNTAX = "syntax"
    RESOURCE_LEAK = "resource_leak"
    MEMORY = "memory_leak"
    MEMORY_ALT = "memory"
    BUG = "bug"
    OTHER = "other"

class ApprovalStatusEnum(str, Enum):
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    STALE = "stale"
    APPLIED = "applied"

class FindingSchema(BaseModel):
    id: str = Field(default="", description="Unique finding identifier")
    rule_id: str = Field(..., description="Rule code (e.g. RESOURCE001)")
    title: str = Field(..., description="Short finding title")
    severity: SeverityEnum = Field(..., description="Severity classification")
    category: str = Field(..., description="Category classification: resource_leak, memory_leak, bug, syntax")
    file_path: str = Field(..., description="Target file path")
    line_number: int = Field(1, description="Starting line number")
    line: int = Field(1, description="Alias for line_number")
    column: int = Field(1, description="Starting column offset")
    end_line: Optional[int] = Field(None, description="Ending line number")
    end_column: Optional[int] = Field(None, description="Ending column offset")
    description: str = Field("", description="Detailed explanation of detected issue")
    suggestion: str = Field("", description="Recommended remediation text")
    suggested_fix: str = Field("", description="Alias for suggestion")
    code_snippet: str = Field("", description="Original code context snippet")
    problematic_code: Optional[str] = Field(None, description="Problematic source code line")
    message: Optional[str] = Field(None, description="Short error message or title")
    explanation: str = Field("", description="Technical AST rationale")
    is_potential_warning: bool = Field(True, description="Distinguish static heuristic vs runtime crash")
    fixable: bool = Field(False, description="Whether fix can be automatically applied")
    original_code: str = Field("", description="Original lines before fix")
    proposed_code: str = Field("", description="Corrected lines after fix")
    unified_diff: str = Field("", description="Unified diff formatted output")
    approval_status: ApprovalStatusEnum = Field(ApprovalStatusEnum.PENDING, description="User approval status")

    @model_validator(mode="before")
    @classmethod
    def sync_line_and_suggestion(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Synchronize line / line_number
            if "line" in data and "line_number" not in data:
                data["line_number"] = data["line"]
            elif "line_number" in data and "line" not in data:
                data["line"] = data["line_number"]

            # Synchronize suggested_fix / suggestion
            if "suggested_fix" in data and "suggestion" not in data:
                data["suggestion"] = data["suggested_fix"]
            elif "suggestion" in data and "suggested_fix" not in data:
                data["suggested_fix"] = data["suggestion"]

            # Synchronize problematic_code / code_snippet
            if "code_snippet" in data and "problematic_code" not in data:
                data["problematic_code"] = data["code_snippet"]
            elif "problematic_code" in data and "code_snippet" not in data:
                data["code_snippet"] = data["problematic_code"]

            # Synchronize message / title / description
            if "title" in data and "message" not in data:
                data["message"] = data["title"]
            elif "message" in data and "title" not in data:
                data["title"] = data["message"]

            # Generate ID if missing
            if not data.get("id"):
                import uuid
                data["id"] = f"find-{uuid.uuid4().hex[:8]}"
        return data

class SummaryMetricsSchema(BaseModel):
    total_issues: int = 0
    syntax_errors: int = 0
    resource_leak_warnings: int = 0
    memory_warnings: int = 0
    bug_warnings: int = 0
    information_count: int = 0
    fixable_count: int = 0
    fixed_issues: int = 0

class AnalysisResultResponse(BaseModel):
    session_id: str
    project_name: str
    source_type: str = Field(..., description="'file', 'zip', or 'github'")
    source_reference: str
    status: str
    scanned_at: str
    duration_seconds: float
    files_scanned: int
    total_lines_analyzed: int
    metrics: SummaryMetricsSchema
    findings: List[FindingSchema]
    files_manifest: List[str] = Field(default_factory=list)
    files_source: Dict[str, str] = Field(default_factory=dict, description="Complete original source code by file_path")
    files_suggested: Dict[str, str] = Field(default_factory=dict, description="Complete suggested code by file_path")
    is_mock_data: bool = False

class AnalysisRunRequest(BaseModel):
    project_id: Optional[str] = Field(None, description="Project workspace identifier to analyze")

class AnalysisReportResponse(BaseModel):
    analysis_id: str = Field(..., description="Unique analysis execution identifier")
    project_id: str = Field(..., description="Project workspace identifier")
    project_name: str = Field(..., description="Project name")
    status: str = Field("completed", description="Analysis status: completed, completed_with_errors, failed")
    scanned_at: str
    duration_seconds: float
    total_files: int
    valid_files: int
    syntax_error_files: int
    metrics: SummaryMetricsSchema
    findings: List[FindingSchema]
    syntax_errors: List[Dict[str, Any]] = Field(default_factory=list)
    files_source: Dict[str, str] = Field(default_factory=dict, description="Complete original source code by file_path")
    files_suggested: Dict[str, str] = Field(default_factory=dict, description="Complete suggested code by file_path")

class RawCodeAnalysisRequest(BaseModel):
    code: str = Field(..., description="Raw Python code snippet to analyze")
    filename: Optional[str] = Field("snippet.py", description="Virtual filename")

class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "PreCommit AI (LeakGuard)"
    version: str = "1.0.0"
    timestamp: str
    python_version: str
    ollama_status: Optional[str] = "configured"

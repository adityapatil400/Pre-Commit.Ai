from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Literal

SeverityType = Literal["error", "warning", "information"]
CategoryType = Literal["syntax", "resource_leak", "memory", "bug", "other"]
ApprovalStatus = Literal["pending", "accepted", "rejected"]

@dataclass
class Finding:
    id: str
    rule_id: str
    title: str
    severity: SeverityType
    category: CategoryType
    file_path: str
    line: int
    column: int = 1
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    description: str = ""
    code_snippet: str = ""
    suggested_fix: str = ""
    explanation: str = ""
    is_potential_warning: bool = True
    fixable: bool = False
    original_code: str = ""
    proposed_code: str = ""
    unified_diff: str = ""
    approval_status: ApprovalStatus = "pending"

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SummaryMetrics:
    total_issues: int = 0
    syntax_errors: int = 0
    resource_leak_warnings: int = 0
    memory_warnings: int = 0
    bug_warnings: int = 0
    information_count: int = 0
    fixable_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class AnalysisResult:
    session_id: str
    project_name: str
    source_type: Literal["file", "zip", "github"]
    source_reference: str
    status: Literal["completed", "failed"]
    scanned_at: str
    duration_seconds: float
    files_scanned: int
    total_lines_analyzed: int
    metrics: SummaryMetrics
    findings: List[Finding]
    files_manifest: List[str] = field(default_factory=list)
    is_mock_data: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        return data

@dataclass
class ValidationResult:
    is_valid: bool
    validated_files: List[str]
    syntax_errors: List[str]
    fixed_count: int
    remaining_count: int
    remaining_findings: List[Finding]

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class CommitResult:
    success: bool
    branch_name: str
    commit_sha: str
    commit_url: str
    committed_files: List[str]
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


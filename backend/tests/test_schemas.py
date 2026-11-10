import pytest
from backend.app.schemas.analysis_schema import (
    FindingSchema,
    SummaryMetricsSchema,
    AnalysisResultResponse,
    SeverityEnum,
    CategoryEnum,
    ApprovalStatusEnum,
)
from backend.app.schemas.fix_schema import ValidateFixesRequest, ValidationResultResponse
from backend.app.schemas.github_schema import GitHubCommitRequest, GitHubCommitResponse

def test_finding_schema_serialization():
    finding = FindingSchema(
        id="test-1",
        rule_id="PY-RES-001",
        title="Unclosed File Descriptor",
        severity=SeverityEnum.WARNING,
        category=CategoryEnum.RESOURCE_LEAK,
        file_path="app.py",
        line=10,
        column=1,
        description="File opened without with context",
        code_snippet="f = open('test.txt')",
        suggested_fix="Use with open('test.txt') as f:",
        explanation="AST detected raw open call",
        is_potential_warning=True,
        fixable=True,
        original_code="f = open('test.txt')",
        proposed_code="with open('test.txt') as f:",
        unified_diff="--- a\n+++ b",
        approval_status=ApprovalStatusEnum.PENDING,
    )

    data = finding.model_dump()
    assert data["rule_id"] == "PY-RES-001"
    assert data["severity"] == "warning"
    assert data["category"] == "resource_leak"
    assert data["fixable"] is True

def test_analysis_result_response_serialization():
    metrics = SummaryMetricsSchema(
        total_issues=1,
        syntax_errors=0,
        resource_leak_warnings=1,
        memory_warnings=0,
        bug_warnings=0,
        information_count=0,
        fixable_count=1,
    )
    result = AnalysisResultResponse(
        session_id="test-session-123",
        project_name="test-project",
        source_type="file",
        source_reference="test.py",
        status="completed",
        scanned_at="10:00 AM, Nov 5, 2026",
        duration_seconds=0.15,
        files_scanned=1,
        total_lines_analyzed=50,
        metrics=metrics,
        findings=[],
        files_manifest=["test.py"],
        is_mock_data=False,
    )

    assert result.session_id == "test-session-123"
    assert result.metrics.total_issues == 1
    assert result.metrics.fixable_count == 1

def test_fix_and_github_schemas():
    val_req = ValidateFixesRequest(session_id="sess-1", approved_finding_ids=["f-1", "f-2"])
    assert len(val_req.approved_finding_ids) == 2

    val_res = ValidationResultResponse(
        is_valid=True,
        validated_files=["main.py"],
        syntax_errors=[],
        fixed_count=2,
        remaining_count=0,
        remaining_findings=[],
    )
    assert val_res.is_valid is True

    commit_res = GitHubCommitResponse(
        success=True,
        branch_name="precommit-ai/fixes-123",
        commit_sha="abcd1234ef",
        commit_url="https://github.com/user/repo/commit/abcd1234ef",
        committed_files=["main.py"],
        message="Committed successfully",
    )
    assert commit_res.success is True


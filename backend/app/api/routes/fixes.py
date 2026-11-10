from typing import Optional
from fastapi import APIRouter, HTTPException, status

from backend.app.llm.fix_generator import LLMFixGenerator, LLMFixValidationError
from backend.app.llm.ollama_client import (
    LLMError,
    OllamaConnectionError,
    ModelUnavailableError,
    LLMTimeoutError,
    LLMResponseError,
)
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.schemas.fix_schema import (
    ValidateFixesRequest,
    ValidationResultResponse,
    FixProposalResponse,
    GenerateFixRequest,
    BatchGenerateFixRequest,
    BatchFixResponse,
    LLMFixPromptRequest,
    LLMFixResponse,
    FixDiffResponse,
    EditFixRequest,
    BatchApproveRequest,
    BatchApproveResponse,
    ApplyApprovedFixesRequest,
    ApplyApprovedFixesResponse,
    IssueItemSchema,
    ExplanationSchema,
    FileFixResponse,
    GenerateFileFixRequest,
)
from backend.app.services.file_service import FileService
from backend.app.services.fix_service import FixService, FixServiceError
from backend.app.utils.logger import logger

router = APIRouter(tags=["Fixes & Remediation"])

@router.post("/validate-fixes", response_model=ValidationResultResponse, summary="Validate approved fixes")
@router.post("/fixes/validate", response_model=ValidationResultResponse, summary="Validate approved fixes (modular route)")
async def validate_fixes_endpoint(req: ValidateFixesRequest):
    """
    Pipeline Steps 6 & 7:
    6. User Approval: Receives user-approved finding IDs.
    7. Code Validation: Applies approved fixes, re-parses AST, and runs static checks.
    """
    try:
        result = FixService.validate_fixes(
            session_id=req.session_id,
            approved_finding_ids=req.approved_finding_ids,
        )
        return result
    except FixServiceError as e:
        logger.warning(f"Fix validation error: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected fix validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fix validation error: {str(e)}")

# --------------------------------------------------------------------------
# LLM Code-Fixing Engine Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/v1/fixes/generate",
    response_model=FixProposalResponse,
    summary="Generate LLM-based code fix for an AST finding"
)
@router.post(
    "/fixes/generate",
    response_model=FixProposalResponse,
    include_in_schema=False
)
async def generate_fix_endpoint(req: GenerateFixRequest):
    """
    Generates a proposed, non-applied code fix for an AST finding using local Ollama.
    
    Security & Validation:
    - Never automatically applies generated code (status remains 'pending_review').
    - Sanitizes source code to ensure secrets/tokens are never exposed to the LLM.
    - Treats repository code as untrusted data, never as prompt instructions.
    - Statically validates that suggested code compiles with ast.parse().
    """
    try:
        proposal = await LLMFixGenerator.generate_fix(
            analysis_id=req.analysis_id,
            finding_id=req.finding_id,
            file_path=req.file_path,
            rule_id=req.rule_id,
            line_number=req.line_number,
            custom_instructions=req.custom_instructions
        )
        return proposal
    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error: {e.message}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
    except ModelUnavailableError as e:
        logger.error(f"Ollama model error: {e.message}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
    except LLMTimeoutError as e:
        logger.error(f"Ollama timeout: {e.message}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=e.message)
    except LLMFixValidationError as e:
        logger.warning(f"Fix proposal validation error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except LLMError as e:
        logger.error(f"LLM error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error generating fix: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate fix: {str(e)}"
        )

@router.post(
    "/v1/fixes/generate-file-fix",
    response_model=FileFixResponse,
    summary="Generate complete Python code fix for a file using Ollama"
)
@router.post(
    "/fixes/generate-file-fix",
    response_model=FileFixResponse,
    include_in_schema=False
)
@router.post(
    "/api/fixes/generate-file-fix",
    response_model=FileFixResponse,
    include_in_schema=False
)
async def generate_file_fix_endpoint(req: GenerateFileFixRequest):
    """
    Step 3, 4, 7:
    Generates the COMPLETE corrected Python source code for an entire file using Ollama.
    Returns complete original Python code and complete corrected code side-by-side with line-by-line diff.
    """
    try:
        ident = req.session_id or req.analysis_id
        session = FileService.get_session(ident) if ident else None
        report = AnalysisEngine.get_analysis_report(ident) if ident and not session else None

        file_path = req.file_path or ""
        original_code = req.original_code or ""
        issues = []

        if session:
            all_findings = session.get("findings", [])
            files_dict = session.get("files", {})
            if req.finding_id and not file_path:
                matching = [f for f in all_findings if f.id == req.finding_id]
                if matching:
                    file_path = matching[0].file_path
            if file_path:
                matched_key = next((k for k in files_dict if k == file_path or k.endswith(file_path) or file_path.endswith(k)), file_path)
                file_path = matched_key
                issues = [f for f in all_findings if f.file_path == file_path or f.file_path.endswith(file_path) or file_path.endswith(f.file_path)]
                if not original_code:
                    original_code = files_dict.get(file_path, "")
        elif report:
            all_findings = report.findings
            files_src = getattr(report, "files_source", {}) or {}
            if req.finding_id and not file_path:
                matching = [f for f in all_findings if f.id == req.finding_id]
                if matching:
                    file_path = matching[0].file_path
            if file_path:
                matched_key = next((k for k in files_src if k == file_path or k.endswith(file_path) or file_path.endswith(k)), None)
                if matched_key:
                    file_path = matched_key
                    original_code = files_src.get(matched_key, "")
                issues = [f for f in all_findings if f.file_path == file_path or f.file_path.endswith(file_path) or file_path.endswith(f.file_path)]
                if not original_code:
                    from backend.app.services.workspace_service import WorkspaceService
                    ws_dir = WorkspaceService.get_workspace_path(report.project_id)
                    src_f = (ws_dir / file_path).resolve()
                    if src_f.is_file():
                        original_code = src_f.read_text(encoding="utf-8", errors="replace")

        if not file_path and req.finding_id:
            file_path = f"file-{req.finding_id}.py"
        elif not file_path:
            file_path = "script.py"

        if not original_code and issues:
            original_code = issues[0].original_code or issues[0].code_snippet or ""

        if not original_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Original source code for file '{file_path}' is unavailable."
            )

        # If no issues provided, analyze original code to discover issues
        if not issues:
            engine = AnalysisEngine(file_path=file_path, source_code=original_code)
            issues = engine.analyze()

        response = await LLMFixGenerator.generate_complete_file_fix(
            file_path=file_path,
            original_code=original_code,
            issues=issues,
            custom_instructions=req.custom_instructions
        )

        # Update cache so session has latest suggested code
        if session and file_path:
            session.setdefault("files_suggested", {})[file_path] = response.suggested_code
            for f in session.get("findings", []):
                if f.file_path == file_path:
                    f.proposed_code = response.suggested_code
                    f.unified_diff = response.diff

        return response
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating complete file fix: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate complete file fix: {str(e)}"
        )

@router.get(
    "/v1/fixes/{fix_id}",
    response_model=FixProposalResponse,
    summary="Get LLM fix proposal by fix_id"
)
@router.get(
    "/fixes/{fix_id}",
    response_model=FixProposalResponse,
    include_in_schema=False
)
async def get_fix_endpoint(fix_id: str):
    """
    Retrieves an existing LLM fix proposal by its fix_id.
    """
    proposal = LLMFixGenerator.get_fix(fix_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fix proposal '{fix_id}' not found."
        )
    return proposal

@router.post(
    "/v1/fixes/generate-batch",
    response_model=BatchFixResponse,
    summary="Generate LLM code fixes in batch"
)
@router.post(
    "/fixes/generate-batch",
    response_model=BatchFixResponse,
    include_in_schema=False
)
async def batch_generate_fixes_endpoint(req: BatchGenerateFixRequest):
    """
    Generates proposed code fixes for multiple findings in an analysis report.
    """
    try:
        return await LLMFixGenerator.batch_generate_fixes(
            analysis_id=req.analysis_id,
            finding_ids=req.finding_ids,
            custom_instructions=req.custom_instructions
        )
    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error during batch fix: {e.message}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error generating batch fixes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate batch fixes: {str(e)}"
        )

# --------------------------------------------------------------------------
# Code Review & Approval Workflow Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/v1/fixes/{fix_id}/diff",
    response_model=FixDiffResponse,
    summary="Get unified diff and metadata for a proposed code fix"
)
@router.get(
    "/fixes/{fix_id}/diff",
    response_model=FixDiffResponse,
    include_in_schema=False
)
async def get_fix_diff_endpoint(fix_id: str):
    """
    Returns original code, suggested code, file path, line number, issue description,
    LLM explanation, and unified diff for code review.
    """
    try:
        return LLMFixGenerator.get_diff(fix_id)
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting diff for fix {fix_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve fix diff: {str(e)}"
        )

@router.post(
    "/v1/fixes/{fix_id}/approve",
    response_model=FixProposalResponse,
    summary="Accept and approve a proposed code fix"
)
@router.post(
    "/fixes/{fix_id}/approve",
    response_model=FixProposalResponse,
    include_in_schema=False
)
async def approve_fix_endpoint(fix_id: str):
    """
    Accepts a proposed fix.
    Ensures that the original source has not changed since analysis.
    Rejects as stale (HTTP 409) if the file has been modified.
    Never modifies original files before explicit apply confirmation.
    """
    try:
        return LLMFixGenerator.approve_fix(fix_id)
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error approving fix {fix_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve fix: {str(e)}"
        )

@router.post(
    "/v1/fixes/{fix_id}/reject",
    response_model=FixProposalResponse,
    summary="Reject a proposed code fix"
)
@router.post(
    "/fixes/{fix_id}/reject",
    response_model=FixProposalResponse,
    include_in_schema=False
)
async def reject_fix_endpoint(fix_id: str):
    """
    Rejects a proposed fix.
    Preserves the rejected suggestion and explanation for the analysis report.
    """
    try:
        return LLMFixGenerator.reject_fix(fix_id)
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error rejecting fix {fix_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject fix: {str(e)}"
        )

@router.post(
    "/v1/fixes/{fix_id}/edit",
    response_model=FixProposalResponse,
    summary="Edit user-suggested code for a proposed fix"
)
@router.post(
    "/fixes/{fix_id}/edit",
    response_model=FixProposalResponse,
    include_in_schema=False
)
async def edit_fix_endpoint(fix_id: str, req: EditFixRequest):
    """
    Edits a proposed code fix with user-modified Python code.
    Re-validates Python syntax using ast.parse() before storing (HTTP 422 if invalid).
    Recomputes the unified diff.
    """
    try:
        return LLMFixGenerator.edit_fix(
            fix_id=fix_id,
            suggested_code=req.suggested_code,
            explanation=req.explanation
        )
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error editing fix {fix_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to edit fix: {str(e)}"
        )

@router.post(
    "/v1/fixes/approve-batch",
    response_model=BatchApproveResponse,
    summary="Batch approve multiple proposed code fixes"
)
@router.post(
    "/fixes/approve-batch",
    response_model=BatchApproveResponse,
    include_in_schema=False
)
async def batch_approve_fixes_endpoint(req: BatchApproveRequest):
    """
    Approves multiple selected fixes in a single request.
    Verifies that no source files have become stale since analysis.
    """
    try:
        return LLMFixGenerator.approve_batch(
            fix_ids=req.fix_ids,
            analysis_id=req.analysis_id
        )
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error batch-approving fixes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch-approve fixes: {str(e)}"
        )

@router.post(
    "/v1/fixes/apply-approved",
    response_model=ApplyApprovedFixesResponse,
    summary="Apply approved fixes with explicit confirmation"
)
@router.post(
    "/fixes/apply-approved",
    response_model=ApplyApprovedFixesResponse,
    include_in_schema=False
)
async def apply_approved_fixes_endpoint(req: ApplyApprovedFixesRequest):
    """
    Applies approved fixes to the project files in the workspace.
    Requires explicit confirmation (confirm=True).
    Re-validates resulting file AST compilation before writing.
    """
    try:
        return LLMFixGenerator.apply_approved_fixes(
            analysis_id=req.analysis_id,
            fix_ids=req.fix_ids,
            confirm=req.confirm
        )
    except LLMFixValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error applying approved fixes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply approved fixes: {str(e)}"
        )

# --------------------------------------------------------------------------
# Legacy LLM Prompt Endpoint
# --------------------------------------------------------------------------
@router.post("/fixes/generate-llm", response_model=LLMFixResponse, summary="Generate intelligent fix using Ollama LLM")
async def generate_llm_fix_endpoint(req: LLMFixPromptRequest):
    """
    Generates an intelligent context-aware code remediation using the local Ollama LLM.
    """
    try:
        result = await FixService.generate_llm_fix(
            rule_id=req.rule_id,
            code_snippet=req.code_snippet,
            file_path=req.file_path,
            context=req.context,
            custom_instructions=req.custom_instructions,
        )
        return result
    except Exception as e:
        logger.error(f"LLM fix generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ollama LLM generation error: {str(e)}")

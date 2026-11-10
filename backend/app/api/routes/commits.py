from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.app.schemas.github_schema import (
    GitHubCommitRequest,
    GitHubCommitResponse,
    CommitPreviewRequest,
    CommitPreviewResponse,
    CommitExecuteRequest,
)
from backend.app.services.commit_service import CommitService, CommitServiceError
from backend.app.services.file_service import FileService
from backend.app.services.fix_service import FixService
from backend.app.utils.logger import logger

router = APIRouter(tags=["Commits & Export"])

# --------------------------------------------------------------------------
# Pipeline Step 8: Commit Preview & Execution
# --------------------------------------------------------------------------

@router.post(
    "/v1/commits/preview",
    response_model=CommitPreviewResponse,
    summary="Preview approved code modifications and branch details before committing"
)
@router.post(
    "/commits/preview",
    response_model=CommitPreviewResponse,
    include_in_schema=False
)
async def preview_commit_endpoint(req: CommitPreviewRequest):
    """
    Computes modified files, unified diff, and target branch without committing.
    Verifies remote repository concurrency against base commit SHA.
    """
    try:
        return await CommitService.preview_commit(req)
    except CommitServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error previewing commit: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate commit preview: {str(e)}"
        )

@router.post(
    "/v1/commits/execute",
    response_model=GitHubCommitResponse,
    summary="Execute commit of approved fixes to dedicated GitHub branch"
)
@router.post(
    "/commits/execute",
    response_model=GitHubCommitResponse,
    include_in_schema=False
)
async def execute_commit_endpoint(req: CommitExecuteRequest):
    """
    Applies approved fixes, creates a dedicated branch (precommit-ai/fix-...),
    validates AST compilation of modified files, and pushes commit directly via GitHub API.
    
    STRICT SECURITY CHECKS:
    - Requires explicit confirmation (confirm=True).
    - Prohibits pushing directly to default branch.
    - Validates write permissions and prevents concurrent overwrite (SHA conflict detection).
    """
    try:
        return await CommitService.execute_commit(req)
    except CommitServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error executing commit: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute commit: {str(e)}"
        )

@router.get(
    "/v1/commits/{commit_id}",
    response_model=GitHubCommitResponse,
    summary="Get commit execution record and status"
)
@router.get(
    "/commits/{commit_id}",
    response_model=GitHubCommitResponse,
    include_in_schema=False
)
async def get_commit_endpoint(commit_id: str):
    """
    Retrieves commit record details, commit SHA, branch, and PR URL.
    """
    record = CommitService.get_commit(commit_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commit execution record '{commit_id}' not found."
        )
    return record

# --------------------------------------------------------------------------
# Pipeline Step 8/9: Download Patched ZIP (Local & GitHub Projects)
# --------------------------------------------------------------------------

@router.get(
    "/v1/commits/download-zip/{analysis_id}",
    summary="Download project ZIP with approved fixes applied"
)
@router.get(
    "/commits/download-zip/{analysis_id}",
    include_in_schema=False
)
@router.get(
    "/download-patched-zip/{analysis_id}",
    summary="Download project ZIP with approved fixes applied (legacy route)"
)
async def download_patched_zip_endpoint(
    analysis_id: str,
    finding_ids: Optional[str] = Query(None, description="Comma-separated finding IDs to apply")
):
    """
    Exports a clean, patched ZIP archive of the project workspace with approved fixes applied.
    """
    try:
        approved_ids = finding_ids.split(",") if finding_ids else None
        zip_buffer, filename = CommitService.download_patched_zip_for_analysis(
            analysis_id=analysis_id,
            approved_finding_ids=approved_ids
        )
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except CommitServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error generating patched zip: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download patched project archive: {str(e)}"
        )

# --------------------------------------------------------------------------
# Legacy route for backwards compatibility
# --------------------------------------------------------------------------

@router.post("/commit-fixes", response_model=GitHubCommitResponse, summary="Commit approved fixes to GitHub (legacy)")
@router.post("/commits/github", response_model=GitHubCommitResponse, summary="Commit approved fixes (modular route)")
async def commit_fixes_legacy_endpoint(req: GitHubCommitRequest):
    """
    Legacy commit endpoint maintaining backwards compatibility.
    """
    try:
        return await CommitService.commit_approved_fixes(
            session_id=req.session_id,
            approved_finding_ids=req.approved_finding_ids,
            github_token=req.github_token,
            commit_message=req.commit_message,
            custom_branch_name=req.branch_name,
        )
    except CommitServiceError as e:
        logger.warning(f"Commit error: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected commit failure: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")

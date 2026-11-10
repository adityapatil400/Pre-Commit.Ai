from typing import Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.schemas.analysis_schema import AnalysisRunRequest, AnalysisReportResponse
from backend.app.schemas.project_schema import ProjectResponse, GitHubCloneRequest
from backend.app.schemas.syntax_schema import SyntaxAnalysisRequest, SyntaxAnalysisResponse
from backend.app.services.workspace_service import (
    WorkspaceService,
    WorkspaceServiceError,
    InvalidFileInputError,
    ProjectNotFoundError,
)
from backend.app.services.github_service import GitHubService, GitHubServiceError
from backend.app.services.syntax_service import SyntaxService
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["Project Input Module"])

@router.post(
    "/upload",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Python project (.py file or .zip archive)"
)
async def upload_project_endpoint(file: UploadFile = File(...)):
    """
    Accepts an individual Python file (.py) or a compressed ZIP archive (.zip).
    
    Security & Validation:
    - Validates file extensions and decodability (rejects binary/executables).
    - Prevents Zip-Slip path traversal attacks.
    - Filters out .git, __pycache__, .venv, venv, and other unnecessary directories.
    - Discovers all Python files recursively preserving original relative paths.
    - Allocates an isolated temporary workspace on disk.
    - Enforces file size, archive size, and file count limits.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file was provided in the upload request."
        )

    filename = file.filename.strip()
    if not (filename.endswith(".py") or filename.endswith(".zip")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .py file or a .zip archive."
        )

    try:
        content_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}"
        )

    if not content_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file payload is empty."
        )

    try:
        if filename.endswith(".py"):
            project = WorkspaceService.create_workspace_from_single_file(
                filename=filename,
                content_bytes=content_bytes
            )
        else:
            project = WorkspaceService.create_workspace_from_zip(
                filename=filename,
                zip_bytes=content_bytes
            )
        return project

    except WorkspaceServiceError as e:
        logger.warning(f"Project upload rejected: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error creating workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating project workspace: {str(e)}"
        )

@router.post(
    "/github/clone",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone GitHub repository into isolated workspace"
)
async def clone_github_repository_endpoint(req: GitHubCloneRequest):
    """
    Accepts a GitHub repository URL, queries metadata, downloads repository files,
    and populates an isolated temporary workspace.
    
    Security & Validation:
    - Validates GitHub repository URL structure.
    - Extracts owner and repository name.
    - Inspects default branch and identifies base commit SHA.
    - Safely downloads zipball archive (strictly zero code execution).
    - Preserves repository directory structure while ignoring .git, venv, and cache dirs.
    - Handles invalid URLs, private repos, 404s, and API rate limits.
    """
    try:
        project = await GitHubService.clone_to_workspace(
            repo_url=req.repo_url,
            branch=req.branch,
            token=req.github_token
        )
        return project
    except GitHubServiceError as e:
        logger.warning(f"GitHub clone failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error cloning GitHub repository: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clone GitHub repository: {str(e)}"
        )

@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project workspace metadata by ID"
)
async def get_project_metadata_endpoint(project_id: str):
    """
    Returns standardized project details including discovered Python files and workspace metadata.
    """
    try:
        return WorkspaceService.get_project(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(e)}"
        )

@router.delete(
    "/projects/{project_id}",
    summary="Clean up and delete project workspace"
)
async def cleanup_project_workspace_endpoint(project_id: str):
    """
    Cleans up and deletes an isolated temporary project workspace.
    """
    removed = WorkspaceService.cleanup_workspace(project_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project workspace '{project_id}' not found or already deleted."
        )
    return {
        "success": True,
        "project_id": project_id,
        "message": "Project workspace cleaned up successfully."
    }

@router.post(
    "/analysis/syntax",
    response_model=SyntaxAnalysisResponse,
    summary="Validate Python syntax across all project files"
)
async def analyze_project_syntax_endpoint(
    req: Optional[SyntaxAnalysisRequest] = None,
    project_id: Optional[str] = Query(None, description="Optional query parameter for project_id")
):
    """
    Parses all discovered Python source files in the project workspace using Python's built-in `ast` library.
    
    Behavior:
    - Never executes source code.
    - Reports precise syntax, indentation, and EOF errors.
    - If a file contains a syntax error, it is isolated and excluded from further analysis.
    - Continues analyzing remaining valid Python files.
    """
    target_project_id = (req.project_id if req and req.project_id else None) or project_id
    if not target_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameter 'project_id' in JSON body or query parameter."
        )

    try:
        return SyntaxService.analyze_project_syntax(target_project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Syntax analysis failed for project {target_project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Syntax analysis failed: {str(e)}"
        )

@router.post(
    "/analysis/run",
    response_model=AnalysisReportResponse,
    summary="Run full AST static analysis engine on project"
)
async def run_project_analysis_endpoint(
    req: Optional[AnalysisRunRequest] = None,
    project_id: Optional[str] = Query(None, description="Optional query parameter for project_id")
):
    """
    Executes the full AST static analysis pipeline:
    1. Resolves project workspace.
    2. Runs syntax checking to isolate invalid files.
    3. Traverses valid files using AST NodeVisitors:
       - Resource leak detection (RESOURCE001-004)
       - Memory-related pattern detection (MEMORY001-005)
       - Bug and code-quality detection (BUG001-005)
    4. Aggregates findings and generates a structured analysis report.
    """
    target_project_id = (req.project_id if req and req.project_id else None) or project_id
    if not target_project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameter 'project_id' in JSON body or query parameter."
        )

    try:
        report = AnalysisEngine.run_project_analysis(target_project_id)
        return report
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Analysis engine execution failed for project {target_project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis engine execution failed: {str(e)}"
        )

@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisReportResponse,
    summary="Get structured analysis report by analysis_id"
)
async def get_analysis_report_endpoint(analysis_id: str):
    """
    Retrieves a cached or persisted structured analysis report by its unique analysis_id.
    """
    report = AnalysisEngine.get_analysis_report(analysis_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis report '{analysis_id}' not found."
        )
    return report

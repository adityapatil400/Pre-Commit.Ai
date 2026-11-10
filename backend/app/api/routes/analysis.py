from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from backend.app.schemas.analysis_schema import (
    AnalysisResultResponse,
    RawCodeAnalysisRequest,
)
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.file_service import FileService, FileServiceError
from backend.app.services.github_service import GitHubService, GitHubServiceError
from backend.app.utils.logger import logger

router = APIRouter(tags=["Analysis"])

@router.post("/analyze", response_model=AnalysisResultResponse, summary="Analyze Python code, ZIP, or GitHub repo")
async def analyze_project_endpoint(
    file: Optional[UploadFile] = File(None),
    github_url: Optional[str] = Form(None),
    github_token: Optional[str] = Form(None),
):
    """
    Core static code analysis endpoint:
    1. Input Handling: Python file, ZIP project, or GitHub repo URL.
    2. Source Retrieval: In-memory extraction (zero disk write).
    3. AST Static Analysis: Safe AST walk, zero code execution.
    4. Issue Detection: Syntax errors, resource leaks, memory leaks, bugs.
    5. Fix Recommendation Engine: Unified diffs and suggested remediation.
    """
    source_type = "zip"
    source_reference = ""
    project_name = "python-project"
    files_content = {}

    try:
        if file and file.filename:
            source_reference = file.filename
            raw_bytes = await file.read()

            if file.filename.endswith(".zip"):
                source_type = "zip"
                project_name = file.filename.replace(".zip", "")
                files_content = FileService.extract_zip_archive(raw_bytes)
            elif file.filename.endswith(".py"):
                source_type = "file"
                project_name = file.filename.replace(".py", "")
                files_content = FileService.extract_single_python_file(file.filename, raw_bytes)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Please upload a .py file or .zip archive."
                )

        elif github_url and github_url.strip():
            source_type = "github"
            source_reference = github_url.strip()
            project_name, files_content = await GitHubService.fetch_repository_files(
                repo_url=github_url.strip(),
                token=github_token
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Please upload a Python file, a ZIP project, or provide a GitHub repository URL."
            )

    except (FileServiceError, GitHubServiceError) as e:
        logger.warning(f"Analysis input error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected source retrieval error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Source retrieval error: {str(e)}")

    result = AnalysisService.analyze_files(
        files_content=files_content,
        project_name=project_name,
        source_type=source_type,
        source_reference=source_reference,
        github_token=github_token,
    )

    return result

@router.post("/analysis/raw", response_model=AnalysisResultResponse, summary="Analyze raw Python code snippet")
async def analyze_raw_code(req: RawCodeAnalysisRequest):
    """
    Analyzes an in-memory Python code snippet string without disk writes.
    """
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="Code snippet cannot be empty.")
    
    return AnalysisService.analyze_raw_snippet(code=req.code, filename=req.filename or "snippet.py")

@router.get("/analysis/{session_id}", summary="Get results for an active analysis session")
async def get_session_details(session_id: str):
    """
    Retrieves cached session metadata and findings for an active session.
    """
    session = FileService.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Analysis session not found or expired.")

    return {
        "session_id": session_id,
        "project_name": session["project_name"],
        "source_type": session["source_type"],
        "source_reference": session["source_reference"],
        "metrics": session["metrics"],
        "files_manifest": list(session["files"].keys()),
        "findings": [f.model_dump() if hasattr(f, "model_dump") else f for f in session["findings"]],
    }

@router.get("/analysis/{session_id}/report", response_class=PlainTextResponse, summary="Download Markdown report")
async def get_session_report(session_id: str):
    """
    Generates and returns an inspection report formatted as GitHub-flavored Markdown.
    """
    report = AnalysisService.generate_session_report(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return report


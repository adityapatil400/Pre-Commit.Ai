from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.github_schema import (
    GitHubRepoFetchRequest,
    GitHubConnectRequest,
    GitHubConnectResponse,
    GitHubRepositoriesResponse,
)
from backend.app.services.github_service import GitHubService, GitHubServiceError
from backend.app.utils.security import SecurityValidator

router = APIRouter(tags=["GitHub"])

@router.post(
    "/v1/github/connect",
    response_model=GitHubConnectResponse,
    summary="Authenticate and connect user GitHub account"
)
@router.post(
    "/github/connect",
    response_model=GitHubConnectResponse,
    include_in_schema=False
)
async def connect_github_account_endpoint(req: GitHubConnectRequest):
    """
    Authenticates the user using a GitHub Personal Access Token or OAuth token.
    Validates token, checks scopes, and returns user identity.
    Never stores or logs raw credentials.
    """
    try:
        return await GitHubService.connect_user(req.token)
    except GitHubServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect GitHub account: {str(e)}"
        )

@router.get(
    "/v1/github/repositories",
    response_model=GitHubRepositoriesResponse,
    summary="List repositories accessible to authenticated user"
)
@router.get(
    "/github/repositories",
    response_model=GitHubRepositoriesResponse,
    include_in_schema=False
)
async def list_github_repositories_endpoint(token: Optional[str] = Query(None, description="Optional GitHub token override")):
    """
    Lists repositories accessible to the authenticated user, indicating push/write permissions.
    """
    try:
        return await GitHubService.get_user_repositories(token)
    except GitHubServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list repositories: {str(e)}"
        )

@router.post("/v1/github/fetch", summary="Fetch repository files from GitHub")
@router.post("/github/fetch", summary="Fetch repository files from GitHub (legacy)")
async def fetch_github_repository(req: GitHubRepoFetchRequest):
    """
    Connects to the GitHub API, downloads the repository archive in-memory,
    and returns the project metadata and Python files manifest.
    """
    try:
        project_name, files = await GitHubService.fetch_repository_files(
            repo_url=req.repo_url,
            token=req.github_token,
            branch=req.branch
        )
    except GitHubServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    return {
        "project_name": project_name,
        "files_count": len(files),
        "manifest": list(files.keys()),
        "total_lines": sum(len(c.splitlines()) for c in files.values()),
    }

@router.get("/v1/github/validate-url", summary="Validate a GitHub repository URL")
@router.get("/github/validate-url", summary="Validate a GitHub repository URL (legacy)")
async def validate_github_url(url: str = Query(..., description="GitHub repository URL")):
    """
    Validates the syntax and structure of a GitHub repository URL.
    """
    is_valid = SecurityValidator.is_valid_github_url(url)
    owner, repo = None, None
    if is_valid:
        try:
            owner, repo = GitHubService.parse_repo_url(url)
        except Exception:
            is_valid = False

    return {
        "valid": is_valid,
        "owner": owner,
        "repo": repo,
    }

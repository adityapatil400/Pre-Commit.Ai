import io
import re
from typing import Dict, List, Optional, Tuple
import httpx

from backend.app.config import settings
from backend.app.schemas.github_schema import (
    GitHubConnectResponse,
    GitHubRepositoriesResponse,
    GitHubRepositoryItem,
)
from backend.app.schemas.project_schema import ProjectResponse
from backend.app.services.file_service import FileService, FileServiceError
from backend.app.services.workspace_service import WorkspaceService, WorkspaceServiceError
from backend.app.utils.logger import logger
from backend.app.utils.security import SecurityValidator

class GitHubServiceError(Exception):
    """Custom exception raised for GitHub interaction failures."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class GitHubService:
    """
    Handles secure interaction with GitHub:
    - Repository URL validation and parsing
    - Metadata and branch/commit inspection
    - In-memory archive extraction and workspace provisioning
    - Strictly static byte extraction (zero code execution)
    """

    @staticmethod
    def parse_repo_url(repo_url: str) -> Tuple[str, str]:
        """
        Parses and validates owner and repository name from a GitHub URL.
        """
        if not repo_url or not isinstance(repo_url, str):
            raise GitHubServiceError("GitHub repository URL must be provided.")

        clean_url = repo_url.strip()
        if not SecurityValidator.validate_github_url(clean_url):
            raise GitHubServiceError(
                "Invalid GitHub repository URL. Format must be https://github.com/owner/repository"
            )

        match = re.match(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$", clean_url)
        if not match:
            raise GitHubServiceError("Failed to extract repository owner and name.")

        owner = match.group(1)
        repo = match.group(2).replace(".git", "")
        return owner, repo

    @classmethod
    async def clone_to_workspace(
        cls,
        repo_url: str,
        branch: Optional[str] = None,
        token: Optional[str] = None
    ) -> ProjectResponse:
        """
        Retrieves Python files from a GitHub repository via zipball archive,
        identifies default branch and commit SHA, and populates an isolated temporary workspace.
        """
        owner, repo = cls.parse_repo_url(repo_url)
        project_name = f"{owner}/{repo}"
        auth_token = token or settings.GITHUB_TOKEN

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-Agent"
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            logger.info(f"Using GitHub token: {SecurityValidator.mask_token(auth_token)}")

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            # 1. Fetch repository metadata to find default branch and check accessibility
            repo_api_url = f"{settings.GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
            try:
                repo_resp = await client.get(repo_api_url, headers=headers)
            except httpx.RequestError as e:
                raise GitHubServiceError(f"Network error connecting to GitHub: {str(e)}", status_code=502)

            if repo_resp.status_code == 404:
                raise GitHubServiceError(
                    f"Repository '{project_name}' not found, unavailable, or is private. "
                    "Please verify the URL or provide a valid GitHub token.",
                    status_code=404
                )
            elif repo_resp.status_code == 401:
                raise GitHubServiceError("Invalid or expired GitHub Personal Access Token.", status_code=401)
            elif repo_resp.status_code == 403:
                rate_limit = repo_resp.headers.get("x-ratelimit-remaining", "")
                if rate_limit == "0":
                    raise GitHubServiceError(
                        "GitHub API rate limit exceeded. Please provide a GitHub token to authenticate.",
                        status_code=429
                    )
                raise GitHubServiceError(f"Access forbidden to repository '{project_name}'.", status_code=403)
            elif repo_resp.status_code != 200:
                raise GitHubServiceError(
                    f"GitHub API error (HTTP {repo_resp.status_code}): {repo_resp.text[:200]}",
                    status_code=repo_resp.status_code
                )

            repo_data = repo_resp.json()
            default_branch = repo_data.get("default_branch", "main")
            target_branch = branch or default_branch

            # 2. Fetch base commit SHA for the target branch
            commit_api_url = f"{settings.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/commits/{target_branch}"
            base_commit_sha = ""
            try:
                commit_resp = await client.get(commit_api_url, headers=headers)
                if commit_resp.status_code == 200:
                    base_commit_sha = commit_resp.json().get("sha", "")
                elif commit_resp.status_code == 404:
                    raise GitHubServiceError(f"Branch or ref '{target_branch}' not found in repository.", status_code=404)
            except httpx.RequestError as e:
                logger.warning(f"Failed to query commit SHA for branch {target_branch}: {e}")

            # 3. Download repository zipball archive
            ref_to_download = base_commit_sha or target_branch
            zipball_url = f"{settings.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/zipball/{ref_to_download}"
            logger.info(f"Downloading repository zipball: {zipball_url}")

            try:
                zip_resp = await client.get(zipball_url, headers=headers)
            except httpx.RequestError as e:
                raise GitHubServiceError(f"Network error downloading repository archive: {str(e)}", status_code=502)

            if zip_resp.status_code != 200:
                raise GitHubServiceError(
                    f"Failed to download repository zipball (HTTP {zip_resp.status_code}).",
                    status_code=zip_resp.status_code
                )

            zip_bytes = zip_resp.content

        # 4. Extract into an isolated workspace using WorkspaceService
        try:
            project_response = WorkspaceService.create_workspace_from_zip(
                filename=f"{repo}.zip",
                zip_bytes=zip_bytes,
                project_name=project_name,
                strip_single_root=True,
                input_type="github",
                source_repository=f"https://github.com/{owner}/{repo}",
                branch=target_branch,
                base_commit_sha=base_commit_sha,
            )
            return project_response
        except WorkspaceServiceError as e:
            raise GitHubServiceError(e.message, status_code=e.status_code)

    @classmethod
    async def fetch_repository_files(
        cls,
        repo_url: str,
        token: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Retrieves Python files from a GitHub repository via zipball.
        Zero disk footprint — processed entirely in-memory.
        Returns: (project_name, Dict[file_path, content])
        """
        owner, repo = cls.parse_repo_url(repo_url)
        project_name = f"{owner}/{repo}"

        auth_token = token or settings.GITHUB_TOKEN
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-Agent"
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            logger.info(f"Using GitHub token: {SecurityValidator.mask_token(auth_token)}")

        zipball_ref = branch or "HEAD"
        zipball_url = f"{settings.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/zipball/{zipball_ref}"

        logger.info(f"Fetching repository archive for `{project_name}` from `{zipball_url}`")

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            try:
                resp = await client.get(zipball_url, headers=headers)
            except httpx.RequestError as e:
                raise GitHubServiceError(f"Network error connecting to GitHub: {str(e)}", status_code=502)

            if resp.status_code == 404:
                raise GitHubServiceError(
                    f"Repository `{project_name}` not found or is private (require valid GitHub Token).",
                    status_code=404
                )
            elif resp.status_code == 401 or resp.status_code == 403:
                rate_limit_msg = resp.headers.get("x-ratelimit-remaining", "")
                if rate_limit_msg == "0":
                    raise GitHubServiceError(
                        "GitHub API rate limit exceeded. Please provide a GitHub Personal Access Token.",
                        status_code=429
                    )
                raise GitHubServiceError(f"GitHub authentication error (HTTP {resp.status_code}).", status_code=resp.status_code)
            elif resp.status_code != 200:
                raise GitHubServiceError(f"GitHub API returned HTTP {resp.status_code}: {resp.text[:200]}", status_code=resp.status_code)

            zip_bytes = resp.content

        try:
            files_dict = FileService.extract_zip_archive(zip_bytes)
        except FileServiceError as e:
            raise GitHubServiceError(f"Failed to process repository archive: {str(e)}")

        logger.info(f"Successfully retrieved {len(files_dict)} Python files from `{project_name}`")
        return project_name, files_dict

    _CONNECTED_TOKEN: Optional[str] = None
    _CONNECTED_USER: Optional[dict] = None

    @classmethod
    def get_connected_token(cls) -> Optional[str]:
        return cls._CONNECTED_TOKEN or settings.GITHUB_TOKEN

    @classmethod
    async def connect_user(cls, token: str) -> GitHubConnectResponse:
        """
        Validates GitHub credentials, retrieves user identity and OAuth scopes.
        Never stores raw passwords; stores token securely in memory.
        """
        if not token or not token.strip():
            raise GitHubServiceError("GitHub token must be provided.", status_code=400)

        clean_token = token.strip()
        headers = {
            "Authorization": f"Bearer {clean_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-Agent"
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(f"{settings.GITHUB_API_BASE_URL}/user", headers=headers)
            except httpx.RequestError as e:
                raise GitHubServiceError(f"Network error connecting to GitHub: {e}", status_code=502)

            if resp.status_code == 401:
                raise GitHubServiceError("Invalid or expired GitHub Personal Access Token.", status_code=401)
            elif resp.status_code != 200:
                raise GitHubServiceError(f"GitHub authentication error (HTTP {resp.status_code}).", status_code=resp.status_code)

            user_data = resp.json()
            scopes_header = resp.headers.get("x-oauth-scopes", "")
            scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]

            cls._CONNECTED_TOKEN = clean_token
            cls._CONNECTED_USER = {
                "login": user_data.get("login"),
                "name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url"),
                "scopes": scopes
            }

            logger.info(f"GitHub account successfully connected: @{user_data.get('login')} (scopes: {scopes})")

            return GitHubConnectResponse(
                connected=True,
                username=user_data.get("login", ""),
                name=user_data.get("name"),
                avatar_url=user_data.get("avatar_url"),
                scopes=scopes,
                message=f"Connected to GitHub as @{user_data.get('login')}."
            )

    @classmethod
    async def get_user_repositories(cls, token: Optional[str] = None) -> GitHubRepositoriesResponse:
        """
        Lists repositories accessible to the connected user with write/push permission flag.
        """
        auth_token = token or cls.get_connected_token()
        if not auth_token:
            raise GitHubServiceError("Authentication required. Please connect a GitHub token.", status_code=401)

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-Agent"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{settings.GITHUB_API_BASE_URL}/user/repos?sort=updated&per_page=100&affiliation=owner,collaborator,organization_member",
                    headers=headers
                )
            except httpx.RequestError as e:
                raise GitHubServiceError(f"Network error connecting to GitHub: {e}", status_code=502)

            if resp.status_code == 401:
                raise GitHubServiceError("Invalid or expired GitHub Personal Access Token.", status_code=401)
            elif resp.status_code != 200:
                raise GitHubServiceError(f"Failed to list repositories (HTTP {resp.status_code}).", status_code=resp.status_code)

            items = []
            for r in resp.json():
                perms = r.get("permissions", {})
                can_push = perms.get("push", False) or perms.get("admin", False)
                items.append(GitHubRepositoryItem(
                    id=r["id"],
                    name=r["name"],
                    full_name=r["full_name"],
                    owner=r["owner"]["login"] if "owner" in r and "login" in r["owner"] else "",
                    html_url=r["html_url"],
                    default_branch=r.get("default_branch", "main"),
                    is_private=r.get("private", False),
                    permissions=perms,
                    can_push=can_push
                ))

            return GitHubRepositoriesResponse(total=len(items), repositories=items)

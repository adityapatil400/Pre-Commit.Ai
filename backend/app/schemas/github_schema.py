from typing import List, Optional
from pydantic import BaseModel, Field

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class GitHubRepoFetchRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL (https://github.com/owner/repo)")
    branch: Optional[str] = Field(None, description="Optional branch or ref")
    github_token: Optional[str] = Field(None, description="Optional GitHub Personal Access Token")

class GitHubConnectRequest(BaseModel):
    token: str = Field(..., description="GitHub Personal Access Token or OAuth access token with repo scope")

class GitHubConnectResponse(BaseModel):
    connected: bool = Field(..., description="True if authentication and token validation succeeded")
    username: str = Field(..., description="Authenticated GitHub username")
    name: Optional[str] = Field(None, description="GitHub user display name")
    avatar_url: Optional[str] = Field(None, description="User avatar image URL")
    scopes: List[str] = Field(default_factory=list, description="OAuth or token scopes")
    message: str = Field(..., description="Status summary message")

class GitHubRepositoryItem(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    html_url: str
    default_branch: str
    is_private: bool
    permissions: Dict[str, bool] = Field(default_factory=dict, description="User permissions: admin, push, pull")
    can_push: bool = Field(False, description="True if user has write/push permissions")

class GitHubRepositoriesResponse(BaseModel):
    total: int
    repositories: List[GitHubRepositoryItem]

class CommitPreviewRequest(BaseModel):
    analysis_id: str = Field(..., description="Active analysis report ID")
    approved_finding_ids: Optional[List[str]] = Field(None, description="Optional subset of approved finding IDs")
    branch_name: Optional[str] = Field(None, description="Target branch name")
    github_token: Optional[str] = Field(None, description="Optional GitHub token override")

class CommitPreviewResponse(BaseModel):
    analysis_id: str
    project_name: str
    source_type: str = Field(..., description="'github' or 'zip'")
    source_repository: Optional[str] = None
    target_branch: str
    base_branch: str
    base_commit_sha: Optional[str] = None
    remote_commit_sha: Optional[str] = None
    is_stale: bool = Field(False, description="True if remote commit SHA differs from analysis base commit SHA")
    stale_reason: Optional[str] = None
    files_to_modify: List[str]
    total_files_modified: int
    unified_diff: str
    can_commit: bool
    requires_confirmation: bool = True

class CommitExecuteRequest(BaseModel):
    analysis_id: str = Field(..., description="Active analysis report ID")
    approved_finding_ids: Optional[List[str]] = Field(None, description="Optional subset of approved finding IDs")
    github_token: Optional[str] = Field(None, description="GitHub PAT with repo scope or contents:write")
    commit_message: Optional[str] = Field(
        "fix: resolve syntax and resource management issues",
        description="Descriptive Git commit message"
    )
    branch_name: Optional[str] = Field(None, description="Custom branch name (defaults to precommit-ai/fix-<analysis_id[:8]>)")
    confirm: bool = Field(False, description="Explicit confirmation required to commit and push to GitHub")
    create_pr: bool = Field(False, description="Optionally create a Pull Request on GitHub")
    pr_title: Optional[str] = Field(None, description="Optional Pull Request title")
    pr_body: Optional[str] = Field(None, description="Optional Pull Request description")

class GitHubCommitResponse(BaseModel):
    commit_id: Optional[str] = Field(None, description="Unique commit execution ID")
    success: bool
    branch_name: str
    commit_sha: str
    commit_url: str
    pull_request_url: Optional[str] = None
    pull_request_number: Optional[int] = None
    committed_files: List[str] = Field(default_factory=list)
    total_committed_files: int = 0
    message: str
    timestamp: Optional[str] = None

class GitHubCommitRequest(BaseModel):
    session_id: str = Field(..., description="Active analysis session UUID")
    approved_finding_ids: List[str] = Field(..., description="IDs of approved fixes to commit")
    github_token: str = Field(..., description="GitHub PAT with repo contents:write scope")
    commit_message: Optional[str] = Field(
        "fix(ast): apply PreCommit AI approved static analysis remediations",
        description="Git commit message"
    )
    branch_name: Optional[str] = Field(None, description="Custom branch name (defaults to precommit-ai/fixes-<timestamp>)")



from typing import List, Optional
from pydantic import BaseModel, Field

class ProjectResponse(BaseModel):
    """
    Standardized response returned by the project input module.
    """
    project_id: str = Field(..., description="Unique project / analysis identifier")
    project_name: str = Field(..., description="Name of the uploaded project or repository")
    input_type: str = Field(..., description="Type of input: 'file', 'zip', or 'github'")
    source_repository: Optional[str] = Field(None, description="GitHub repository URL if cloned from GitHub")
    branch: Optional[str] = Field(None, description="Branch name (for GitHub inputs)")
    base_commit_sha: Optional[str] = Field(None, description="Base commit SHA (for GitHub inputs)")
    python_files: List[str] = Field(default_factory=list, description="Relative paths of discovered Python files")
    total_files: int = Field(0, description="Total count of discovered Python files")

class GitHubCloneRequest(BaseModel):
    """
    Request payload for cloning a GitHub repository into an isolated workspace.
    """
    repo_url: str = Field(..., description="GitHub repository URL (https://github.com/owner/repo)")
    branch: Optional[str] = Field(None, description="Optional branch or tag to clone")
    github_token: Optional[str] = Field(None, description="Optional GitHub Personal Access Token")


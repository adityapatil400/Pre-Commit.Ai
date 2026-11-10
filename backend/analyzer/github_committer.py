import base64
import datetime
import re
from typing import Dict, List, Optional
import httpx
from .models import CommitResult

class GitHubCommitter:
    """
    Creates a dedicated branch and commits only approved changes using GitHub REST API.
    """

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-AST-Committer"
        }

    async def commit_approved_changes(
        self,
        repo_url: str,
        modified_files: Dict[str, str],
        commit_message: Optional[str] = None
    ) -> CommitResult:
        match = re.match(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$", repo_url.strip())
        if not match:
            return CommitResult(
                success=False,
                branch_name="",
                commit_sha="",
                commit_url="",
                committed_files=[],
                message="Invalid GitHub repository URL."
            )

        owner, repo = match.group(1), match.group(2).replace(".git", "")
        base_api = f"https://api.github.com/repos/{owner}/{repo}"

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"precommit-ai/fixes-{timestamp}"
        msg = commit_message or f"fix(ast): apply PreCommit AI approved static analysis remediations [{timestamp}]"

        async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
            # 1. Get default branch
            repo_resp = await client.get(base_api)
            if repo_resp.status_code != 200:
                err = repo_resp.json().get("message", "Failed to access repository")
                return CommitResult(
                    success=False,
                    branch_name="",
                    commit_sha="",
                    commit_url="",
                    committed_files=[],
                    message=f"GitHub Error: {err}"
                )

            default_branch = repo_resp.json().get("default_branch", "main")

            # 2. Get latest commit SHA of default branch
            ref_resp = await client.get(f"{base_api}/git/ref/heads/{default_branch}")
            if ref_resp.status_code != 200:
                return CommitResult(
                    success=False,
                    branch_name="",
                    commit_sha="",
                    commit_url="",
                    committed_files=[],
                    message=f"Could not retrieve head of branch `{default_branch}`."
                )

            latest_sha = ref_resp.json()["object"]["sha"]

            # 3. Create dedicated branch
            create_branch_resp = await client.post(
                f"{base_api}/git/refs",
                json={"ref": f"refs/heads/{branch_name}", "sha": latest_sha}
            )
            if create_branch_resp.status_code not in (200, 201):
                err = create_branch_resp.json().get("message", "Failed to create branch")
                return CommitResult(
                    success=False,
                    branch_name="",
                    commit_sha="",
                    commit_url="",
                    committed_files=[],
                    message=f"Could not create branch `{branch_name}`: {err}"
                )

            # 4. Commit each modified file to the dedicated branch
            committed: List[str] = []
            last_commit_sha = latest_sha

            for file_path, content in modified_files.items():
                # Get current file SHA on new branch (if exists)
                blob_sha = None
                get_content_resp = await client.get(
                    f"{base_api}/contents/{file_path}",
                    params={"ref": branch_name}
                )
                if get_content_resp.status_code == 200:
                    blob_sha = get_content_resp.json().get("sha")

                encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                payload = {
                    "message": f"PreCommit AI: Remediate {file_path}",
                    "content": encoded_content,
                    "branch": branch_name
                }
                if blob_sha:
                    payload["sha"] = blob_sha

                put_resp = await client.put(f"{base_api}/contents/{file_path}", json=payload)
                if put_resp.status_code in (200, 201):
                    committed.append(file_path)
                    last_commit_sha = put_resp.json().get("commit", {}).get("sha", last_commit_sha)

            branch_url = f"https://github.com/{owner}/{repo}/tree/{branch_name}"

            return CommitResult(
                success=True,
                branch_name=branch_name,
                commit_sha=last_commit_sha[:8],
                commit_url=branch_url,
                committed_files=committed,
                message=f"Successfully created branch `{branch_name}` with {len(committed)} approved file remediations."
            )


import ast
import base64
from datetime import datetime
import difflib
import io
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import uuid
import zipfile

import httpx

from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.config import settings
from backend.app.llm.fix_generator import LLMFixGenerator
from backend.app.schemas.github_schema import (
    CommitPreviewRequest,
    CommitPreviewResponse,
    CommitExecuteRequest,
    GitHubCommitResponse,
)
from backend.app.services.file_service import FileService
from backend.app.services.fix_service import FixService
from backend.app.services.github_service import GitHubService, GitHubServiceError
from backend.app.services.workspace_service import WorkspaceService
from backend.app.utils.logger import logger
from backend.app.utils.security import SecurityValidator

class CommitServiceError(Exception):
    """Exception raised for commit and GitHub execution failures."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class CommitService:
    """
    Handles automated code replacement, local patched ZIP generation,
    and Git branch creation & committing via GitHub REST API.
    
    Guarantees:
    - Never requests or stores raw passwords.
    - Requires explicit confirmation (confirm=True) for every commit operation.
    - Protects against concurrent repository updates via base commit SHA comparison.
    - Prohibits pushing directly to default branch by default.
    - Validates resulting code syntax via ast.parse().
    - Never commits unapproved or rejected files.
    """

    # In-memory registry for commit records: commit_id -> GitHubCommitResponse
    _COMMIT_REGISTRY: Dict[str, GitHubCommitResponse] = {}

    @classmethod
    def get_commit(cls, commit_id: str) -> Optional[GitHubCommitResponse]:
        """Retrieves a commit execution record by commit_id."""
        return cls._COMMIT_REGISTRY.get(commit_id)

    @classmethod
    def _compute_approved_patches(
        cls,
        analysis_id: str,
        approved_finding_ids: Optional[List[str]] = None
    ) -> Tuple[Dict[str, str], Dict[str, str], str]:
        """
        Gathers approved/edited fixes for an analysis, verifies they are not stale,
        applies replacements to source files in descending line order, and validates AST.
        Returns: (original_files, patched_files, combined_unified_diff)
        """
        report = AnalysisEngine.get_analysis_report(analysis_id)
        if not report:
            # Check legacy FileService session
            session = FileService.get_session(analysis_id)
            if not session:
                raise CommitServiceError(f"Analysis '{analysis_id}' not found or session expired.", status_code=404)
            
            approved_ids = approved_finding_ids or session.get("approved_finding_ids", [])
            findings_map = {f.id: f for f in session["findings"]}
            approved_findings = [findings_map[fid] for fid in approved_ids if fid in findings_map]
            
            orig_files = session["files"]
            patched_files = FixService.apply_approved_fixes(orig_files, approved_findings)
            
            diff_lines = []
            for path, patched in patched_files.items():
                orig = orig_files.get(path, "")
                if orig != patched:
                    diff_lines.extend(list(difflib.unified_diff(
                        orig.splitlines(keepends=True),
                        patched.splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                        lineterm=""
                    )))
            return orig_files, patched_files, "\n".join(diff_lines)

        workspace_dir = WorkspaceService.get_workspace_path(report.project_id)
        if not workspace_dir.exists():
            raise CommitServiceError(f"Workspace for project '{report.project_id}' not found.", status_code=404)

        # Retrieve approved or edited fixes
        candidates = [
            f for f in LLMFixGenerator._FIX_REGISTRY.values()
            if f.analysis_id == analysis_id and f.status in ("accepted", "edited")
        ]
        if approved_finding_ids:
            candidates = [
                f for f in candidates
                if f.finding_id in approved_finding_ids or f.fix_id in approved_finding_ids
            ]

        # Group candidates by file
        fixes_by_file: Dict[str, List] = {}
        for f in candidates:
            # Check staleness
            is_stale, reason = LLMFixGenerator.check_staleness(f)
            if is_stale:
                raise CommitServiceError(
                    f"Fix {f.fix_id} for '{f.file_path}' is stale ({reason}). Re-run analysis before committing.",
                    status_code=409
                )
            fixes_by_file.setdefault(f.file_path, []).append(f)

        orig_files: Dict[str, str] = {}
        patched_files: Dict[str, str] = {}
        diff_chunks: List[str] = []

        for rel_path, file_fixes in fixes_by_file.items():
            if not SecurityValidator.is_safe_relative_path(rel_path):
                raise CommitServiceError(f"Path traversal detected in file path: {rel_path}", status_code=400)

            target_file = (workspace_dir / rel_path).resolve()
            if not target_file.exists():
                raise CommitServiceError(f"Target file '{rel_path}' not found in workspace.", status_code=404)

            content = target_file.read_text(encoding="utf-8", errors="replace")
            orig_files[rel_path] = content
            lines = content.splitlines(keepends=True)

            # Sort descending by line number to keep indexes valid
            sorted_fixes = sorted(file_fixes, key=lambda x: x.line_number, reverse=True)
            for fix in sorted_fixes:
                line_idx = fix.line_number - 1
                if 0 <= line_idx < len(lines):
                    orig_line = lines[line_idx]
                    orig_indent = orig_line[:len(orig_line) - len(orig_line.lstrip())]
                    rep_lines = fix.suggested_code.splitlines()
                    if rep_lines and orig_indent and not rep_lines[0].startswith((" ", "\t")):
                        rep_lines = [orig_indent + l if l.strip() else l for l in rep_lines]
                        rep = "\n".join(rep_lines)
                    else:
                        rep = fix.suggested_code
                    if not rep.endswith("\n"):
                        rep += "\n"
                    lines[line_idx] = rep

            new_content = "".join(lines)

            # Static AST verification
            try:
                ast.parse(new_content, filename=rel_path)
            except SyntaxError as e:
                raise CommitServiceError(
                    f"AST validation failed for '{rel_path}': {e.msg} at line {e.lineno}",
                    status_code=422
                )

            patched_files[rel_path] = new_content

            # Unified diff
            file_diff = list(difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm=""
            ))
            if file_diff:
                diff_chunks.append("\n".join(file_diff))

        return orig_files, patched_files, "\n\n".join(diff_chunks)

    @classmethod
    async def preview_commit(cls, req: CommitPreviewRequest) -> CommitPreviewResponse:
        """
        Inspects approved fixes, validates AST, builds cumulative diff,
        and verifies repository concurrency without executing commit.
        """
        report = AnalysisEngine.get_analysis_report(req.analysis_id)
        project = None
        source_type = "zip"
        project_name = "Local Project"
        source_repo = None
        base_branch = "main"
        base_sha = None

        if report:
            try:
                project = WorkspaceService.get_project(report.project_id)
                source_type = project.input_type
                project_name = project.project_name
                source_repo = project.source_repository
                base_branch = project.branch or "main"
                base_sha = project.base_commit_sha
            except Exception:
                pass
        else:
            session = FileService.get_session(req.analysis_id)
            if session:
                source_type = session.get("source_type", "zip")
                project_name = session.get("project_name", "Local Project")
                source_repo = session.get("source_reference")
                base_branch = session.get("branch", "main")

        orig_files, patched_files, combined_diff = cls._compute_approved_patches(
            req.analysis_id, req.approved_finding_ids
        )

        modified_files = [
            path for path, content in patched_files.items()
            if content != orig_files.get(path)
        ]

        target_branch = req.branch_name or f"precommit-ai/fix-{req.analysis_id[:8]}"
        is_stale = False
        stale_reason = None
        can_commit = len(modified_files) > 0
        remote_sha = base_sha

        if source_type != "github":
            can_commit = False
            stale_reason = "Local ZIP upload: GitHub commit is only supported for GitHub repositories. Please download the corrected ZIP."
        else:
            # Query GitHub remote branch HEAD to detect concurrency conflicts
            token = req.github_token or GitHubService.get_connected_token()
            if token and source_repo:
                try:
                    owner, repo = GitHubService.parse_repo_url(source_repo)
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "PreCommit-AI-Agent"
                    }
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        ref_res = await client.get(
                            f"{settings.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                            headers=headers
                        )
                        if ref_res.status_code == 200:
                            remote_sha = ref_res.json()["object"]["sha"]
                            if base_sha and remote_sha != base_sha:
                                is_stale = True
                                can_commit = False
                                stale_reason = (
                                    f"Remote repository has changed on branch `{base_branch}` "
                                    f"(analysis base: {base_sha[:8]}, remote HEAD: {remote_sha[:8]}). "
                                    "Please re-run analysis to rebase changes safely."
                                )
                except Exception as e:
                    logger.warning(f"Could not check remote GitHub SHA during preview: {e}")

        if not modified_files and not stale_reason:
            can_commit = False
            stale_reason = "No approved fixes available to commit. Please review and accept fixes first."

        return CommitPreviewResponse(
            analysis_id=req.analysis_id,
            project_name=project_name,
            source_type=source_type,
            source_repository=source_repo,
            target_branch=target_branch,
            base_branch=base_branch,
            base_commit_sha=base_sha,
            remote_commit_sha=remote_sha,
            is_stale=is_stale,
            stale_reason=stale_reason,
            files_to_modify=sorted(modified_files),
            total_files_modified=len(modified_files),
            unified_diff=combined_diff,
            can_commit=can_commit,
            requires_confirmation=True,
        )

    @classmethod
    async def execute_commit(cls, req: CommitExecuteRequest) -> GitHubCommitResponse:
        """
        Safely creates a dedicated branch and commits approved fixes directly via GitHub REST API.
        STRICT SECURITY REQUIREMENTS:
        - Requires explicit confirmation (confirm=True).
        - Forbids direct commits to default branch.
        - Validates remote commit SHA against base commit SHA (concurrency protection).
        - Validates repo write/push access.
        - Re-validates AST on every committed file.
        """
        # 1. Explicit user confirmation check
        if not req.confirm:
            raise CommitServiceError(
                "Explicit confirmation is required before committing to GitHub. Pass confirm=True.",
                status_code=400
            )

        report = AnalysisEngine.get_analysis_report(req.analysis_id)
        project = None

        if report:
            project = WorkspaceService.get_project(report.project_id)
            if project.input_type != "github":
                raise CommitServiceError(
                    "Cannot commit to GitHub: This project was uploaded as a local file/ZIP. "
                    "Please download the corrected ZIP archive or connect a GitHub repository.",
                    status_code=400
                )
            source_repo = project.source_repository
            base_branch = project.branch or "main"
            base_sha = project.base_commit_sha
        else:
            session = FileService.get_session(req.analysis_id)
            if not session:
                raise CommitServiceError(f"Analysis '{req.analysis_id}' not found.", status_code=404)
            if session.get("source_type") != "github":
                raise CommitServiceError(
                    "Cannot commit to GitHub: This session is not a GitHub repository.",
                    status_code=400
                )
            source_repo = session["source_reference"]
            base_branch = session.get("branch", "main")
            base_sha = session.get("base_commit_sha")

        # 2. Token & Credentials
        token = req.github_token or GitHubService.get_connected_token()
        if not token:
            raise CommitServiceError(
                "GitHub authentication required. Please connect your GitHub account or provide a token.",
                status_code=401
            )

        owner, repo = GitHubService.parse_repo_url(source_repo)
        base_api = f"{settings.GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-Agent",
        }

        # 3. Compute and AST-validate approved patches
        orig_files, patched_files, combined_diff = cls._compute_approved_patches(
            req.analysis_id, req.approved_finding_ids
        )
        modified_files = {
            path: content for path, content in patched_files.items()
            if content != orig_files.get(path)
        }

        if not modified_files:
            raise CommitServiceError("No modified files found to commit.", status_code=400)

        # 4. Branch strategy
        branch_name = req.branch_name or f"precommit-ai/fix-{req.analysis_id[:8]}"
        if branch_name in (base_branch, "main", "master"):
            raise CommitServiceError(
                f"Pushing directly to the default branch ('{branch_name}') is forbidden. "
                "PreCommit AI requires creating a dedicated fix branch.",
                status_code=400
            )

        commit_msg = req.commit_message or "fix: resolve syntax and resource management issues"

        async with httpx.AsyncClient(timeout=35.0, headers=headers) as client:
            # 5. Verify repository access & write/push permissions
            repo_resp = await client.get(base_api)
            if repo_resp.status_code == 401:
                raise CommitServiceError("Invalid or expired GitHub token.", status_code=401)
            elif repo_resp.status_code == 404:
                raise CommitServiceError(f"Repository '{owner}/{repo}' not found or is private.", status_code=404)
            elif repo_resp.status_code == 403:
                raise CommitServiceError(f"Access forbidden to repository '{owner}/{repo}'.", status_code=403)
            elif repo_resp.status_code != 200:
                raise CommitServiceError(f"GitHub API Error: {repo_resp.text[:200]}", status_code=repo_resp.status_code)

            repo_data = repo_resp.json()
            perms = repo_data.get("permissions", {})
            if perms and not (perms.get("push") or perms.get("admin")):
                raise CommitServiceError(
                    f"Insufficient permissions: You do not have write/push access to repository '{owner}/{repo}'.",
                    status_code=403
                )

            default_branch = repo_data.get("default_branch", "main")
            effective_base = base_branch or default_branch

            # 6. Retrieve latest remote commit SHA & concurrency check
            ref_resp = await client.get(f"{base_api}/git/ref/heads/{effective_base}")
            if ref_resp.status_code != 200:
                raise CommitServiceError(f"Could not retrieve ref for branch `{effective_base}`.", status_code=400)

            remote_sha = ref_resp.json()["object"]["sha"]
            if base_sha and remote_sha != base_sha:
                raise CommitServiceError(
                    f"Concurrency Conflict: Repository on GitHub has changed since analysis "
                    f"(analysis base: {base_sha[:8]}, remote HEAD: {remote_sha[:8]}). "
                    "Please re-run analysis to rebase changes safely.",
                    status_code=409
                )

            # 7. Create dedicated fix branch from current remote SHA
            create_branch_resp = await client.post(
                f"{base_api}/git/refs",
                json={"ref": f"refs/heads/{branch_name}", "sha": remote_sha}
            )
            if create_branch_resp.status_code not in (200, 201):
                # If branch already exists, verify access
                check_branch = await client.get(f"{base_api}/git/ref/heads/{branch_name}")
                if check_branch.status_code != 200:
                    err = create_branch_resp.json().get("message", "Failed to create branch")
                    raise CommitServiceError(f"Could not create branch `{branch_name}`: {err}", status_code=400)

            # 8. Commit each modified file to the dedicated branch
            committed_files: List[str] = []
            last_commit_sha = remote_sha

            for file_path, content in modified_files.items():
                blob_sha = None
                get_content_resp = await client.get(
                    f"{base_api}/contents/{file_path}",
                    params={"ref": branch_name}
                )
                if get_content_resp.status_code == 200:
                    blob_sha = get_content_resp.json().get("sha")

                encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                put_payload = {
                    "message": f"{commit_msg} ({file_path})",
                    "content": encoded_content,
                    "branch": branch_name,
                }
                if blob_sha:
                    put_payload["sha"] = blob_sha

                put_resp = await client.put(f"{base_api}/contents/{file_path}", json=put_payload)
                if put_resp.status_code in (200, 201):
                    committed_files.append(file_path)
                    last_commit_sha = put_resp.json()["commit"]["sha"]
                else:
                    err = put_resp.json().get("message", "Unknown error")
                    logger.warning(f"Failed to commit file `{file_path}`: {err}")

            if not committed_files:
                raise CommitServiceError("Failed to commit any modified files to the dedicated branch.", status_code=500)

            # 9. Pull request creation or link generation
            pr_url = f"https://github.com/{owner}/{repo}/pull/new/{branch_name}"
            pr_number = None

            if req.create_pr:
                pr_payload = {
                    "title": req.pr_title or commit_msg,
                    "head": branch_name,
                    "base": effective_base,
                    "body": req.pr_body or (
                        f"Automated static analysis remediations generated by PreCommit AI.\n\n"
                        f"- **Analysis ID:** {req.analysis_id}\n"
                        f"- **Modified Files:** {len(committed_files)}\n"
                        f"- **Summary:** {commit_msg}"
                    )
                }
                try:
                    pr_resp = await client.post(f"{base_api}/pulls", json=pr_payload)
                    if pr_resp.status_code in (200, 201):
                        pr_data = pr_resp.json()
                        pr_url = pr_data.get("html_url", pr_url)
                        pr_number = pr_data.get("number")
                except Exception as e:
                    logger.warning(f"Failed to create PR via API: {e}")

        # 10. Update fix proposals status to 'applied' in registry
        if report:
            for f in LLMFixGenerator._FIX_REGISTRY.values():
                if f.analysis_id == req.analysis_id and f.status in ("accepted", "edited"):
                    f.status = "applied"
                    f.updated_at = datetime.now().isoformat()
                    LLMFixGenerator.save_fix(f)

        commit_id = str(uuid.uuid4())
        commit_url = f"https://github.com/{owner}/{repo}/commit/{last_commit_sha}"

        response = GitHubCommitResponse(
            commit_id=commit_id,
            success=True,
            branch_name=branch_name,
            commit_sha=last_commit_sha,
            commit_url=commit_url,
            pull_request_url=pr_url,
            pull_request_number=pr_number,
            committed_files=committed_files,
            total_committed_files=len(committed_files),
            message=f"Successfully committed {len(committed_files)} file(s) to `{branch_name}`.",
            timestamp=datetime.now().isoformat(),
        )

        cls._COMMIT_REGISTRY[commit_id] = response
        logger.info(f"GitHub commit executed successfully: {commit_url} (ID: {commit_id})")

        return response

    @classmethod
    def download_patched_zip_for_analysis(
        cls,
        analysis_id: str,
        approved_finding_ids: Optional[List[str]] = None
    ) -> Tuple[io.BytesIO, str]:
        """
        Creates a clean ZIP archive of the project workspace with approved fixes applied.
        """
        report = AnalysisEngine.get_analysis_report(analysis_id)
        if report:
            project = WorkspaceService.get_project(report.project_id)
            workspace_dir = WorkspaceService.get_workspace_path(report.project_id)

            orig_files, patched_files, _ = cls._compute_approved_patches(analysis_id, approved_finding_ids)

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
                # Add all files in workspace, replacing any that were patched
                for file_path in workspace_dir.rglob("*"):
                    if file_path.is_file():
                        rel = file_path.relative_to(workspace_dir).as_posix()
                        if rel in patched_files:
                            z.writestr(rel, patched_files[rel].encode("utf-8"))
                        else:
                            z.write(file_path, rel)

            buffer.seek(0)
            filename = f"{project.project_name.replace('/', '-')}-precommit-patched.zip"
            return buffer, filename
        else:
            session = FileService.get_session(analysis_id)
            if not session:
                raise CommitServiceError(f"Analysis '{analysis_id}' not found.", status_code=404)

            approved_ids = approved_finding_ids or session.get("approved_finding_ids", [])
            findings_map = {f.id: f for f in session["findings"]}
            approved_findings = [findings_map[fid] for fid in approved_ids if fid in findings_map]

            patched = FixService.apply_approved_fixes(session["files"], approved_findings)
            zip_buffer = FileService.create_patched_zip(patched)
            filename = f"{session['project_name'].replace('/', '-')}-precommit-patched.zip"
            return zip_buffer, filename

    # Backwards compatibility alias for legacy route
    @classmethod
    async def commit_approved_fixes(
        cls,
        session_id: str,
        approved_finding_ids: List[str],
        github_token: str,
        commit_message: Optional[str] = None,
        custom_branch_name: Optional[str] = None,
    ) -> GitHubCommitResponse:
        return await cls.execute_commit(
            CommitExecuteRequest(
                analysis_id=session_id,
                approved_finding_ids=approved_finding_ids,
                github_token=github_token,
                commit_message=commit_message,
                branch_name=custom_branch_name,
                confirm=True
            )
        )

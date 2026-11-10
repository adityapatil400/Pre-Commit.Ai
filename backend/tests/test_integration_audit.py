import ast
import io
import json
import os
import zipfile
import pytest
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.llm.ollama_client import OllamaClient
from backend.app.services.workspace_service import WorkspaceService
from backend.app.services.github_service import GitHubService

client = TestClient(app)

def create_sample_project_zip() -> bytes:
    """Creates an in-memory zip archive with valid, leaky, and syntax-broken files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # File 1: Resource leak (unclosed file)
        z.writestr(
            "app.py",
            "def read_data(path):\n"
            "    f = open(path, 'r')\n"
            "    data = f.read()\n"
            "    return data\n"
        )
        # File 2: Bug (mutable default argument)
        z.writestr(
            "utils.py",
            "def append_item(item, container=[]):\n"
            "    container.append(item)\n"
            "    return container\n"
        )
        # File 3: Syntax error
        z.writestr(
            "bad_syntax.py",
            "def broken_function(\n"
            "    print('syntax error missing closing paren')\n"
        )
    return buf.getvalue()

def create_malicious_code_zip() -> bytes:
    """Creates a zip with potentially harmful code that must NEVER be executed."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "malicious.py",
            "import os\n"
            "os.environ['PRECOMMIT_AUDIT_PWNED'] = 'COMPROMISED'\n"
            "def safe_func():\n"
            "    pass\n"
        )
    return buf.getvalue()


class TestCompleteLocalWorkflow:
    """
    Tests the complete end-to-end lifecycle for local projects (Steps 1 through 12):
    Upload -> Syntax Check -> AST Static Analysis -> Report -> LLM Fix -> Review (Diff/Edit/Approve/Reject) -> Apply -> ZIP Download -> Cleanup
    """

    def test_full_local_zip_workflow(self, monkeypatch):
        # Step 1: Upload ZIP Project
        zip_bytes = create_sample_project_zip()
        upload_resp = client.post(
            "/api/v1/upload",
            files={"file": ("my_project.zip", zip_bytes, "application/zip")}
        )
        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        project_id = upload_data["project_id"]
        assert upload_data["total_files"] == 3
        assert "app.py" in upload_data["python_files"]
        assert "bad_syntax.py" in upload_data["python_files"]

        # Step 4 & 5: Syntax Validation across all files
        syntax_resp = client.post(
            "/api/v1/analysis/syntax",
            json={"project_id": project_id}
        )
        assert syntax_resp.status_code == 200
        syntax_data = syntax_resp.json()
        assert syntax_data["total_python_files"] == 3
        assert syntax_data["files_with_syntax_errors_count"] == 1
        assert syntax_data["successfully_parsed_count"] == 2
        assert "bad_syntax.py" in [e["file_path"] for e in syntax_data["syntax_errors"]]

        # Step 6 & 7: Run Full AST Static Analysis Engine
        analysis_resp = client.post(
            "/api/v1/analysis/run",
            json={"project_id": project_id}
        )
        assert analysis_resp.status_code == 200
        analysis_data = analysis_resp.json()
        analysis_id = analysis_data["analysis_id"]
        assert analysis_data["metrics"]["syntax_errors"] == 1
        assert analysis_data["metrics"]["resource_leak_warnings"] >= 1
        assert analysis_data["metrics"]["bug_warnings"] >= 1

        # Check retrieval of analysis report
        get_report_resp = client.get(f"/api/v1/analysis/{analysis_id}")
        assert get_report_resp.status_code == 200
        assert get_report_resp.json()["analysis_id"] == analysis_id

        # Step 8: Generate AI Fix using Ollama (Mocked LLM)
        mock_fix_json = json.dumps({
            "explanation": "Replaced raw open() with a 'with open()' context manager to ensure automatic closure.",
            "suggested_code": "    with open(path, 'r') as f:\n        data = f.read()\n        return data"
        })

        async def mock_generate(self, *args, **kwargs):
            return mock_fix_json

        monkeypatch.setattr(OllamaClient, "generate", mock_generate)

        # Find the resource leak finding ID
        resource_finding = next(f for f in analysis_data["findings"] if f["category"] == "resource_leak")
        fix_resp = client.post(
            "/api/v1/fixes/generate",
            json={"analysis_id": analysis_id, "finding_id": resource_finding["id"]}
        )
        assert fix_resp.status_code == 200
        fix_data = fix_resp.json()
        fix_id = fix_data["fix_id"]
        assert fix_data["status"] == "pending_review"
        assert "with open" in fix_data["suggested_code"]

        # Step 9: View Diff between original and suggested code
        diff_resp = client.get(f"/api/v1/fixes/{fix_id}/diff")
        assert diff_resp.status_code == 200
        diff_data = diff_resp.json()
        assert diff_data["fix_id"] == fix_id
        assert "--- a/app.py" in diff_data["diff"]
        assert "+++ b/app.py" in diff_data["diff"]

        # Step 10: Review Actions:
        # A. Try editing with invalid Python syntax -> expect 422
        bad_edit_resp = client.post(
            f"/api/v1/fixes/{fix_id}/edit",
            json={"suggested_code": "    with open(path: broken syntax"}
        )
        assert bad_edit_resp.status_code == 422

        # B. Edit with valid Python code
        valid_edit_code = "    with open(path, 'r', encoding='utf-8') as f:\n        return f.read()"
        edit_resp = client.post(
            f"/api/v1/fixes/{fix_id}/edit",
            json={"suggested_code": valid_edit_code, "explanation": "Added explicit utf-8 encoding."}
        )
        assert edit_resp.status_code == 200
        assert edit_resp.json()["status"] == "edited"

        # C. Approve Fix
        approve_resp = client.post(f"/api/v1/fixes/{fix_id}/approve")
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "accepted"

        # Step 11: Apply Approved Fixes
        # A. Attempt to apply without confirm -> expect 400
        no_confirm_resp = client.post(
            "/api/v1/fixes/apply-approved",
            json={"analysis_id": analysis_id, "fix_ids": [fix_id], "confirm": False}
        )
        assert no_confirm_resp.status_code == 400

        # B. Apply with explicit confirm
        apply_resp = client.post(
            "/api/v1/fixes/apply-approved",
            json={"analysis_id": analysis_id, "fix_ids": [fix_id], "confirm": True}
        )
        assert apply_resp.status_code == 200
        apply_data = apply_resp.json()
        assert apply_data["success"] is True
        assert "app.py" in apply_data["modified_files"]

        # Verify that the file on disk was modified and AST compiles cleanly
        workspace_dir = WorkspaceService.get_workspace_path(project_id)
        patched_app_code = (workspace_dir / "app.py").read_text()
        assert "encoding='utf-8'" in patched_app_code
        ast.parse(patched_app_code)

        # Step 12: Download Patched ZIP archive
        zip_download_resp = client.get(f"/api/v1/commits/download-zip/{analysis_id}")
        assert zip_download_resp.status_code == 200
        assert zip_download_resp.headers["content-type"] == "application/zip"

        # Validate streamed ZIP contents in-memory
        downloaded_zip = zipfile.ZipFile(io.BytesIO(zip_download_resp.content))
        zip_namelist = downloaded_zip.namelist()
        assert "app.py" in zip_namelist
        zip_app_code = downloaded_zip.read("app.py").decode("utf-8")
        assert "encoding='utf-8'" in zip_app_code

        # Clean up project workspace
        cleanup_resp = client.delete(f"/api/v1/projects/{project_id}")
        assert cleanup_resp.status_code == 200
        assert not workspace_dir.exists()


class TestCompleteGitHubWorkflow:
    """
    Tests the complete end-to-end GitHub workflow (Steps 2, 3, 8, 12, 13):
    Account Connect -> Repo Listing -> Clone -> Analysis -> Fix Approval -> Preview Commit -> Commit Execution with Branch & PR -> Commit Record
    """

    def test_full_github_workflow(self, monkeypatch):
        # Step 1: Connect GitHub Account
        async def mock_github_user_handler(request: httpx.Request, *args, **kwargs):
            if request.url.path == "/user":
                return httpx.Response(
                    200,
                    json={
                        "login": "octocat",
                        "name": "The Octocat",
                        "avatar_url": "https://github.com/images/error/octocat_happy.gif",
                        "html_url": "https://github.com/octocat",
                    },
                    headers={"X-OAuth-Scopes": "repo, workflow"}
                )
            return httpx.Response(404)

        monkeypatch.setattr(
            httpx.AsyncClient, "send",
            lambda self, req, *args, **kwargs: mock_github_user_handler(req, *args, **kwargs)
        )

        connect_resp = client.post("/api/v1/github/connect", json={"token": "ghp_test_token_12345"})
        assert connect_resp.status_code == 200
        connect_data = connect_resp.json()
        assert connect_data["username"] == "octocat"
        assert connect_data["connected"] is True

        # Step 2: List accessible repositories
        async def mock_repos_handler(request: httpx.Request, *args, **kwargs):
            if request.url.path == "/user/repos":
                return httpx.Response(200, json=[{
                    "id": 12345,
                    "name": "sample-repo",
                    "full_name": "octocat/sample-repo",
                    "owner": {"login": "octocat"},
                    "html_url": "https://github.com/octocat/sample-repo",
                    "default_branch": "main",
                    "permissions": {"push": True, "admin": True},
                    "private": False,
                }])
            return httpx.Response(404)

        monkeypatch.setattr(
            httpx.AsyncClient, "send",
            lambda self, req, *args, **kwargs: mock_repos_handler(req, *args, **kwargs)
        )

        repos_resp = client.get("/api/v1/github/repositories")
        assert repos_resp.status_code == 200
        assert repos_resp.json()["total"] == 1
        assert repos_resp.json()["repositories"][0]["full_name"] == "octocat/sample-repo"

        # Step 3: Clone GitHub repository into isolated workspace (Mocked API)
        repo_zip_buf = io.BytesIO()
        with zipfile.ZipFile(repo_zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(
                "octocat-sample-repo-1234567/server.py",
                "def start_server():\n"
                "    f = open('config.json', 'r')\n"
                "    return f.read()\n"
            )
        repo_zip_bytes = repo_zip_buf.getvalue()

        async def mock_clone_handler(request: httpx.Request, *args, **kwargs):
            path = request.url.path
            if path == "/repos/octocat/sample-repo":
                return httpx.Response(200, json={"default_branch": "main", "private": False})
            if path == "/repos/octocat/sample-repo/commits/main":
                return httpx.Response(200, json={"sha": "sha_base_1111111111111111111111111111111111111111"})
            if "/zipball" in path:
                return httpx.Response(200, content=repo_zip_bytes, headers={"Content-Type": "application/zip"})
            return httpx.Response(404)

        monkeypatch.setattr(
            httpx.AsyncClient, "send",
            lambda self, req, *args, **kwargs: mock_clone_handler(req, *args, **kwargs)
        )

        clone_resp = client.post(
            "/api/v1/github/clone",
            json={"repo_url": "https://github.com/octocat/sample-repo", "github_token": "ghp_test_token_12345"}
        )
        assert clone_resp.status_code == 201
        clone_data = clone_resp.json()
        project_id = clone_data["project_id"]
        assert clone_data["base_commit_sha"] == "sha_base_1111111111111111111111111111111111111111"

        # Step 4: Run Static Analysis on cloned repo
        analysis_resp = client.post("/api/v1/analysis/run", json={"project_id": project_id})
        assert analysis_resp.status_code == 200
        analysis_data = analysis_resp.json()
        analysis_id = analysis_data["analysis_id"]
        assert analysis_data["metrics"]["resource_leak_warnings"] >= 1

        # Step 5: Generate and Approve Fix
        finding = analysis_data["findings"][0]
        mock_fix_json = json.dumps({
            "explanation": "Use context manager for file handling.",
            "suggested_code": "    with open('config.json', 'r') as f:\n        return f.read()"
        })

        async def mock_gen(self, *args, **kwargs):
            return mock_fix_json

        monkeypatch.setattr(OllamaClient, "generate", mock_gen)

        fix_resp = client.post("/api/v1/fixes/generate", json={"analysis_id": analysis_id, "finding_id": finding["id"]})
        fix_id = fix_resp.json()["fix_id"]

        # Approve fix
        approve_resp = client.post(f"/api/v1/fixes/{fix_id}/approve")
        assert approve_resp.status_code == 200

        # Step 6: Commit Preview (Step 8 preview)
        async def mock_preview_handler(request: httpx.Request, *args, **kwargs):
            if request.url.path == "/repos/octocat/sample-repo/commits/main":
                return httpx.Response(200, json={"sha": "sha_base_1111111111111111111111111111111111111111"})
            return httpx.Response(404)

        monkeypatch.setattr(
            httpx.AsyncClient, "send",
            lambda self, req, *args, **kwargs: mock_preview_handler(req, *args, **kwargs)
        )

        preview_resp = client.post(
            "/api/v1/commits/preview",
            json={"analysis_id": analysis_id, "approved_finding_ids": [fix_id]}
        )
        assert preview_resp.status_code == 200
        preview_data = preview_resp.json()
        assert preview_data["can_commit"] is True
        assert preview_data["total_files_modified"] == 1
        assert "server.py" in preview_data["files_to_modify"]
        assert preview_data["target_branch"].startswith("precommit-ai/fix-")

        # Step 7: Commit Execution
        async def mock_commit_api_router(request: httpx.Request, *args, **kwargs):
            url_str = str(request.url)
            path = request.url.path
            method = request.method

            if method == "GET" and path == "/repos/octocat/sample-repo":
                return httpx.Response(200, json={"default_branch": "main", "permissions": {"push": True, "admin": True}})
            if method == "GET" and "/git/ref/heads/main" in path:
                return httpx.Response(200, json={"object": {"sha": "sha_base_1111111111111111111111111111111111111111"}})
            if method == "POST" and "/git/refs" in path:
                return httpx.Response(201, json={"ref": "refs/heads/precommit-ai/fix-branch"})
            if method == "GET" and "/contents/server.py" in path:
                return httpx.Response(200, json={"sha": "blob_server_sha_123"})
            if method == "PUT" and "/contents/server.py" in path:
                return httpx.Response(200, json={"commit": {"sha": "commit_sha_789"}})
            if method == "POST" and "/pulls" in path:
                return httpx.Response(201, json={
                    "html_url": "https://github.com/octocat/sample-repo/pull/42",
                    "number": 42
                })
            return httpx.Response(404, json={"detail": f"Not found: {url_str}"})

        monkeypatch.setattr(
            httpx.AsyncClient, "send",
            lambda self, req, *args, **kwargs: mock_commit_api_router(req, *args, **kwargs)
        )

        commit_resp = client.post(
            "/api/v1/commits/execute",
            json={
                "analysis_id": analysis_id,
                "approved_finding_ids": [fix_id],
                "github_token": "ghp_test_token_12345",
                "commit_message": "fix: apply context manager to config read",
                "confirm": True,
                "create_pr": True
            }
        )
        assert commit_resp.status_code == 200
        commit_data = commit_resp.json()
        assert commit_data["success"] is True
        assert commit_data["commit_sha"] == "commit_sha_789"
        assert commit_data["pull_request_number"] == 42
        assert "server.py" in commit_data["committed_files"]

        # Step 8: Query Commit Record by commit_id
        commit_id = commit_data["commit_id"]
        get_commit_resp = client.get(f"/api/v1/commits/{commit_id}")
        assert get_commit_resp.status_code == 200
        assert get_commit_resp.json()["commit_id"] == commit_id

        # Clean up
        WorkspaceService.cleanup_workspace(project_id)


class TestSecurityAuditsAndInvariants:
    """
    Audits security invariant enforcement:
    - Zero code execution
    - Zip Slip path traversal prevention
    - Stale commit SHA race condition prevention
    - Permission enforcement
    """

    def test_zero_code_execution_invariant(self):
        """Ensures that code contained in uploaded files is NEVER executed."""
        if "PRECOMMIT_AUDIT_PWNED" in os.environ:
            del os.environ["PRECOMMIT_AUDIT_PWNED"]

        zip_bytes = create_malicious_code_zip()
        upload_resp = client.post(
            "/api/v1/upload",
            files={"file": ("malicious.zip", zip_bytes, "application/zip")}
        )
        assert upload_resp.status_code == 201
        project_id = upload_resp.json()["project_id"]

        # Run syntax and static analysis
        syntax_resp = client.post("/api/v1/analysis/syntax", json={"project_id": project_id})
        assert syntax_resp.status_code == 200

        analysis_resp = client.post("/api/v1/analysis/run", json={"project_id": project_id})
        assert analysis_resp.status_code == 200

        # Verify environment variable was NEVER set
        assert "PRECOMMIT_AUDIT_PWNED" not in os.environ, "SECURITY VIOLATION: Uploaded code was executed!"

        WorkspaceService.cleanup_workspace(project_id)

    def test_zip_slip_path_traversal_blocked(self):
        """Verifies Zip-Slip archive path traversal attacks are rejected and cannot escape workspace."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("../../etc/cron.d/exploit.py", "print('exploit')")
            z.writestr("safe_module.py", "print('safe')")
        
        resp = client.post(
            "/api/v1/upload",
            files={"file": ("slip.zip", buf.getvalue(), "application/zip")}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "../../etc/cron.d/exploit.py" not in data["python_files"]
        assert "safe_module.py" in data["python_files"]

        # Verify filesystem does not contain the escaped path
        workspace_dir = WorkspaceService.get_workspace_path(data["project_id"])
        assert not (workspace_dir / "../../etc/cron.d/exploit.py").resolve().exists()

        WorkspaceService.cleanup_workspace(data["project_id"])

    def test_stale_commit_sha_rejection(self, monkeypatch):
        """Verifies that commits are halted if the remote repo has moved since analysis."""
        # Setup mock project with base SHA
        project = WorkspaceService.create_workspace_from_single_file(
            "main.py",
            b"def run():\n    f = open('test.txt')\n    return f.read()\n"
        )
        project.input_type = "github"
        project.source_repository = "https://github.com/octocat/sample-repo"
        project.base_commit_sha = "sha_initial_111111"
        WorkspaceService.save_project(project)

        analysis = AnalysisEngine.run_project_analysis(project.project_id)

        # Generate and approve a fix so there are modified files to commit
        finding = analysis.findings[0]
        async def mock_gen(self, *args, **kwargs):
            return json.dumps({
                "explanation": "Use with open",
                "suggested_code": "    with open('test.txt') as f:\n        return f.read()"
            })
        monkeypatch.setattr(OllamaClient, "generate", mock_gen)

        fix_resp = client.post("/api/v1/fixes/generate", json={"analysis_id": analysis.analysis_id, "finding_id": finding.id})
        fix_id = fix_resp.json()["fix_id"]
        client.post(f"/api/v1/fixes/{fix_id}/approve")

        # Mock remote repo having moved to a new commit SHA
        async def mock_stale_handler(request: httpx.Request, *args, **kwargs):
            if request.url.path == "/repos/octocat/sample-repo" and request.method == "GET":
                return httpx.Response(200, json={"permissions": {"push": True}, "default_branch": "main"})
            if "/git/ref/heads/main" in request.url.path and request.method == "GET":
                # Remote has moved!
                return httpx.Response(200, json={"object": {"sha": "sha_remote_NEW_999999"}})
            return httpx.Response(404)

        monkeypatch.setattr(
            httpx.AsyncClient, "send",
            lambda self, req, *args, **kwargs: mock_stale_handler(req, *args, **kwargs)
        )

        commit_resp = client.post(
            "/api/v1/commits/execute",
            json={
                "analysis_id": analysis.analysis_id,
                "approved_finding_ids": [fix_id],
                "github_token": "ghp_test_token_12345",
                "confirm": True
            }
        )
        assert commit_resp.status_code == 409
        assert "concurrency conflict" in commit_resp.json()["detail"].lower()

        WorkspaceService.cleanup_workspace(project.project_id)

import io
import json
import zipfile
import pytest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.llm.ollama_client import OllamaClient
from backend.app.services.workspace_service import WorkspaceService
from backend.app.services.github_service import GitHubService

client = TestClient(app)

def create_zip_bytes(files_dict: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for file_path, content in files_dict.items():
            if isinstance(content, bytes):
                z.writestr(file_path, content)
            else:
                z.writestr(file_path, content.encode("utf-8"))
    return buffer.getvalue()

# ---------------------------------------------------------------------------
# 1. GitHub Connect & Repository Tests
# ---------------------------------------------------------------------------

def test_github_connect_success():
    mock_resp = httpx.Response(
        status_code=200,
        json={"login": "octocat", "name": "The Octocat", "avatar_url": "https://avatars.githubusercontent.com/u/583234"},
        headers={"x-oauth-scopes": "repo, read:user"}
    )
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = client.post("/api/v1/github/connect", json={"token": "ghp_validToken123456789"})
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["username"] == "octocat"
        assert "repo" in data["scopes"]

def test_github_connect_invalid_token():
    mock_resp = httpx.Response(
        status_code=401,
        json={"message": "Bad credentials"}
    )
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = client.post("/api/v1/github/connect", json={"token": "ghp_invalidToken"})
        assert res.status_code == 401
        assert "Invalid or expired" in res.json()["detail"]

def test_get_github_repositories():
    mock_repos = [
        {
            "id": 12345,
            "name": "my-python-app",
            "full_name": "octocat/my-python-app",
            "owner": {"login": "octocat"},
            "html_url": "https://github.com/octocat/my-python-app",
            "default_branch": "main",
            "private": False,
            "permissions": {"admin": True, "push": True, "pull": True}
        },
        {
            "id": 67890,
            "name": "read-only-repo",
            "full_name": "other/read-only-repo",
            "owner": {"login": "other"},
            "html_url": "https://github.com/other/read-only-repo",
            "default_branch": "main",
            "private": True,
            "permissions": {"admin": False, "push": False, "pull": True}
        }
    ]
    mock_resp = httpx.Response(status_code=200, json=mock_repos)
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = client.get("/api/v1/github/repositories?token=ghp_testToken")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["repositories"][0]["can_push"] is True
        assert data["repositories"][1]["can_push"] is False

# ---------------------------------------------------------------------------
# 2. Local ZIP Project Workflow Tests
# ---------------------------------------------------------------------------

def test_local_zip_download_workflow():
    code_reader = "def process():\n    f = open('data.txt', 'r')\n    return f.read()\n"
    zip_bytes = create_zip_bytes({"reader.py": code_reader})

    up_res = client.post("/api/v1/upload", files={"file": ("project.zip", io.BytesIO(zip_bytes), "application/zip")})
    assert up_res.status_code == 201
    project_id = up_res.json()["project_id"]

    an_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    assert an_res.status_code == 200
    report = an_res.json()
    analysis_id = report["analysis_id"]

    # Generate fix
    llm_resp = json.dumps({
        "explanation": "Use with open() context manager.",
        "suggested_code": "    with open('data.txt', 'r') as f:\n        return f.read()"
    })
    async def mock_gen(self, prompt="", **kwargs):
        return llm_resp

    with patch.object(OllamaClient, "generate", new=mock_gen):
        fix_res = client.post("/api/v1/fixes/generate", json={"analysis_id": analysis_id})
        assert fix_res.status_code == 200
        fix = fix_res.json()

    # Approve fix
    client.post(f"/api/v1/fixes/{fix['fix_id']}/approve")

    # Download patched ZIP
    dl_res = client.get(f"/api/v1/commits/download-zip/{analysis_id}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"

    # Inspect zip contents
    zip_buf = io.BytesIO(dl_res.content)
    with zipfile.ZipFile(zip_buf, "r") as z:
        assert "reader.py" in z.namelist()
        patched_code = z.read("reader.py").decode("utf-8")
        assert "with open('data.txt', 'r') as f:" in patched_code

    # Attempting to commit a local ZIP project to GitHub without a repo should be rejected
    commit_res = client.post("/api/v1/commits/execute", json={
        "analysis_id": analysis_id,
        "github_token": "ghp_dummy",
        "confirm": True
    })
    assert commit_res.status_code == 400
    assert "Cannot commit to GitHub: This project was uploaded as a local file/ZIP" in commit_res.json()["detail"]

    WorkspaceService.cleanup_workspace(project_id)

# ---------------------------------------------------------------------------
# 3. GitHub Project Commit Workflow Fixture & Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def github_project_with_fixes():
    """
    Sets up a GitHub project with 2 Python files:
    - reader.py (RESOURCE001)
    - calc.py (BUG001)
    Generates fixes for both.
    """
    code_reader = "def process():\n    f = open('data.txt', 'r')\n    return f.read()\n"
    code_calc = "def compute(items=[]):\n    return sum(items)\n"

    zip_bytes = create_zip_bytes({
        "reader.py": code_reader,
        "calc.py": code_calc
    })

    # Create workspace directly as input_type='github'
    proj = WorkspaceService.create_workspace_from_zip(
        filename="my-repo.zip",
        zip_bytes=zip_bytes,
        project_name="octocat/my-repo",
        strip_single_root=False,
        input_type="github",
        source_repository="https://github.com/octocat/my-repo",
        branch="main",
        base_commit_sha="111122223333444455556666777788889999aaaa"
    )
    project_id = proj.project_id

    an_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    assert an_res.status_code == 200
    report = an_res.json()
    analysis_id = report["analysis_id"]

    # Generate fixes
    f_res = next(f for f in report["findings"] if f["rule_id"] == "RESOURCE001")
    f_bug = next(f for f in report["findings"] if f["rule_id"] == "BUG001")

    llm_resp_1 = json.dumps({
        "explanation": "Use with open() context manager.",
        "suggested_code": "    with open('data.txt', 'r') as f:\n        return f.read()"
    })
    llm_resp_2 = json.dumps({
        "explanation": "Replace mutable default argument with None sentinel.",
        "suggested_code": "def compute(items=None):\n    if items is None:\n        items = []\n    return sum(items)"
    })

    async def mock_gen(self, prompt="", **kwargs):
        if "RESOURCE001" in prompt:
            return llm_resp_1
        return llm_resp_2

    with patch.object(OllamaClient, "generate", new=mock_gen):
        fix_1 = client.post("/api/v1/fixes/generate", json={"analysis_id": analysis_id, "finding_id": f_res["id"]}).json()
        fix_2 = client.post("/api/v1/fixes/generate", json={"analysis_id": analysis_id, "finding_id": f_bug["id"]}).json()

    yield project_id, analysis_id, fix_1, fix_2

    WorkspaceService.cleanup_workspace(project_id)

def test_commit_preview_workflow(github_project_with_fixes):
    project_id, analysis_id, fix_1, fix_2 = github_project_with_fixes

    # Approve fix 1 only
    client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")

    mock_ref_resp = httpx.Response(
        status_code=200,
        json={"object": {"sha": "111122223333444455556666777788889999aaaa"}}
    )
    with patch("httpx.AsyncClient.get", return_value=mock_ref_resp):
        res = client.post("/api/v1/commits/preview", json={
            "analysis_id": analysis_id,
            "github_token": "ghp_mockToken"
        })
        assert res.status_code == 200
        preview = res.json()
        assert preview["can_commit"] is True
        assert preview["is_stale"] is False
        assert preview["total_files_modified"] == 1
        assert "reader.py" in preview["files_to_modify"]
        assert "calc.py" not in preview["files_to_modify"] # Unapproved fix not in preview
        assert "with open('data.txt', 'r') as f:" in preview["unified_diff"]
        assert preview["requires_confirmation"] is True

def test_commit_execution_requires_confirmation(github_project_with_fixes):
    project_id, analysis_id, fix_1, fix_2 = github_project_with_fixes

    client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")

    # Call with confirm=False -> Expect 400
    res = client.post("/api/v1/commits/execute", json={
        "analysis_id": analysis_id,
        "github_token": "ghp_mockToken",
        "confirm": False
    })
    assert res.status_code == 400
    assert "Explicit confirmation is required" in res.json()["detail"]

def test_commit_execution_forbids_default_branch(github_project_with_fixes):
    project_id, analysis_id, fix_1, fix_2 = github_project_with_fixes

    client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")

    # Call with branch_name="main" -> Expect 400 forbidden direct push to default branch
    res = client.post("/api/v1/commits/execute", json={
        "analysis_id": analysis_id,
        "github_token": "ghp_mockToken",
        "branch_name": "main",
        "confirm": True
    })
    assert res.status_code == 400
    assert "forbidden" in res.json()["detail"].lower()

def test_commit_execution_stale_sha_conflict(github_project_with_fixes):
    project_id, analysis_id, fix_1, fix_2 = github_project_with_fixes

    client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")

    # Mock GitHub API where remote SHA differs from base SHA (concurrent commit on GitHub)
    async def mock_handler(request: httpx.Request, *args, **kwargs):
        url = str(request.url)
        if "/repos/octocat/my-repo" in url and "/git/ref/heads/main" in url:
            return httpx.Response(status_code=200, json={"object": {"sha": "DIFFERENT_REMOTE_SHA_9999"}})
        elif "/repos/octocat/my-repo" in url:
            return httpx.Response(status_code=200, json={"default_branch": "main", "permissions": {"push": True}})
        return httpx.Response(status_code=404)

    with patch("httpx.AsyncClient.send", side_effect=mock_handler):
        res = client.post("/api/v1/commits/execute", json={
            "analysis_id": analysis_id,
            "github_token": "ghp_mockToken",
            "confirm": True
        })
        assert res.status_code == 409
        assert "Concurrency Conflict" in res.json()["detail"]

def test_commit_execution_permission_denied(github_project_with_fixes):
    project_id, analysis_id, fix_1, fix_2 = github_project_with_fixes

    client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")

    # Mock user having read-only (no push) permissions
    async def mock_handler(request: httpx.Request, *args, **kwargs):
        url = str(request.url)
        if "/repos/octocat/my-repo" in url and "/git" not in url:
            return httpx.Response(status_code=200, json={"default_branch": "main", "permissions": {"push": False, "admin": False}})
        return httpx.Response(status_code=404)

    with patch("httpx.AsyncClient.send", side_effect=mock_handler):
        res = client.post("/api/v1/commits/execute", json={
            "analysis_id": analysis_id,
            "github_token": "ghp_mockToken",
            "confirm": True
        })
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]

def test_commit_execution_success_with_pr_link(github_project_with_fixes):
    project_id, analysis_id, fix_1, fix_2 = github_project_with_fixes

    # 1. Accept fix 1, reject fix 2
    client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")
    client.post(f"/api/v1/fixes/{fix_2['fix_id']}/reject")

    async def mock_github_router(request: httpx.Request, *args, **kwargs):
        url = str(request.url)
        method = request.method

        if method == "GET" and url.endswith("/repos/octocat/my-repo"):
            return httpx.Response(status_code=200, json={
                "default_branch": "main",
                "permissions": {"push": True, "admin": False}
            })
        elif method == "GET" and "/git/ref/heads/main" in url:
            return httpx.Response(status_code=200, json={
                "object": {"sha": "111122223333444455556666777788889999aaaa"}
            })
        elif method == "POST" and "/git/refs" in url:
            return httpx.Response(status_code=201, json={"ref": "refs/heads/precommit-ai/fix-test"})
        elif method == "GET" and "/contents/reader.py" in url:
            return httpx.Response(status_code=200, json={"sha": "blob_reader_sha_123"})
        elif method == "PUT" and "/contents/reader.py" in url:
            return httpx.Response(status_code=200, json={
                "commit": {"sha": "new_commit_sha_9876543210"}
            })
        elif method == "POST" and "/pulls" in url:
            return httpx.Response(status_code=201, json={
                "html_url": "https://github.com/octocat/my-repo/pull/42",
                "number": 42
            })
        return httpx.Response(status_code=404)

    with patch("httpx.AsyncClient.send", side_effect=mock_github_router):
        res = client.post("/api/v1/commits/execute", json={
            "analysis_id": analysis_id,
            "github_token": "ghp_validToken123",
            "commit_message": "fix: resolve syntax and resource management issues",
            "confirm": True,
            "create_pr": True
        })
        assert res.status_code == 200
        data = res.json()

        assert data["success"] is True
        assert "precommit-ai/fix-" in data["branch_name"]
        assert data["commit_sha"] == "new_commit_sha_9876543210"
        assert "https://github.com/octocat/my-repo/commit/new_commit_sha_9876543210" in data["commit_url"]
        assert data["pull_request_url"] == "https://github.com/octocat/my-repo/pull/42"
        assert data["pull_request_number"] == 42
        assert "reader.py" in data["committed_files"]
        assert "calc.py" not in data["committed_files"] # Rejected fix was NOT committed!

        # Verify queryable via GET /api/v1/commits/{commit_id}
        commit_id = data["commit_id"]
        get_res = client.get(f"/api/v1/commits/{commit_id}")
        assert get_res.status_code == 200
        assert get_res.json()["commit_sha"] == data["commit_sha"]

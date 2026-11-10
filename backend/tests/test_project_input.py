import io
import os
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from backend.app.main import app
from backend.app.services.workspace_service import WorkspaceService
from backend.app.config import settings

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers for creating test in-memory archives
# ---------------------------------------------------------------------------
def create_zip_bytes(files_dict: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for file_path, content in files_dict.items():
            z.writestr(file_path, content)
    return buffer.getvalue()

# ---------------------------------------------------------------------------
# Option A Tests: Individual Python Files
# ---------------------------------------------------------------------------
def test_upload_valid_single_python_file():
    code = b"def greet(name: str) -> str:\n    return f'Hello, {name}'\n"
    files = {"file": ("script.py", io.BytesIO(code), "text/x-python")}
    
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 201
    
    data = response.json()
    assert "project_id" in data
    assert data["project_name"] == "script"
    assert data["input_type"] == "file"
    assert data["source_repository"] is None
    assert data["branch"] is None
    assert data["base_commit_sha"] is None
    assert data["python_files"] == ["script.py"]
    assert data["total_files"] == 1

    # Verify isolated temporary workspace exists on disk
    workspace_dir = WorkspaceService.get_workspace_path(data["project_id"])
    assert workspace_dir.exists()
    assert (workspace_dir / "script.py").exists()
    assert (workspace_dir / "script.py").read_bytes() == code

    # Cleanup
    WorkspaceService.cleanup_workspace(data["project_id"])
    assert not workspace_dir.exists()

def test_upload_binary_python_file_rejected():
    # File containing binary null bytes
    binary_content = b"print('hello')\x00\x01\x02binary_garbage"
    files = {"file": ("corrupt.py", io.BytesIO(binary_content), "text/x-python")}
    
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert "Binary or non-text content detected" in response.json()["detail"]

# ---------------------------------------------------------------------------
# Option A Tests: ZIP Archives
# ---------------------------------------------------------------------------
def test_upload_valid_zip_archive():
    zip_contents = {
        "my_project/src/app.py": "import os\nprint('app')",
        "my_project/src/utils/helpers.py": "def helper(): pass",
        "my_project/tests/test_app.py": "def test_foo(): pass",
        "my_project/README.md": "# Docs",
    }
    zip_bytes = create_zip_bytes(zip_contents)
    files = {"file": ("my_project.zip", io.BytesIO(zip_bytes), "application/zip")}

    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert data["project_name"] == "my_project"
    assert data["input_type"] == "zip"
    assert data["total_files"] == 3
    # Check that relative file paths are discovered recursively and preserved
    assert "src/app.py" in data["python_files"]
    assert "src/utils/helpers.py" in data["python_files"]
    assert "tests/test_app.py" in data["python_files"]

    # Verify workspace files on disk
    workspace_dir = WorkspaceService.get_workspace_path(data["project_id"])
    assert workspace_dir.exists()
    assert (workspace_dir / "src/app.py").exists()
    assert (workspace_dir / "src/utils/helpers.py").exists()

    # Cleanup
    WorkspaceService.cleanup_workspace(data["project_id"])

def test_upload_zip_filters_unnecessary_directories():
    zip_contents = {
        "src/main.py": "print('clean')",
        "src/__pycache__/main.cpython-313.pyc": "compiled binary",
        ".git/config": "[core]\nrepositoryformatversion = 0",
        ".venv/lib/site-packages/dummy.py": "# ignore virtualenv",
        "venv/bin/activate": "# venv",
        "node_modules/package.json": "{}",
        ".pytest_cache/v/cache/nodeids": "cache",
    }
    zip_bytes = create_zip_bytes(zip_contents)
    files = {"file": ("clean_repo.zip", io.BytesIO(zip_bytes), "application/zip")}

    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 201

    data = response.json()
    assert data["python_files"] == ["src/main.py"]
    assert data["total_files"] == 1

    # Cleanup
    WorkspaceService.cleanup_workspace(data["project_id"])

def test_upload_zip_with_no_python_files():
    zip_contents = {
        "README.md": "# Just documentation",
        "assets/logo.png": "png_content",
        "data.json": '{"name": "test"}',
    }
    zip_bytes = create_zip_bytes(zip_contents)
    files = {"file": ("docs_only.zip", io.BytesIO(zip_bytes), "application/zip")}

    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert "No Python (.py) source files found" in response.json()["detail"]

def test_upload_malformed_zip_archive():
    corrupted_bytes = b"PK\x03\x04this is totally corrupted zip payload"
    files = {"file": ("broken.zip", io.BytesIO(corrupted_bytes), "application/zip")}

    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert "not a valid ZIP archive" in response.json()["detail"]

def test_upload_zip_slip_path_traversal_blocked():
    # Attempting to escape the workspace with ../
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("../../etc/malicious.py", "malicious_code = 1")
        z.writestr("safe_app.py", "print('safe')")

    files = {"file": ("zip_slip.zip", io.BytesIO(zip_buffer.getvalue()), "application/zip")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    # Verify malicious path was blocked and safe path was extracted
    assert "../../etc/malicious.py" not in data["python_files"]
    assert "safe_app.py" in data["python_files"]

    WorkspaceService.cleanup_workspace(data["project_id"])

# ---------------------------------------------------------------------------
# Validation Tests: Invalid Extensions and Payloads
# ---------------------------------------------------------------------------
def test_upload_invalid_file_extension():
    files = {"file": ("analysis.txt", io.BytesIO(b"Hello world"), "text/plain")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_upload_empty_file_rejected():
    files = {"file": ("empty.py", io.BytesIO(b""), "text/x-python")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 400
    assert "Uploaded file payload is empty" in response.json()["detail"]

# ---------------------------------------------------------------------------
# Project Retrieval and Workspace Lifecycle Tests
# ---------------------------------------------------------------------------
def test_get_project_and_delete_workflow():
    # 1. Upload a project
    code = b"x = 100\n"
    files = {"file": ("project.py", io.BytesIO(code), "text/x-python")}
    create_res = client.post("/api/v1/upload", files=files)
    assert create_res.status_code == 201
    project_id = create_res.json()["project_id"]

    # 2. Retrieve project metadata
    get_res = client.get(f"/api/v1/projects/{project_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["project_id"] == project_id
    assert data["total_files"] == 1
    assert data["python_files"] == ["project.py"]

    # 3. Clean up workspace via DELETE
    del_res = client.delete(f"/api/v1/projects/{project_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 4. Verify project is now 404
    get_after_del = client.get(f"/api/v1/projects/{project_id}")
    assert get_after_del.status_code == 404

def test_get_nonexistent_project_returns_404():
    response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found or workspace has expired" in response.json()["detail"]

# ---------------------------------------------------------------------------
# Option B Tests: GitHub Repository Cloning
# ---------------------------------------------------------------------------
@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_github_clone_invalid_url():
    payload = {"repo_url": "https://notgithub.com/someone/repo"}
    response = client.post("/api/v1/github/clone", json=payload)
    assert response.status_code == 400
    assert "Invalid GitHub repository URL" in response.json()["detail"]

def test_github_clone_malformed_url():
    payload = {"repo_url": "just_a_string"}
    response = client.post("/api/v1/github/clone", json=payload)
    assert response.status_code == 400
    assert "Invalid GitHub repository URL" in response.json()["detail"]

def test_github_clone_success_mocked():
    # Mocking GitHub API responses:
    # 1. GET /repos/octocat/Hello-World -> default_branch: "master"
    # 2. GET /repos/octocat/Hello-World/commits/master -> sha: "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
    # 3. GET /repos/octocat/Hello-World/zipball/... -> zip archive containing Python files
    mock_zip_bytes = create_zip_bytes({
        "octocat-Hello-World-7fd1a60/app.py": "print('hello from github')",
        "octocat-Hello-World-7fd1a60/utils.py": "x = 42",
        "octocat-Hello-World-7fd1a60/README.md": "# Hello World",
    })

    async def mock_async_client_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        if "/commits/" in url:
            return httpx.Response(200, json={"sha": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"}, request=req)
        elif "/zipball/" in url:
            return httpx.Response(200, content=mock_zip_bytes, request=req)
        elif "/repos/octocat/Hello-World" in url:
            return httpx.Response(200, json={"default_branch": "master", "name": "Hello-World"}, request=req)
        return httpx.Response(404, request=req)

    with patch("httpx.AsyncClient.get", side_effect=mock_async_client_get):
        payload = {"repo_url": "https://github.com/octocat/Hello-World"}
        response = client.post("/api/v1/github/clone", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["project_name"] == "octocat/Hello-World"
        assert data["input_type"] == "github"
        assert data["source_repository"] == "https://github.com/octocat/Hello-World"
        assert data["branch"] == "master"
        assert data["base_commit_sha"] == "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
        assert data["total_files"] == 2
        assert "app.py" in data["python_files"]
        assert "utils.py" in data["python_files"]

        # Workspace verification
        workspace_dir = WorkspaceService.get_workspace_path(data["project_id"])
        assert workspace_dir.exists()
        assert (workspace_dir / "app.py").exists()

        WorkspaceService.cleanup_workspace(data["project_id"])

def test_github_clone_private_or_404_repo_handling():
    async def mock_404_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(404, json={"message": "Not Found"}, request=req)

    with patch("httpx.AsyncClient.get", side_effect=mock_404_get):
        payload = {"repo_url": "https://github.com/ghost/private-secret-repo"}
        response = client.post("/api/v1/github/clone", json=payload)
        assert response.status_code == 404
        assert "not found, unavailable, or is private" in response.json()["detail"]

def test_github_clone_rate_limit_handling():
    async def mock_rate_limit_get(url, *args, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0"},
            json={"message": "API rate limit exceeded"},
            request=req
        )

    with patch("httpx.AsyncClient.get", side_effect=mock_rate_limit_get):
        payload = {"repo_url": "https://github.com/popular/project"}
        response = client.post("/api/v1/github/clone", json=payload)
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"]

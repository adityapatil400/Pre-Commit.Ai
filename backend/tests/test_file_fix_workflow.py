import io
import json
import zipfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.llm.ollama_client import OllamaClient
from backend.app.services.workspace_service import WorkspaceService

client = TestClient(app)

def create_sample_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("app/handler.py", "def process():\n    f = open('log.txt')\n    return f.read()\n")
        z.writestr("app/utils.py", "def check(flag=True):\n    return flag == True\n")
    return buf.getvalue()

def test_generate_file_fix_structured_response():
    """
    Verifies that POST /api/v1/fixes/generate-file-fix returns complete original
    and complete suggested code with the exact structured response format required.
    """
    zip_bytes = create_sample_zip()
    upload_res = client.post("/api/v1/upload", files={"file": ("project.zip", io.BytesIO(zip_bytes), "application/zip")})
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project_id"]

    run_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    assert run_res.status_code == 200
    report = run_res.json()
    analysis_id = report["analysis_id"]

    # Mock Ollama returning complete corrected Python file
    mock_complete_code = (
        "def process():\n"
        "    with open('log.txt') as f:\n"
        "        return f.read()\n"
    )

    async def mock_generate(self, *args, **kwargs):
        return f"```python\n{mock_complete_code}```"

    with patch.object(OllamaClient, "generate", new=mock_generate):
        resp = client.post("/api/v1/fixes/generate-file-fix", json={
            "analysis_id": analysis_id,
            "file_path": "app/handler.py"
        })
        assert resp.status_code == 200
        data = resp.json()

        # Step 4 verification
        assert data["filename"] == "handler.py"
        assert "def process():" in data["original_code"]
        assert "f = open('log.txt')" in data["original_code"]
        assert "with open('log.txt') as f:" in data["suggested_code"]
        assert "def process():" in data["suggested_code"]
        assert len(data["issues"]) >= 1
        assert "Resource Leak" in data["issues"][0]["type"] or "resource_leak" in data["issues"][0]["type"]

        # Explanation structure verification
        exp = data["explanation"]
        assert "what_is_error" in exp
        assert "how_it_is_fixed" in exp
        assert "why_it_is_correct" in exp
        assert "side_effects" in exp

        # Step 7 verification
        assert data["is_valid"] is True
        assert len(data["validation_errors"]) == 0
        assert data["diff"] != ""
        assert "+    with open('log.txt') as f:" in data["diff"]

    WorkspaceService.cleanup_workspace(project_id)

def test_generate_file_fix_fallback_when_ollama_offline():
    """
    Verifies that when Ollama is offline or times out, the backend gracefully falls back
    to the AST remediation engine to provide a complete, valid corrected file.
    """
    zip_bytes = create_sample_zip()
    upload_res = client.post("/api/v1/upload", files={"file": ("project.zip", io.BytesIO(zip_bytes), "application/zip")})
    project_id = upload_res.json()["project_id"]

    run_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    analysis_id = run_res.json()["analysis_id"]

    async def mock_fail(self, *args, **kwargs):
        raise TimeoutError("Ollama connection timed out")

    with patch.object(OllamaClient, "generate", new=mock_fail):
        resp = client.post("/api/v1/fixes/generate-file-fix", json={
            "analysis_id": analysis_id,
            "file_path": "app/handler.py"
        })
        assert resp.status_code == 200
        data = resp.json()

        # AST fallback produces complete corrected code
        assert "with open('log.txt') as f:" in data["suggested_code"]
        assert "def process():" in data["suggested_code"]
        assert data["is_valid"] is True
        assert "AST Remediation Engine" in data["ai_model"]

    WorkspaceService.cleanup_workspace(project_id)


import io
import json
import zipfile
import pytest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.llm.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    ModelUnavailableError,
    LLMTimeoutError,
)
from backend.app.llm.fix_generator import LLMFixGenerator, LLMFixValidationError
from backend.app.services.workspace_service import WorkspaceService
from backend.app.utils.security import SecurityValidator

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

@pytest.fixture
def setup_project_with_analysis():
    """Creates a project workspace and runs analysis to generate an active analysis_id."""
    zip_bytes = create_zip_bytes({
        "services/reader.py": "def load_data():\n    f = open('data.csv', 'r')\n    return f.read()\n",
        "services/calc.py": "def compute(items=[]):\n    return sum(items)\n",
    })
    upload_res = client.post("/api/v1/upload", files={"file": ("project.zip", io.BytesIO(zip_bytes), "application/zip")})
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project_id"]

    run_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    assert run_res.status_code == 200
    report = run_res.json()
    analysis_id = report["analysis_id"]

    yield project_id, analysis_id, report

    # Teardown
    WorkspaceService.cleanup_workspace(project_id)

# ---------------------------------------------------------------------------
# 1. Valid Suggestion Workflow Test
# ---------------------------------------------------------------------------
def test_generate_fix_valid_suggestion(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis
    finding = next(f for f in report["findings"] if f["rule_id"] == "RESOURCE001")

    valid_llm_json = json.dumps({
        "explanation": "Wrapped file open in a with-statement context manager to guarantee deterministic closure.",
        "suggested_code": "    with open('data.csv', 'r') as f:\n        return f.read()"
    })

    async def mock_generate(self, prompt: str = "", **kwargs):
        # Verify untrusted data boundary and prompt structure
        assert "<source_code>" in prompt
        assert "RESOURCE001" in prompt
        return valid_llm_json

    with patch.object(OllamaClient, "generate", new=mock_generate):
        response = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id,
            "finding_id": finding["id"]
        })
        assert response.status_code == 200
        data = response.json()

        # Verify structured response format required by prompt
        assert "fix_id" in data
        assert data["analysis_id"] == analysis_id
        assert data["file_path"] == finding["file_path"]
        assert "reader.py" in data["file_path"]
        assert data["issue"] == finding["title"]
        assert "open('data.csv', 'r')" in data["original_code"]
        assert "with open('data.csv', 'r') as f:" in data["suggested_code"]
        assert "with-statement context manager" in data["explanation"]
        assert data["status"] == "pending_review"  # Never automatically applied
        assert data["diff"] is not None
        assert "reader.py" in data["diff"]

        # Verify GET /api/v1/fixes/{fix_id}
        fix_id = data["fix_id"]
        get_res = client.get(f"/api/v1/fixes/{fix_id}")
        assert get_res.status_code == 200
        assert get_res.json()["fix_id"] == fix_id

# ---------------------------------------------------------------------------
# 2. Batch Fix Generation Test
# ---------------------------------------------------------------------------
def test_generate_batch_fixes(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis

    batch_response_json = json.dumps({
        "explanation": "Applied automated best-practice correction.",
        "suggested_code": "# Corrected implementation\npass"
    })

    async def mock_batch_generate(self, prompt: str = "", **kwargs):
        return batch_response_json

    with patch.object(OllamaClient, "generate", new=mock_batch_generate):
        response = client.post("/api/v1/fixes/generate-batch", json={
            "analysis_id": analysis_id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == analysis_id
        assert data["total_requested"] >= 2
        assert data["total_generated"] >= 2
        assert len(data["fixes"]) >= 2
        assert all(f["status"] == "pending_review" for f in data["fixes"])

# ---------------------------------------------------------------------------
# 3. Malformed LLM Output Handling Test
# ---------------------------------------------------------------------------
def test_generate_fix_malformed_llm_output(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis

    async def mock_malformed_generate(self, prompt: str = "", **kwargs):
        # Returns unparseable text without code or valid JSON
        return "I am sorry, I am unable to assist with this code snippet."

    with patch.object(OllamaClient, "generate", new=mock_malformed_generate):
        response = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id
        })
        assert response.status_code == 422
        assert "Could not parse" in response.json()["detail"]

# ---------------------------------------------------------------------------
# 4. Syntax-Invalid Suggestion Validation Test
# ---------------------------------------------------------------------------
def test_generate_fix_syntax_invalid_suggestion(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis

    syntax_broken_json = json.dumps({
        "explanation": "Here is broken syntax.",
        "suggested_code": "def broken(\n   = = = invalid python syntax"
    })

    async def mock_syntax_invalid_generate(self, prompt: str = "", **kwargs):
        return syntax_broken_json

    with patch.object(OllamaClient, "generate", new=mock_syntax_invalid_generate):
        response = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id
        })
        assert response.status_code == 422
        assert "syntax error" in response.json()["detail"].lower()

# ---------------------------------------------------------------------------
# 5. Unavailable Model Handling Test
# ---------------------------------------------------------------------------
def test_generate_fix_unavailable_model(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis

    async def mock_model_unavailable(self, prompt: str = "", **kwargs):
        raise ModelUnavailableError("llama3.2:latest")

    with patch.object(OllamaClient, "generate", new=mock_model_unavailable):
        response = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id
        })
        assert response.status_code == 503
        assert "is not installed or available" in response.json()["detail"]

# ---------------------------------------------------------------------------
# 6. Ollama Not Running / Connection Error Handling Test
# ---------------------------------------------------------------------------
def test_generate_fix_ollama_not_running(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis

    async def mock_connection_error(self, prompt: str = "", **kwargs):
        raise OllamaConnectionError("http://localhost:11434")

    with patch.object(OllamaClient, "generate", new=mock_connection_error):
        response = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id
        })
        assert response.status_code == 503
        assert "Ensure Ollama is running" in response.json()["detail"]

        # Verify that original analysis report is preserved on Ollama failure
        analysis_res = client.get(f"/api/v1/analysis/{analysis_id}")
        assert analysis_res.status_code == 200
        assert analysis_res.json()["analysis_id"] == analysis_id

# ---------------------------------------------------------------------------
# 7. LLM Request Timeout Handling Test
# ---------------------------------------------------------------------------
def test_generate_fix_timeout(setup_project_with_analysis):
    project_id, analysis_id, report = setup_project_with_analysis

    async def mock_timeout(self, prompt: str = "", **kwargs):
        raise LLMTimeoutError(30.0)

    with patch.object(OllamaClient, "generate", new=mock_timeout):
        response = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id
        })
        assert response.status_code == 504
        assert "timed out after 30.0 seconds" in response.json()["detail"]

# ---------------------------------------------------------------------------
# 8. Security Test: Secrets Sanitization in Prompt
# ---------------------------------------------------------------------------
def test_secret_sanitization_in_prompt():
    raw_code = """
GITHUB_TOKEN = "ghp_1234567890abcdef1234567890abcdef"
OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"
password = "super_secret_password_12345"
"""
    sanitized = SecurityValidator.sanitize_secrets(raw_code)
    assert "ghp_1234567890abcdef1234567890abcdef" not in sanitized
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in sanitized
    assert "super_secret_password_12345" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

def test_get_nonexistent_fix_returns_404():
    response = client.get("/api/v1/fixes/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

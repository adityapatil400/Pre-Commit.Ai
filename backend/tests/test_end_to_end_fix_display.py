import ast
import io
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.app.main import app
from backend.app.llm.ollama_client import OllamaClient

client = TestClient(app)

SAMPLE_FILE_CONTENT = """import os

def load_user_records(filename, default_items=[]):
    file_handle = open(filename, 'r')
    records = file_handle.readlines()
    return records
"""

def test_complete_workflow_code_display_and_fix():
    """
    Step 8 Complete Workflow Verification:
    1. Upload Python file.
    2. Extract original complete source code.
    3. Run AST static analysis.
    4. Detect issues (RESOURCE001, MEMORY003, BUG001).
    5. Pass original code and issues to Ollama.
    6. Generate complete corrected code.
    7. Validate corrected code with ast.parse().
    8. Verify both complete code versions are returned.
    9. Verify structured response format and explanation.
    """
    # 1 & 2: Upload file and extract source code
    upload_resp = client.post(
        "/api/analyze",
        files={"file": ("user_service.py", io.BytesIO(SAMPLE_FILE_CONTENT.encode("utf-8")), "text/x-python")}
    )
    assert upload_resp.status_code == 200
    analysis_data = upload_resp.json()
    session_id = analysis_data["session_id"]

    # 3 & 4: Verify issues detected
    assert len(analysis_data["findings"]) >= 1
    resource_finding = next((f for f in analysis_data["findings"] if f["rule_id"] == "RESOURCE001"), None)
    assert resource_finding is not None

    # Step 2 Verification: Current Code panel must have the COMPLETE original source code
    assert resource_finding["original_code"] == SAMPLE_FILE_CONTENT
    assert "import os" in resource_finding["original_code"]
    assert "def load_user_records" in resource_finding["original_code"]
    assert "file_handle = open" in resource_finding["original_code"]

    # Step 3 Verification: AI Suggested Fix must have COMPLETE corrected Python code
    assert resource_finding["proposed_code"] != ""
    assert "with open" in resource_finding["proposed_code"]
    assert "def load_user_records" in resource_finding["proposed_code"]

    # 5, 6, 7: Invoke Ollama file remediation
    mock_ollama_output = """import os

def load_user_records(filename, default_items=None):
    if default_items is None:
        default_items = []
    with open(filename, 'r') as file_handle:
        records = [line for line in file_handle]
        return records
"""

    async def mock_generate(self, *args, **kwargs):
        return f"```python\n{mock_ollama_output}\n```"

    with patch.object(OllamaClient, "generate", new=mock_generate):
        fix_resp = client.post(
            "/api/v1/fixes/generate-file-fix",
            json={
                "session_id": session_id,
                "file_path": "user_service.py",
            }
        )
        assert fix_resp.status_code == 200
        fix_data = fix_resp.json()

        # Step 4 Response Structure Verification
        assert fix_data["filename"] == "user_service.py"
        assert fix_data["original_code"] == SAMPLE_FILE_CONTENT
        assert fix_data["suggested_code"].strip() == mock_ollama_output.strip()
        assert "with open(filename, 'r') as file_handle:" in fix_data["suggested_code"]
        assert len(fix_data["issues"]) >= 1

        # Explanation Structure
        exp = fix_data["explanation"]
        assert len(exp["what_is_error"]) > 0
        assert len(exp["how_it_is_fixed"]) > 0
        assert len(exp["why_it_is_correct"]) > 0
        assert len(exp["side_effects"]) > 0

        # Step 7 AST Validation of corrected code
        assert fix_data["is_valid"] is True
        assert len(fix_data["validation_errors"]) == 0

        # Statically verify with ast.parse
        parsed_tree = ast.parse(fix_data["suggested_code"])
        assert parsed_tree is not None

        # Verify diff
        assert "-    file_handle = open(filename, 'r')" in fix_data["diff"]
        assert "+    with open(filename, 'r') as file_handle:" in fix_data["diff"]

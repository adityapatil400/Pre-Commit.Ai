import io
import json
import zipfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.llm.ollama_client import OllamaClient
from backend.app.llm.fix_generator import LLMFixGenerator
from backend.app.services.workspace_service import WorkspaceService

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
def review_workflow_setup():
    """
    Sets up a workspace project with 2 Python files and generates 2 fixes.
    Returns (project_id, analysis_id, fix_1, fix_2).
    """
    code_reader = (
        "def process():\n"
        "    f = open('data.txt', 'r')\n"
        "    return f.read()\n"
    )
    code_calc = (
        "def compute(items=[]):\n"
        "    return sum(items)\n"
    )

    zip_bytes = create_zip_bytes({
        "data_reader.py": code_reader,
        "calculator.py": code_calc,
    })

    # 1. Upload
    up_res = client.post("/api/v1/upload", files={"file": ("project.zip", io.BytesIO(zip_bytes), "application/zip")})
    assert up_res.status_code == 201
    project_id = up_res.json()["project_id"]

    # 2. Analyze
    an_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    assert an_res.status_code == 200
    report = an_res.json()
    analysis_id = report["analysis_id"]

    finding_resource = next(f for f in report["findings"] if f["rule_id"] == "RESOURCE001")
    finding_bug = next(f for f in report["findings"] if f["rule_id"] == "BUG001")

    # 3. Generate fixes with mock Ollama
    llm_resp_1 = json.dumps({
        "explanation": "Wrapped open() with a context manager to ensure proper cleanup.",
        "suggested_code": "    with open('data.txt', 'r') as f:\n        return f.read()"
    })
    llm_resp_2 = json.dumps({
        "explanation": "Replaced mutable default argument with None sentinel.",
        "suggested_code": "def compute(items=None):\n    if items is None:\n        items = []\n    return sum(items)"
    })

    async def mock_generate(self, prompt: str = "", **kwargs):
        if "RESOURCE001" in prompt:
            return llm_resp_1
        return llm_resp_2

    with patch.object(OllamaClient, "generate", new=mock_generate):
        fix_res_1 = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id,
            "finding_id": finding_resource["id"]
        })
        assert fix_res_1.status_code == 200
        fix_1 = fix_res_1.json()

        fix_res_2 = client.post("/api/v1/fixes/generate", json={
            "analysis_id": analysis_id,
            "finding_id": finding_bug["id"]
        })
        assert fix_res_2.status_code == 200
        fix_2 = fix_res_2.json()

    yield project_id, analysis_id, fix_1, fix_2

    # Teardown workspace
    WorkspaceService.cleanup_workspace(project_id)

# ---------------------------------------------------------------------------
# 1. Test Unified Code Diff
# ---------------------------------------------------------------------------
def test_get_code_diff_details(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    res = client.get(f"/api/v1/fixes/{fix_1['fix_id']}/diff")
    assert res.status_code == 200
    diff_data = res.json()

    assert diff_data["fix_id"] == fix_1["fix_id"]
    assert diff_data["file_path"] == fix_1["file_path"]
    assert diff_data["line_number"] == fix_1["line_number"]
    assert diff_data["issue"] == fix_1["issue"]
    assert diff_data["explanation"] == fix_1["explanation"]
    assert diff_data["original_code"] == fix_1["original_code"]
    assert diff_data["suggested_code"] == fix_1["suggested_code"]
    assert "--- a/" in diff_data["diff"]
    assert "+++ b/" in diff_data["diff"]
    assert diff_data["status"] == "pending_review"
    assert diff_data["is_stale"] is False

# ---------------------------------------------------------------------------
# 2. Test Single Fix Approval (Never modifies file before explicit apply)
# ---------------------------------------------------------------------------
def test_approve_fix_workflow(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    # Verify original file content before approval
    ws_path = WorkspaceService.get_workspace_path(project_id)
    file_path = ws_path / fix_1["file_path"]
    original_file_content = file_path.read_text()
    assert "f = open('data.txt', 'r')" in original_file_content

    # Approve fix 1
    res = client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")
    assert res.status_code == 200
    approved_data = res.json()
    assert approved_data["status"] == "accepted"

    # Verification: original file MUST NOT be modified before confirmation
    current_content = file_path.read_text()
    assert current_content == original_file_content

# ---------------------------------------------------------------------------
# 3. Test Fix Rejection & Preservation for Reports
# ---------------------------------------------------------------------------
def test_reject_fix_preserves_suggestion(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    res = client.post(f"/api/v1/fixes/{fix_2['fix_id']}/reject")
    assert res.status_code == 200
    rejected_data = res.json()
    assert rejected_data["status"] == "rejected"

    # Preserved in registry and accessible for diff/reports
    get_res = client.get(f"/api/v1/fixes/{fix_2['fix_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "rejected"
    assert get_res.json()["suggested_code"] == fix_2["suggested_code"]
    assert get_res.json()["explanation"] == fix_2["explanation"]

# ---------------------------------------------------------------------------
# 4. Test Edit Suggested Code
# ---------------------------------------------------------------------------
def test_edit_suggested_code_valid_and_invalid(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    # 4a. Edit with valid Python code
    user_edited_code = "    with open('data.txt', 'r', encoding='utf-8') as f:\n        return f.read()"
    edit_res = client.post(f"/api/v1/fixes/{fix_1['fix_id']}/edit", json={
        "suggested_code": user_edited_code,
        "explanation": "User custom fix specifying explicit utf-8 encoding."
    })
    assert edit_res.status_code == 200
    edited_data = edit_res.json()
    assert edited_data["status"] == "edited"
    assert "encoding='utf-8'" in edited_data["suggested_code"]
    assert "explicit utf-8 encoding" in edited_data["explanation"]
    assert "encoding='utf-8'" in edited_data["diff"]

    # 4b. Edit with invalid Python syntax -> Expect 422 Unprocessable Entity
    broken_syntax = "    with open('data.txt' = = = syntax error"
    invalid_edit_res = client.post(f"/api/v1/fixes/{fix_1['fix_id']}/edit", json={
        "suggested_code": broken_syntax
    })
    assert invalid_edit_res.status_code == 422
    assert "Syntax error in edited code" in invalid_edit_res.json()["detail"]

# ---------------------------------------------------------------------------
# 5. Test Stale Source File Detection & Rejection
# ---------------------------------------------------------------------------
def test_stale_source_file_detection(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    # Simulate external file modification in workspace after analysis
    ws_path = WorkspaceService.get_workspace_path(project_id)
    file_path = ws_path / fix_1["file_path"]
    file_path.write_text("def completely_modified_externally():\n    pass\n")

    # Attempt to approve stale fix -> Expect 409 Conflict
    approve_res = client.post(f"/api/v1/fixes/{fix_1['fix_id']}/approve")
    assert approve_res.status_code == 409
    assert "has been modified since analysis" in approve_res.json()["detail"]

    # Attempt to edit stale fix -> Expect 409 Conflict
    edit_res = client.post(f"/api/v1/fixes/{fix_1['fix_id']}/edit", json={
        "suggested_code": "pass"
    })
    assert edit_res.status_code == 409
    assert "has been modified since analysis" in edit_res.json()["detail"]

    # Verify diff reports is_stale: True
    diff_res = client.get(f"/api/v1/fixes/{fix_1['fix_id']}/diff")
    assert diff_res.status_code == 200
    assert diff_res.json()["is_stale"] is True

# ---------------------------------------------------------------------------
# 6. Test Batch Approval (Multiple Fixes Selection)
# ---------------------------------------------------------------------------
def test_batch_approve_fixes(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    # Batch approve both fixes
    batch_res = client.post("/api/v1/fixes/approve-batch", json={
        "fix_ids": [fix_1["fix_id"], fix_2["fix_id"]],
        "analysis_id": analysis_id
    })
    assert batch_res.status_code == 200
    batch_data = batch_res.json()

    assert batch_data["total_requested"] == 2
    assert batch_data["total_approved"] == 2
    assert len(batch_data["approved_fixes"]) == 2
    assert len(batch_data["rejected_stale_fixes"]) == 0

    # Test batch approval with one stale file
    ws_path = WorkspaceService.get_workspace_path(project_id)
    file_path_1 = ws_path / fix_1["file_path"]
    file_path_1.write_text("# Externally modified\nx = 1\n")

    batch_stale_res = client.post("/api/v1/fixes/approve-batch", json={
        "fix_ids": [fix_1["fix_id"], fix_2["fix_id"]]
    })
    assert batch_stale_res.status_code == 200
    stale_batch_data = batch_stale_res.json()
    assert stale_batch_data["total_approved"] == 1
    assert len(stale_batch_data["rejected_stale_fixes"]) == 1
    assert stale_batch_data["rejected_stale_fixes"][0]["fix_id"] == fix_1["fix_id"]

# ---------------------------------------------------------------------------
# 7. Test Explicit Confirmation Before Applying Approved Changes
# ---------------------------------------------------------------------------
def test_apply_approved_fixes_requires_explicit_confirmation(review_workflow_setup):
    project_id, analysis_id, fix_1, fix_2 = review_workflow_setup

    # Approve fix 2
    client.post(f"/api/v1/fixes/{fix_2['fix_id']}/approve")

    # 7a. Call apply without confirm=True -> Expect 400 Bad Request
    apply_unconfirmed = client.post("/api/v1/fixes/apply-approved", json={
        "analysis_id": analysis_id,
        "confirm": False
    })
    assert apply_unconfirmed.status_code == 400
    assert "Explicit confirmation is required" in apply_unconfirmed.json()["detail"]

    # 7b. Call apply with confirm=True -> Successfully modifies workspace file
    apply_confirmed = client.post("/api/v1/fixes/apply-approved", json={
        "analysis_id": analysis_id,
        "confirm": True
    })
    assert apply_confirmed.status_code == 200
    applied_data = apply_confirmed.json()
    assert applied_data["success"] is True
    assert applied_data["applied_count"] >= 1
    assert "calculator.py" in applied_data["modified_files"]

    # Verify calculator.py was safely updated in workspace
    ws_path = WorkspaceService.get_workspace_path(project_id)
    calc_path = ws_path / "calculator.py"
    calc_content = calc_path.read_text()
    assert "def compute(items=None):" in calc_content


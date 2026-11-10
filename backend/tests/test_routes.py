import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_analyze_raw_code_route():
    payload = {
        "code": "def calc(items=[]):\n    except_var = 1\n",
        "filename": "calc.py"
    }
    response = client.post("/api/analysis/raw", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["files_scanned"] == 1
    assert len(data["findings"]) > 0

def test_analyze_uploaded_py_file():
    code_content = b"def test(a=[]):\n    pass\n"
    files = {"file": ("test_code.py", io.BytesIO(code_content), "text/x-python")}
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "test_code"
    assert data["source_type"] == "file"
    assert "session_id" in data
    assert data["metrics"]["total_issues"] >= 1

def test_validate_fixes_flow():
    # 1. Analyze code to generate session
    code = b"def foo(items=[]):\n    pass\n"
    files = {"file": ("demo.py", io.BytesIO(code), "text/x-python")}
    res = client.post("/api/analyze", files=files)
    assert res.status_code == 200
    data = res.json()
    session_id = data["session_id"]
    findings = data["findings"]
    fixable_id = next((f["id"] for f in findings if f["fixable"]), None)

    if fixable_id:
        val_res = client.post("/api/validate-fixes", json={
            "session_id": session_id,
            "approved_finding_ids": [fixable_id]
        })
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["is_valid"] is True
        assert val_data["fixed_count"] >= 1

        # Test download patched zip
        dl_res = client.get(f"/api/download-patched-zip/{session_id}")
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/zip"

def test_github_validate_url_route():
    valid_res = client.get("/api/github/validate-url", params={"url": "https://github.com/fastapi/fastapi"})
    assert valid_res.status_code == 200
    assert valid_res.json()["valid"] is True
    assert valid_res.json()["owner"] == "fastapi"
    assert valid_res.json()["repo"] == "fastapi"

    invalid_res = client.get("/api/github/validate-url", params={"url": "https://notgithub.com/bad/repo"})
    assert invalid_res.status_code == 200
    assert invalid_res.json()["valid"] is False

def test_upload_file_manifest_route():
    code = b"x = 10\n"
    files = {"file": ("script.py", io.BytesIO(code), "text/x-python")}
    res = client.post("/api/upload/file", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "script.py"
    assert data["files_count"] == 1


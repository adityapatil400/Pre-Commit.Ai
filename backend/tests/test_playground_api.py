import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

def test_playground_run_valid_code():
    code = """
def calculate_sum(a, b):
    return a + b

print("Sum:", calculate_sum(10, 25))
"""
    res = client.post("/api/playground/run", json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "completed"
    assert "Sum: 35" in data["stdout"]
    assert data["exit_code"] == 0
    assert data["execution_time_ms"] > 0

def test_playground_run_runtime_exception():
    code = """
def divide(a, b):
    return a / b

divide(10, 0)
"""
    res = client.post("/api/playground/run", json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["status"] == "error"
    assert data["exit_code"] != 0
    assert "ZeroDivisionError" in data["stderr"]
    assert "ZeroDivisionError" in (data["traceback"] or "")

def test_playground_run_timeout():
    code = "while True: pass"
    res = client.post("/api/playground/run", json={"code": code, "timeout_seconds": 1.0})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["status"] == "timeout"
    assert data["exit_code"] == -1
    assert "timed out" in data["error_message"].lower()

def test_playground_run_empty_code():
    res = client.post("/api/playground/run", json={"code": "   \n  "})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["stdout"] == ""

def test_playground_analyze_multiple_issues():
    code = """
for i into range(5):
    f = open("leak.txt")
    print(i)
"""
    res = client.post("/api/playground/analyze", json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert data["total_issues"] >= 2
    types = [i["type"] for i in data["issues"]]
    assert "Syntax Error" in types
    assert "Resource Leak" in types
    assert data["metrics"]["syntax_errors"] >= 1
    assert data["metrics"]["resource_leaks"] >= 1
    assert data["metrics"]["risk_score"] < 100

def test_playground_fix_generation():
    code = """
for i into range(5):
    print(i)

{
"""
    res = client.post("/api/playground/fix", json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert "for i in range(5):" in data["suggested_code"] or "for i in range(5):" in data["corrected_code"]
    assert "{" not in data["suggested_code"].splitlines()[-1]
    assert data["is_valid"] is True
    assert "what_is_error" in data["explanation"]
    assert "how_it_is_fixed" in data["explanation"]

def test_playground_run_and_analyze():
    code = """
print("Executing!")
x = 100
"""
    res = client.post("/api/playground/run-and-analyze", json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert "execution" in data
    assert "analysis" in data
    assert data["execution"]["success"] is True
    assert "Executing!" in data["execution"]["stdout"]
    assert data["analysis"]["metrics"]["risk_score"] == 100

def test_playground_cors_preflight():
    # Test CORS with Vite port 5174
    res = client.options(
        "/api/playground/run",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5174"
    assert res.headers.get("access-control-allow-credentials") == "true"


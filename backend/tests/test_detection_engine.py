import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.analyzer.ast_parser import ASTParser
from backend.app.analyzer.rules.resource_leak import ResourceLeakVisitor
from backend.app.analyzer.rules.memory_leak import MemoryLeakVisitor
from backend.app.analyzer.rules.bug_detection import BugDetectionVisitor
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

# ---------------------------------------------------------------------------
# 1. Resource Leak Detection Rules Tests
# ---------------------------------------------------------------------------
def test_rule_resource001_unclosed_file():
    code = "f = open('data.txt', 'r')\ncontent = f.read()\n"
    res = ASTParser.parse_source(code, filename="test_res1.py")
    visitor = ResourceLeakVisitor("test_res1.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "RESOURCE001"]
    assert len(matches) == 1
    assert matches[0].category == "resource_leak"
    assert matches[0].severity == "warning"
    assert matches[0].line_number == 1
    assert "with open" in matches[0].suggestion

def test_rule_resource001_clean_with_context():
    code = "with open('data.txt', 'r') as f:\n    content = f.read()\n"
    res = ASTParser.parse_source(code, filename="test_res1_clean.py")
    visitor = ResourceLeakVisitor("test_res1_clean.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "RESOURCE001"]
    assert len(matches) == 0

def test_rule_resource002_unclosed_connection_and_socket():
    code = """
import socket, sqlite3
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
db = sqlite3.connect("mydb.db")
"""
    res = ASTParser.parse_source(code, filename="net.py")
    visitor = ResourceLeakVisitor("net.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "RESOURCE002"]
    assert len(matches) >= 2
    assert all(f.category == "resource_leak" for f in matches)

def test_rule_resource003_missing_cleanup_in_try():
    code = """
try:
    f = open("log.txt", "w")
    f.write("entry")
except IOError:
    print("error")
"""
    res = ASTParser.parse_source(code, filename="try_err.py")
    visitor = ResourceLeakVisitor("try_err.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "RESOURCE003"]
    assert len(matches) == 1
    assert "finally" in matches[0].suggestion

def test_rule_resource004_subprocess_popen_unmanaged():
    code = "import subprocess\nproc = subprocess.Popen(['ls', '-la'])\n"
    res = ASTParser.parse_source(code, filename="sub.py")
    visitor = ResourceLeakVisitor("sub.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "RESOURCE004"]
    assert len(matches) == 1
    assert "subprocess.Popen" in matches[0].description

# ---------------------------------------------------------------------------
# 2. Memory-Related Detection Rules Tests
# ---------------------------------------------------------------------------
def test_rule_memory001_unbounded_global_growth():
    code = """
cache = []

def record(item):
    cache.append(item)
"""
    res = ASTParser.parse_source(code, filename="cache.py")
    visitor = MemoryLeakVisitor("cache.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "MEMORY001"]
    assert len(matches) == 1
    assert matches[0].category == "memory_leak"
    assert "collections.deque" in matches[0].suggestion

def test_rule_memory002_custom_del_destructor():
    code = """
class Node:
    def __init__(self, val):
        self.val = val
    def __del__(self):
        print("cleaning")
"""
    res = ASTParser.parse_source(code, filename="node.py")
    visitor = MemoryLeakVisitor("node.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "MEMORY002"]
    assert len(matches) == 1
    assert "__del__" in matches[0].title

def test_rule_memory003_unbuffered_readlines():
    code = "lines = f.readlines()\n"
    res = ASTParser.parse_source(code, filename="read.py")
    visitor = MemoryLeakVisitor("read.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "MEMORY003"]
    assert len(matches) == 1
    assert "line-by-line" in matches[0].suggestion

def test_rule_memory004_global_reference_mutation():
    code = """
def update():
    global session_data
    session_data = {"key": "val"}
"""
    res = ASTParser.parse_source(code, filename="glob.py")
    visitor = MemoryLeakVisitor("glob.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "MEMORY004"]
    assert len(matches) == 1
    assert "session_data" in matches[0].title

def test_rule_memory005_nested_closure_retention():
    code = """
def outer(large_dataset):
    def callback():
        return len(large_dataset)
    return callback
"""
    res = ASTParser.parse_source(code, filename="closure.py")
    visitor = MemoryLeakVisitor("closure.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "MEMORY005"]
    assert len(matches) == 1
    assert "closure" in matches[0].title.lower()

# ---------------------------------------------------------------------------
# 3. Bug Detection Rules Tests
# ---------------------------------------------------------------------------
def test_rule_bug001_mutable_defaults():
    code = "def process(items=[], config={}): pass\n"
    res = ASTParser.parse_source(code, filename="defaults.py")
    visitor = BugDetectionVisitor("defaults.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "BUG001"]
    assert len(matches) == 2
    assert all(f.category == "bug" for f in matches)
    assert all(f.severity == "error" for f in matches)

def test_rule_bug002_suspicious_comparisons():
    code = """
if val == None:
    pass
if item != None:
    pass
if tag is "admin":
    pass
if count == count:
    pass
"""
    res = ASTParser.parse_source(code, filename="comp.py")
    visitor = BugDetectionVisitor("comp.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "BUG002"]
    assert len(matches) == 4
    titles = [f.title for f in matches]
    assert any("== None" in t for t in titles)
    assert any("!= None" in t for t in titles)
    assert any("literal comparison" in t for t in titles)
    assert any("self-comparison" in t for t in titles)

def test_rule_bug003_suspicious_exceptions():
    code = """
try:
    x = 1
except:
    pass
"""
    res = ASTParser.parse_source(code, filename="exc.py")
    visitor = BugDetectionVisitor("exc.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "BUG003"]
    assert len(matches) >= 1
    assert any("Bare `except:`" in f.title for f in matches)

def test_rule_bug004_unreachable_code():
    code = """
def calculate():
    return 42
    print("never reached")
    x = 10
"""
    res = ASTParser.parse_source(code, filename="dead.py")
    visitor = BugDetectionVisitor("dead.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "BUG004"]
    assert len(matches) == 1
    assert matches[0].line_number == 4
    assert "Unreachable code" in matches[0].title

def test_rule_bug005_unused_variables():
    code = """
def compute():
    unused_var = 100
    y = 5
    return y * 2
"""
    res = ASTParser.parse_source(code, filename="unused.py")
    visitor = BugDetectionVisitor("unused.py", code.splitlines(keepends=True))
    visitor.visit(res.tree)

    matches = [f for f in visitor.findings if f.rule_id == "BUG005"]
    assert len(matches) == 1
    assert "unused_var" in matches[0].title

# ---------------------------------------------------------------------------
# 4. Finding Schema Compliance Tests
# ---------------------------------------------------------------------------
def test_finding_schema_exact_keys():
    engine = AnalysisEngine(
        file_path="sample.py",
        source_code="f = open('test.txt')\ndef foo(arg=[]):\n    pass\n"
    )
    findings = engine.analyze()
    assert len(findings) >= 2

    for f in findings:
        dump = f.model_dump()
        # Verify mandatory keys required by the prompt
        assert "rule_id" in dump
        assert "category" in dump
        assert "severity" in dump
        assert "title" in dump
        assert "file_path" in dump
        assert "line_number" in dump
        assert "description" in dump
        assert "suggestion" in dump

# ---------------------------------------------------------------------------
# 5. Full Engine Project Analysis Workflow & API Tests
# ---------------------------------------------------------------------------
def test_analysis_run_api_endpoint_workflow():
    # 1. Prepare project with resource leak, memory issue, bug, and syntax error
    zip_bytes = create_zip_bytes({
        "app/service.py": "def fetch(items=[]):\n    f = open('data.csv')\n    return f.read()\n",
        "app/helper.py": "def helper():\n    if x == None: pass\n",
        "app/broken.py": "def invalid(\n",
    })
    upload_res = client.post("/api/v1/upload", files={"file": ("project.zip", io.BytesIO(zip_bytes), "application/zip")})
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project_id"]

    # 2. Execute static analysis engine via POST /api/v1/analysis/run
    run_res = client.post("/api/v1/analysis/run", json={"project_id": project_id})
    assert run_res.status_code == 200
    report = run_res.json()

    assert "analysis_id" in report
    analysis_id = report["analysis_id"]
    assert report["project_id"] == project_id
    assert report["total_files"] == 3
    assert report["valid_files"] == 2
    assert report["syntax_error_files"] == 1
    assert report["status"] == "completed_with_errors"

    # Verify summary metrics
    metrics = report["metrics"]
    assert metrics["total_issues"] > 0
    assert metrics["syntax_errors"] == 1
    assert metrics["resource_leak_warnings"] >= 1
    assert metrics["bug_warnings"] >= 1

    # Verify findings contain expected categories
    finding_rules = [f["rule_id"] for f in report["findings"]]
    assert "SYNTAX001" in finding_rules
    assert "RESOURCE001" in finding_rules
    assert "BUG001" in finding_rules

    # 3. Retrieve report via GET /api/v1/analysis/{analysis_id}
    get_res = client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_res.status_code == 200
    assert get_res.json()["analysis_id"] == analysis_id
    assert get_res.json()["project_id"] == project_id

    # 4. Cleanup workspace
    WorkspaceService.cleanup_workspace(project_id)

def test_analysis_run_api_error_handling():
    # Non-existent project returns 404
    res_404 = client.post("/api/v1/analysis/run", json={"project_id": "00000000-0000-0000-0000-000000000000"})
    assert res_404.status_code == 404

    # Missing project_id returns 400
    res_400 = client.post("/api/v1/analysis/run", json={})
    assert res_400.status_code == 400

    # Non-existent analysis_id returns 404
    res_get_404 = client.get("/api/v1/analysis/nonexistent-analysis-id")
    assert res_get_404.status_code == 404


import io
import os
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.analyzer.ast_parser import ASTParser, ParseResult
from backend.app.analyzer.syntax_checker import SyntaxChecker
from backend.app.services.syntax_service import SyntaxService
from backend.app.services.workspace_service import WorkspaceService
from backend.app.config import settings

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
# 1. AST Parser Unit Tests
# ---------------------------------------------------------------------------
def test_ast_parser_valid_source():
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res = ASTParser.parse_source(code, filename="math_utils.py")
    
    assert res.success is True
    assert res.tree is not None
    assert res.syntax_error is None
    assert res.filename == "math_utils.py"

    # Test tuple unpacking compatibility: tree, err = parse_result
    tree, err = res
    assert tree is not None
    assert err is None

def test_ast_parser_empty_file_is_valid():
    """In Python, empty files or comments-only files parse cleanly into an empty Module."""
    res_empty = ASTParser.parse_source("", filename="empty.py")
    assert res_empty.success is True
    assert res_empty.tree is not None
    assert len(res_empty.tree.body) == 0

    res_comments = ASTParser.parse_source("# Just comments\n# Another line\n", filename="comments.py")
    assert res_comments.success is True
    assert res_comments.tree is not None

def test_ast_parser_invalid_syntax():
    bad_code = "def broken(\n    print('unclosed parenthesis')"
    res = ASTParser.parse_source(bad_code, filename="bad.py")

    assert res.success is False
    assert res.tree is None
    assert res.syntax_error is not None
    assert isinstance(res.syntax_error, SyntaxError)

    tree, err = res
    assert tree is None
    assert err is not None

# ---------------------------------------------------------------------------
# 2. Syntax Checker Detection & Classification Tests
# ---------------------------------------------------------------------------
def test_syntax_checker_indentation_errors():
    indent_code = "def foo():\nprint('bad indent')\n"
    res = ASTParser.parse_source(indent_code, filename="indent.py")

    assert res.success is False
    assert isinstance(res.syntax_error, IndentationError)

    detail = SyntaxChecker.format_error_detail(res.syntax_error, file_path="indent.py", source_code=indent_code)
    assert detail.error_type == "IndentationError"
    assert detail.file_path == "indent.py"
    assert detail.line_number == 2
    assert "expected an indented block" in detail.error_message.lower()

def test_syntax_checker_unexpected_eof():
    eof_code = "if True:\n"
    res = ASTParser.parse_source(eof_code, filename="eof.py")

    assert res.success is False
    detail = SyntaxChecker.format_error_detail(res.syntax_error, file_path="eof.py", source_code=eof_code)
    assert detail.error_type in ("UnexpectedEOFError", "IndentationError", "SyntaxError")
    assert detail.line_number >= 1

def test_syntax_checker_unmatched_brackets():
    bracket_code = "items = [1, 2, 3\nprint(items)"
    res = ASTParser.parse_source(bracket_code, filename="brackets.py")

    assert res.success is False
    detail = SyntaxChecker.format_error_detail(res.syntax_error, file_path="brackets.py", source_code=bracket_code)
    assert detail.error_type == "UnmatchedBracketError"
    assert "was never closed" in detail.error_message.lower() or "unmatched" in detail.error_message.lower()

def test_syntax_checker_invalid_expression():
    expr_code = "x = = 42\n"
    res = ASTParser.parse_source(expr_code, filename="expr.py")

    assert res.success is False
    detail = SyntaxChecker.format_error_detail(res.syntax_error, file_path="expr.py", source_code=expr_code)
    assert detail.error_type == "SyntaxError"
    assert "invalid syntax" in detail.error_message.lower()
    assert detail.line_number == 1

def test_syntax_checker_encoding_error_detection(tmp_path):
    # Create a file with invalid binary null bytes
    bad_file = tmp_path / "corrupted_encoding.py"
    bad_file.write_bytes(b"\x00\x80\xFFdef foo(): pass")

    parse_res = ASTParser.parse_file(bad_file, relative_path="corrupted_encoding.py")
    assert parse_res.success is False
    assert parse_res.syntax_error is not None

    detail = SyntaxChecker.format_error_detail(parse_res.syntax_error, file_path="corrupted_encoding.py")
    assert detail.error_type == "EncodingError"
    assert "Encoding error" in detail.error_message or "null byte" in detail.error_message

# ---------------------------------------------------------------------------
# 3. Multiple Files Behavior Requirement Test
# ---------------------------------------------------------------------------
def test_syntax_service_multiple_files_isolation():
    """
    Important behavior requirement:
    If a Python file contains a syntax error:
    - Report the syntax error.
    - Do not attempt AST-based semantic analysis on that invalid file.
    - Continue analyzing other valid Python files.
    """
    zip_bytes = create_zip_bytes({
        "app/valid_one.py": "def first(): return 1\n",
        "app/invalid_syntax.py": "def broken(x\n    return x\n",
        "app/invalid_indent.py": "x = 1\n  y = 2\n",
        "app/valid_two.py": "class Worker:\n    def run(self): pass\n",
        "app/empty_module.py": "",
    })

    # Upload project to create workspace
    files = {"file": ("multi_test.zip", io.BytesIO(zip_bytes), "application/zip")}
    upload_res = client.post("/api/v1/upload", files=files)
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project_id"]

    # Run Syntax Service
    response = SyntaxService.analyze_project_syntax(project_id)

    assert response.project_id == project_id
    assert response.total_python_files == 5
    assert response.successfully_parsed_count == 3
    assert response.files_with_syntax_errors_count == 2
    assert response.status == "completed_with_errors"

    # Verify valid files were all parsed successfully
    assert "valid_one.py" in response.successfully_parsed_files
    assert "valid_two.py" in response.successfully_parsed_files
    assert "empty_module.py" in response.successfully_parsed_files

    # Verify invalid files were reported accurately
    assert "invalid_syntax.py" in response.files_with_syntax_errors
    assert "invalid_indent.py" in response.files_with_syntax_errors
    assert len(response.syntax_errors) == 2

    # Check error details
    error_files = [e.file_path for e in response.syntax_errors]
    assert "invalid_syntax.py" in error_files
    assert "invalid_indent.py" in error_files

    # Cleanup
    WorkspaceService.cleanup_workspace(project_id)

# ---------------------------------------------------------------------------
# 4. API Endpoint Integration Tests (POST /api/v1/analysis/syntax)
# ---------------------------------------------------------------------------
def test_api_syntax_analysis_endpoint_success():
    zip_bytes = create_zip_bytes({
        "main.py": "def main(): print('hello')",
        "broken.py": "def bad(\n",
    })
    files = {"file": ("api_test.zip", io.BytesIO(zip_bytes), "application/zip")}
    upload_res = client.post("/api/v1/upload", files=files)
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project_id"]

    # Test via JSON body
    syntax_res = client.post("/api/v1/analysis/syntax", json={"project_id": project_id})
    assert syntax_res.status_code == 200

    data = syntax_res.json()
    assert data["project_id"] == project_id
    assert data["total_python_files"] == 2
    assert data["successfully_parsed_count"] == 1
    assert data["files_with_syntax_errors_count"] == 1
    assert "main.py" in data["successfully_parsed_files"]
    assert "broken.py" in data["files_with_syntax_errors"]
    assert len(data["syntax_errors"]) == 1
    assert data["syntax_errors"][0]["file_path"] == "broken.py"
    assert data["syntax_errors"][0]["line_number"] >= 1

    # Test via Query param
    syntax_query_res = client.post(f"/api/v1/analysis/syntax?project_id={project_id}")
    assert syntax_query_res.status_code == 200

    # Cleanup
    WorkspaceService.cleanup_workspace(project_id)

def test_api_syntax_analysis_nonexistent_project_returns_404():
    response = client.post(
        "/api/v1/analysis/syntax",
        json={"project_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 404
    assert "not found or workspace has expired" in response.json()["detail"]

def test_api_syntax_analysis_missing_project_id_returns_400():
    response = client.post("/api/v1/analysis/syntax", json={})
    assert response.status_code == 400
    assert "Missing required parameter" in response.json()["detail"]

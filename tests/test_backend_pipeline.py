import io
import zipfile
import pytest
from backend.analyzer.ast_scanner import ASTScanner
from backend.analyzer.fix_engine import FixEngine
from backend.analyzer.source_retriever import SourceRetriever

SAMPLE_BUGGY_PYTHON = """import socket

CACHE = []

class Node:
    def __init__(self, parent=None):
        self.parent = parent
    def __del__(self):
        pass

def process_items(items=[]):
    CACHE.append(items)
    f = open("output.log", "w")
    f.write("logging...")
    
    s = socket.socket()
    
    val = None
    if val == None:
        pass
        
    try:
        x = 1 / 0
    except:
        pass

    with open("big.txt") as bf:
        lines = bf.readlines()
"""

def test_ast_scanner_detects_all_issues():
    scanner = ASTScanner("test_sample.py", SAMPLE_BUGGY_PYTHON)
    findings = scanner.scan()

    rule_ids = {f.rule_id for f in findings}
    print("Detected Rule IDs:", rule_ids)

    # Verify detection of each class of issue:
    assert "PY-BUG-001" in rule_ids  # Mutable default
    assert "PY-RES-001" in rule_ids  # Unclosed file
    assert "PY-RES-002" in rule_ids  # Unmanaged socket
    assert "PY-BUG-003" in rule_ids  # Comparison with None
    assert "PY-BUG-002" in rule_ids  # Bare except
    assert "PY-MEM-001" in rule_ids  # Unbounded global
    assert "PY-MEM-002" in rule_ids  # Class with __del__
    assert "PY-MEM-003" in rule_ids  # Full readlines

def test_syntax_error_detection():
    invalid_py = "def broken(\n    return 42"
    scanner = ASTScanner("broken.py", invalid_py)
    findings = scanner.scan()

    assert len(findings) == 1
    assert findings[0].rule_id == "PY-SYN-001"
    assert findings[0].severity == "error"

def test_fix_recommendation_and_validation():
    scanner = ASTScanner("test_sample.py", SAMPLE_BUGGY_PYTHON)
    findings = scanner.scan()

    # Filter fixable findings
    fixable = [f for f in findings if f.fixable]
    assert len(fixable) >= 4

    files = {"test_sample.py": SAMPLE_BUGGY_PYTHON}
    patched_files = FixEngine.apply_fixes(files, fixable)

    assert patched_files["test_sample.py"] != SAMPLE_BUGGY_PYTHON
    assert "except Exception:" in patched_files["test_sample.py"]
    assert "is None" in patched_files["test_sample.py"]

    # Re-validate with AST (Step 7: Code Validation)
    validation = FixEngine.validate_code(patched_files, len(findings))
    assert validation.is_valid is True
    assert len(validation.syntax_errors) == 0
    assert validation.fixed_count > 0

def test_zip_extraction_and_safety():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("app/main.py", "print('hello world')\n")
        z.writestr("app/test.txt", "not python")
        z.writestr("app/__pycache__/cached.py", "should be skipped")

    buf.seek(0)
    files = SourceRetriever.from_zip_bytes(buf.getvalue())
    assert "app/main.py" in files or "main.py" in files
    assert not any("__pycache__" in k for k in files)

if __name__ == "__main__":
    test_ast_scanner_detects_all_issues()
    test_syntax_error_detection()
    test_fix_recommendation_and_validation()
    test_zip_extraction_and_safety()
    print("All backend tests passed successfully!")


import pytest
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.schemas.analysis_schema import SeverityEnum, CategoryEnum

def test_syntax_error_detection():
    bad_code = "def foo(\n    print('broken syntax'"
    engine = AnalysisEngine(file_path="bad.py", source_code=bad_code)
    findings = engine.analyze()

    assert len(findings) >= 1
    assert all(f.severity == SeverityEnum.ERROR for f in findings)
    assert all(f.category == CategoryEnum.SYNTAX for f in findings)
    assert "bad.py" in findings[0].file_path

def test_resource_leak_open_detection():
    code = """
def read_data():
    f = open("data.csv", "r")
    data = f.read()
    return data
"""
    engine = AnalysisEngine(file_path="reader.py", source_code=code)
    findings = engine.analyze()

    res_findings = [f for f in findings if f.rule_id in ("RESOURCE001", "PY-RES-001")]
    assert len(res_findings) >= 1
    assert res_findings[0].category == CategoryEnum.RESOURCE_LEAK
    assert res_findings[0].line == 3
    assert res_findings[0].is_potential_warning is True

def test_resource_clean_with_open():
    code = """
def read_data():
    with open("data.csv", "r") as f:
        return f.read()
"""
    engine = AnalysisEngine(file_path="reader_clean.py", source_code=code)
    findings = engine.analyze()
    res_findings = [f for f in findings if f.rule_id in ("RESOURCE001", "PY-RES-001")]
    assert len(res_findings) == 0

def test_bug_mutable_default():
    code = """
def append_item(val, container=[]):
    container.append(val)
    return container
"""
    engine = AnalysisEngine(file_path="bug.py", source_code=code)
    findings = engine.analyze()

    bug_findings = [f for f in findings if f.rule_id in ("BUG001", "PY-BUG-001")]
    assert len(bug_findings) == 1
    assert bug_findings[0].fixable is True
    assert "None" in bug_findings[0].proposed_code

def test_bug_bare_except():
    code = """
try:
    x = 1 / 0
except:
    pass
"""
    engine = AnalysisEngine(file_path="except.py", source_code=code)
    findings = engine.analyze()

    bare_findings = [f for f in findings if f.rule_id in ("BUG003", "PY-BUG-002") and "Bare" in f.title]
    assert len(bare_findings) == 1
    assert bare_findings[0].fixable is True
    assert "except Exception:" in bare_findings[0].proposed_code

def test_memory_leak_global_collection():
    code = """
cache = []

def add(item):
    cache.append(item)
"""
    engine = AnalysisEngine(file_path="cache.py", source_code=code)
    findings = engine.analyze()

    mem_findings = [f for f in findings if f.rule_id in ("MEMORY001", "PY-MEM-001")]
    assert len(mem_findings) == 1
    assert mem_findings[0].category in (CategoryEnum.MEMORY, "memory_leak", "memory")


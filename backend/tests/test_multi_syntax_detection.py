import ast
import pytest
from backend.app.analyzer.syntax_checker import SyntaxChecker
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.analyzer.ast_remediator import ASTRemediator
from backend.app.llm.fix_generator import LLMFixGenerator

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# ---------------------------------------------------------------------------
# 1. Single Syntax Error Test
# ---------------------------------------------------------------------------
def test_single_syntax_error():
    code = """def add(a, b):
    print('Result: ' + (a + b)
"""
    errors = SyntaxChecker.check_multiple_syntax_errors(code, file_path="single_err.py")
    assert len(errors) == 1
    assert errors[0].line_number == 2
    assert "UnmatchedBracketError" in errors[0].error_type or "parenthesis" in errors[0].error_message.lower()

# ---------------------------------------------------------------------------
# 2. STEP 8 Explicit Example: 2 Syntax Errors ('into' + '{')
# ---------------------------------------------------------------------------
def test_step_8_exact_example():
    code = """#Error Demo
for i in range(1, 20):
    print(i)

for j into range(2,20):
    print(j)

{
"""
    errors = SyntaxChecker.check_multiple_syntax_errors(code, file_path="step8_demo.py")
    assert len(errors) == 2, f"Expected 2 syntax errors, found {len(errors)}: {errors}"
    
    # Error 1: 'into' keyword error on line 5
    err1 = errors[0]
    assert err1.line_number == 5
    assert "into" in err1.error_message.lower() or "into" in err1.source_snippet
    assert "in" in err1.suggestion.lower()

    # Error 2: Unmatched '{' on line 8
    err2 = errors[1]
    assert err2.line_number == 8
    assert "{" in err2.source_snippet or "curly brace" in err2.error_message.lower() or "never closed" in err2.error_message.lower()

    # Test AST Remediation on this exact example
    findings = SyntaxChecker.format_all_syntax_errors(code, file_path="step8_demo.py")
    assert len(findings) == 2
    
    corrected_code = ASTRemediator.remediate_complete_file(code, findings)
    assert "for j in range(2,20):" in corrected_code or "for j in range(2, 20):" in corrected_code
    assert "{" not in corrected_code.splitlines()[-1]
    
    # Validation: corrected code parses cleanly with ast.parse()
    tree = ast.parse(corrected_code)
    assert tree is not None

# ---------------------------------------------------------------------------
# 3. 5 Syntax Errors in a Single File
# ---------------------------------------------------------------------------
def test_five_syntax_errors():
    code_5 = """# 5 Syntax Errors File
def func1():
    print('unclosed string)

for idx into range(10):
    pass

if value == 10
    pass

x = 1 +

{
"""
    errors = SyntaxChecker.check_multiple_syntax_errors(code_5, file_path="five_err.py")
    assert len(errors) >= 4, f"Expected at least 4-5 errors, detected {len(errors)}: {[e.line_number for e in errors]}"

    error_lines = [e.line_number for e in errors]
    # Verify errors across the file are detected (not stopping at line 3)
    assert any(line >= 8 for line in error_lines), "Downstream errors must be discovered"

# ---------------------------------------------------------------------------
# 4. Multi-Error Detection and End-to-End AnalysisEngine
# ---------------------------------------------------------------------------
def test_analysis_engine_multi_syntax():
    code = """# Multi error file
for a into items:
    print(a)

{
"""
    engine = AnalysisEngine(file_path="multi.py", source_code=code)
    findings = engine.analyze()

    assert len(findings) == 2
    assert findings[0].line == 2
    assert findings[1].line == 5
    assert all(f.category == "syntax" for f in findings)
    assert all(f.fixable is True for f in findings)
    assert findings[0].proposed_code != ""
    assert "for a in items:" in findings[0].proposed_code

# ---------------------------------------------------------------------------
# 5. Full Structured FileFixResponse with Ollama / Remediator
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_generate_complete_file_fix_multi_error():
    code = """#Error Demo
for i in range(1, 20):
    print(i)

for j into range(2,20):
    print(j)

{
"""
    findings = SyntaxChecker.format_all_syntax_errors(code, file_path="demo.py")
    assert len(findings) == 2

    res = await LLMFixGenerator.generate_complete_file_fix(
        file_path="demo.py",
        original_code=code,
        issues=findings
    )

    assert res.is_valid is True
    assert len(res.validation_errors) == 0
    assert "for j in range(2,20):" in res.suggested_code or "for j in range(2, 20):" in res.suggested_code
    assert res.corrected_code is not None
    assert len(res.fixes_applied) >= 1
    assert res.diff != ""
    # AST validation passes
    ast.parse(res.suggested_code)

# ---------------------------------------------------------------------------
# 6. Physical File Example Tests (1, 2, 5, and combined leak)
# ---------------------------------------------------------------------------
def test_example_files():
    from pathlib import Path
    examples_dir = Path("examples")

    # A: Error Demo (2 errors)
    code_demo = (examples_dir / "error_demo.py").read_text(encoding="utf-8")
    errs_demo = SyntaxChecker.check_multiple_syntax_errors(code_demo, "examples/error_demo.py")
    assert len(errs_demo) == 2
    assert errs_demo[0].line_number == 5
    assert errs_demo[1].line_number == 8

    # B: Single Error
    code_single = (examples_dir / "single_error.py").read_text(encoding="utf-8")
    errs_single = SyntaxChecker.check_multiple_syntax_errors(code_single, "examples/single_error.py")
    assert len(errs_single) == 1
    assert errs_single[0].line_number == 2

    # C: 5 Errors File
    code_five = (examples_dir / "five_errors.py").read_text(encoding="utf-8")
    errs_five = SyntaxChecker.check_multiple_syntax_errors(code_five, "examples/five_errors.py")
    assert len(errs_five) >= 4

    # D: Multiple errors with resource leak in same file
    code_leaks = (examples_dir / "multiple_errors_with_leaks.py").read_text(encoding="utf-8")
    engine = AnalysisEngine(file_path="examples/multiple_errors_with_leaks.py", source_code=code_leaks)
    findings = engine.analyze()
    # Must detect both syntax errors AND resource leak
    categories = [f.category for f in findings]
    assert "syntax" in categories
    assert "resource_leak" in categories


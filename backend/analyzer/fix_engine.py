import ast
import difflib
from typing import Dict, List, Tuple
from .models import Finding, ValidationResult
from .ast_scanner import ASTScanner

class FixEngine:
    """
    Applies approved code fixes to source files and validates AST compilation.
    """

    @staticmethod
    def apply_fixes(files_content: Dict[str, str], approved_findings: List[Finding]) -> Dict[str, str]:
        """
        Applies a list of approved findings to their respective files.
        Processes findings per file in descending line order to prevent offset drift.
        """
        patched_files = dict(files_content)

        # Group findings by file path
        findings_by_file: Dict[str, List[Finding]] = {}
        for f in approved_findings:
            if f.fixable and f.proposed_code:
                findings_by_file.setdefault(f.file_path, []).append(f)

        for file_path, findings in findings_by_file.items():
            if file_path not in patched_files:
                continue

            content = patched_files[file_path]
            lines = content.splitlines(keepends=True)

            # Sort descending by line number
            findings_sorted = sorted(findings, key=lambda x: x.line, reverse=True)

            for f in findings_sorted:
                line_idx = f.line - 1
                if 0 <= line_idx < len(lines):
                    # Replace the problematic line with proposed code
                    replacement = f.proposed_code
                    if not replacement.endswith("\n"):
                        replacement += "\n"
                    lines[line_idx] = replacement

            patched_files[file_path] = "".join(lines)

        return patched_files

    @classmethod
    def validate_code(cls, patched_files: Dict[str, str], original_findings_count: int) -> ValidationResult:
        """
        Re-parses the proposed code with AST and runs static checks to ensure clean, valid code.
        """
        syntax_errors: List[str] = []
        remaining_findings: List[Finding] = []
        validated_files: List[str] = list(patched_files.keys())

        for file_path, code in patched_files.items():
            # Step 1: AST Parse Validation
            try:
                ast.parse(code, filename=file_path)
            except SyntaxError as e:
                syntax_errors.append(f"{file_path}:{e.lineno or 1}: {e.msg}")
                continue

            # Step 2: Re-run static AST scanner on patched code
            scanner = ASTScanner(file_path, code)
            findings = scanner.scan()
            remaining_findings.extend(findings)

        is_valid = len(syntax_errors) == 0
        remaining_count = len(remaining_findings)
        fixed_count = max(0, original_findings_count - remaining_count)

        return ValidationResult(
            is_valid=is_valid,
            validated_files=validated_files,
            syntax_errors=syntax_errors,
            fixed_count=fixed_count,
            remaining_count=remaining_count,
            remaining_findings=remaining_findings
        )


from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.analyzer.ast_parser import ASTParser
from backend.app.analyzer.syntax_checker import SyntaxChecker
from backend.app.schemas.syntax_schema import SyntaxAnalysisResponse, SyntaxErrorDetail
from backend.app.services.workspace_service import WorkspaceService, ProjectNotFoundError
from backend.app.utils.logger import logger

class SyntaxService:
    """
    Coordinates Python AST parsing and syntax checking across files in a project workspace.
    Guarantees that ALL syntax errors in every file are detected and isolated while valid
    files and recoverable syntax regions are parsed and analyzed.
    """

    @classmethod
    def analyze_project_syntax(cls, project_id: str) -> SyntaxAnalysisResponse:
        """
        Scans and validates syntax for all discovered Python files in the given project workspace,
        discovering multiple syntax errors per file where present.
        """
        project = WorkspaceService.get_project(project_id)
        workspace_dir = WorkspaceService.get_workspace_path(project_id)

        if not workspace_dir.exists():
            raise ProjectNotFoundError(project_id)

        successfully_parsed_files: List[str] = []
        files_with_syntax_errors: List[str] = []
        syntax_errors: List[SyntaxErrorDetail] = []

        logger.info(
            f"Starting multi-pass syntax analysis for project '{project_id}' "
            f"({len(project.python_files)} Python files to inspect)"
        )

        for rel_path in project.python_files:
            file_path = (workspace_dir / rel_path).resolve()

            # Prevent directory traversal beyond workspace boundaries
            if not str(file_path).startswith(str(workspace_dir.resolve())):
                logger.warning(f"Skipping out-of-bounds file path: {rel_path}")
                continue

            if not file_path.is_file():
                continue

            # Read source code safely
            source_code = ""
            try:
                source_code, _ = ASTParser.read_source_file(file_path)
            except Exception as e:
                # Encoding or read failure
                err_detail = SyntaxErrorDetail(
                    file_path=rel_path,
                    line_number=1,
                    column_number=1,
                    error_type="EncodingError",
                    error_message=f"Failed to read file: {e}",
                    source_snippet="",
                    suggestion="Verify file encoding (prefer UTF-8) and ensure no binary data."
                )
                files_with_syntax_errors.append(rel_path)
                syntax_errors.append(err_detail)
                continue

            # Multi-pass syntax error detection for ALL errors
            file_errors = SyntaxChecker.check_multiple_syntax_errors(source_code, file_path=rel_path)

            if not file_errors:
                successfully_parsed_files.append(rel_path)
            else:
                files_with_syntax_errors.append(rel_path)
                syntax_errors.extend(file_errors)
                logger.info(
                    f"SyntaxService: Detected {len(file_errors)} syntax error(s) in '{rel_path}'"
                )

        total_files = len(successfully_parsed_files) + len(files_with_syntax_errors)
        status = "completed" if not files_with_syntax_errors else "completed_with_errors"

        logger.info(
            f"Syntax analysis for '{project_id}' completed: "
            f"{len(successfully_parsed_files)} valid, {len(files_with_syntax_errors)} files with {len(syntax_errors)} total errors."
        )

        return SyntaxAnalysisResponse(
            project_id=project_id,
            total_python_files=total_files,
            successfully_parsed_count=len(successfully_parsed_files),
            files_with_syntax_errors_count=len(files_with_syntax_errors),
            successfully_parsed_files=successfully_parsed_files,
            files_with_syntax_errors=files_with_syntax_errors,
            syntax_errors=syntax_errors,
            status=status
        )

    @classmethod
    def analyze_source_code_snippet(
        cls,
        source_code: str,
        filename: str = "snippet.py"
    ) -> Tuple[bool, Optional[SyntaxErrorDetail]]:
        """
        Validates syntax of an in-memory Python code string.
        Returns (is_valid, first_error_detail) for legacy backwards-compatibility.
        """
        errors = SyntaxChecker.check_multiple_syntax_errors(source_code, file_path=filename)
        if not errors:
            return True, None
        return False, errors[0]

    @classmethod
    def analyze_source_code_snippet_all(
        cls,
        source_code: str,
        filename: str = "snippet.py"
    ) -> Tuple[bool, List[SyntaxErrorDetail]]:
        """
        Validates syntax of an in-memory Python code string, returning ALL detected syntax errors.
        """
        errors = SyntaxChecker.check_multiple_syntax_errors(source_code, file_path=filename)
        return (len(errors) == 0, errors)

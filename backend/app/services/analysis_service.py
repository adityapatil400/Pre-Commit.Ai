import difflib
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.analyzer.ast_remediator import ASTRemediator
from backend.app.schemas.analysis_schema import (
    AnalysisResultResponse,
    FindingSchema,
    SummaryMetricsSchema,
    CategoryEnum,
    SeverityEnum,
)
from backend.app.services.file_service import FileService
from backend.app.utils.logger import logger
from backend.app.utils.report_generator import ReportGenerator

class AnalysisService:
    """
    Coordinates static code analysis workflows across Python files.
    Enforces zero-code-execution AST inspections and compiles findings.
    """

    @classmethod
    def analyze_files(
        cls,
        files_content: Dict[str, str],
        project_name: str,
        source_type: str,
        source_reference: str,
        github_token: Optional[str] = None
    ) -> AnalysisResultResponse:
        """
        Executes AST static analysis across a dictionary of Python files.
        Guarantees that every finding preserves complete original Python source code
        and provides verified complete suggested code.
        """
        start_time = time.time()
        all_findings: List[FindingSchema] = []
        files_suggested: Dict[str, str] = {}
        total_lines = 0

        logger.info(f"Starting AST analysis for project `{project_name}` ({len(files_content)} files)")

        for file_path, code in files_content.items():
            lines_count = len(code.splitlines())
            total_lines += lines_count

            engine = AnalysisEngine(file_path=file_path, source_code=code)
            file_findings = engine.analyze()

            # Generate complete suggested code for this file if findings exist
            suggested_code = ASTRemediator.remediate_complete_file(code, file_findings) if file_findings else code
            files_suggested[file_path] = suggested_code

            # Compute unified diff between complete original and complete suggested code
            diff_lines = list(difflib.unified_diff(
                code.splitlines(keepends=True),
                suggested_code.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm=""
            ))
            full_diff = "\n".join(diff_lines)

            # Ensure every finding has COMPLETE original and suggested Python source code
            for f in file_findings:
                f.original_code = code
                f.proposed_code = suggested_code
                f.unified_diff = full_diff
                if not f.code_snippet and f.line:
                    lines = code.splitlines()
                    if 0 <= f.line - 1 < len(lines):
                        f.code_snippet = lines[f.line - 1].strip()

            all_findings.extend(file_findings)

        # Compute summary metrics
        syntax_count = sum(1 for f in all_findings if f.severity == SeverityEnum.ERROR and f.category == CategoryEnum.SYNTAX)
        leak_count = sum(1 for f in all_findings if f.category == CategoryEnum.RESOURCE_LEAK)
        mem_count = sum(1 for f in all_findings if f.category == CategoryEnum.MEMORY)
        bug_count = sum(1 for f in all_findings if f.category == CategoryEnum.BUG)
        info_count = sum(1 for f in all_findings if f.severity == SeverityEnum.INFORMATION)
        fixable_count = sum(1 for f in all_findings if f.fixable)

        metrics = SummaryMetricsSchema(
            total_issues=len(all_findings),
            syntax_errors=syntax_count,
            resource_leak_warnings=leak_count,
            memory_warnings=mem_count,
            bug_warnings=bug_count,
            information_count=info_count,
            fixable_count=fixable_count,
        )

        duration = round(time.time() - start_time, 2)
        session_id = str(uuid.uuid4())

        # Save session data for subsequent fix validation and commit steps
        session_data = {
            "session_id": session_id,
            "project_name": project_name,
            "source_type": source_type,
            "source_reference": source_reference,
            "files": files_content,
            "files_suggested": files_suggested,
            "findings": all_findings,
            "github_token": github_token,
            "metrics": metrics.model_dump(),
            "created_at": datetime.now().isoformat()
        }
        FileService.save_session(session_id, session_data)

        logger.info(
            f"Analysis completed: session={session_id}, issues={len(all_findings)}, "
            f"fixable={fixable_count}, duration={duration}s"
        )

        return AnalysisResultResponse(
            session_id=session_id,
            project_name=project_name,
            source_type=source_type,
            source_reference=source_reference,
            status="completed",
            scanned_at=datetime.now().strftime("%I:%M %p, %b %d, %Y"),
            duration_seconds=duration,
            files_scanned=len(files_content),
            total_lines_analyzed=total_lines,
            metrics=metrics,
            findings=all_findings,
            files_manifest=list(files_content.keys()),
            files_source=files_content,
            files_suggested=files_suggested,
            is_mock_data=False,
        )

    @classmethod
    def analyze_raw_snippet(cls, code: str, filename: str = "snippet.py") -> AnalysisResultResponse:
        """
        Performs static analysis on a single raw Python code snippet.
        """
        files = {filename: code}
        return cls.analyze_files(
            files_content=files,
            project_name="code-snippet",
            source_type="file",
            source_reference=filename
        )

    @classmethod
    def generate_session_report(cls, session_id: str) -> Optional[str]:
        """
        Compiles a Markdown report for a completed session.
        """
        session = FileService.get_session(session_id)
        if not session:
            return None

        findings_dicts = [f.model_dump() if hasattr(f, "model_dump") else f for f in session["findings"]]
        return ReportGenerator.generate_markdown_report(
            project_name=session["project_name"],
            source_type=session["source_type"],
            source_ref=session["source_reference"],
            metrics=session["metrics"],
            findings=findings_dicts,
            scanned_at=session.get("created_at", datetime.now().isoformat())
        )


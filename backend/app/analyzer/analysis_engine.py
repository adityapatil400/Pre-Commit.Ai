import ast
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from backend.app.analyzer.ast_parser import ASTParser
from backend.app.analyzer.syntax_checker import SyntaxChecker
from backend.app.analyzer.rules.resource_leak import ResourceLeakVisitor
from backend.app.analyzer.rules.memory_leak import MemoryLeakVisitor
from backend.app.analyzer.rules.bug_detection import BugDetectionVisitor
from backend.app.schemas.analysis_schema import (
    AnalysisReportResponse,
    FindingSchema,
    SummaryMetricsSchema,
    SeverityEnum,
)
from backend.app.utils.logger import logger

class AnalysisEngine:
    """
    Core static code analysis engine for PreCommit AI.
    
    Orchestration Workflow:
    1. Receives project_id and resolves isolated workspace.
    2. Discovers Python source files.
    3. Runs syntax checking to isolate invalid files.
    4. Parses valid files using ASTParser (ast.parse) with zero code execution.
    5. Executes registered AST NodeVisitors (ResourceLeak, MemoryLeak, BugDetection).
    6. Aggregates findings and formats structured metadata.
    7. Generates and caches the standardized analysis report.
    """

    # In-memory storage for analysis reports: analysis_id -> AnalysisReportResponse
    _ANALYSIS_STORE: Dict[str, AnalysisReportResponse] = {}

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.lines = source_code.splitlines(keepends=True)
        self.global_collections: Set[str] = set()

    def analyze(self) -> List[FindingSchema]:
        """
        Runs static analysis on a single file's source code string.
        Preserves backwards compatibility with legacy routes while detecting ALL syntax errors
        and safely recoverable AST semantic issues.
        """
        from backend.app.analyzer.ast_remediator import ASTRemediator
        import difflib

        findings: List[FindingSchema] = []

        # Step 1: Multi-Pass Syntax Verification
        syntax_findings = SyntaxChecker.format_all_syntax_errors(self.source_code, self.file_path)
        if syntax_findings:
            findings.extend(syntax_findings)
            # Attempt to obtain a safely recovered AST for semantic analysis
            recovered_code = ASTRemediator.remediate_complete_file(self.source_code, syntax_findings)
            try:
                recovered_tree = ast.parse(recovered_code, filename=self.file_path)
                rec_lines = recovered_code.splitlines(keepends=True)
                
                # Check resource leaks on recoverable code
                res_vis = ResourceLeakVisitor(file_path=self.file_path, lines=rec_lines)
                res_vis.visit(recovered_tree)
                findings.extend(res_vis.findings)

                # Check bugs on recoverable code
                bug_vis = BugDetectionVisitor(file_path=self.file_path, lines=rec_lines)
                bug_vis.visit(recovered_tree)
                findings.extend(bug_vis.findings)
            except Exception:
                pass

            # Attach unified diff and suggested code to all findings
            suggested_code = ASTRemediator.remediate_complete_file(self.source_code, findings)
            diff_lines = list(difflib.unified_diff(
                self.source_code.splitlines(keepends=True),
                suggested_code.splitlines(keepends=True),
                fromfile=f"a/{self.file_path}",
                tofile=f"b/{self.file_path}",
                lineterm=""
            ))
            full_diff = "\n".join(diff_lines)
            for f in findings:
                f.original_code = self.source_code
                f.proposed_code = suggested_code
                f.unified_diff = full_diff

            return findings

        # Step 2: AST Parsing for syntactically clean source
        parse_result = ASTParser.parse_source(self.source_code, filename=self.file_path)
        if not parse_result.success or not parse_result.tree:
            finding = SyntaxChecker.format_syntax_error(
                parse_result.syntax_error, self.file_path, self.source_code
            )
            return [finding]

        tree = parse_result.tree

        # Step 3: Resource Leak Detection Visitor
        res_visitor = ResourceLeakVisitor(file_path=self.file_path, lines=self.lines)
        res_visitor.visit(tree)
        findings.extend(res_visitor.findings)

        # Step 4: Memory Leak Detection Visitor
        mem_visitor = MemoryLeakVisitor(file_path=self.file_path, lines=self.lines)
        mem_visitor.visit(tree)
        findings.extend(mem_visitor.findings)

        # Step 5: Bug Detection Visitor
        bug_visitor = BugDetectionVisitor(file_path=self.file_path, lines=self.lines)
        bug_visitor.visit(tree)
        findings.extend(bug_visitor.findings)

        # Attach complete suggested code and diff
        if findings:
            suggested_code = ASTRemediator.remediate_complete_file(self.source_code, findings)
            diff_lines = list(difflib.unified_diff(
                self.source_code.splitlines(keepends=True),
                suggested_code.splitlines(keepends=True),
                fromfile=f"a/{self.file_path}",
                tofile=f"b/{self.file_path}",
                lineterm=""
            ))
            full_diff = "\n".join(diff_lines)
            for f in findings:
                f.original_code = self.source_code
                f.proposed_code = suggested_code
                f.unified_diff = full_diff

        return findings

    @classmethod
    def run_project_analysis(cls, project_id: str) -> AnalysisReportResponse:
        """
        Executes the complete static analysis pipeline on an entire project workspace.
        """
        from backend.app.services.syntax_service import SyntaxService
        from backend.app.services.workspace_service import WorkspaceService, ProjectNotFoundError

        start_time = time.time()
        project = WorkspaceService.get_project(project_id)
        workspace_dir = WorkspaceService.get_workspace_path(project_id)

        if not workspace_dir.exists():
            raise ProjectNotFoundError(project_id)

        logger.info(f"AnalysisEngine: Starting scan for project '{project_id}' ({project.project_name})")

        # Step 3: Run syntax validation to isolate syntax failures
        syntax_res = SyntaxService.analyze_project_syntax(project_id)

        all_findings: List[FindingSchema] = []
        files_source: Dict[str, str] = {}
        files_suggested: Dict[str, str] = {}

        from backend.app.analyzer.ast_remediator import ASTRemediator
        import difflib

        # Convert syntax errors into formal findings and generate proposed fixes
        syntax_by_file: Dict[str, List[FindingSchema]] = {}
        for err in syntax_res.syntax_errors:
            err_file = (workspace_dir / err.file_path).resolve()
            err_code = ""
            if err_file.is_file():
                try:
                    err_code = err_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    err_code = err.source_snippet
            else:
                err_code = err.source_snippet

            files_source[err.file_path] = err_code

            f_obj = FindingSchema(
                id=f"syn-{uuid.uuid4().hex[:8]}",
                rule_id="SYNTAX001",
                title=f"{err.error_type}: {err.error_message}",
                severity=SeverityEnum.ERROR,
                category="syntax",
                file_path=err.file_path,
                line_number=err.line_number,
                line=err.line_number,
                column=err.column_number,
                description=f"Python syntax compilation error on line {err.line_number}: {err.error_message}.",
                suggestion=err.suggestion or "Correct the syntax error.",
                suggested_fix=err.suggestion or "Correct the syntax error.",
                code_snippet=err.source_snippet,
                problematic_code=err.source_snippet,
                message=err.error_message,
                explanation="Definitive AST compilation failure. Python cannot compile this file.",
                is_potential_warning=False,
                fixable=True,
                original_code=err_code,
                proposed_code="",
                unified_diff=""
            )
            syntax_by_file.setdefault(err.file_path, []).append(f_obj)

        for rel_path, f_list in syntax_by_file.items():
            err_code = files_source.get(rel_path, "")
            suggested_code = ASTRemediator.remediate_complete_file(err_code, f_list)
            files_suggested[rel_path] = suggested_code

            diff_lines = list(difflib.unified_diff(
                err_code.splitlines(keepends=True),
                suggested_code.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm=""
            ))
            full_diff = "\n".join(diff_lines)

            for f in f_list:
                f.original_code = err_code
                f.proposed_code = suggested_code
                f.unified_diff = full_diff

            all_findings.extend(f_list)

            # Also attempt to run visitors on recoverable AST if remediated code compiles
            try:
                rec_tree = ast.parse(suggested_code, filename=rel_path)
                rec_lines = suggested_code.splitlines(keepends=True)
                res_vis = ResourceLeakVisitor(file_path=rel_path, lines=rec_lines)
                res_vis.visit(rec_tree)
                for rf in res_vis.findings:
                    rf.original_code = err_code
                    rf.proposed_code = suggested_code
                    rf.unified_diff = full_diff
                    all_findings.append(rf)

                bug_vis = BugDetectionVisitor(file_path=rel_path, lines=rec_lines)
                bug_vis.visit(rec_tree)
                for bf in bug_vis.findings:
                    bf.original_code = err_code
                    bf.proposed_code = suggested_code
                    bf.unified_diff = full_diff
                    all_findings.append(bf)
            except Exception:
                pass

        # Step 4 & 5: Parse and execute registered AST NodeVisitors on valid files only

        for rel_path in syntax_res.successfully_parsed_files:
            file_path = (workspace_dir / rel_path).resolve()
            if not file_path.is_file():
                continue

            parse_res = ASTParser.parse_file(file_path, relative_path=rel_path)
            if not parse_res.success or not parse_res.tree:
                continue

            lines = parse_res.source_code.splitlines(keepends=True)
            code = parse_res.source_code
            files_source[rel_path] = code

            file_findings: List[FindingSchema] = []

            # Visitor 1: Resource Leak Detection
            res_visitor = ResourceLeakVisitor(file_path=rel_path, lines=lines)
            res_visitor.visit(parse_res.tree)
            file_findings.extend(res_visitor.findings)

            # Visitor 2: Memory-Related Detection
            mem_visitor = MemoryLeakVisitor(file_path=rel_path, lines=lines)
            mem_visitor.visit(parse_res.tree)
            file_findings.extend(mem_visitor.findings)

            # Visitor 3: Bug Detection
            bug_visitor = BugDetectionVisitor(file_path=rel_path, lines=lines)
            bug_visitor.visit(parse_res.tree)
            file_findings.extend(bug_visitor.findings)

            # Generate complete suggested code for this file
            suggested_code = ASTRemediator.remediate_complete_file(code, file_findings) if file_findings else code
            files_suggested[rel_path] = suggested_code

            diff_lines = list(difflib.unified_diff(
                code.splitlines(keepends=True),
                suggested_code.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm=""
            ))
            full_diff = "\n".join(diff_lines)

            # Attach COMPLETE original code, suggested code, and diff to findings
            for f in file_findings:
                f.original_code = code
                f.proposed_code = suggested_code
                f.unified_diff = full_diff

            all_findings.extend(file_findings)

        # Step 6: Compute summary metrics
        syntax_count = sum(1 for f in all_findings if f.category == "syntax")
        leak_count = sum(1 for f in all_findings if f.category == "resource_leak")
        mem_count = sum(1 for f in all_findings if f.category in ("memory", "memory_leak"))
        bug_count = sum(1 for f in all_findings if f.category == "bug")
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
        analysis_id = str(uuid.uuid4())
        status = "completed" if syntax_res.files_with_syntax_errors_count == 0 else "completed_with_errors"

        # Step 7: Generate structured analysis report
        report = AnalysisReportResponse(
            analysis_id=analysis_id,
            project_id=project_id,
            project_name=project.project_name,
            status=status,
            scanned_at=datetime.now().strftime("%I:%M %p, %b %d, %Y"),
            duration_seconds=duration,
            total_files=syntax_res.total_python_files,
            valid_files=syntax_res.successfully_parsed_count,
            syntax_error_files=syntax_res.files_with_syntax_errors_count,
            metrics=metrics,
            findings=all_findings,
            syntax_errors=[e.model_dump() for e in syntax_res.syntax_errors],
            files_source=files_source,
            files_suggested=files_suggested,
        )

        # Cache report in memory
        cls._ANALYSIS_STORE[analysis_id] = report

        # Persist report to workspace disk
        report_file = workspace_dir / "analysis_report.json"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist analysis_report.json: {e}")

        logger.info(
            f"AnalysisEngine: Finished analysis {analysis_id} for {project.project_name} "
            f"({len(all_findings)} findings across {syntax_res.total_python_files} files in {duration}s)"
        )
        return report

    @classmethod
    def get_analysis_report(cls, analysis_id: str) -> Optional[AnalysisReportResponse]:
        """
        Retrieves a completed analysis report by analysis_id.
        """
        if analysis_id in cls._ANALYSIS_STORE:
            return cls._ANALYSIS_STORE[analysis_id]

        from backend.app.services.workspace_service import WorkspaceService

        # Check all workspace directories for analysis_report.json matching analysis_id
        workspaces_root = Path(WorkspaceService.get_workspace_path("dummy")).parent
        if workspaces_root.exists():
            for report_path in workspaces_root.glob("*/analysis_report.json"):
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("analysis_id") == analysis_id:
                            report = AnalysisReportResponse(**data)
                            cls._ANALYSIS_STORE[analysis_id] = report
                            return report
                except Exception:
                    pass

        return None

import ast
from typing import Dict, List, Optional, Tuple
from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.llm.fix_generator import FixGenerator
from backend.app.llm.ollama_client import OllamaClient
from backend.app.schemas.analysis_schema import FindingSchema
from backend.app.schemas.fix_schema import ValidationResultResponse, LLMFixResponse
from backend.app.services.file_service import FileService
from backend.app.utils.logger import logger

class FixServiceError(Exception):
    pass

class FixService:
    """
    Handles fix application, AST-based regression verification,
    and optional LLM-assisted remediation suggestions.
    """

    @classmethod
    def apply_approved_fixes(
        cls,
        files_content: Dict[str, str],
        approved_findings: List[FindingSchema]
    ) -> Dict[str, str]:
        """
        Applies approved fixes to files in descending line order to prevent offset drift.
        """
        patched_files = dict(files_content)

        # Group findings by file path
        findings_by_file: Dict[str, List[FindingSchema]] = {}
        for f in approved_findings:
            if f.fixable and f.proposed_code:
                findings_by_file.setdefault(f.file_path, []).append(f)

        for file_path, findings in findings_by_file.items():
            if file_path not in patched_files:
                continue

            content = patched_files[file_path]
            lines = content.splitlines(keepends=True)

            # Sort descending by line number so line indexes remain valid
            sorted_findings = sorted(findings, key=lambda x: x.line, reverse=True)

            for f in sorted_findings:
                line_idx = f.line - 1
                if 0 <= line_idx < len(lines):
                    replacement = f.proposed_code
                    if not replacement.endswith("\n"):
                        replacement += "\n"
                    lines[line_idx] = replacement

            patched_files[file_path] = "".join(lines)

        return patched_files

    @classmethod
    def validate_fixes(
        cls,
        session_id: str,
        approved_finding_ids: List[str]
    ) -> ValidationResultResponse:
        """
        Re-parses the proposed code with AST and runs static checks to ensure clean, valid code.
        """
        session = FileService.get_session(session_id)
        report = None
        if not session:
            report = AnalysisEngine.get_analysis_report(session_id)
            if not report:
                raise FixServiceError("Analysis session expired or not found.")
            from backend.app.services.workspace_service import WorkspaceService
            workspace_dir = WorkspaceService.get_workspace_path(report.project_id)
            if not workspace_dir.exists():
                raise FixServiceError(f"Workspace for project '{report.project_id}' not found.")
            
            original_files = {}
            for py_file in workspace_dir.rglob("*.py"):
                rel = str(py_file.relative_to(workspace_dir))
                try:
                    original_files[rel] = py_file.read_text(encoding="utf-8")
                except Exception:
                    pass
            findings_map = {f.id: f for f in report.findings}
            approved_findings = [findings_map[fid] for fid in approved_finding_ids if fid in findings_map]
            original_count = len(report.findings)
        else:
            findings_map = {f.id: f for f in session["findings"]}
            approved_findings = [
                findings_map[fid] for fid in approved_finding_ids if fid in findings_map
            ]
            original_files = session["files"]
            original_count = len(session["findings"])

        # Apply approved fixes
        patched_files = cls.apply_approved_fixes(original_files, approved_findings)

        syntax_errors: List[str] = []
        remaining_findings: List[FindingSchema] = []
        validated_files: List[str] = list(patched_files.keys())

        # Step 7: AST Validation & Re-scan
        for file_path, code in patched_files.items():
            try:
                ast.parse(code, filename=file_path)
            except SyntaxError as e:
                syntax_errors.append(f"{file_path}:{e.lineno or 1}: {e.msg}")
                continue

            # Re-scan for remaining issues
            engine = AnalysisEngine(file_path=file_path, source_code=code)
            remaining_findings.extend(engine.analyze())

        is_valid = len(syntax_errors) == 0
        remaining_count = len(remaining_findings)
        fixed_count = max(0, original_count - remaining_count)

        # Update session with patched content if session exists
        if session:
            session["patched_files"] = patched_files
            session["approved_finding_ids"] = approved_finding_ids
            FileService.save_session(session_id, session)

        logger.info(
            f"Fix validation for session {session_id}: valid={is_valid}, "
            f"fixed={fixed_count}, remaining={remaining_count}"
        )

        return ValidationResultResponse(
            is_valid=is_valid,
            validated_files=validated_files,
            syntax_errors=syntax_errors,
            fixed_count=fixed_count,
            remaining_count=remaining_count,
            remaining_findings=remaining_findings,
        )

    @classmethod
    async def generate_llm_fix(
        cls,
        rule_id: str,
        code_snippet: str,
        file_path: str,
        context: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> LLMFixResponse:
        """
        Uses local Ollama LLM to propose an intelligent code fix.
        """
        prompt = FixGenerator.create_fix_prompt(
            rule_id=rule_id,
            code_snippet=code_snippet,
            file_path=file_path,
            context=context,
            custom_instructions=custom_instructions
        )

        ollama = OllamaClient()
        response_text = await ollama.generate(prompt=prompt)
        parsed = FixGenerator.parse_llm_response(response_text)

        diff = FixGenerator.build_unified_diff(
            file_path=file_path,
            original=code_snippet,
            replacement=parsed["suggested_code"]
        )

        return LLMFixResponse(
            rule_id=rule_id,
            explanation=parsed["explanation"],
            suggested_code=parsed["suggested_code"],
            diff=diff,
            model_used=ollama.model
        )


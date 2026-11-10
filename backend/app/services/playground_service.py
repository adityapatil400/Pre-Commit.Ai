import ast
import uuid
from typing import List, Optional

from backend.app.analyzer.analysis_engine import AnalysisEngine
from backend.app.llm.fix_generator import LLMFixGenerator
from backend.app.schemas.analysis_schema import FindingSchema, SeverityEnum
from backend.app.schemas.playground_schema import (
    PlaygroundIssue,
    PlaygroundMetrics,
    PlaygroundAnalysisResult,
    PlaygroundFixResponse,
    PlaygroundFixExplanation,
    PlaygroundRunAndAnalyzeResponse,
    PlaygroundAssistantResponse,
    PlaygroundOllamaStatusResponse,
)
from backend.app.services.playground_runner import PlaygroundRunner
from backend.app.utils.logger import logger

class PlaygroundService:
    """
    Coordinates Python Playground execution, AST static analysis, and Ollama AI code fixing.
    """

    @classmethod
    def analyze_code(cls, code: str, filename: str = "playground.py") -> PlaygroundAnalysisResult:
        if not code or not code.strip():
            return PlaygroundAnalysisResult(
                total_issues=0,
                metrics=PlaygroundMetrics(
                    total_issues=0,
                    syntax_errors=0,
                    potential_bugs=0,
                    resource_leaks=0,
                    risk_score=100
                ),
                issues=[]
            )

        engine = AnalysisEngine(file_path=filename, source_code=code)
        raw_findings: List[FindingSchema] = engine.analyze()

        issues: List[PlaygroundIssue] = []
        syntax_count = 0
        bug_count = 0
        resource_count = 0
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        for f in raw_findings:
            # Map severity
            sev_str = "Medium"
            cat = (f.category or "").lower()
            rule = (f.rule_id or "").upper()

            if cat == "syntax" or (f.severity == SeverityEnum.ERROR and ("RES" in rule or "SYN" in rule)):
                sev_str = "Critical"
                critical_count += 1
            elif f.severity == SeverityEnum.ERROR:
                sev_str = "High"
                high_count += 1
            elif f.severity == SeverityEnum.WARNING:
                sev_str = "Medium"
                medium_count += 1
            else:
                sev_str = "Low"
                low_count += 1

            # Map type
            type_str = "Code Issue"
            if cat == "syntax":
                type_str = "Syntax Error"
                syntax_count += 1
            elif cat == "resource_leak":
                type_str = "Resource Leak"
                resource_count += 1
            elif cat in ("memory", "memory_leak"):
                type_str = "Memory Leak"
                resource_count += 1
            elif cat == "bug":
                type_str = "Bug"
                bug_count += 1

            snippet = f.problematic_code or f.code_snippet or ""
            desc = f.description or f.title or "Detected code issue"
            sugg = f.suggestion or f.suggested_fix or "Review and correct the statement."

            issues.append(PlaygroundIssue(
                id=f.id or f"iss-{uuid.uuid4().hex[:8]}",
                severity=sev_str,
                type=type_str,
                line=f.line or f.line_number or 1,
                column=f.column or 1,
                problematic_code=snippet,
                description=desc,
                suggestion=sugg,
                rule_id=f.rule_id
            ))

        # Calculate Risk Score (100 is best, decreases with issue severity)
        penalty = (critical_count * 30) + (high_count * 15) + (medium_count * 5) + (low_count * 2)
        risk_score = max(0, 100 - penalty)

        metrics = PlaygroundMetrics(
            total_issues=len(issues),
            syntax_errors=syntax_count,
            potential_bugs=bug_count,
            resource_leaks=resource_count,
            risk_score=risk_score
        )

        return PlaygroundAnalysisResult(
            total_issues=len(issues),
            metrics=metrics,
            issues=issues
        )

    @classmethod
    async def generate_fix(
        cls,
        code: str,
        issue_id: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> PlaygroundFixResponse:
        engine = AnalysisEngine(file_path="playground.py", source_code=code)
        findings = engine.analyze()

        target_findings = findings
        if issue_id:
            matching = [f for f in findings if f.id == issue_id]
            if matching:
                target_findings = matching

        # Invoke Ollama / ASTRemediator
        file_fix_res = await LLMFixGenerator.generate_complete_file_fix(
            file_path="playground.py",
            original_code=code,
            issues=target_findings,
            custom_instructions=custom_instructions
        )

        # Convert remaining issues to PlaygroundIssue
        unres: List[PlaygroundIssue] = []
        for r in file_fix_res.unresolved_issues:
            unres.append(PlaygroundIssue(
                id=f"unres-{uuid.uuid4().hex[:8]}",
                severity=r.severity,
                type=r.type,
                line=r.line,
                column=1,
                problematic_code="",
                description=r.description,
                suggestion=r.suggestion,
                rule_id=r.rule_id
            ))

        return PlaygroundFixResponse(
            original_code=file_fix_res.original_code,
            suggested_code=file_fix_res.suggested_code,
            corrected_code=file_fix_res.suggested_code,
            diff=file_fix_res.diff,
            ai_model=file_fix_res.ai_model,
            is_valid=file_fix_res.is_valid,
            validation_errors=file_fix_res.validation_errors,
            explanation=PlaygroundFixExplanation(
                what_is_error=file_fix_res.explanation.what_is_error,
                how_it_is_fixed=file_fix_res.explanation.how_it_is_fixed,
                why_it_is_correct=file_fix_res.explanation.why_it_is_correct,
                side_effects=file_fix_res.explanation.side_effects
            ),
            fixes_applied=file_fix_res.fixes_applied,
            unresolved_issues=unres
        )

    @classmethod
    def run_and_analyze(
        cls,
        code: str,
        timeout_seconds: float = 5.0,
        stdin_input: str = ""
    ) -> PlaygroundRunAndAnalyzeResponse:
        # 1. Execute safely in isolated sandbox
        exec_result = PlaygroundRunner.execute_code(
            code=code,
            timeout_seconds=timeout_seconds,
            stdin_input=stdin_input
        )

        # 2. Analyze statically with AST
        analysis_result = cls.analyze_code(code)

        return PlaygroundRunAndAnalyzeResponse(
            execution=exec_result,
            analysis=analysis_result
        )

    @classmethod
    async def check_ollama_status(cls) -> PlaygroundOllamaStatusResponse:
        from backend.app.llm.ollama_client import ollama_client
        connected = await ollama_client.is_available()
        return PlaygroundOllamaStatusResponse(
            connected=connected,
            model=ollama_client.model,
            base_url=ollama_client.base_url
        )

    @classmethod
    async def ask_assistant(
        cls,
        prompt: str,
        code: str = "",
        filename: str = "main.py",
        history: Optional[List[dict]] = None
    ) -> PlaygroundAssistantResponse:
        from backend.app.llm.ollama_client import ollama_client
        system_prompt = (
            "You are an expert Python programming assistant embedded in the PreCommit AI VS Code Playground. "
            "You help developers understand AST static analysis findings, fix syntax errors, resource leaks, "
            "and memory retention issues, optimize Python code, and write clean, PEP 8 compliant code. "
            "Be clear, concise, and professional. Provide code examples in markdown code blocks."
        )

        user_content = f"Active File: `{filename}`\n"
        if code.strip():
            user_content += f"```python\n{code}\n```\n\n"
        user_content += f"Question / Request:\n{prompt}"

        is_up = await ollama_client.is_available()
        if not is_up:
            lower_q = prompt.lower()
            if "leak" in lower_q or "resource" in lower_q:
                answer = (
                    "### Resource Leak Analysis\n\n"
                    "In Python, resource leaks occur when operating system resources (such as file descriptors, "
                    "sockets, or database connections) are acquired without guaranteed cleanup.\n\n"
                    "**Recommended Solution:**\n"
                    "Always use context managers (`with` statements):\n"
                    "```python\nwith open('filename.txt', 'r') as f:\n    data = f.read()\n```\n"
                    "The `with` statement ensures `f.close()` is called automatically, even if an exception occurs."
                )
            elif "syntax" in lower_q or "error" in lower_q:
                answer = (
                    "### Syntax Error Explanation\n\n"
                    "Python's syntax parser requires valid syntax before bytecode compilation. Common mistakes include:\n"
                    "- Missing colons `:` after `def`, `if`, `for`, `while`, or `class` statements.\n"
                    "- Unbalanced parentheses `()`, brackets `[]`, or braces `{}`.\n"
                    "- Indentation inconsistencies (mixing spaces and tabs).\n\n"
                    "Check the **Problems** tab at the bottom of the editor to jump directly to the flagged line numbers."
                )
            else:
                answer = (
                    f"I analyzed your code in `{filename}`. To enable live LLM assistance, "
                    f"ensure Ollama is running locally with the `{ollama_client.model}` model (`ollama run {ollama_client.model}`). "
                    "PreCommit AI's AST static analysis engine remains fully operational."
                )
            return PlaygroundAssistantResponse(answer=answer, model="PreCommit AI Assistant")

        try:
            res_text = await ollama_client.generate(
                prompt=user_content,
                system=system_prompt,
                temperature=0.2
            )
            return PlaygroundAssistantResponse(answer=res_text, model=f"Ollama ({ollama_client.model})")
        except Exception as e:
            return PlaygroundAssistantResponse(
                answer=f"Could not reach Ollama: {str(e)}. Please check your Ollama configuration.",
                model="Error"
            )



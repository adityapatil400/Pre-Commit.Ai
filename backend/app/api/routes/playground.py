from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.playground_schema import (
    PlaygroundRunRequest,
    PlaygroundExecutionResult,
    PlaygroundAnalyzeRequest,
    PlaygroundAnalysisResult,
    PlaygroundFixRequest,
    PlaygroundFixResponse,
    PlaygroundRunAndAnalyzeResponse,
    PlaygroundAssistantRequest,
    PlaygroundAssistantResponse,
    PlaygroundOllamaStatusResponse,
)
from backend.app.services.playground_runner import PlaygroundRunner
from backend.app.services.playground_service import PlaygroundService
from backend.app.utils.logger import logger

router = APIRouter(prefix="/playground", tags=["Python Playground"])

@router.post(
    "/run",
    response_model=PlaygroundExecutionResult,
    summary="Safely execute Python code in an isolated sandbox"
)
async def run_playground_code(req: PlaygroundRunRequest):
    """
    Executes Python source code inside a secure, ephemeral subprocess sandbox:
    - Zero execution inside the main FastAPI process.
    - Stripped environment (no host application secrets, DB keys, or tokens).
    - Isolated directory with strict timeout (0.5s - 10.0s).
    - Returns stdout, stderr, exit code, and execution time.
    """
    try:
        return PlaygroundRunner.execute_code(
            code=req.code,
            timeout_seconds=req.timeout_seconds,
            stdin_input=req.stdin_input or ""
        )
    except Exception as e:
        logger.error(f"Playground run endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(e)}"
        )

@router.post(
    "/analyze",
    response_model=PlaygroundAnalysisResult,
    summary="Perform static AST analysis on Playground Python code"
)
async def analyze_playground_code(req: PlaygroundAnalyzeRequest):
    """
    Statically analyzes Python source code without executing it:
    - Detects syntax errors across multiple passes.
    - Detects potential resource leaks (unclosed files, connections).
    - Detects memory leak patterns and static bugs.
    - Returns structured issue list, metrics, and health risk score.
    """
    try:
        return PlaygroundService.analyze_code(
            code=req.code,
            filename=req.filename or "playground.py"
        )
    except Exception as e:
        logger.error(f"Playground analyze endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis error: {str(e)}"
        )

@router.post(
    "/fix",
    response_model=PlaygroundFixResponse,
    summary="Generate AI-powered code fix using Ollama or ASTRemediator"
)
async def fix_playground_code(req: PlaygroundFixRequest):
    """
    Generates AI-powered remediation proposals for Playground code:
    - Retains original functionality while fixing all reported issues.
    - Statically validates that suggested code compiles with AST.
    - Returns structured explanation (what, how, why, side-effects) and unified diff.
    """
    try:
        return await PlaygroundService.generate_fix(
            code=req.code,
            issue_id=req.issue_id,
            custom_instructions=req.custom_instructions
        )
    except Exception as e:
        logger.error(f"Playground fix endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fix generation error: {str(e)}"
        )

@router.post(
    "/run-and-analyze",
    response_model=PlaygroundRunAndAnalyzeResponse,
    summary="Simultaneously execute and statically analyze Python code"
)
async def run_and_analyze_playground_code(req: PlaygroundRunRequest):
    """
    Runs both isolated execution and static AST analysis, returning independent results.
    """
    try:
        return PlaygroundService.run_and_analyze(
            code=req.code,
            timeout_seconds=req.timeout_seconds,
            stdin_input=req.stdin_input or ""
        )
    except Exception as e:
        logger.error(f"Playground run-and-analyze endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Run & analyze error: {str(e)}"
        )

@router.get(
    "/ollama-status",
    response_model=PlaygroundOllamaStatusResponse,
    summary="Check status of Ollama connection and current model"
)
async def check_ollama_status():
    """
    Returns connectivity status and model info for the local Ollama LLM service.
    """
    try:
        return await PlaygroundService.check_ollama_status()
    except Exception as e:
        logger.error(f"Playground ollama status check error: {e}", exc_info=True)
        return PlaygroundOllamaStatusResponse(
            connected=False,
            model="unknown",
            base_url="unknown"
        )

@router.post(
    "/assistant",
    response_model=PlaygroundAssistantResponse,
    summary="Interactive AI Assistant for questions and code explanations"
)
async def ask_playground_assistant(req: PlaygroundAssistantRequest):
    """
    Answers questions about the active Python code, explaining errors,
    suggesting optimizations, or generating functions using Ollama.
    """
    try:
        return await PlaygroundService.ask_assistant(
            prompt=req.prompt,
            code=req.code,
            filename=req.filename or "main.py",
            history=req.history or []
        )
    except Exception as e:
        logger.error(f"Playground assistant error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant error: {str(e)}"
        )



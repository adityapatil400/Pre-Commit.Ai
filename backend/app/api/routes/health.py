import sys
from datetime import datetime
from fastapi import APIRouter
from backend.app.config import Settings
from backend.app.schemas.analysis_schema import HealthResponse
from backend.app.llm.ollama_client import OllamaClient

router = APIRouter(tags=["Health & System"])
settings = Settings()

@router.get("/health", response_model=HealthResponse, summary="System Health Check")
async def health_check():
    """
    Returns system status, Python runtime version, application version,
    and checks connectivity to the local Ollama LLM engine.
    """
    ollama_client = OllamaClient()
    ollama_ok = await ollama_client.check_health()
    ollama_status = "connected" if ollama_ok else "unavailable (offline)"

    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.VERSION,
        timestamp=datetime.now().isoformat(),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ollama_status=ollama_status,
    )


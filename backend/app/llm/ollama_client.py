import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import settings
from backend.app.utils.logger import logger

class LLMError(Exception):
    """Base exception for all LLM client errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class OllamaConnectionError(LLMError):
    """Raised when the Ollama server is unreachable."""
    def __init__(self, url: str):
        super().__init__(
            f"Ollama LLM service is unreachable at '{url}'. Ensure Ollama is running (`ollama serve`).",
            status_code=503
        )

class ModelUnavailableError(LLMError):
    """Raised when the specified model is not downloaded or available in Ollama."""
    def __init__(self, model: str):
        super().__init__(
            f"Ollama model '{model}' is not installed or available. Run `ollama pull {model}` to download it.",
            status_code=503
        )

class LLMTimeoutError(LLMError):
    """Raised when an LLM generation request times out."""
    def __init__(self, timeout_seconds: float):
        super().__init__(
            f"LLM request timed out after {timeout_seconds} seconds.",
            status_code=504
        )

class LLMResponseError(LLMError):
    """Raised when the LLM returns an error status code or malformed payload."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)

class BaseLLMClient(ABC):
    """
    Abstract interface for LLM providers.
    Allows easy extension to other providers (OpenAI, Anthropic, vLLM, etc.).
    """

    @abstractmethod
    async def is_available(self) -> bool:
        """Checks if the LLM provider service is active and responsive."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_format: bool = False
    ) -> str:
        """Generates a text completion for a given prompt."""
        pass

class OllamaClient(BaseLLMClient):
    """
    Modular client for interacting with a local Ollama LLM server.
    Configured via environment variables OLLAMA_BASE_URL and OLLAMA_MODEL.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        raw_url = base_url or os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)
        self.base_url = raw_url.rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", settings.OLLAMA_MODEL)
        self.timeout = timeout or float(os.getenv("OLLAMA_TIMEOUT_SECONDS", str(settings.OLLAMA_TIMEOUT_SECONDS)))

    async def is_available(self) -> bool:
        """
        Pings Ollama /api/tags to verify connectivity.
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def check_health(self) -> bool:
        """Alias for is_available()."""
        return await self.is_available()

    async def list_models(self) -> List[str]:
        """
        Returns a list of all model names installed locally in Ollama.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Failed to list Ollama models: {e}")
        return []

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_format: bool = False,
        temperature: float = 0.1
    ) -> str:
        """
        Sends an inference request to Ollama /api/generate.
        Supports structured JSON mode and low temperature for reliable code generation.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system:
            payload["system"] = system
        if json_format:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
        except httpx.ConnectError:
            raise OllamaConnectionError(self.base_url)
        except httpx.TimeoutException:
            raise LLMTimeoutError(self.timeout)
        except httpx.RequestError as e:
            raise LLMResponseError(f"Network error communicating with Ollama: {str(e)}")

        if res.status_code == 404:
            raise ModelUnavailableError(self.model)
        elif res.status_code != 200:
            raise LLMResponseError(
                f"Ollama returned HTTP {res.status_code}: {res.text[:200]}",
                status_code=res.status_code
            )

        try:
            data = res.json()
            response_text = data.get("response", "")
            if not response_text:
                raise LLMResponseError("Ollama returned an empty response string.")
            return response_text
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMResponseError(f"Failed to decode Ollama response JSON: {str(e)}")

ollama_client = OllamaClient()

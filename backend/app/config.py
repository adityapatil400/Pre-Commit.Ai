import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application Settings using Pydantic Settings.
    Loads configurations from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # Core Application Configuration
    APP_NAME: str = "PreCommit AI (LeakGuard)"
    APP_ENV: str = "development"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # GitHub Configuration
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE_URL: str = "https://api.github.com"

    # Ollama Local LLM Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0

    # File and Upload Limits
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_FILE_SIZE_MB: int = 10
    MAX_PROJECT_FILES: int = 1000
    WORKSPACE_EXPIRY_HOURS: int = 24
    TEMP_DIR: str = "/tmp/precommit_ai"

    # Ignored directories during discovery & extraction
    IGNORED_DIRS: List[str] = [
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
        "build",
        "dist",
        ".eggs",
    ]

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def workspaces_dir(self) -> str:
        path = os.path.join(self.TEMP_DIR, "workspaces")
        os.makedirs(path, exist_ok=True)
        return path

settings = Settings()

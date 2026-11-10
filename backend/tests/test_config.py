import pytest
from backend.app.config import Settings

def test_settings_defaults():
    settings = Settings()
    assert settings.APP_NAME == "PreCommit AI (LeakGuard)"
    assert settings.PORT == 8000
    assert settings.MAX_UPLOAD_SIZE_MB == 50
    assert settings.max_upload_size_bytes == 50 * 1024 * 1024
    assert isinstance(settings.CORS_ORIGINS, list)
    assert any("5173" in origin for origin in settings.CORS_ORIGINS)

def test_cors_origins_parsing():
    settings = Settings(CORS_ORIGINS="http://localhost:5173,http://localhost:3000")
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) == 2
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://localhost:3000" in settings.CORS_ORIGINS


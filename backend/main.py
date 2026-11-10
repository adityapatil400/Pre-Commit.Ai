"""
PreCommit AI (LeakGuard) - Backend Entrypoint
Delegates to the modular FastAPI application in backend.app.main.
"""
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    from backend.app.config import Settings
    settings = Settings()
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

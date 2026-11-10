import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app.config import Settings
from backend.app.utils.logger import logger
from backend.app.api.routes import health, analysis, upload, github, fixes, commits, projects, playground

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION} [{settings.APP_ENV}]")
    logger.info(f"Ollama Target URL: {settings.OLLAMA_BASE_URL} (Model: {settings.OLLAMA_MODEL})")
    logger.info(f"CORS Allowed Origins: {settings.CORS_ORIGINS}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

tags_metadata = [
    {
        "name": "Health & System",
        "description": "System health checks, runtime metrics, and LLM connection status.",
    },
    {
        "name": "Analysis",
        "description": "AST-based static code analysis pipeline across Python files, ZIPs, or GitHub repositories.",
    },
    {
        "name": "Upload",
        "description": "Safe upload and in-memory archive extraction with Zip-Slip protection.",
    },
    {
        "name": "GitHub",
        "description": "GitHub repository integration and archive fetching via GitHub API.",
    },
    {
        "name": "Fixes & Remediation",
        "description": "Code fix application, AST regression validation, and Ollama LLM fix generation.",
    },
    {
        "name": "Commits & Export",
        "description": "Automated GitHub commit creation and patched project archive export.",
    },
    {
        "name": "Project Input Module",
        "description": "Project input module: ZIP archives, Python files, and GitHub cloning into isolated workspaces.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "### PreCommit AI (LeakGuard) Backend API\n\n"
        "Python AST-based static code analyzer detecting syntax errors, bugs, and potential "
        "resource or memory leaks with fix recommendations and automated GitHub commits."
    ),
    version=settings.VERSION,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --------------------------------------------------------------------------
# CORS Configuration for React Frontend
# --------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Request Logging Middleware
# --------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)"
    )
    return response

# --------------------------------------------------------------------------
# API Routes Mounting
# --------------------------------------------------------------------------
# Mount health check at both /api/health and /health
app.include_router(health.router, prefix="/api")
app.include_router(health.router)

# Mount core analysis routes at /api
app.include_router(analysis.router, prefix="/api")

# Mount upload and github services at /api
app.include_router(upload.router, prefix="/api")
app.include_router(github.router, prefix="/api")

# Mount fix and commit services at /api and top-level
app.include_router(fixes.router, prefix="/api")
app.include_router(fixes.router)
app.include_router(commits.router, prefix="/api")
app.include_router(commits.router)

# Mount project input module (/api/v1/upload, /api/v1/github/clone, /api/v1/projects/{project_id})
app.include_router(projects.router)

# Mount Python Playground routes (/api/playground, /api/v1/playground, /playground)
app.include_router(playground.router, prefix="/api")
app.include_router(playground.router, prefix="/api/v1")
app.include_router(playground.router)

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to Swagger UI documentation."""
    return RedirectResponse(url="/docs")


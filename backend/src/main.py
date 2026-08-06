"""ProTech NAS — FastAPI Backend Entry Point."""

import os
import subprocess
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .database import init_db
from .logging_config import setup_logging
from .routers.dashboard import router as dashboard_router
from .routers.storage import router as storage_router
from .routers.shares import router as shares_router
from .routers.docker_mgr import router as docker_router
from .routers.users import router as users_router, auth_router as users_auth_router
from .routers.files import router as files_router
from .routers.system import router as system_router, dashboard_router as system_dashboard_router
from .routers.network import router as network_router
from .routers.backup import router as backup_router
from .routers.remote import router as remote_router
from .routers.notifications import router as notifications_router


# ─── Version Info ─────────────────────────────────────────────────────────────

def _read_version() -> str:
    """Read version from VERSION file."""
    # Try project root (relative to this file: src/main.py → ../../VERSION)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    version_file = os.path.join(base, "..", "VERSION")
    try:
        with open(os.path.abspath(version_file)) as f:
            return f.read().strip()
    except FileNotFoundError:
        pass
    # Try OTA_APP_DIR
    app_dir = os.getenv("OTA_APP_DIR", "/opt/protech-nas")
    try:
        with open(os.path.join(app_dir, "VERSION")) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


def _read_git_hash() -> str:
    """Read git short hash."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.abspath(os.path.join(base, ".."))
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=project_root,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


APP_VERSION = _read_version()
APP_GIT_HASH = _read_git_hash()

# Initialize structured logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("LOG_FORMAT", "console") == "json",
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Import models so Base.metadata knows all tables
    import src.models  # noqa: F401
    await init_db()

    # Start backup scheduler
    from .scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()

    logger.info("app_started", version=APP_VERSION, git_hash=APP_GIT_HASH)
    yield

    # Shutdown scheduler gracefully
    shutdown_scheduler()
    logger.info("app_shutdown")


app = FastAPI(
    title="ProTech NAS",
    description="NAS 管理系統 — 儲存 / 共享 / Docker / 使用者管理",
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow Vue.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Add request_id to structlog context for request tracing."""
    import uuid
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)

    # Log non-health requests
    if request.url.path not in ("/api/health", "/"):
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
    return response

# Mount routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(storage_router)
app.include_router(shares_router)
app.include_router(docker_router)
app.include_router(users_router)
app.include_router(users_auth_router)
app.include_router(files_router)
app.include_router(system_router)
app.include_router(system_dashboard_router)
app.include_router(network_router)
app.include_router(backup_router)
app.include_router(remote_router)
app.include_router(notifications_router)


@app.get("/")
def root():
    return {"status": "ok", "service": "protech-nas", "version": APP_VERSION, "git_hash": APP_GIT_HASH}


@app.get("/api/health")
def health():
    return {"status": "healthy", "version": APP_VERSION, "git_hash": APP_GIT_HASH}

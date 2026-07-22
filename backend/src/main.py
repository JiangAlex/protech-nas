"""ProTech NAS — FastAPI Backend Entry Point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .database import init_db
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Import models so Base.metadata knows all tables
    import src.models  # noqa: F401
    await init_db()
    yield


app = FastAPI(
    title="ProTech NAS",
    description="NAS 管理系統 — 儲存 / 共享 / Docker / 使用者管理",
    version="0.1.0",
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
    return {"status": "ok", "service": "protech-nas", "version": "0.1.0"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}

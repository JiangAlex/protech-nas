"""ProTech NAS — FastAPI Backend Entry Point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .routers.dashboard import router as dashboard_router
from .routers.storage import router as storage_router
from .routers.shares import router as shares_router
from .routers.docker_mgr import router as docker_router
from .routers.users import router as users_router

app = FastAPI(
    title="ProTech NAS",
    description="NAS 管理系統 — 儲存 / 共享 / Docker / 使用者管理",
    version="0.1.0",
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


@app.get("/")
def root():
    return {"status": "ok", "service": "protech-nas", "version": "0.1.0"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}

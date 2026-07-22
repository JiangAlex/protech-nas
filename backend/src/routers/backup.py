"""Backup router — backup task management API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.backup_service import (
    list_backup_tasks, create_backup_task, run_backup,
    update_backup_task, delete_backup_task, get_backup_history,
    restore_backup, schedule_backup,
    list_snapshots, create_snapshot, delete_snapshot
)

router = APIRouter(prefix="/api/backup", tags=["backup"])


class BackupTaskCreate(BaseModel):
    name: str
    source: str
    destination: str
    schedule: Optional[str] = ""
    retention_days: int = 30
    method: str = "rsync"


@router.get("/tasks")
async def get_tasks(user=Depends(get_current_user)):
    """List all backup tasks."""
    return list_backup_tasks()


@router.post("/tasks")
async def post_task(task: BackupTaskCreate, user=Depends(get_current_user)):
    """Create a new backup task."""
    result = create_backup_task(task.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/tasks/{task_id}/run")
async def post_run(task_id: str, user=Depends(get_current_user)):
    """Execute a backup task immediately."""
    result = run_backup(task_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class BackupTaskUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    schedule: Optional[str] = None
    retention_days: Optional[int] = None


class RestoreRequest(BaseModel):
    task_id: str
    version: str
    target_path: Optional[str] = None


class ScheduleRequest(BaseModel):
    cron_expr: str


@router.put("/tasks/{task_id}")
async def put_task(task_id: str, data: BackupTaskUpdate, user=Depends(get_current_user)):
    """Update an existing backup task."""
    config = {k: v for k, v in data.model_dump().items() if v is not None}
    result = update_backup_task(task_id, config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/tasks/{task_id}")
async def del_task(task_id: str, user=Depends(get_current_user)):
    """Delete a backup task (data preserved)."""
    result = delete_backup_task(task_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/tasks/{task_id}/history")
async def get_history(task_id: str, user=Depends(get_current_user)):
    """Get backup execution history."""
    result = get_backup_history(task_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/restore")
async def post_restore(data: RestoreRequest, user=Depends(get_current_user)):
    """Restore a backup version."""
    result = restore_backup(data.task_id, data.version, data.target_path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/tasks/{task_id}/schedule")
async def put_schedule(task_id: str, data: ScheduleRequest, user=Depends(get_current_user)):
    """Update backup task schedule."""
    result = schedule_backup(task_id, data.cron_expr)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Snapshots ───────────────────────────────────────────────────────────────


class SnapshotCreate(BaseModel):
    subvol: str


@router.get("/snapshots")
async def get_snapshots(user=Depends(get_current_user)):
    """List all filesystem snapshots."""
    return list_snapshots()


@router.post("/snapshots")
async def post_snapshot(data: SnapshotCreate, user=Depends(get_current_user)):
    """Create a new filesystem snapshot."""
    result = create_snapshot(data.subvol)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/snapshots/{path:path}")
async def del_snapshot(path: str, user=Depends(get_current_user)):
    """Delete a filesystem snapshot."""
    result = delete_snapshot(path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

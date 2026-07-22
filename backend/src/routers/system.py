"""System router — logs, power management, temperature API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.system_service import (
    get_system_logs, power_action, get_temperatures,
    list_services, control_service, update_system_settings, get_hardware_info,
    check_updates, apply_updates,
    list_cron_jobs, add_cron_job, remove_cron_job, record_metrics, get_metrics_history
)

router = APIRouter(prefix="/api/system", tags=["system"])


class PowerRequest(BaseModel):
    action: str  # "shutdown" or "reboot"


@router.get("/logs")
async def get_logs(
    unit: Optional[str] = Query(None),
    lines: int = Query(100, ge=1, le=5000),
    since: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    """Get system logs from journalctl."""
    result = get_system_logs(unit=unit, lines=lines, since=since)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/power/shutdown")
async def post_shutdown(user=Depends(get_current_user)):
    """Shut down the system. WARNING: Immediate."""
    result = power_action("shutdown")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/power/reboot")
async def post_reboot(user=Depends(get_current_user)):
    """Reboot the system. WARNING: Immediate."""
    result = power_action("reboot")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/temperature")
async def get_temp(user=Depends(get_current_user)):
    """Get CPU and disk temperatures."""
    result = get_temperatures()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


class ServiceAction(BaseModel):
    action: str  # start/stop/restart/enable/disable


class SystemSettings(BaseModel):
    hostname: Optional[str] = None
    timezone: Optional[str] = None
    ntp_enabled: Optional[bool] = None


class UpdateApply(BaseModel):
    packages: Optional[list] = None


@router.get("/services")
async def get_services(user=Depends(get_current_user)):
    """List systemd services."""
    return list_services()


@router.post("/services/{name}/{action}")
async def post_service_action(name: str, action: str, user=Depends(get_current_user)):
    """Start/stop/restart/enable/disable a service."""
    result = control_service(name, action)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/settings")
async def put_settings(data: SystemSettings, user=Depends(get_current_user)):
    """Update system settings (hostname, timezone, NTP)."""
    config = {k: v for k, v in data.model_dump().items() if v is not None}
    if not config:
        raise HTTPException(status_code=422, detail="No settings provided")
    result = update_system_settings(config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/hardware")
async def get_hardware(user=Depends(get_current_user)):
    """Get detailed hardware information."""
    return get_hardware_info()


@router.get("/updates")
async def get_updates(user=Depends(get_current_user)):
    """Check for available updates."""
    result = check_updates()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/updates/apply")
async def post_apply_updates(data: UpdateApply = UpdateApply(), user=Depends(get_current_user)):
    """Apply system updates."""
    result = apply_updates(data.packages)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Cron Jobs ───────────────────────────────────────────────────────────────


class CronJobCreate(BaseModel):
    schedule: str
    command: str


@router.get("/cron")
async def get_cron_jobs(user=Depends(get_current_user)):
    """List all cron jobs."""
    return list_cron_jobs()


@router.post("/cron")
async def post_cron_job(data: CronJobCreate, user=Depends(get_current_user)):
    """Add a new cron job."""
    result = add_cron_job(data.schedule, data.command)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/cron/{job_id}")
async def del_cron_job(job_id: str, user=Depends(get_current_user)):
    """Remove a cron job."""
    result = remove_cron_job(job_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Metrics ─────────────────────────────────────────────────────────────────

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.post("/metrics/record")
async def post_record_metrics(user=Depends(get_current_user)):
    """Record current system metrics snapshot."""
    result = record_metrics()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@dashboard_router.get("/history")
async def get_dashboard_history(hours: int = Query(24, ge=1, le=720), user=Depends(get_current_user)):
    """Get historical system metrics."""
    result = get_metrics_history(hours=hours)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

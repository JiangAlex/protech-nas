"""Storage router — disk, RAID, mount management API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.storage_service import (
    list_disks, list_mounts, get_raid_status, mount_disk, unmount_disk,
    format_disk, get_smart_info, run_smart_test
)

router = APIRouter(prefix="/api/storage", tags=["storage"])


class MountRequest(BaseModel):
    device: str
    mount_point: str
    fs_type: Optional[str] = "ext4"


@router.get("/disks")
async def get_disks(user=Depends(get_current_user)):
    """List all disks and partitions."""
    return list_disks()


@router.get("/mounts")
async def get_mounts(user=Depends(get_current_user)):
    """List all mount points."""
    return list_mounts()


@router.get("/raid")
async def get_raid(user=Depends(get_current_user)):
    """Get RAID array status."""
    return get_raid_status()


@router.post("/mount")
async def post_mount(req: MountRequest, user=Depends(get_current_user)):
    """Mount a device."""
    result = mount_disk(req.device, req.mount_point, req.fs_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/unmount")
async def post_unmount(req: MountRequest, user=Depends(get_current_user)):
    """Unmount a device."""
    result = unmount_disk(req.mount_point)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class FormatRequest(BaseModel):
    device: str
    fs_type: str


class SmartTestRequest(BaseModel):
    test_type: str = "short"


@router.post("/format")
async def post_format(req: FormatRequest, user=Depends(get_current_user)):
    """Format a disk partition. WARNING: Irreversible."""
    result = format_disk(req.device, req.fs_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/smart/{device:path}")
async def get_smart(device: str, user=Depends(get_current_user)):
    """Get S.M.A.R.T. health info for a device."""
    # device comes URL-decoded, e.g. "dev/sda" -> prepend /
    if not device.startswith("/"):
        device = f"/{device}"
    result = get_smart_info(device)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/smart/{device:path}/test")
async def post_smart_test(device: str, req: SmartTestRequest, user=Depends(get_current_user)):
    """Run a S.M.A.R.T. self-test."""
    if not device.startswith("/"):
        device = f"/{device}"
    result = run_smart_test(device, req.test_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

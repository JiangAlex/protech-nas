"""Versioning router — file version control API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

from ..auth import get_current_user
from ..services.versioning_service import (
    create_snapshot, list_versions, get_version, restore_version,
    delete_version, get_version_file, compare_versions,
)

router = APIRouter(prefix="/api/versions", tags=["versions"])


class SnapshotRequest(BaseModel):
    path: str
    comment: str = ""


class RestoreRequest(BaseModel):
    path: str
    version_id: str


class DeleteVersionRequest(BaseModel):
    path: str
    version_id: str


class CompareRequest(BaseModel):
    path: str
    version_id_a: str
    version_id_b: str


@router.post("/snapshot")
async def post_snapshot(req: SnapshotRequest, user=Depends(get_current_user)):
    """Create a new version snapshot of a file.

    This captures the current state of a file and stores it as a new version.
    """
    result = create_snapshot(req.path, req.comment)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/list")
async def get_version_list(path: str = Query(...), user=Depends(get_current_user)):
    """List all versions of a file.

    Returns version history ordered from newest to oldest.
    """
    result = list_versions(path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/detail")
async def get_version_detail(
    path: str = Query(...),
    version_id: str = Query(...),
    user=Depends(get_current_user),
):
    """Get detailed information about a specific version."""
    result = get_version(path, version_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/restore")
async def post_restore(req: RestoreRequest, user=Depends(get_current_user)):
    """Restore a file to a specific version.

    This will create a backup of the current file before restoring,
    so you can undo the restore if needed.
    """
    result = restore_version(req.path, req.version_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/delete")
async def delete_version_endpoint(req: DeleteVersionRequest, user=Depends(get_current_user)):
    """Delete a specific version of a file."""
    result = delete_version(req.path, req.version_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/download")
async def get_version_download(
    path: str = Query(...),
    version_id: str = Query(...),
    user=Depends(get_current_user),
):
    """Download a specific version of a file."""
    result = get_version_file(path, version_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return FileResponse(
        path=result["version_path"],
        filename=result["filename"],
        media_type="application/octet-stream",
    )


@router.post("/compare")
async def post_compare(req: CompareRequest, user=Depends(get_current_user)):
    """Compare two versions of a file.

    Returns information about size differences and whether the content is identical.
    """
    result = compare_versions(req.path, req.version_id_a, req.version_id_b)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

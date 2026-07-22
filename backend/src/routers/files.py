"""Files router — file manager API (browse, upload, download, mkdir, delete)."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..auth import get_current_user
from ..services.file_service import (
    list_directory, save_upload, get_download_path, make_directory, delete_item,
    move_item, copy_item, get_file_info,
    compress, extract, create_share_link
)

router = APIRouter(prefix="/api/files", tags=["files"])


class MkdirRequest(BaseModel):
    path: str


class DeleteRequest(BaseModel):
    path: str


@router.get("/list")
async def get_file_list(path: str = Query(...), user=Depends(get_current_user)):
    """List files and directories in the given path."""
    result = list_directory(path)
    if not result["success"]:
        status = 404 if "not exist" in result.get("error", "") else 403 if "denied" in result.get("error", "") else 400
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.post("/upload")
async def post_upload(
    dest: str = Query(...),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload a file to the specified destination directory."""
    content = await file.read()
    result = save_upload(file.filename or "upload", content, dest)
    if not result["success"]:
        status = 413 if "too large" in result.get("error", "") else 403 if "denied" in result.get("error", "") else 400
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.get("/download")
async def get_download(path: str = Query(...), user=Depends(get_current_user)):
    """Download a file."""
    result = get_download_path(path)
    if not result["success"]:
        status = 404 if "not found" in result.get("error", "").lower() else 403 if "denied" in result.get("error", "") else 400
        raise HTTPException(status_code=status, detail=result["error"])
    return FileResponse(
        path=result["absolute_path"],
        filename=result["filename"],
        media_type="application/octet-stream",
    )


@router.post("/mkdir")
async def post_mkdir(req: MkdirRequest, user=Depends(get_current_user)):
    """Create a new directory."""
    result = make_directory(req.path)
    if not result["success"]:
        status = 403 if "denied" in result.get("error", "") else 400
        raise HTTPException(status_code=status, detail=result["error"])
    return result


@router.delete("/delete")
async def delete_file(req: DeleteRequest, user=Depends(get_current_user)):
    """Delete a file or directory."""
    result = delete_item(req.path)
    if not result["success"]:
        status = 404 if "not found" in result.get("error", "").lower() else 403 if "denied" in result.get("error", "") else 400
        raise HTTPException(status_code=status, detail=result["error"])
    return result


class MoveRequest(BaseModel):
    src: str
    dst: str


class CopyRequest(BaseModel):
    src: str
    dst: str


@router.post("/move")
async def post_move(req: MoveRequest, user=Depends(get_current_user)):
    """Move or rename a file/directory."""
    result = move_item(req.src, req.dst)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/copy")
async def post_copy(req: CopyRequest, user=Depends(get_current_user)):
    """Copy a file or directory."""
    result = copy_item(req.src, req.dst)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/info")
async def get_info(path: str = Query(...), user=Depends(get_current_user)):
    """Get detailed file information."""
    result = get_file_info(path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

from typing import Optional, List


# ─── Compress / Extract / Share ──────────────────────────────────────────────


class CompressRequest(BaseModel):
    paths: List[str]
    format: str = "zip"
    dest: str


class ExtractRequest(BaseModel):
    archive: str
    dest: str


class ShareLinkRequest(BaseModel):
    path: str
    expires_hours: int = 24
    password: Optional[str] = None


@router.post("/compress")
async def post_compress(req: CompressRequest, user=Depends(get_current_user)):
    """Compress files/directories into an archive."""
    result = compress(req.paths, req.format, req.dest)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/extract")
async def post_extract(req: ExtractRequest, user=Depends(get_current_user)):
    """Extract an archive to a destination directory."""
    result = extract(req.archive, req.dest)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/share")
async def post_share_link(req: ShareLinkRequest, user=Depends(get_current_user)):
    """Create a temporary share link for a file."""
    result = create_share_link(req.path, req.expires_hours, req.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

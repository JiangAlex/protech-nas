"""Shares router — SMB/NFS share management API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..auth import get_current_user
from ..services.samba_service import list_smb_shares, add_smb_share, remove_smb_share
from ..services.nfs_service import list_nfs_exports, add_nfs_export, remove_nfs_export

router = APIRouter(prefix="/api/shares", tags=["shares"])


class SMBShareCreate(BaseModel):
    name: str
    path: str
    comment: Optional[str] = ""
    read_only: bool = False
    guest_ok: bool = False
    valid_users: Optional[str] = ""


class NFSExportCreate(BaseModel):
    path: str
    clients: str  # e.g., "192.168.1.0/24(rw,sync,no_subtree_check)"


# ─── SMB Endpoints ───────────────────────────────────────────────────────────

@router.get("/smb")
async def get_smb_shares(user=Depends(get_current_user)):
    """List all Samba shares."""
    return list_smb_shares()


@router.post("/smb")
async def create_smb_share(share: SMBShareCreate, user=Depends(get_current_user)):
    """Create a new Samba share."""
    result = add_smb_share(share.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/smb/{name}")
async def delete_smb_share(name: str, user=Depends(get_current_user)):
    """Delete a Samba share."""
    result = remove_smb_share(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── NFS Endpoints ───────────────────────────────────────────────────────────

@router.get("/nfs")
async def get_nfs_exports(user=Depends(get_current_user)):
    """List all NFS exports."""
    return list_nfs_exports()


@router.post("/nfs")
async def create_nfs_export(export: NFSExportCreate, user=Depends(get_current_user)):
    """Create a new NFS export."""
    result = add_nfs_export(export.path, export.clients)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/nfs")
async def delete_nfs_export(path: str, user=Depends(get_current_user)):
    """Remove an NFS export by path."""
    result = remove_nfs_export(path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

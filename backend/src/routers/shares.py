"""Shares router — SMB/NFS share management API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..auth import get_current_user
from ..services.samba_service import list_smb_shares, add_smb_share, remove_smb_share, update_smb_share, get_share_acl, set_share_acl, get_smb_status
from ..services.nfs_service import list_nfs_exports, add_nfs_export, remove_nfs_export, update_nfs_export, get_nfs_status

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


class SMBShareUpdate(BaseModel):
    path: Optional[str] = ""
    comment: Optional[str] = ""
    read_only: bool = False
    guest_ok: bool = False
    valid_users: Optional[str] = ""


class NFSExportUpdate(BaseModel):
    clients: str


@router.put("/smb/{name}")
async def update_smb(name: str, share: SMBShareUpdate, user=Depends(get_current_user)):
    """Update an existing SMB share."""
    result = update_smb_share(name, share.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/nfs")
async def update_nfs(path: str, export: NFSExportUpdate, user=Depends(get_current_user)):
    """Update an existing NFS export."""
    result = update_nfs_export(path, export.clients)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class ACLEntry(BaseModel):
    type: str  # "user" or "group"
    name: str
    perms: str  # "rwx" etc


class ACLUpdate(BaseModel):
    acl: List[ACLEntry]


@router.get("/smb/{name}/acl")
async def get_smb_acl(name: str, user=Depends(get_current_user)):
    """Get filesystem ACL for a share."""
    result = get_share_acl(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/smb/{name}/acl")
async def put_smb_acl(name: str, data: ACLUpdate, user=Depends(get_current_user)):
    """Set filesystem ACL for a share."""
    result = set_share_acl(name, [e.model_dump() for e in data.acl])
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/smb/status")
async def get_smb_service_status(user=Depends(get_current_user)):
    """Get Samba service status and connections."""
    return get_smb_status()


@router.get("/nfs/status")
async def get_nfs_service_status(user=Depends(get_current_user)):
    """Get NFS service status and connections."""
    return get_nfs_status()

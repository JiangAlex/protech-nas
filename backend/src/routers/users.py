"""Users router — system user and group management API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.user_service import (
    list_users, create_user, delete_user, change_password,
    list_groups, create_group, delete_group
)

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    username: str
    password: str
    groups: Optional[str] = ""  # comma-separated group names
    smb_enabled: bool = True


class PasswordChange(BaseModel):
    password: str


class GroupCreate(BaseModel):
    name: str


@router.get("")
async def get_users(user=Depends(get_current_user)):
    """List all system users (UID >= 1000)."""
    return list_users()


@router.post("")
async def post_user(data: UserCreate, user=Depends(get_current_user)):
    """Create a new system user."""
    result = create_user(data.username, data.password, data.groups, data.smb_enabled)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/{username}")
async def del_user(username: str, user=Depends(get_current_user)):
    """Delete a system user."""
    result = delete_user(username)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/{username}/password")
async def put_password(username: str, data: PasswordChange, user=Depends(get_current_user)):
    """Change user password."""
    result = change_password(username, data.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Groups ──────────────────────────────────────────────────────────────────

@router.get("/groups")
async def get_groups(user=Depends(get_current_user)):
    """List all groups."""
    return list_groups()


@router.post("/groups")
async def post_group(data: GroupCreate, user=Depends(get_current_user)):
    """Create a new group."""
    result = create_group(data.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/groups/{name}")
async def del_group(name: str, user=Depends(get_current_user)):
    """Delete a group."""
    result = delete_group(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

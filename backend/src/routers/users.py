"""Users router — system user and group management API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from ..auth import get_current_user
from ..services.user_service import (
    list_users, create_user, delete_user, change_password,
    list_groups, create_group, delete_group, update_user,
    disable_user, enable_user, update_group_members, get_quota, set_quota,
    setup_totp, verify_totp, get_audit_log, list_sessions, revoke_session
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


class UserUpdate(BaseModel):
    shell: Optional[str] = None
    groups: Optional[str] = None


@router.put("/{username}")
async def put_user(username: str, data: UserUpdate, user=Depends(get_current_user)):
    """Update user properties (shell, groups)."""
    config = {k: v for k, v in data.model_dump().items() if v is not None}
    if not config:
        raise HTTPException(status_code=422, detail="No changes specified")
    result = update_user(username, config)
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


class UserStatus(BaseModel):
    enabled: bool


class GroupMembers(BaseModel):
    add: Optional[List[str]] = []
    remove: Optional[List[str]] = []


class QuotaSet(BaseModel):
    soft_mb: int
    hard_mb: int


@router.put("/{username}/status")
async def put_user_status(username: str, data: UserStatus, user=Depends(get_current_user)):
    """Enable or disable a user."""
    if data.enabled:
        result = enable_user(username)
    else:
        result = disable_user(username)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/groups/{name}/members")
async def put_group_members(name: str, data: GroupMembers, user=Depends(get_current_user)):
    """Add or remove users from a group."""
    result = update_group_members(name, add=data.add, remove=data.remove)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "; ".join(result.get("errors", []))))
    return result


@router.get("/{username}/quota")
async def get_user_quota(username: str, user=Depends(get_current_user)):
    """Get user disk quota."""
    result = get_quota(username)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/{username}/quota")
async def put_user_quota(username: str, data: QuotaSet, user=Depends(get_current_user)):
    """Set user disk quota."""
    result = set_quota(username, data.soft_mb, data.hard_mb)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Two-Factor Authentication ───────────────────────────────────────────────


class TOTPVerify(BaseModel):
    code: str


@router.post("/{username}/2fa/setup")
async def post_2fa_setup(username: str, user=Depends(get_current_user)):
    """Set up TOTP two-factor authentication for a user."""
    result = setup_totp(username)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{username}/2fa/verify")
async def post_2fa_verify(username: str, data: TOTPVerify, user=Depends(get_current_user)):
    """Verify a TOTP code to activate 2FA."""
    result = verify_totp(username, data.code)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Audit Log ───────────────────────────────────────────────────────────────


@router.get("/audit")
async def get_audit(
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=5000),
    user=Depends(get_current_user),
):
    """Get user audit log entries."""
    result = get_audit_log(username=username, action=action, limit=limit)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Sessions ────────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.get("/sessions")
async def get_sessions(user=Depends(get_current_user)):
    """List active sessions for the current user."""
    result = list_sessions(user)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@auth_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user)):
    """Revoke a specific session."""
    result = revoke_session(session_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

"""Notifications router — notification settings and history API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.notification_service import (
    get_notification_settings, update_notification_settings,
    send_notification, list_notifications, mark_read
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationSettings(BaseModel):
    email: Optional[dict] = None
    telegram: Optional[dict] = None
    webhook: Optional[dict] = None


class TestNotification(BaseModel):
    channel: str = "all"


@router.get("")
async def get_notifs(unread_only: bool = Query(False), user=Depends(get_current_user)):
    """List notifications."""
    return list_notifications(unread_only=unread_only)


@router.get("/settings")
async def get_settings(user=Depends(get_current_user)):
    """Get notification channel settings."""
    return get_notification_settings()


@router.put("/settings")
async def put_settings(data: NotificationSettings, user=Depends(get_current_user)):
    """Update notification settings."""
    config = {k: v for k, v in data.model_dump().items() if v is not None}
    result = update_notification_settings(config)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/test")
async def post_test(data: TestNotification, user=Depends(get_current_user)):
    """Send a test notification."""
    result = send_notification(data.channel, "測試通知", "這是一則來自 ProTech NAS 的測試通知。")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.put("/{notification_id}/read")
async def put_read(notification_id: str, user=Depends(get_current_user)):
    """Mark a notification as read."""
    result = mark_read(notification_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

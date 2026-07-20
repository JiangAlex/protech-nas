"""Dashboard router — system monitoring API."""

from fastapi import APIRouter, Depends
from ..auth import get_current_user
from ..services.system_service import get_system_info

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(user=Depends(get_current_user)):
    """Get system overview: CPU, RAM, disk, network, uptime."""
    return get_system_info()

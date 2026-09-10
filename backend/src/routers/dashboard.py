"""Dashboard router — system monitoring API."""

from fastapi import APIRouter, Depends
from ..auth import get_current_user
from ..services.system_service import get_system_info

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(user=Depends(get_current_user)):
    """Get system overview: CPU, RAM, disk, network, uptime."""
    return get_system_info()


@router.get("/metrics")
async def public_metrics():
    """Unauthenticated metrics endpoint for NAS server manager polling.

    Phase 1: no token. Access is restricted at the network layer by Tailscale
    ACL (only tag:nas-server can reach tag:nas-client). Phase 2 will add a
    shared-secret header or token check.
    """
    return get_system_info()

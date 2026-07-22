"""Network router — network interface management API."""

from fastapi import APIRouter, Depends
from ..auth import get_current_user
from ..services.network_service import (
    list_interfaces, configure_interface,
    list_firewall_rules, add_firewall_rule, delete_firewall_rule,
    get_realtime_stats,
    ping, traceroute, dns_lookup, send_wol
)

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/interfaces")
async def get_interfaces(user=Depends(get_current_user)):
    """List all network interfaces with IP, MAC, status, and speed."""
    return list_interfaces()

from fastapi import HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from ..auth import get_current_user


class InterfaceConfig(BaseModel):
    method: str = "dhcp"  # "dhcp" or "static"
    ip: Optional[str] = None
    gateway: Optional[str] = None
    dns: Optional[List[str]] = []


class FirewallRule(BaseModel):
    chain: str = "INPUT"
    protocol: str = "tcp"
    port: Optional[int] = None
    source: str = "0.0.0.0/0"
    target: str = "ACCEPT"


@router.put("/interfaces/{name}")
async def put_interface(name: str, config: InterfaceConfig, user=Depends(get_current_user)):
    """Configure a network interface."""
    result = configure_interface(name, config.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/firewall/rules")
async def get_fw_rules(user=Depends(get_current_user)):
    """List firewall rules."""
    return list_firewall_rules()


@router.post("/firewall/rules")
async def post_fw_rule(rule: FirewallRule, user=Depends(get_current_user)):
    """Add a firewall rule."""
    result = add_firewall_rule(rule.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/firewall/rules/{rule_id}")
async def delete_fw_rule(rule_id: int, chain: str = Query("INPUT"), user=Depends(get_current_user)):
    """Delete a firewall rule by line number."""
    result = delete_firewall_rule(rule_id, chain)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/stats")
async def get_net_stats(user=Depends(get_current_user)):
    """Get real-time network speed per interface."""
    return get_realtime_stats()


# ─── Network Diagnostics ─────────────────────────────────────────────────────


class PingRequest(BaseModel):
    host: str
    count: int = 4


class TracerouteRequest(BaseModel):
    host: str


class DNSLookupRequest(BaseModel):
    domain: str
    record_type: str = "A"


class WOLRequest(BaseModel):
    mac: str


@router.post("/diag/ping")
async def post_ping(req: PingRequest, user=Depends(get_current_user)):
    """Ping a host."""
    result = ping(req.host, req.count)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/diag/traceroute")
async def post_traceroute(req: TracerouteRequest, user=Depends(get_current_user)):
    """Traceroute to a host."""
    result = traceroute(req.host)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/diag/dns")
async def post_dns_lookup(req: DNSLookupRequest, user=Depends(get_current_user)):
    """DNS lookup for a domain."""
    result = dns_lookup(req.domain, req.record_type)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/wol")
async def post_wol(req: WOLRequest, user=Depends(get_current_user)):
    """Send Wake-on-LAN magic packet."""
    result = send_wol(req.mac)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

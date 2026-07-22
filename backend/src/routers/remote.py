"""Remote access router — DDNS, SSL, VPN API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..auth import get_current_user
from ..services.remote_service import (
    get_ddns_config, update_ddns_config, ddns_update_ip,
    get_ssl_status, issue_ssl_cert,
    get_vpn_status, update_vpn_config,
    add_vpn_peer, remove_vpn_peer, manage_reverse_proxy,
    list_proxy_rules, delete_proxy_rule
)

router = APIRouter(prefix="/api/remote", tags=["remote"])


class DDNSConfig(BaseModel):
    provider: str
    domain: str
    token: str
    enabled: bool = True


class SSLIssue(BaseModel):
    domain: str
    email: str = "admin@localhost"


class VPNConfig(BaseModel):
    address: str = "10.0.0.1/24"
    listen_port: int = 51820
    private_key: str
    dns: Optional[str] = ""


@router.get("/ddns")
async def get_ddns(user=Depends(get_current_user)):
    """Get DDNS configuration."""
    return get_ddns_config()


@router.put("/ddns")
async def put_ddns(data: DDNSConfig, user=Depends(get_current_user)):
    """Update DDNS configuration."""
    result = update_ddns_config(data.provider, data.domain, data.token, data.enabled)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/ddns/update")
async def post_ddns_update(user=Depends(get_current_user)):
    """Trigger DDNS IP update now."""
    result = ddns_update_ip()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/ssl")
async def get_ssl(user=Depends(get_current_user)):
    """Get SSL certificate status."""
    return get_ssl_status()


@router.post("/ssl/issue")
async def post_ssl_issue(data: SSLIssue, user=Depends(get_current_user)):
    """Issue a Let's Encrypt SSL certificate."""
    result = issue_ssl_cert(data.domain, data.email)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/vpn/status")
async def get_vpn(user=Depends(get_current_user)):
    """Get VPN status."""
    return get_vpn_status()


@router.put("/vpn/config")
async def put_vpn(data: VPNConfig, user=Depends(get_current_user)):
    """Update VPN configuration."""
    result = update_vpn_config(data.model_dump())
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── VPN Peers ───────────────────────────────────────────────────────────────


class VPNPeerAdd(BaseModel):
    public_key: str
    allowed_ips: str
    endpoint: Optional[str] = None


@router.get("/vpn/peers")
async def get_vpn_peers(user=Depends(get_current_user)):
    """List VPN peers."""
    status = get_vpn_status()
    return {"peers": status.get("peers", [])}


@router.post("/vpn/peers")
async def post_vpn_peer(data: VPNPeerAdd, user=Depends(get_current_user)):
    """Add a VPN peer."""
    result = add_vpn_peer(data.public_key, data.allowed_ips, data.endpoint)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/vpn/peers/{public_key}")
async def del_vpn_peer(public_key: str, user=Depends(get_current_user)):
    """Remove a VPN peer."""
    result = remove_vpn_peer(public_key)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Reverse Proxy ───────────────────────────────────────────────────────────


class ProxyRule(BaseModel):
    domain: str
    upstream: str
    ssl: bool = False


class ReverseProxyRequest(BaseModel):
    rules: List[ProxyRule]


@router.get("/reverse-proxy")
async def get_reverse_proxy(user=Depends(get_current_user)):
    """List current reverse proxy configurations."""
    return list_proxy_rules()


@router.post("/reverse-proxy")
async def post_reverse_proxy(data: ReverseProxyRequest, user=Depends(get_current_user)):
    """Create/update reverse proxy rules."""
    rules = [r.model_dump() for r in data.rules]
    result = manage_reverse_proxy(rules)
    if not result.get("success", True):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Proxy Rules (frontend-compatible endpoints) ─────────────────────────────


@router.get("/proxy/rules")
async def get_proxy_rules(user=Depends(get_current_user)):
    """List current proxy rules."""
    result = list_proxy_rules()
    return result


@router.post("/proxy/rules")
async def post_proxy_rule(data: ProxyRule, user=Depends(get_current_user)):
    """Add a single proxy rule."""
    result = manage_reverse_proxy([data.model_dump()])
    if not result.get("success", True):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/proxy/rules/{domain}")
async def del_proxy_rule(domain: str, user=Depends(get_current_user)):
    """Delete a proxy rule by domain."""
    result = delete_proxy_rule(domain)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

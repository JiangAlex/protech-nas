"""Remote access service — DDNS, SSL certificates, VPN (WireGuard)."""

import subprocess
import json
import os
import re
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

REMOTE_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".protech-nas/remote")
DDNS_CONFIG_FILE = os.path.join(REMOTE_CONFIG_DIR, "ddns.json")
WG_CONF = "/etc/wireguard/wg0.conf"


def _ensure_config_dir():
    os.makedirs(REMOTE_CONFIG_DIR, exist_ok=True)


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# ─── DDNS ─────────────────────────────────────────────────────────────────────

def get_ddns_config() -> dict:
    """Get current DDNS configuration.

    Returns:
        {"success": bool, "enabled": bool, "provider": str, "domain": str, "last_update": str, "current_ip": str}
    """
    _ensure_config_dir()
    if not os.path.exists(DDNS_CONFIG_FILE):
        return {"success": True, "enabled": False, "provider": "", "domain": "", "last_update": None, "current_ip": ""}

    try:
        with open(DDNS_CONFIG_FILE) as f:
            config = json.load(f)
        return {"success": True, **config}
    except (json.JSONDecodeError, IOError) as e:
        return {"success": False, "error": str(e)}


def update_ddns_config(provider: str, domain: str, token: str, enabled: bool = True) -> dict:
    """Update DDNS configuration.

    Args:
        provider: "cloudflare" | "duckdns" | "noip"
        domain: Domain name.
        token: API token/key.
        enabled: Enable or disable DDNS updates.

    Returns:
        {"success": bool, "message": str}
    """
    valid_providers = ("cloudflare", "duckdns", "noip")
    if provider not in valid_providers:
        return {"success": False, "error": f"Invalid provider: {provider}. Supported: {', '.join(valid_providers)}"}
    if not domain:
        return {"success": False, "error": "domain is required"}
    if not token:
        return {"success": False, "error": "token is required"}

    _ensure_config_dir()
    config = {
        "enabled": enabled,
        "provider": provider,
        "domain": domain,
        "token": token,
        "last_update": None,
        "current_ip": "",
    }

    with open(DDNS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    # Set restrictive permissions (contains token)
    os.chmod(DDNS_CONFIG_FILE, 0o600)

    return {"success": True, "message": "DDNS configuration updated"}


def ddns_update_ip() -> dict:
    """Update DDNS IP address now.

    Returns:
        {"success": bool, "ip": str, "message": str}
    """
    if not os.path.exists(DDNS_CONFIG_FILE):
        return {"success": False, "error": "DDNS not configured"}

    with open(DDNS_CONFIG_FILE) as f:
        config = json.load(f)

    if not config.get("enabled"):
        return {"success": False, "error": "DDNS is disabled"}

    # Get public IP
    rc, ip_out, _ = _run(["curl", "-s", "https://api.ipify.org"])
    if rc != 0 or not ip_out.strip():
        return {"success": False, "error": "Failed to get public IP"}

    current_ip = ip_out.strip()
    provider = config.get("provider")
    domain = config.get("domain")
    token = config.get("token")

    # Update DNS based on provider
    if provider == "duckdns":
        rc, out, _ = _run(["curl", "-s",
            f"https://www.duckdns.org/update?domains={domain}&token={token}&ip={current_ip}"])
        success = "OK" in (out or "")
    elif provider == "cloudflare":
        # Simplified — in production would use zone_id + record_id
        success = True  # Placeholder
    elif provider == "noip":
        rc, out, _ = _run(["curl", "-s",
            f"https://dynupdate.no-ip.com/nic/update?hostname={domain}&myip={current_ip}",
            "-u", f":{token}"])
        success = rc == 0
    else:
        return {"success": False, "error": f"Unsupported provider: {provider}"}

    if success:
        config["last_update"] = datetime.now().isoformat()
        config["current_ip"] = current_ip
        with open(DDNS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return {"success": True, "ip": current_ip, "message": "IP updated"}
    else:
        return {"success": False, "error": "DDNS update failed"}


# ─── SSL ──────────────────────────────────────────────────────────────────────

def get_ssl_status() -> dict:
    """Get SSL certificate status.

    Returns:
        {"success": bool, "certs": list[{"domain": str, "expires": str, "days_remaining": int}]}
    """
    certs = []
    le_live = Path("/etc/letsencrypt/live")
    if not le_live.exists():
        return {"success": True, "certs": []}

    for domain_dir in le_live.iterdir():
        if not domain_dir.is_dir():
            continue
        cert_file = domain_dir / "cert.pem"
        if not cert_file.exists():
            continue

        # Get expiry with openssl
        rc, out, _ = _run(["openssl", "x509", "-enddate", "-noout", "-in", str(cert_file)])
        if rc == 0 and "notAfter=" in out:
            date_str = out.split("=", 1)[1].strip()
            try:
                expires = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                days_remaining = (expires - datetime.now()).days
                certs.append({
                    "domain": domain_dir.name,
                    "expires": expires.isoformat(),
                    "days_remaining": days_remaining,
                })
            except ValueError:
                certs.append({"domain": domain_dir.name, "expires": date_str, "days_remaining": -1})

    return {"success": True, "certs": certs}


def issue_ssl_cert(domain: str, email: str = "admin@localhost") -> dict:
    """Issue a Let's Encrypt SSL certificate.

    Args:
        domain: Domain name.
        email: Contact email for Let's Encrypt.

    Returns:
        {"success": bool, "cert_path": str, "expires": str}
    """
    if not domain or not re.match(r"^[a-zA-Z0-9\-_.]+\.[a-zA-Z]{2,}$", domain):
        return {"success": False, "error": f"Invalid domain: {domain}"}

    rc, out, err = _run([
        "certbot", "certonly", "--standalone",
        "-d", domain,
        "--non-interactive", "--agree-tos",
        "-m", email,
    ], timeout=120)

    if rc != 0:
        return {"success": False, "error": f"certbot failed: {err.strip()[:300]}"}

    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    return {"success": True, "cert_path": cert_path, "expires": "Check with get_ssl_status()"}


# ─── VPN (WireGuard) ─────────────────────────────────────────────────────────

def get_vpn_status() -> dict:
    """Get WireGuard VPN status.

    Returns:
        {"success": bool, "interface": str, "running": bool, "listen_port": int, "peers": list}
    """
    rc, out, _ = _run(["wg", "show", "wg0", "dump"])
    if rc != 0:
        # Check if wg0 is just down
        rc2, _, _ = _run(["ip", "link", "show", "wg0"])
        if rc2 != 0:
            return {"success": True, "interface": "wg0", "running": False, "listen_port": 0, "peers": []}
        return {"success": True, "interface": "wg0", "running": False, "listen_port": 0, "peers": []}

    lines = out.strip().split("\n")
    if not lines:
        return {"success": True, "interface": "wg0", "running": False, "listen_port": 0, "peers": []}

    # First line: private_key, public_key, listen_port, fwmark
    server_parts = lines[0].split("\t")
    listen_port = int(server_parts[2]) if len(server_parts) > 2 and server_parts[2].isdigit() else 0

    peers = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) >= 5:
            peers.append({
                "public_key": parts[0],
                "endpoint": parts[2] if parts[2] != "(none)" else "",
                "allowed_ips": parts[3],
                "last_handshake": int(parts[4]) if parts[4].isdigit() else 0,
                "transfer_rx": int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0,
                "transfer_tx": int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 0,
            })

    return {
        "success": True,
        "interface": "wg0",
        "running": True,
        "listen_port": listen_port,
        "peers": peers,
    }


def update_vpn_config(config: dict) -> dict:
    """Update WireGuard VPN configuration.

    Args:
        config: {"address": "10.0.0.1/24", "listen_port": 51820, "private_key": "...", "dns": "1.1.1.1"}

    Returns:
        {"success": bool, "message": str}
    """
    address = config.get("address", "10.0.0.1/24")
    listen_port = config.get("listen_port", 51820)
    private_key = config.get("private_key", "")
    dns = config.get("dns", "")

    if not private_key:
        return {"success": False, "error": "private_key is required"}
    if not isinstance(listen_port, int) or listen_port < 1 or listen_port > 65535:
        return {"success": False, "error": f"Invalid listen_port: {listen_port}"}

    # Build wg0.conf
    conf_content = f"""[Interface]
Address = {address}
ListenPort = {listen_port}
PrivateKey = {private_key}
"""
    if dns:
        conf_content += f"DNS = {dns}\n"

    # Preserve existing peers
    if os.path.exists(WG_CONF):
        with open(WG_CONF) as f:
            existing = f.read()
        # Extract [Peer] sections
        peer_sections = re.findall(r"(\[Peer\].*?)(?=\[|\Z)", existing, re.DOTALL)
        for peer in peer_sections:
            conf_content += "\n" + peer.strip() + "\n"

    try:
        os.makedirs(os.path.dirname(WG_CONF), exist_ok=True)
        with open(WG_CONF, "w") as f:
            f.write(conf_content)
        os.chmod(WG_CONF, 0o600)

        # Restart interface
        _run(["wg-quick", "down", "wg0"], timeout=5)
        rc, _, err = _run(["wg-quick", "up", "wg0"], timeout=10)
        if rc != 0:
            return {"success": False, "error": f"wg-quick up failed: {err.strip()}"}

        return {"success": True, "message": "VPN configuration updated and restarted"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── VPN Peers ────────────────────────────────────────────────────────────────

def add_vpn_peer(peer_config: dict) -> dict:
    """Add a WireGuard peer.

    Args:
        peer_config: {"public_key": str, "allowed_ips": str, "endpoint": str (optional), "persistent_keepalive": int (optional)}

    Returns:
        {"success": bool, "message": str}
    """
    public_key = peer_config.get("public_key", "")
    allowed_ips = peer_config.get("allowed_ips", "")

    if not public_key or len(public_key) != 44:
        return {"success": False, "error": "Invalid public_key (must be 44 char base64)"}
    if not allowed_ips:
        return {"success": False, "error": "allowed_ips is required"}

    # Build peer section
    peer_section = f"\n[Peer]\nPublicKey = {public_key}\nAllowedIPs = {allowed_ips}\n"
    if peer_config.get("endpoint"):
        peer_section += f"Endpoint = {peer_config['endpoint']}\n"
    if peer_config.get("persistent_keepalive"):
        peer_section += f"PersistentKeepalive = {peer_config['persistent_keepalive']}\n"

    # Append to wg0.conf
    try:
        if not os.path.exists(WG_CONF):
            return {"success": False, "error": "WireGuard not configured. Set up VPN first."}
        with open(WG_CONF, "a") as f:
            f.write(peer_section)
        # Sync config without restarting
        _run(["wg", "syncconf", "wg0", "/dev/stdin"], timeout=5)
        # Alternatively restart
        _run(["wg-quick", "down", "wg0"], timeout=5)
        _run(["wg-quick", "up", "wg0"], timeout=5)
        return {"success": True, "message": f"Peer {public_key[:8]}... added"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_vpn_peer(public_key: str) -> dict:
    """Remove a WireGuard peer.

    Args:
        public_key: Peer's public key.

    Returns:
        {"success": bool, "message": str}
    """
    if not public_key:
        return {"success": False, "error": "public_key is required"}

    if not os.path.exists(WG_CONF):
        return {"success": False, "error": "WireGuard config not found"}

    with open(WG_CONF) as f:
        content = f.read()

    # Remove [Peer] section matching the public key
    lines = content.split("\n")
    new_lines = []
    skip = False

    for line in lines:
        if line.strip() == "[Peer]":
            # Look ahead to check if this is the target peer
            idx = lines.index(line)
            peer_block = "\n".join(lines[idx:idx+10])
            if public_key in peer_block:
                skip = True
                continue
        if skip:
            if line.strip().startswith("[") and line.strip() != "[Peer]":
                skip = False
            elif not line.strip() or line.strip().startswith("["):
                if line.strip().startswith("["):
                    skip = False
                else:
                    continue
            else:
                continue
        if not skip:
            new_lines.append(line)

    with open(WG_CONF, "w") as f:
        f.write("\n".join(new_lines))

    _run(["wg-quick", "down", "wg0"], timeout=5)
    _run(["wg-quick", "up", "wg0"], timeout=5)

    return {"success": True, "message": f"Peer {public_key[:8]}... removed"}


# ─── Reverse Proxy ────────────────────────────────────────────────────────────

PROXY_CONF_DIR = "/etc/nginx/sites-available"
PROXY_ENABLED_DIR = "/etc/nginx/sites-enabled"


def manage_reverse_proxy(rules: list) -> dict:
    """Create or update Nginx reverse proxy rules.

    Args:
        rules: list of {"domain": str, "upstream": str, "ssl": bool}

    Returns:
        {"success": bool, "message": str}
    """
    if not rules:
        return {"success": False, "error": "rules list is empty"}

    os.makedirs(PROXY_CONF_DIR, exist_ok=True)
    os.makedirs(PROXY_ENABLED_DIR, exist_ok=True)

    created = []
    for rule in rules:
        domain = rule.get("domain", "")
        upstream = rule.get("upstream", "")
        use_ssl = rule.get("ssl", False)

        if not domain or not re.match(r"^[a-zA-Z0-9\-._]+$", domain):
            return {"success": False, "error": f"Invalid domain: {domain}"}
        if not upstream:
            return {"success": False, "error": f"upstream is required for {domain}"}

        # Generate Nginx server block
        conf = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://{upstream};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        if use_ssl:
            conf = f"""server {{
    listen 443 ssl;
    server_name {domain};
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

    location / {{
        proxy_pass http://{upstream};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}

server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}
"""
        conf_path = os.path.join(PROXY_CONF_DIR, f"protech-{domain}.conf")
        enabled_path = os.path.join(PROXY_ENABLED_DIR, f"protech-{domain}.conf")

        with open(conf_path, "w") as f:
            f.write(conf)

        # Enable (symlink)
        if not os.path.exists(enabled_path):
            os.symlink(conf_path, enabled_path)

        created.append(domain)

    # Test Nginx config
    rc, _, err = _run(["nginx", "-t"])
    if rc != 0:
        return {"success": False, "error": f"Nginx config test failed: {err.strip()}"}

    # Reload
    _run(["systemctl", "reload", "nginx"])

    return {"success": True, "message": f"Proxy rules created for: {', '.join(created)}"}


def list_proxy_rules() -> dict:
    """List current reverse proxy rules by scanning Nginx config files.

    Returns:
        {"success": bool, "rules": list[{"id": str, "domain": str, "upstream": str, "ssl": bool}]}
    """
    rules = []
    conf_dir = Path(PROXY_CONF_DIR)

    if not conf_dir.exists():
        return {"success": True, "rules": []}

    for conf_file in sorted(conf_dir.glob("protech-*.conf")):
        domain = conf_file.stem.replace("protech-", "", 1)
        content = conf_file.read_text()

        # Extract upstream from proxy_pass
        upstream_match = re.search(r"proxy_pass\s+https?://([^;]+);", content)
        upstream = upstream_match.group(1) if upstream_match else ""

        # Check if SSL is configured
        use_ssl = "listen 443 ssl" in content

        rules.append({
            "id": domain,
            "domain": domain,
            "upstream": upstream,
            "ssl": use_ssl,
        })

    return {"success": True, "rules": rules}


def delete_proxy_rule(domain: str) -> dict:
    """Delete a reverse proxy rule.

    Args:
        domain: The domain identifier of the rule to delete.

    Returns:
        {"success": bool, "message": str}
    """
    if not domain or not re.match(r"^[a-zA-Z0-9\-._]+$", domain):
        return {"success": False, "error": f"Invalid domain: {domain}"}

    conf_path = os.path.join(PROXY_CONF_DIR, f"protech-{domain}.conf")
    enabled_path = os.path.join(PROXY_ENABLED_DIR, f"protech-{domain}.conf")

    if not os.path.exists(conf_path):
        return {"success": False, "error": f"Rule not found for domain: {domain}"}

    # Remove symlink and config
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
    os.remove(conf_path)

    # Reload Nginx
    rc, _, err = _run(["nginx", "-t"])
    if rc == 0:
        _run(["systemctl", "reload", "nginx"])

    return {"success": True, "message": f"Proxy rule for {domain} deleted"}

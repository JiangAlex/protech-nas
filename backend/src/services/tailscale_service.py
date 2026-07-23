"""Tailscale service — manage Tailscale VPN via CLI."""

import subprocess
import json


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a command with timeout."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "tailscale not installed"
    except Exception as e:
        return -1, "", str(e)


def get_status() -> dict:
    """Get Tailscale connection status and peer list.

    Returns:
        {
            "success": bool,
            "installed": bool,
            "running": bool,
            "self": {"hostname": str, "ip": str, "id": str, "online": bool},
            "peers": [{"hostname": str, "ip": str, "os": str, "online": bool, "exit_node": bool}]
        }
    """
    # Check if tailscale is installed
    rc, out, err = _run(["tailscale", "version"])
    if rc != 0:
        return {"success": False, "installed": False, "error": "Tailscale is not installed"}

    version = out.strip().split("\n")[0] if out else "unknown"

    # Get status in JSON format
    rc, out, err = _run(["tailscale", "status", "--json"])
    if rc != 0:
        # tailscale installed but not running
        return {
            "success": True,
            "installed": True,
            "running": False,
            "version": version,
            "self": {},
            "peers": [],
        }

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"success": False, "installed": True, "error": "Failed to parse tailscale status"}

    # Parse self node
    self_node = {}
    if data.get("Self"):
        s = data["Self"]
        self_node = {
            "hostname": s.get("HostName", ""),
            "ip": s.get("TailscaleIPs", [""])[0] if s.get("TailscaleIPs") else "",
            "id": s.get("ID", ""),
            "online": s.get("Online", False),
            "dns_name": s.get("DNSName", ""),
        }

    # Parse peers
    peers = []
    peer_map = data.get("Peer") or {}
    for key, p in peer_map.items():
        peers.append({
            "hostname": p.get("HostName", ""),
            "ip": p.get("TailscaleIPs", [""])[0] if p.get("TailscaleIPs") else "",
            "os": p.get("OS", ""),
            "online": p.get("Online", False),
            "exit_node": p.get("ExitNode", False),
            "exit_node_option": p.get("ExitNodeOption", False),
            "id": p.get("ID", ""),
            "dns_name": p.get("DNSName", ""),
        })

    # Check backend state
    backend_state = data.get("BackendState", "")
    running = backend_state == "Running"

    return {
        "success": True,
        "installed": True,
        "running": running,
        "version": version,
        "backend_state": backend_state,
        "self": self_node,
        "peers": peers,
    }


def tailscale_up(options: dict = None) -> dict:
    """Start/connect Tailscale.

    Args:
        options: Optional settings:
            - advertise_routes (str): Comma-separated CIDR routes (e.g. "192.168.1.0/24")
            - advertise_exit_node (bool): Offer this node as exit node
            - accept_routes (bool): Accept routes from other nodes
            - hostname (str): Override hostname
            - ssh (bool): Enable Tailscale SSH

    Returns:
        {"success": bool, "message": str, "auth_url": str | None}
    """
    cmd = ["sudo", "tailscale", "up"]

    if options:
        if options.get("advertise_routes"):
            cmd += ["--advertise-routes", options["advertise_routes"]]
        if options.get("advertise_exit_node"):
            cmd.append("--advertise-exit-node")
        if options.get("accept_routes"):
            cmd.append("--accept-routes")
        if options.get("hostname"):
            cmd += ["--hostname", options["hostname"]]
        if options.get("ssh"):
            cmd.append("--ssh")
        if options.get("reset"):
            cmd.append("--reset")

    rc, out, err = _run(cmd, timeout=30)

    # tailscale up may return auth URL
    auth_url = None
    combined = out + err
    for line in combined.split("\n"):
        if "https://login.tailscale.com/" in line or "https://login.tailscale.com" in line:
            # Extract URL
            parts = line.split()
            for part in parts:
                if part.startswith("https://"):
                    auth_url = part
                    break

    if rc == 0:
        return {"success": True, "message": "Tailscale connected", "auth_url": auth_url}
    elif auth_url:
        return {"success": True, "message": "Authentication required", "auth_url": auth_url}
    else:
        return {"success": False, "error": err.strip() or "Failed to start Tailscale"}


def tailscale_down() -> dict:
    """Disconnect Tailscale (keeps login).

    Returns:
        {"success": bool, "message": str}
    """
    rc, out, err = _run(["sudo", "tailscale", "down"])
    if rc == 0:
        return {"success": True, "message": "Tailscale disconnected"}
    return {"success": False, "error": err.strip() or "Failed to stop Tailscale"}


def tailscale_logout() -> dict:
    """Logout from Tailscale (requires re-auth to reconnect).

    Returns:
        {"success": bool, "message": str}
    """
    rc, out, err = _run(["sudo", "tailscale", "logout"])
    if rc == 0:
        return {"success": True, "message": "Logged out from Tailscale"}
    return {"success": False, "error": err.strip() or "Failed to logout"}


def set_exit_node(peer_ip: str = "") -> dict:
    """Use a peer as exit node, or clear exit node.

    Args:
        peer_ip: Tailscale IP of the peer to use as exit node. Empty string to clear.

    Returns:
        {"success": bool, "message": str}
    """
    if peer_ip:
        cmd = ["sudo", "tailscale", "set", "--exit-node", peer_ip]
    else:
        cmd = ["sudo", "tailscale", "set", "--exit-node="]

    rc, out, err = _run(cmd)
    if rc == 0:
        if peer_ip:
            return {"success": True, "message": f"Exit node set to {peer_ip}"}
        else:
            return {"success": True, "message": "Exit node cleared"}
    return {"success": False, "error": err.strip() or "Failed to set exit node"}


def set_advertise_routes(routes: str) -> dict:
    """Advertise subnet routes.

    Args:
        routes: Comma-separated CIDR (e.g. "192.168.1.0/24,10.0.0.0/8"). Empty to clear.

    Returns:
        {"success": bool, "message": str}
    """
    if routes:
        cmd = ["sudo", "tailscale", "set", "--advertise-routes", routes]
    else:
        cmd = ["sudo", "tailscale", "set", "--advertise-routes="]

    rc, out, err = _run(cmd)
    if rc == 0:
        return {"success": True, "message": f"Advertised routes: {routes or '(cleared)'}"}
    return {"success": False, "error": err.strip() or "Failed to set routes"}


def get_ip() -> dict:
    """Get this node's Tailscale IP addresses.

    Returns:
        {"success": bool, "ipv4": str, "ipv6": str}
    """
    rc, out, err = _run(["tailscale", "ip"])
    if rc != 0:
        return {"success": False, "error": err.strip() or "Not connected"}

    lines = out.strip().split("\n")
    ipv4 = ""
    ipv6 = ""
    for line in lines:
        line = line.strip()
        if ":" in line:
            ipv6 = line
        elif line:
            ipv4 = line

    return {"success": True, "ipv4": ipv4, "ipv6": ipv6}

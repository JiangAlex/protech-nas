"""NFS service — manage NFS exports via /etc/exports."""

import subprocess
from pathlib import Path

EXPORTS_FILE = "/etc/exports"


def _reload_exports():
    """Reload NFS exports."""
    subprocess.run(["exportfs", "-ra"], capture_output=True)


def list_nfs_exports() -> dict:
    """Parse /etc/exports and list all exports."""
    try:
        content = Path(EXPORTS_FILE).read_text()
    except FileNotFoundError:
        return {"success": True, "exports": [], "note": "/etc/exports not found"}

    exports = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            parts = line.split(None, 1)
            if len(parts) >= 2:
                exports.append({"path": parts[0], "clients": parts[1]})
            elif len(parts) == 1:
                exports.append({"path": parts[0], "clients": ""})

    return {"success": True, "exports": exports}


def add_nfs_export(path: str, clients: str) -> dict:
    """Add a new NFS export."""
    if not path:
        return {"success": False, "error": "path is required"}

    # Ensure path exists
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except PermissionError:
        import subprocess
        r = subprocess.run(["sudo", "mkdir", "-p", path], capture_output=True, text=True)
        if r.returncode != 0:
            return {"success": False, "error": f"Cannot create directory {path}: {r.stderr}"}

    # Set proper ownership and permissions
    import subprocess as _sp
    import os
    user = os.getenv("USER", "root")
    _sp.run(["sudo", "chown", f"{user}:{user}", path], capture_output=True)
    _sp.run(["sudo", "chmod", "775", path], capture_output=True)

    entry = f"{path} {clients}\n"

    try:
        with open(EXPORTS_FILE, "a") as f:
            f.write(entry)
        _reload_exports()
        return {"success": True, "message": f"Export {path} added"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_nfs_export(path: str) -> dict:
    """Remove an NFS export by path."""
    try:
        content = Path(EXPORTS_FILE).read_text()
    except FileNotFoundError:
        return {"success": False, "error": "/etc/exports not found"}

    lines = content.split("\n")
    new_lines = [l for l in lines if not l.strip().startswith(path)]

    try:
        Path(EXPORTS_FILE).write_text("\n".join(new_lines))
        _reload_exports()
        return {"success": True, "message": f"Export {path} removed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


import re


def update_nfs_export(path: str, clients: str) -> dict:
    """Update an existing NFS export's client rules.

    Args:
        path: The export path that already exists in /etc/exports.
        clients: New client specification (e.g. "192.168.1.0/24(rw,sync,no_subtree_check)").

    Returns:
        {"success": bool, "message": str}
    """
    if not path:
        return {"success": False, "error": "path is required"}
    if not clients:
        return {"success": False, "error": "clients is required"}

    # Basic clients format validation
    if not re.match(r"^[\d./a-zA-Z*]+([\s(][^\n]+)?$", clients.strip()):
        return {"success": False, "error": f"Invalid clients format: {clients}"}

    try:
        content = Path(EXPORTS_FILE).read_text()
    except FileNotFoundError:
        return {"success": False, "error": "/etc/exports not found"}

    lines = content.split("\n")
    found = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped.startswith(path):
            # Check it's the exact path (not just a prefix match)
            parts = stripped.split(None, 1)
            if parts[0] == path:
                new_lines.append(f"{path} {clients}")
                found = True
                continue
        new_lines.append(line)

    if not found:
        return {"success": False, "error": f"Export path {path} not found in /etc/exports"}

    try:
        Path(EXPORTS_FILE).write_text("\n".join(new_lines))
        _reload_exports()
        return {"success": True, "message": f"Export {path} updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_nfs_status() -> dict:
    """Get NFS service status and connected clients.

    Returns:
        {"success": bool, "service_running": bool, "clients": list[dict]}
    """
    r = subprocess.run(["systemctl", "is-active", "nfs-server"], capture_output=True, text=True)
    running = r.stdout.strip() == "active"

    clients = []
    if running:
        r = subprocess.run(["showmount", "-a", "--no-headers"], capture_output=True, text=True)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                if ":" in line:
                    ip, mount = line.split(":", 1)
                    clients.append({"ip": ip.strip(), "mount": mount.strip()})

    return {"success": True, "service_running": running, "clients": clients}

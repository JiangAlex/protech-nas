"""Samba service — manage SMB shares via smb.conf."""

import subprocess
import re
from pathlib import Path

SMB_CONF = "/etc/samba/smb.conf"


def _restart_smbd():
    """Restart Samba service."""
    subprocess.run(["systemctl", "restart", "smbd"], capture_output=True)


def list_smb_shares() -> dict:
    """Parse smb.conf and list all user-defined shares."""
    try:
        content = Path(SMB_CONF).read_text()
    except FileNotFoundError:
        return {"success": True, "shares": [], "note": "smb.conf not found"}

    shares = []
    current_share = None

    for line in content.split("\n"):
        line = line.strip()
        # Match section headers like [sharename]
        match = re.match(r"^\[(.+)\]$", line)
        if match:
            name = match.group(1)
            if name.lower() not in ("global", "homes", "printers", "print$"):
                current_share = {"name": name}
                shares.append(current_share)
            else:
                current_share = None
        elif current_share and "=" in line:
            key, _, value = line.partition("=")
            current_share[key.strip()] = value.strip()

    return {"success": True, "shares": shares}


def add_smb_share(config: dict) -> dict:
    """Add a new SMB share to smb.conf."""
    name = config.get("name", "")
    path = config.get("path", "")
    if not name or not path:
        return {"success": False, "error": "name and path are required"}

    # Ensure path exists
    Path(path).mkdir(parents=True, exist_ok=True)

    # Build share block
    block = f"\n[{name}]\n"
    block += f"   path = {path}\n"
    block += f"   comment = {config.get('comment', '')}\n"
    block += f"   read only = {'yes' if config.get('read_only') else 'no'}\n"
    block += f"   guest ok = {'yes' if config.get('guest_ok') else 'no'}\n"
    if config.get("valid_users"):
        block += f"   valid users = {config['valid_users']}\n"
    block += "   create mask = 0664\n"
    block += "   directory mask = 0775\n"

    try:
        with open(SMB_CONF, "a") as f:
            f.write(block)
        _restart_smbd()
        return {"success": True, "message": f"Share [{name}] created"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_smb_share(name: str) -> dict:
    """Remove an SMB share from smb.conf."""
    try:
        content = Path(SMB_CONF).read_text()
    except FileNotFoundError:
        return {"success": False, "error": "smb.conf not found"}

    # Remove the section [name] and its content until next section or EOF
    lines = content.split("\n")
    new_lines = []
    skip = False

    for line in lines:
        match = re.match(r"^\[(.+)\]$", line.strip())
        if match:
            if match.group(1) == name:
                skip = True
                continue
            else:
                skip = False
        if not skip:
            new_lines.append(line)

    try:
        Path(SMB_CONF).write_text("\n".join(new_lines))
        _restart_smbd()
        return {"success": True, "message": f"Share [{name}] removed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

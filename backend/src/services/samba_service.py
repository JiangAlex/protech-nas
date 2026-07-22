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


def update_smb_share(name: str, config: dict) -> dict:
    """Update an existing SMB share in smb.conf.

    Args:
        name: Share name to update (must already exist).
        config: Dict with fields to update. Supported keys:
            path, comment, read_only, guest_ok, valid_users

    Returns:
        {"success": bool, "message": str}
    """
    # Reject reserved section names
    if name.lower() in ("global", "homes", "printers", "print$"):
        return {"success": False, "error": f"Cannot modify reserved section: {name}"}

    try:
        content = Path(SMB_CONF).read_text()
    except FileNotFoundError:
        return {"success": False, "error": "smb.conf not found"}

    lines = content.split("\n")
    section_start = None
    section_end = None

    # Find the section boundaries
    for i, line in enumerate(lines):
        match = re.match(r"^\[(.+)\]$", line.strip())
        if match:
            if match.group(1) == name:
                section_start = i
            elif section_start is not None and section_end is None:
                section_end = i
                break

    if section_start is None:
        return {"success": False, "error": f"Share [{name}] not found in smb.conf"}

    if section_end is None:
        section_end = len(lines)

    # Build updated section
    path = config.get("path", "")
    new_section = [f"[{name}]"]
    new_section.append(f"   path = {path}" if path else f"   path = {_get_existing_value(lines, section_start, section_end, 'path')}")
    new_section.append(f"   comment = {config.get('comment', '')}")
    new_section.append(f"   read only = {'yes' if config.get('read_only') else 'no'}")
    new_section.append(f"   guest ok = {'yes' if config.get('guest_ok') else 'no'}")
    if config.get("valid_users"):
        new_section.append(f"   valid users = {config['valid_users']}")
    new_section.append("   create mask = 0664")
    new_section.append("   directory mask = 0775")

    # Replace old section with new
    new_lines = lines[:section_start] + new_section + lines[section_end:]

    try:
        Path(SMB_CONF).write_text("\n".join(new_lines))
        # Validate config before restarting
        rc = subprocess.run(["testparm", "-s", "--suppress-prompt"], capture_output=True).returncode
        if rc != 0:
            # Rollback
            Path(SMB_CONF).write_text(content)
            return {"success": False, "error": "Invalid smb.conf syntax after update. Changes rolled back."}
        _restart_smbd()
        return {"success": True, "message": f"Share [{name}] updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_existing_value(lines: list, start: int, end: int, key: str) -> str:
    """Extract value for a key from a section's lines."""
    for line in lines[start:end]:
        stripped = line.strip()
        if "=" in stripped:
            k, _, v = stripped.partition("=")
            if k.strip() == key:
                return v.strip()
    return ""


def get_share_acl(name: str) -> dict:
    """Get filesystem ACL for a share's path.

    Args:
        name: Share name (to look up its path from smb.conf).

    Returns:
        {"success": bool, "owner": str, "group": str, "permissions": str, "acl": list[dict]}
    """
    # Look up share path
    shares = list_smb_shares()
    share = next((s for s in shares.get("shares", []) if s.get("name") == name), None)
    if not share:
        return {"success": False, "error": f"Share [{name}] not found"}

    share_path = share.get("path", "")
    if not share_path or not Path(share_path).exists():
        return {"success": False, "error": f"Share path does not exist: {share_path}"}

    rc, out, err = subprocess.run(
        ["getfacl", "--numeric", "--absolute-names", share_path],
        capture_output=True, text=True
    ).returncode, "", ""
    r = subprocess.run(["getfacl", "--absolute-names", share_path], capture_output=True, text=True)
    if r.returncode != 0:
        return {"success": False, "error": f"getfacl failed: {r.stderr.strip()}"}

    out = r.stdout
    owner = ""
    group = ""
    permissions = ""
    acl_entries = []

    for line in out.split("\n"):
        line = line.strip()
        if line.startswith("# owner:"):
            owner = line.split(":", 1)[1].strip()
        elif line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
        elif line.startswith("user:") and "::" not in line:
            parts = line.split(":")
            if len(parts) == 3 and parts[1]:
                acl_entries.append({"type": "user", "name": parts[1], "perms": parts[2]})
            elif len(parts) == 3 and not parts[1]:
                permissions = parts[2]
        elif line.startswith("group:") and "::" not in line:
            parts = line.split(":")
            if len(parts) == 3 and parts[1]:
                acl_entries.append({"type": "group", "name": parts[1], "perms": parts[2]})

    return {
        "success": True,
        "owner": owner,
        "group": group,
        "permissions": permissions,
        "acl": acl_entries,
    }


def set_share_acl(name: str, acl: list[dict]) -> dict:
    """Set filesystem ACL on a share's path.

    Args:
        name: Share name.
        acl: List of ACL entries [{"type": "user"/"group", "name": str, "perms": "rwx"}]

    Returns:
        {"success": bool, "message": str}
    """
    shares = list_smb_shares()
    share = next((s for s in shares.get("shares", []) if s.get("name") == name), None)
    if not share:
        return {"success": False, "error": f"Share [{name}] not found"}

    share_path = share.get("path", "")
    if not share_path or not Path(share_path).exists():
        return {"success": False, "error": f"Share path does not exist: {share_path}"}

    errors = []
    for entry in acl:
        entry_type = entry.get("type", "")
        entry_name = entry.get("name", "")
        perms = entry.get("perms", "")

        if entry_type not in ("user", "group"):
            errors.append(f"Invalid type: {entry_type}")
            continue
        if not entry_name:
            errors.append("Empty name in ACL entry")
            continue
        if not re.match(r"^[rwx\-]{1,3}$", perms):
            errors.append(f"Invalid permissions: {perms}")
            continue

        prefix = "u" if entry_type == "user" else "g"
        r = subprocess.run(
            ["setfacl", "-m", f"{prefix}:{entry_name}:{perms}", share_path],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            errors.append(f"Failed to set {entry_type}:{entry_name}: {r.stderr.strip()}")

    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return {"success": True, "message": f"ACL updated for [{name}]"}


def get_smb_status() -> dict:
    """Get Samba service status and active connections.

    Returns:
        {"success": bool, "service_running": bool, "connections": list[dict]}
    """
    # Check service status
    r = subprocess.run(["systemctl", "is-active", "smbd"], capture_output=True, text=True)
    running = r.stdout.strip() == "active"

    connections = []
    if running:
        r = subprocess.run(["smbstatus", "-b", "--no-header"], capture_output=True, text=True)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 4:
                    connections.append({
                        "pid": parts[0],
                        "user": parts[1],
                        "group": parts[2],
                        "ip": parts[3] if len(parts) > 3 else "",
                    })

    return {"success": True, "service_running": running, "connections": connections}

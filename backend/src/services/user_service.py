"""User service — manage Linux system users and groups."""

import subprocess


def _run(cmd: list[str], input_data: str = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10, input=input_data)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


def list_users() -> dict:
    """List system users with UID >= 1000 (excluding nobody)."""
    users = []
    try:
        with open("/etc/passwd", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 7:
                    uid = int(parts[2])
                    if uid >= 1000 and parts[0] != "nobody":
                        users.append({
                            "username": parts[0],
                            "uid": uid,
                            "gid": int(parts[3]),
                            "home": parts[5],
                            "shell": parts[6],
                        })
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "users": users}


def create_user(username: str, password: str, groups: str = "", smb_enabled: bool = True) -> dict:
    """Create a new system user with optional Samba access."""
    # Create user
    cmd = ["useradd", "-m", "-s", "/bin/bash"]
    if groups:
        cmd += ["-G", groups]
    cmd.append(username)

    rc, out, err = _run(cmd)
    if rc != 0:
        return {"success": False, "error": err.strip() or "useradd failed"}

    # Set password
    rc, out, err = _run(["chpasswd"], input_data=f"{username}:{password}")
    if rc != 0:
        return {"success": False, "error": f"Failed to set password: {err.strip()}"}

    # Enable Samba access
    if smb_enabled:
        rc, out, err = _run(["smbpasswd", "-a", "-s", username], input_data=f"{password}\n{password}\n")
        if rc != 0:
            return {"success": True, "message": f"User {username} created (Samba setup failed: {err.strip()})"}
        _run(["smbpasswd", "-e", username])

    return {"success": True, "message": f"User {username} created"}


def delete_user(username: str) -> dict:
    """Delete a system user and their home directory."""
    rc, out, err = _run(["userdel", "-r", username])
    if rc != 0:
        return {"success": False, "error": err.strip() or "userdel failed"}

    # Remove from Samba
    _run(["smbpasswd", "-x", username])

    return {"success": True, "message": f"User {username} deleted"}


def change_password(username: str, password: str) -> dict:
    """Change a user's password (system + Samba)."""
    rc, out, err = _run(["chpasswd"], input_data=f"{username}:{password}")
    if rc != 0:
        return {"success": False, "error": err.strip()}

    # Update Samba password
    _run(["smbpasswd", "-a", "-s", username], input_data=f"{password}\n{password}\n")

    return {"success": True, "message": f"Password changed for {username}"}


def update_user(username: str, config: dict) -> dict:
    """Update an existing user's properties.

    Args:
        username: The user to modify.
        config: Dict with optional keys:
            - shell (str): New login shell (must exist in /etc/shells)
            - groups (str): Comma-separated supplementary groups
            - home (str): New home directory

    Returns:
        {"success": bool, "message": str}
    """
    if not username:
        return {"success": False, "error": "username is required"}

    # Prevent modifying root
    if username == "root":
        return {"success": False, "error": "Cannot modify root user"}

    # Verify user exists
    rc, _, err = _run(["id", username])
    if rc != 0:
        return {"success": False, "error": f"User {username} does not exist"}

    cmd = ["usermod"]

    # Shell
    shell = config.get("shell")
    if shell:
        # Validate shell exists in /etc/shells
        try:
            valid_shells = [
                line.strip() for line in open("/etc/shells")
                if line.strip() and not line.startswith("#")
            ]
        except FileNotFoundError:
            valid_shells = ["/bin/bash", "/bin/sh", "/usr/sbin/nologin"]
        if shell not in valid_shells:
            return {"success": False, "error": f"Invalid shell: {shell}. Valid: {', '.join(valid_shells)}"}
        cmd += ["-s", shell]

    # Supplementary groups
    groups = config.get("groups")
    if groups is not None:
        cmd += ["-G", groups]

    # Home directory
    home = config.get("home")
    if home:
        cmd += ["-d", home, "-m"]

    if len(cmd) == 1:
        return {"success": False, "error": "No changes specified"}

    cmd.append(username)
    rc, _, err = _run(cmd)
    if rc != 0:
        return {"success": False, "error": err.strip() or "usermod failed"}

    return {"success": True, "message": f"User {username} updated"}


def list_groups() -> dict:
    """List groups with GID >= 1000."""
    groups = []
    try:
        with open("/etc/group", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 4:
                    gid = int(parts[2])
                    if gid >= 1000:
                        groups.append({
                            "name": parts[0],
                            "gid": gid,
                            "members": parts[3].split(",") if parts[3] else [],
                        })
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "groups": groups}


def create_group(name: str) -> dict:
    """Create a new group."""
    rc, out, err = _run(["groupadd", name])
    if rc != 0:
        return {"success": False, "error": err.strip() or "groupadd failed"}
    return {"success": True, "message": f"Group {name} created"}


def delete_group(name: str) -> dict:
    """Delete a group."""
    rc, out, err = _run(["groupdel", name])
    if rc != 0:
        return {"success": False, "error": err.strip() or "groupdel failed"}
    return {"success": True, "message": f"Group {name} deleted"}


def disable_user(username: str) -> dict:
    """Disable a user account (lock password + disable Samba).

    Returns:
        {"success": bool, "message": str}
    """
    if username == "root":
        return {"success": False, "error": "Cannot disable root"}

    rc, _, err = _run(["id", username])
    if rc != 0:
        return {"success": False, "error": f"User {username} does not exist"}

    rc, _, err = _run(["usermod", "-L", username])
    if rc != 0:
        return {"success": False, "error": f"Failed to lock: {err.strip()}"}

    # Disable Samba access
    _run(["smbpasswd", "-d", username])

    return {"success": True, "message": f"User {username} disabled"}


def enable_user(username: str) -> dict:
    """Enable a disabled user account.

    Returns:
        {"success": bool, "message": str}
    """
    rc, _, err = _run(["id", username])
    if rc != 0:
        return {"success": False, "error": f"User {username} does not exist"}

    rc, _, err = _run(["usermod", "-U", username])
    if rc != 0:
        return {"success": False, "error": f"Failed to unlock: {err.strip()}"}

    # Enable Samba access
    _run(["smbpasswd", "-e", username])

    return {"success": True, "message": f"User {username} enabled"}


def update_group_members(group_name: str, add: list = None, remove: list = None) -> dict:
    """Add or remove users from a group.

    Args:
        group_name: Target group.
        add: List of usernames to add.
        remove: List of usernames to remove.

    Returns:
        {"success": bool, "added": list, "removed": list, "errors": list}
    """
    add = add or []
    remove = remove or []
    errors = []
    added = []
    removed = []

    # Verify group exists
    rc, _, _ = _run(["getent", "group", group_name])
    if rc != 0:
        return {"success": False, "error": f"Group {group_name} does not exist"}

    for user in add:
        rc, _, err = _run(["gpasswd", "-a", user, group_name])
        if rc == 0:
            added.append(user)
        else:
            errors.append(f"Failed to add {user}: {err.strip()}")

    for user in remove:
        rc, _, err = _run(["gpasswd", "-d", user, group_name])
        if rc == 0:
            removed.append(user)
        else:
            errors.append(f"Failed to remove {user}: {err.strip()}")

    return {
        "success": len(errors) == 0,
        "added": added,
        "removed": removed,
        "errors": errors,
    }


def get_quota(username: str) -> dict:
    """Get disk quota for a user.

    Returns:
        {"success": bool, "username": str, "used_mb": float, "soft_limit_mb": float, "hard_limit_mb": float}
    """
    rc, _, err = _run(["id", username])
    if rc != 0:
        return {"success": False, "error": f"User {username} does not exist"}

    rc, out, err = _run(["quota", "-u", username, "--no-wrap", "-p"])
    if rc != 0 and "none" in err.lower():
        return {"success": False, "error": "Quota not enabled on this filesystem"}
    if rc != 0:
        return {"success": False, "error": err.strip() or "quota command failed"}

    # Parse quota output
    # Filesystem  blocks   quota   limit   grace   files   quota   limit   grace
    used_mb = 0.0
    soft_limit_mb = 0.0
    hard_limit_mb = 0.0

    lines = out.strip().split("\n")
    for line in lines[2:]:  # Skip headers
        parts = line.split()
        if len(parts) >= 4:
            try:
                used_mb = round(int(parts[1].rstrip("*")) / 1024, 1)  # blocks to MB
                soft_limit_mb = round(int(parts[2]) / 1024, 1)
                hard_limit_mb = round(int(parts[3]) / 1024, 1)
            except (ValueError, IndexError):
                continue
            break

    return {
        "success": True,
        "username": username,
        "used_mb": used_mb,
        "soft_limit_mb": soft_limit_mb,
        "hard_limit_mb": hard_limit_mb,
    }


def set_quota(username: str, soft_mb: int, hard_mb: int, filesystem: str = "/") -> dict:
    """Set disk quota for a user.

    Args:
        username: Target user.
        soft_mb: Soft limit in MB.
        hard_mb: Hard limit in MB.
        filesystem: Filesystem to apply quota on.

    Returns:
        {"success": bool, "message": str}
    """
    if soft_mb < 0 or hard_mb < 0:
        return {"success": False, "error": "Quota values must be positive"}
    if soft_mb > hard_mb:
        return {"success": False, "error": "Soft limit cannot exceed hard limit"}

    rc, _, err = _run(["id", username])
    if rc != 0:
        return {"success": False, "error": f"User {username} does not exist"}

    # setquota -u user block-soft block-hard inode-soft inode-hard filesystem
    soft_blocks = soft_mb * 1024  # MB to KB blocks
    hard_blocks = hard_mb * 1024

    rc, _, err = _run([
        "setquota", "-u", username,
        str(soft_blocks), str(hard_blocks),
        "0", "0",  # No inode limits
        filesystem
    ])
    if rc != 0:
        return {"success": False, "error": f"setquota failed: {err.strip()}"}

    return {"success": True, "message": f"Quota set for {username}: soft={soft_mb}MB, hard={hard_mb}MB"}


import json as _json
import hashlib
import hmac
import struct
import time as _time
import os as _os
from pathlib import Path as _Path

# ─── TOTP (2FA) ──────────────────────────────────────────────────────────────

TOTP_SECRETS_FILE = os.path.join(_os.path.expanduser("~"), ".protech-nas/totp_secrets.json")
SESSIONS_FILE = os.path.join(_os.path.expanduser("~"), ".protech-nas/sessions.json")
AUDIT_LOG_FILE = os.path.join(_os.path.expanduser("~"), ".protech-nas/audit.json")


def _load_json_file(path, default=None):
    try:
        with open(path) as f:
            return _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        return default if default is not None else {}


def _save_json_file(path, data):
    _os.makedirs(_os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        _json.dump(data, f, indent=2, default=str)


def _generate_base32_secret(length=32):
    """Generate a random base32 secret."""
    import base64
    random_bytes = _os.urandom(length)
    return base64.b32encode(random_bytes).decode("ascii").rstrip("=")


def _totp_code(secret: str, time_step: int = 30) -> str:
    """Generate current TOTP code from secret."""
    import base64
    # Decode base32 secret
    padded = secret + "=" * (8 - len(secret) % 8) if len(secret) % 8 else secret
    key = base64.b32decode(padded.upper())
    # Time counter
    counter = int(_time.time()) // time_step
    counter_bytes = struct.pack(">Q", counter)
    # HMAC-SHA1
    h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    # Dynamic truncation
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1000000).zfill(6)


def setup_totp(username: str) -> dict:
    """Generate TOTP secret and provisioning URI for a user.

    Returns:
        {"success": bool, "secret": str, "qr_uri": str}
    """
    rc, _, _ = _run(["id", username])
    if rc != 0:
        return {"success": False, "error": f"User {username} does not exist"}

    secret = _generate_base32_secret(20)
    qr_uri = f"otpauth://totp/ProTech%20NAS:{username}?secret={secret}&issuer=ProTech%20NAS"

    # Store secret
    secrets = _load_json_file(TOTP_SECRETS_FILE, {})
    secrets[username] = {"secret": secret, "enabled": False}
    _save_json_file(TOTP_SECRETS_FILE, secrets)
    _os.chmod(TOTP_SECRETS_FILE, 0o600)

    return {"success": True, "secret": secret, "qr_uri": qr_uri}


def verify_totp(username: str, code: str) -> dict:
    """Verify a TOTP code and enable 2FA if first verification.

    Returns:
        {"success": bool, "valid": bool}
    """
    secrets = _load_json_file(TOTP_SECRETS_FILE, {})
    user_totp = secrets.get(username)
    if not user_totp:
        return {"success": False, "error": f"2FA not set up for {username}"}

    secret = user_totp["secret"]

    # Check current and adjacent time steps (±1)
    valid = False
    for offset in [-1, 0, 1]:
        counter = (int(_time.time()) // 30) + offset
        counter_bytes = struct.pack(">Q", counter)
        import base64
        padded = secret + "=" * (8 - len(secret) % 8) if len(secret) % 8 else secret
        key = base64.b32decode(padded.upper())
        h = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        o = h[-1] & 0x0F
        c = struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF
        expected = str(c % 1000000).zfill(6)
        if code == expected:
            valid = True
            break

    if valid and not user_totp.get("enabled"):
        secrets[username]["enabled"] = True
        _save_json_file(TOTP_SECRETS_FILE, secrets)

    return {"success": True, "valid": valid}


# ─── Audit Log ────────────────────────────────────────────────────────────────

def get_audit_log(filters: dict = None) -> dict:
    """Get user audit log.

    Args:
        filters: {"username": str, "action": str, "limit": int}

    Returns:
        {"success": bool, "logs": list[dict]}
    """
    filters = filters or {}
    logs = _load_json_file(AUDIT_LOG_FILE, [])

    # Apply filters
    if filters.get("username"):
        logs = [l for l in logs if l.get("username") == filters["username"]]
    if filters.get("action"):
        logs = [l for l in logs if l.get("action") == filters["action"]]

    limit = min(filters.get("limit", 100), 1000)
    logs = list(reversed(logs))[:limit]

    return {"success": True, "logs": logs}


# ─── Sessions ─────────────────────────────────────────────────────────────────

def list_sessions() -> dict:
    """List active sessions.

    Returns:
        {"success": bool, "sessions": list[dict]}
    """
    sessions = _load_json_file(SESSIONS_FILE, [])
    # Filter expired (older than 24h)
    now = _time.time()
    active = [s for s in sessions if now - s.get("created_ts", 0) < 86400]
    return {"success": True, "sessions": active}


def revoke_session(session_id: str) -> dict:
    """Revoke (invalidate) a session.

    Returns:
        {"success": bool}
    """
    sessions = _load_json_file(SESSIONS_FILE, [])
    original = len(sessions)
    sessions = [s for s in sessions if s.get("id") != session_id]

    if len(sessions) == original:
        return {"success": False, "error": f"Session {session_id} not found"}

    _save_json_file(SESSIONS_FILE, sessions)
    return {"success": True}

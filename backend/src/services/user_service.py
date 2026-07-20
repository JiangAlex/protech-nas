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

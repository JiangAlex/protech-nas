"""Storage service — disk, RAID, mount management via system commands."""

import subprocess
import json


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


def list_disks() -> dict:
    """List all disks and partitions using lsblk."""
    rc, out, err = _run(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL"])
    if rc != 0:
        return {"success": False, "error": err}
    try:
        data = json.loads(out)
        return {"success": True, "devices": data.get("blockdevices", [])}
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse lsblk output"}


def list_mounts() -> dict:
    """List mounted filesystems using df."""
    rc, out, err = _run(["df", "-h", "--output=source,fstype,size,used,avail,pcent,target"])
    if rc != 0:
        return {"success": False, "error": err}
    lines = out.strip().split("\n")
    if len(lines) < 2:
        return {"success": True, "mounts": []}
    headers = lines[0].split()
    mounts = []
    for line in lines[1:]:
        parts = line.split(None, 6)
        if len(parts) >= 7:
            mounts.append({
                "device": parts[0],
                "fstype": parts[1],
                "size": parts[2],
                "used": parts[3],
                "avail": parts[4],
                "use_percent": parts[5],
                "mount_point": parts[6],
            })
    return {"success": True, "mounts": mounts}


def get_raid_status() -> dict:
    """Get RAID array status from /proc/mdstat."""
    try:
        with open("/proc/mdstat", "r") as f:
            content = f.read()
        return {"success": True, "mdstat": content}
    except FileNotFoundError:
        return {"success": True, "mdstat": "No RAID arrays detected (mdstat not available)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def mount_disk(device: str, mount_point: str, fs_type: str = "ext4") -> dict:
    """Mount a device to a mount point."""
    # Create mount point if not exists
    _run(["mkdir", "-p", mount_point])
    rc, out, err = _run(["mount", "-t", fs_type, device, mount_point])
    if rc != 0:
        return {"success": False, "error": err.strip()}
    return {"success": True, "message": f"Mounted {device} to {mount_point}"}


def unmount_disk(mount_point: str) -> dict:
    """Unmount a mount point."""
    rc, out, err = _run(["umount", mount_point])
    if rc != 0:
        return {"success": False, "error": err.strip()}
    return {"success": True, "message": f"Unmounted {mount_point}"}

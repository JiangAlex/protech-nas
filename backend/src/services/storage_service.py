"""Storage service — disk, RAID, mount management via system commands."""

import subprocess
import json
import re


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


def _sudo_run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a command with sudo and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=timeout)
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
        # Flatten nested children (partitions) into a flat list
        devices = []
        for dev in data.get("blockdevices", []):
            children = dev.pop("children", [])
            devices.append(dev)
            for child in children:
                child.pop("children", None)
                devices.append(child)
        return {"success": True, "devices": devices}
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


# ─── Device Validation ────────────────────────────────────────────────────────

_ALLOWED_DEVICE_PATTERN = re.compile(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?)$")


def _get_system_disk() -> str:
    """Detect which disk holds the root filesystem (/)."""
    try:
        rc, out, _ = _run(["findmnt", "-n", "-o", "SOURCE", "/"])
        if rc == 0 and out.strip():
            source = out.strip()  # e.g. /dev/sdb2
            # Strip partition number to get parent disk
            m = re.match(r"(/dev/sd[a-z])", source)
            if m:
                return m.group(1)
            # NVMe: /dev/nvme0n1p2 -> /dev/nvme0n1
            m = re.match(r"(/dev/nvme\d+n\d+)", source)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "/dev/sda"  # fallback: assume sda is system disk


def _validate_device(device: str) -> str | None:
    """Validate device path. Returns error message or None if valid."""
    if not device:
        return "device is required"
    if not _ALLOWED_DEVICE_PATTERN.match(device):
        return f"Invalid device path: {device}"

    # Block the system disk and all its partitions
    sys_disk = _get_system_disk()
    if device == sys_disk or device.startswith(sys_disk) and (
        len(device) == len(sys_disk) or device[len(sys_disk):].isdigit()
        or device[len(sys_disk):].startswith("p")
    ):
        return f"Device {device} is on the system disk ({sys_disk}). Operation blocked to protect the OS."
    return None


# ─── Format ──────────────────────────────────────────────────────────────────

_SUPPORTED_FS = ("ext4", "xfs", "btrfs", "exfat")


def format_disk(device: str, fs_type: str) -> dict:
    """Format a disk partition with the specified filesystem.

    Args:
        device: Device path (e.g. /dev/sdb1). /dev/sda* is blocked.
        fs_type: Filesystem type (ext4, xfs, btrfs).

    Returns:
        {"success": bool, "message": str, "error": str}

    WARNING: This is an irreversible operation — all data on the device will be lost.
    """
    # Validate device
    err = _validate_device(device)
    if err:
        return {"success": False, "error": err}

    # Validate fs_type
    if fs_type not in _SUPPORTED_FS:
        return {"success": False, "error": f"Unsupported filesystem: {fs_type}. Supported: {', '.join(_SUPPORTED_FS)}"}

    # Check device is not mounted
    rc, out, _ = _run(["findmnt", "-n", "-o", "TARGET", device])
    if rc == 0 and out.strip():
        return {"success": False, "error": f"Device {device} is currently mounted at {out.strip()}. Unmount first."}

    # Check device exists
    rc, _, err_msg = _run(["lsblk", device])
    if rc != 0:
        return {"success": False, "error": f"Device {device} does not exist."}

    # Execute format
    cmd = [f"mkfs.{fs_type}"]
    if fs_type == "ext4":
        cmd.append("-F")  # Force, skip confirmation
    elif fs_type == "xfs":
        cmd.append("-f")  # Force overwrite
    elif fs_type == "btrfs":
        cmd.append("-f")  # Force overwrite
    # exfat: mkfs.exfat has no force flag needed
    cmd.append(device)

    rc, out, err_msg = _sudo_run(cmd)
    if rc != 0:
        return {"success": False, "error": f"Format failed: {err_msg.strip()}"}

    return {"success": True, "message": f"Formatted {device} as {fs_type}"}


# ─── S.M.A.R.T. ─────────────────────────────────────────────────────────────

def get_smart_info(device: str) -> dict:
    """Read S.M.A.R.T. health information for a device.

    Args:
        device: Device path (e.g. /dev/sda).

    Returns:
        {
            "success": bool,
            "smart_status": str,       # "PASSED" / "FAILED"
            "temperature": int | None,
            "power_on_hours": int | None,
            "attributes": list[dict]
        }
    """
    # Allow /dev/sda for SMART (read-only, safe)
    if not device or not re.match(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?)$", device):
        return {"success": False, "error": f"Invalid device path: {device}"}

    rc, out, err_msg = _sudo_run(["smartctl", "-a", "--json=c", device])
    # smartctl returns non-zero for various reasons, but JSON output may still be valid
    if not out.strip():
        if "not found" in err_msg.lower() or rc == 127:
            return {"success": False, "error": "smartctl not installed. Install smartmontools."}
        return {"success": False, "error": f"smartctl failed: {err_msg.strip()}"}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse smartctl JSON output"}

    # Extract status
    smart_status = "UNKNOWN"
    status_obj = data.get("smart_status", {})
    if isinstance(status_obj, dict):
        passed = status_obj.get("passed")
        if passed is True:
            smart_status = "PASSED"
        elif passed is False:
            smart_status = "FAILED"

    # Extract temperature
    temperature = None
    temp_obj = data.get("temperature", {})
    if isinstance(temp_obj, dict):
        temperature = temp_obj.get("current")

    # Extract power on hours
    power_on_hours = None
    power_obj = data.get("power_on_time", {})
    if isinstance(power_obj, dict):
        power_on_hours = power_obj.get("hours")

    # Extract attributes
    attributes = []
    ata_attrs = data.get("ata_smart_attributes", {}).get("table", [])
    for attr in ata_attrs:
        attributes.append({
            "id": attr.get("id"),
            "name": attr.get("name"),
            "value": attr.get("value"),
            "worst": attr.get("worst"),
            "thresh": attr.get("thresh"),
            "raw_value": attr.get("raw", {}).get("value") if isinstance(attr.get("raw"), dict) else attr.get("raw"),
        })

    return {
        "success": True,
        "smart_status": smart_status,
        "temperature": temperature,
        "power_on_hours": power_on_hours,
        "attributes": attributes,
    }


def run_smart_test(device: str, test_type: str = "short") -> dict:
    """Run a S.M.A.R.T. self-test on a device.

    Args:
        device: Device path (e.g. /dev/sda).
        test_type: Test type — "short", "long", or "conveyance".

    Returns:
        {"success": bool, "message": str, "estimated_minutes": int}
    """
    if not device or not re.match(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?)$", device):
        return {"success": False, "error": f"Invalid device path: {device}"}

    allowed_tests = ("short", "long", "conveyance")
    if test_type not in allowed_tests:
        return {"success": False, "error": f"Invalid test type: {test_type}. Allowed: {', '.join(allowed_tests)}"}

    rc, out, err_msg = _sudo_run(["smartctl", "-t", test_type, device])
    if rc == 127:
        return {"success": False, "error": "smartctl not installed. Install smartmontools."}

    # Parse estimated completion time from output
    estimated_minutes = 2 if test_type == "short" else 120 if test_type == "long" else 5

    # Try to extract from output like "Please wait 2 minutes for test to complete."
    match = re.search(r"(\d+)\s*minutes?", out)
    if match:
        estimated_minutes = int(match.group(1))

    # smartctl may return non-zero even on success for -t
    if "Testing has begun" in out or "test has begun" in out.lower() or rc == 0:
        return {
            "success": True,
            "message": f"S.M.A.R.T. {test_type} test started on {device}",
            "estimated_minutes": estimated_minutes,
        }

    return {"success": False, "error": f"Failed to start test: {err_msg.strip() or out.strip()}"}


# ─── fstab Management ─────────────────────────────────────────────────────────

def get_fstab() -> dict:
    """Parse /etc/fstab and return entries."""
    try:
        entries = []
        with open("/etc/fstab", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    entries.append({
                        "device": parts[0],
                        "mount": parts[1],
                        "fs": parts[2],
                        "options": parts[3] if len(parts) > 3 else "defaults",
                        "dump": int(parts[4]) if len(parts) > 4 else 0,
                        "pass": int(parts[5]) if len(parts) > 5 else 0,
                    })
        return {"success": True, "entries": entries}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_fstab_entry(device: str, mount: str, fs: str, options: str = "defaults") -> dict:
    """Add an entry to /etc/fstab."""
    if not device or not mount or not fs:
        return {"success": False, "error": "device, mount, and fs are required"}

    # Check for duplicate mount point
    current = get_fstab()
    if current["success"]:
        for entry in current["entries"]:
            if entry["mount"] == mount:
                return {"success": False, "error": f"Mount point {mount} already exists in fstab"}

    line = f"{device}\t{mount}\t{fs}\t{options}\t0\t2\n"
    try:
        rc, _, err = _sudo_run(["bash", "-c", f"echo '{line.strip()}' >> /etc/fstab"])
        if rc != 0:
            return {"success": False, "error": err.strip()}
        return {"success": True, "message": f"Added {mount} to fstab"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remove_fstab_entry(mount: str) -> dict:
    """Remove an entry from /etc/fstab by mount point."""
    if not mount:
        return {"success": False, "error": "mount is required"}
    if mount in ("/", "/boot", "/boot/efi"):
        return {"success": False, "error": f"Cannot remove system mount point: {mount}"}

    try:
        # Use sed to remove the line matching the mount point
        escaped = mount.replace("/", "\\/")
        rc, _, err = _sudo_run(["sed", "-i", f"/\\s{escaped}\\s/d", "/etc/fstab"])
        if rc != 0:
            return {"success": False, "error": err.strip()}
        return {"success": True, "message": f"Removed {mount} from fstab"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Usage History ────────────────────────────────────────────────────────────

def get_usage_history(days: int = 30) -> dict:
    """Get disk usage history. Returns current snapshot since no DB collection is running yet."""
    # Without a background collection job, return current usage as a single data point
    try:
        from datetime import datetime
        rc, out, err = _run(["df", "--output=source,used,pcent,target", "-B1"])
        if rc != 0:
            return {"success": True, "history": []}

        history = []
        now = datetime.now().isoformat()
        lines = out.strip().split("\n")
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[0].startswith("/dev/"):
                used_bytes = int(parts[1]) if parts[1].isdigit() else 0
                percent_str = parts[2].replace("%", "")
                percent = float(percent_str) if percent_str.replace(".", "").isdigit() else 0
                history.append({
                    "timestamp": now,
                    "device": parts[0],
                    "used_gb": round(used_bytes / (1024**3), 2),
                    "percent": percent,
                })
        return {"success": True, "history": history}
    except Exception as e:
        return {"success": True, "history": []}


# ─── Partition Management ─────────────────────────────────────────────────────

def create_partition(device: str, size: str, part_type: str = "primary") -> dict:
    """Create a partition on a disk."""
    err = _validate_device(device)
    if err:
        return {"success": False, "error": err}
    if not size:
        return {"success": False, "error": "size is required"}
    if part_type not in ("primary", "logical"):
        return {"success": False, "error": "part_type must be 'primary' or 'logical'"}

    rc, out, err_msg = _sudo_run(["parted", "-s", device, "mkpart", part_type, "0%", size])
    if rc != 0:
        return {"success": False, "error": f"Failed: {err_msg.strip()}"}
    return {"success": True, "partition": f"{device}1", "message": f"Partition created on {device}"}


def delete_partition(device: str) -> dict:
    """Delete a partition."""
    if not device:
        return {"success": False, "error": "device is required"}
    # Extract disk and partition number
    import re
    m = re.match(r"^(/dev/sd[a-z])(\d+)$", device)
    if not m:
        return {"success": False, "error": f"Invalid partition path: {device}"}
    disk = m.group(1)
    part_num = m.group(2)

    # Block system disk
    sys_disk = _get_system_disk()
    if disk == sys_disk:
        return {"success": False, "error": f"Cannot delete partition on system disk ({sys_disk})"}

    # Check not mounted
    rc, out, _ = _run(["findmnt", "-n", "-o", "TARGET", device])
    if rc == 0 and out.strip():
        return {"success": False, "error": f"Partition {device} is mounted at {out.strip()}. Unmount first."}

    rc, _, err_msg = _sudo_run(["parted", "-s", disk, "rm", part_num])
    if rc != 0:
        return {"success": False, "error": f"Failed: {err_msg.strip()}"}
    return {"success": True, "message": f"Partition {device} deleted"}

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


# ─── RAID Management ──────────────────────────────────────────────────────────

_ALLOWED_RAID_LEVELS = ("1", "5", "6", "10")


def get_raid_detail(array: str = "/dev/md0") -> dict:
    """Get detailed RAID array info via mdadm --detail.

    Returns:
        {
            "success": bool,
            "array": str,
            "level": str,
            "state": str,
            "devices": int,
            "active": int,
            "working": int,
            "failed": int,
            "spare": int,
            "disks": [{"device": str, "state": str, "role": int}],
            "raw": str
        }
    """
    if not array or not re.match(r"^/dev/md\d+$", array):
        return {"success": False, "error": f"Invalid array path: {array}"}

    rc, out, err = _sudo_run(["mdadm", "--detail", array])
    if rc != 0:
        if "No such file" in err or "does not appear" in err:
            return {"success": False, "error": f"Array {array} does not exist."}
        if rc == 127:
            return {"success": False, "error": "mdadm not installed. Install: sudo apt install mdadm"}
        return {"success": False, "error": err.strip()}

    # Parse output
    info = {"success": True, "array": array, "raw": out, "disks": []}

    for line in out.split("\n"):
        line = line.strip()
        if "Raid Level" in line:
            info["level"] = line.split(":")[-1].strip()
        elif "State :" in line or "State  :" in line:
            info["state"] = line.split(":")[-1].strip()
        elif "Raid Devices" in line:
            info["devices"] = int(line.split(":")[-1].strip())
        elif "Active Devices" in line:
            info["active"] = int(line.split(":")[-1].strip())
        elif "Working Devices" in line:
            info["working"] = int(line.split(":")[-1].strip())
        elif "Failed Devices" in line:
            info["failed"] = int(line.split(":")[-1].strip())
        elif "Spare Devices" in line:
            info["spare"] = int(line.split(":")[-1].strip())

    # Parse disk list (lines like: "0  8  16  0  active sync  /dev/sdb1")
    in_disk_section = False
    for line in out.split("\n"):
        if "Number" in line and "Major" in line and "Minor" in line:
            in_disk_section = True
            continue
        if in_disk_section and line.strip():
            parts = line.split()
            if len(parts) >= 7 and parts[-1].startswith("/dev/"):
                device = parts[-1]
                # State is everything between the number columns and device
                state_parts = parts[4:-1]
                state = " ".join(state_parts)
                info["disks"].append({"device": device, "state": state})

    return info


def create_raid(level: str, devices: list[str], array: str = "/dev/md0",
                filesystem: str = "ext4", mount_point: str = "") -> dict:
    """Create a new RAID array.

    Args:
        level: RAID level ("1", "5", "6", "10")
        devices: List of device paths (e.g. ["/dev/sdb1", "/dev/sdc1"])
        array: Array device path (default: /dev/md0)
        filesystem: Filesystem to format the array (ext4, xfs, btrfs)
        mount_point: Optional mount point (e.g. "/mnt/nas-data")

    Returns:
        {"success": bool, "message": str, "array": str}
    """
    # Validate level
    if level not in _ALLOWED_RAID_LEVELS:
        return {"success": False, "error": f"Unsupported RAID level: {level}. Supported: {', '.join(_ALLOWED_RAID_LEVELS)}"}

    # Validate device count
    min_devices = {"1": 2, "5": 3, "6": 4, "10": 4}
    if len(devices) < min_devices[level]:
        return {"success": False, "error": f"RAID {level} requires at least {min_devices[level]} devices, got {len(devices)}."}

    # Validate array path
    if not re.match(r"^/dev/md\d+$", array):
        return {"success": False, "error": f"Invalid array path: {array}"}

    # Check if array already exists
    rc, _, _ = _sudo_run(["mdadm", "--detail", array])
    if rc == 0:
        return {"success": False, "error": f"Array {array} already exists. Stop it first."}

    # Validate each device
    sys_disk = _get_system_disk()
    for dev in devices:
        if not re.match(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?)$", dev):
            return {"success": False, "error": f"Invalid device: {dev}"}
        # Block system disk
        if dev.startswith(sys_disk):
            return {"success": False, "error": f"Device {dev} is on the system disk. Blocked."}
        # Check not mounted
        rc, out, _ = _run(["findmnt", "-n", "-o", "TARGET", dev])
        if rc == 0 and out.strip():
            return {"success": False, "error": f"Device {dev} is mounted at {out.strip()}. Unmount first."}

    # Create the RAID array
    cmd = [
        "mdadm", "--create", array,
        "--level", level,
        "--raid-devices", str(len(devices)),
        "--metadata=1.2",
        "--run",
    ] + devices

    rc, out, err = _sudo_run(cmd, timeout=120)
    if rc != 0:
        return {"success": False, "error": f"mdadm --create failed: {err.strip()}"}

    result = {"success": True, "message": f"RAID {level} array {array} created with {len(devices)} devices.", "array": array}

    # Format if requested
    if filesystem and filesystem in _SUPPORTED_FS:
        fmt_cmd = [f"mkfs.{filesystem}"]
        if filesystem in ("ext4", "xfs", "btrfs"):
            fmt_cmd.append("-f" if filesystem in ("xfs", "btrfs") else "-F")
        fmt_cmd.append(array)
        rc2, _, err2 = _sudo_run(fmt_cmd, timeout=300)
        if rc2 != 0:
            result["warning"] = f"Array created but format failed: {err2.strip()}"
        else:
            result["message"] += f" Formatted as {filesystem}."

    # Mount if requested
    if mount_point and filesystem:
        _sudo_run(["mkdir", "-p", mount_point])
        rc3, _, err3 = _sudo_run(["mount", array, mount_point])
        if rc3 == 0:
            result["message"] += f" Mounted at {mount_point}."
            result["mount_point"] = mount_point
        else:
            result["warning"] = result.get("warning", "") + f" Mount failed: {err3.strip()}"

    # Save mdadm config
    _sudo_run(["bash", "-c", "mdadm --detail --scan >> /etc/mdadm/mdadm.conf"])
    _sudo_run(["update-initramfs", "-u"], timeout=120)

    return result


def add_raid_disk(array: str, device: str) -> dict:
    """Add a disk to an existing RAID array (for rebuilding or adding spare).

    Args:
        array: Array device (e.g. "/dev/md0")
        device: Device to add (e.g. "/dev/sdd1")
    """
    if not re.match(r"^/dev/md\d+$", array):
        return {"success": False, "error": f"Invalid array: {array}"}

    err = _validate_device(device)
    if err:
        return {"success": False, "error": err}

    # Check device not mounted
    rc, out, _ = _run(["findmnt", "-n", "-o", "TARGET", device])
    if rc == 0 and out.strip():
        return {"success": False, "error": f"Device {device} is mounted at {out.strip()}. Unmount first."}

    # Check array exists
    rc, _, err_msg = _sudo_run(["mdadm", "--detail", array])
    if rc != 0:
        return {"success": False, "error": f"Array {array} does not exist."}

    # Add disk
    rc, out, err_msg = _sudo_run(["mdadm", "--add", array, device])
    if rc != 0:
        return {"success": False, "error": f"Failed to add {device}: {err_msg.strip()}"}

    return {"success": True, "message": f"Added {device} to {array}. Rebuild will start automatically."}


def remove_raid_disk(array: str, device: str) -> dict:
    """Remove (fail + remove) a disk from a RAID array.

    Args:
        array: Array device (e.g. "/dev/md0")
        device: Device to remove (e.g. "/dev/sdb1")
    """
    if not re.match(r"^/dev/md\d+$", array):
        return {"success": False, "error": f"Invalid array: {array}"}

    if not device or not re.match(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?)$", device):
        return {"success": False, "error": f"Invalid device: {device}"}

    # Mark as faulty first
    rc, _, err_msg = _sudo_run(["mdadm", "--fail", array, device])
    if rc != 0:
        return {"success": False, "error": f"Failed to mark {device} as faulty: {err_msg.strip()}"}

    # Remove
    rc, _, err_msg = _sudo_run(["mdadm", "--remove", array, device])
    if rc != 0:
        return {"success": False, "error": f"Failed to remove {device}: {err_msg.strip()}"}

    return {"success": True, "message": f"Removed {device} from {array}."}


def stop_raid(array: str) -> dict:
    """Stop (deactivate) a RAID array.

    Args:
        array: Array device (e.g. "/dev/md0")

    WARNING: This will make the array inaccessible until reassembled.
    """
    if not re.match(r"^/dev/md\d+$", array):
        return {"success": False, "error": f"Invalid array: {array}"}

    # Check if mounted, unmount first
    rc, out, _ = _run(["findmnt", "-n", "-o", "TARGET", array])
    if rc == 0 and out.strip():
        mount_target = out.strip()
        rc2, _, err2 = _sudo_run(["umount", mount_target])
        if rc2 != 0:
            return {"success": False, "error": f"Cannot unmount {mount_target}: {err2.strip()}"}

    rc, _, err_msg = _sudo_run(["mdadm", "--stop", array])
    if rc != 0:
        return {"success": False, "error": f"Failed to stop {array}: {err_msg.strip()}"}

    return {"success": True, "message": f"Array {array} stopped."}


def assemble_raid(array: str = "/dev/md0", devices: list[str] | None = None) -> dict:
    """Assemble (reactivate) an existing RAID array.

    Args:
        array: Array device (e.g. "/dev/md0")
        devices: Optional list of devices. If not provided, mdadm scans automatically.
    """
    if not re.match(r"^/dev/md\d+$", array):
        return {"success": False, "error": f"Invalid array: {array}"}

    cmd = ["mdadm", "--assemble", array]
    if devices:
        for dev in devices:
            if not re.match(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(p\d+)?)$", dev):
                return {"success": False, "error": f"Invalid device: {dev}"}
        cmd += devices
    else:
        cmd.append("--scan")

    rc, out, err_msg = _sudo_run(cmd)
    if rc != 0:
        return {"success": False, "error": f"Failed to assemble {array}: {err_msg.strip()}"}

    return {"success": True, "message": f"Array {array} assembled successfully."}

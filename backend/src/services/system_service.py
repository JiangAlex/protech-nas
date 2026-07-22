"""System service — collects system info via psutil."""

import platform
import time
import psutil


def get_system_info() -> dict:
    """Get system overview: CPU, RAM, disk, network, uptime."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    # Memory
    mem = psutil.virtual_memory()

    # Disk usage (root partition)
    disk = psutil.disk_usage("/")

    # Network I/O
    net = psutil.net_io_counters()

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else 0,
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
        },
        "uptime": f"{days}d {hours}h {minutes}m",
        "uptime_seconds": uptime_seconds,
    }


import subprocess
import json
import re


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def _sudo_run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a command with sudo and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# ─── System Logs ──────────────────────────────────────────────────────────────

def get_system_logs(unit: str = None, lines: int = 100, since: str = None) -> dict:
    """Read system logs via journalctl.

    Args:
        unit: Systemd unit to filter (e.g. "smbd", "docker"). None for all.
        lines: Number of lines to return (1-5000).
        since: Time filter (e.g. "1 hour ago", "2026-07-20"). None for no filter.

    Returns:
        {
            "success": bool,
            "logs": list[{"timestamp": str, "unit": str, "priority": str, "message": str}]
        }
    """
    # Validate lines
    lines = max(1, min(lines, 5000))

    cmd = ["journalctl", "--output=json", f"-n{lines}", "--no-pager"]

    if unit:
        # Validate unit name (prevent injection)
        if not re.match(r"^[a-zA-Z0-9\-_.@]+$", unit):
            return {"success": False, "error": f"Invalid unit name: {unit}"}
        cmd += ["-u", unit]

    if since:
        # Basic validation
        if not re.match(r"^[\d\-\s:a-zA-Z]+$", since):
            return {"success": False, "error": f"Invalid since format: {since}"}
        cmd += [f"--since={since}"]

    rc, out, err = _run(cmd, timeout=15)
    if rc != 0 and not out:
        return {"success": False, "error": err.strip() or "journalctl failed"}

    # Parse JSON lines
    log_entries = []
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            log_entries.append({
                "timestamp": entry.get("__REALTIME_TIMESTAMP", ""),
                "unit": entry.get("_SYSTEMD_UNIT", entry.get("SYSLOG_IDENTIFIER", "")),
                "priority": str(entry.get("PRIORITY", "")),
                "message": entry.get("MESSAGE", ""),
            })
        except json.JSONDecodeError:
            continue

    return {"success": True, "logs": log_entries}


# ─── Power Management ─────────────────────────────────────────────────────────

_ALLOWED_POWER_ACTIONS = ("shutdown", "reboot")


def power_action(action: str) -> dict:
    """Execute a power action (shutdown or reboot).

    Args:
        action: "shutdown" or "reboot".

    Returns:
        {"success": bool, "message": str}

    WARNING: This will immediately shut down or reboot the system.
    """
    if action not in _ALLOWED_POWER_ACTIONS:
        return {"success": False, "error": f"Invalid action: {action}. Allowed: {', '.join(_ALLOWED_POWER_ACTIONS)}"}

    if action == "shutdown":
        cmd = ["shutdown", "-h", "now"]
    else:
        cmd = ["reboot"]

    rc, _, err = _run(cmd, timeout=10)
    # Command may not return if system shuts down immediately
    if rc != 0 and rc != -1:
        return {"success": False, "error": err.strip() or f"{action} failed"}

    return {"success": True, "message": f"System {action} initiated"}


# ─── Temperature ──────────────────────────────────────────────────────────────

def get_temperatures() -> dict:
    """Get CPU and disk temperatures.

    Returns:
        {
            "success": bool,
            "cpu_temp_c": float | None,
            "disks": list[{"device": str, "temp_c": int}]
        }
    """
    cpu_temp = _get_cpu_temperature()
    disk_temps = _get_disk_temperatures()

    return {
        "success": True,
        "cpu_temp_c": cpu_temp,
        "disks": disk_temps,
    }


def _get_cpu_temperature() -> float | None:
    """Read CPU temperature from lm-sensors or thermal zone."""
    # Try sensors first
    rc, out, _ = _run(["sensors", "--json"])
    if rc == 0 and out.strip():
        try:
            data = json.loads(out)
            # Look for coretemp or k10temp
            for chip_name, chip_data in data.items():
                if not isinstance(chip_data, dict):
                    continue
                for key, value in chip_data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_val in value.items():
                            if "input" in sub_key and isinstance(sub_val, (int, float)):
                                return round(sub_val, 1)
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: read thermal zone
    try:
        temp_str = open("/sys/class/thermal/thermal_zone0/temp").read().strip()
        return round(int(temp_str) / 1000.0, 1)
    except (FileNotFoundError, ValueError):
        pass

    return None


def _get_disk_temperatures() -> list[dict]:
    """Read disk temperatures via smartctl."""
    disks = []

    # Get list of block devices
    rc, out, _ = _run(["lsblk", "-dn", "-o", "NAME,TYPE"])
    if rc != 0:
        return disks

    for line in out.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "disk":
            device = f"/dev/{parts[0]}"
            rc, smart_out, _ = _sudo_run(["smartctl", "-A", "--json=c", device])
            if rc in (0, 4):  # 4 = SMART ok but some attrs failing
                try:
                    data = json.loads(smart_out)
                    temp_obj = data.get("temperature", {})
                    if isinstance(temp_obj, dict) and "current" in temp_obj:
                        disks.append({"device": device, "temp_c": temp_obj["current"]})
                except (json.JSONDecodeError, KeyError):
                    continue

    return disks


# ─── Service Management ───────────────────────────────────────────────────────

def list_services() -> dict:
    """List systemd services and their status.

    Returns:
        {"success": bool, "services": list[{"name": str, "status": str, "enabled": bool, "description": str}]}
    """
    rc, out, err = _run(["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"])
    if rc != 0:
        return {"success": False, "error": err.strip() or "systemctl failed"}

    services = []
    for line in out.strip().split("\n"):
        parts = line.split(None, 4)
        if len(parts) >= 4:
            name = parts[0].replace(".service", "")
            status = parts[2]  # active/inactive/failed
            description = parts[4] if len(parts) > 4 else ""

            # Check if enabled
            r = subprocess.run(["systemctl", "is-enabled", parts[0]], capture_output=True, text=True)
            enabled = r.stdout.strip() == "enabled"

            services.append({
                "name": name,
                "status": status,
                "enabled": enabled,
                "description": description,
            })

    return {"success": True, "services": services}


def control_service(name: str, action: str) -> dict:
    """Start, stop, restart, enable or disable a systemd service.

    Args:
        name: Service name (without .service suffix).
        action: "start" | "stop" | "restart" | "enable" | "disable"
    """
    allowed_actions = ("start", "stop", "restart", "enable", "disable")
    if action not in allowed_actions:
        return {"success": False, "error": f"Invalid action: {action}. Allowed: {', '.join(allowed_actions)}"}

    if not re.match(r"^[a-zA-Z0-9\-_.@]+$", name):
        return {"success": False, "error": f"Invalid service name: {name}"}

    rc, _, err = _run(["systemctl", action, f"{name}.service"])
    if rc != 0:
        return {"success": False, "error": f"systemctl {action} {name} failed: {err.strip()}"}

    return {"success": True, "message": f"Service {name} {action}ed"}


# ─── System Settings ──────────────────────────────────────────────────────────

def update_system_settings(config: dict) -> dict:
    """Update system settings (hostname, timezone, NTP).

    Args:
        config: {"hostname": str, "timezone": str, "ntp_enabled": bool}
    """
    errors = []

    hostname = config.get("hostname")
    if hostname:
        if not re.match(r"^[a-zA-Z0-9\-]{1,63}$", hostname):
            return {"success": False, "error": f"Invalid hostname: {hostname}"}
        rc, _, err = _run(["hostnamectl", "set-hostname", hostname])
        if rc != 0:
            errors.append(f"hostname: {err.strip()}")

    timezone = config.get("timezone")
    if timezone:
        rc, _, err = _run(["timedatectl", "set-timezone", timezone])
        if rc != 0:
            errors.append(f"timezone: {err.strip()}")

    ntp_enabled = config.get("ntp_enabled")
    if ntp_enabled is not None:
        val = "true" if ntp_enabled else "false"
        rc, _, err = _run(["timedatectl", "set-ntp", val])
        if rc != 0:
            errors.append(f"ntp: {err.strip()}")

    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return {"success": True, "message": "System settings updated"}


# ─── Hardware Info ────────────────────────────────────────────────────────────

def get_hardware_info() -> dict:
    """Get detailed hardware information.

    Returns:
        {"success": bool, "cpu": dict, "memory": dict, "pci_devices": list}
    """
    # CPU
    cpu_info = {}
    rc, out, _ = _run(["lscpu"])
    if rc == 0:
        for line in out.split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if "Model name" in key:
                    cpu_info["model"] = val
                elif key == "CPU(s)":
                    cpu_info["cores"] = int(val) if val.isdigit() else val
                elif "Thread(s) per core" in key:
                    cpu_info["threads_per_core"] = int(val) if val.isdigit() else val

    # Memory
    memory_info = {}
    rc, out, _ = _run(["free", "-b", "--si"])
    if rc == 0:
        lines = out.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 2:
                memory_info["total_gb"] = round(int(parts[1]) / (1000 ** 3), 1)

    # PCI
    pci_devices = []
    rc, out, _ = _run(["lspci", "-m"])
    if rc == 0:
        for line in out.strip().split("\n")[:20]:  # Limit to 20
            pci_devices.append(line.strip())

    return {
        "success": True,
        "cpu": cpu_info,
        "memory": memory_info,
        "pci_devices": pci_devices,
    }


# ─── System Updates ───────────────────────────────────────────────────────────

def check_updates() -> dict:
    """Check for available system updates.

    Returns:
        {"success": bool, "upgradable_count": int, "packages": list[dict]}
    """
    # Run apt update first
    rc, _, err = _run(["apt-get", "update", "-qq"], timeout=60)
    if rc != 0:
        return {"success": False, "error": f"apt update failed: {err.strip()}"}

    # List upgradable
    rc, out, _ = _run(["apt", "list", "--upgradable"], timeout=30)
    packages = []
    for line in out.strip().split("\n"):
        if "/" in line and "upgradable" in line.lower():
            # Format: package/source version [upgradable from: old_version]
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0].split("/")[0]
                version = parts[1]
                old_version = ""
                if "from:" in line:
                    idx = line.index("from:")
                    old_version = line[idx + 5:].strip().rstrip("]")
                packages.append({"name": name, "available": version, "current": old_version})

    return {"success": True, "upgradable_count": len(packages), "packages": packages}


def apply_updates(packages: list = None) -> dict:
    """Apply system updates.

    Args:
        packages: List of package names to update. None = update all.

    Returns:
        {"success": bool, "updated_count": int, "message": str}
    """
    if packages:
        cmd = ["apt-get", "install", "--only-upgrade", "-y"] + packages
    else:
        cmd = ["apt-get", "upgrade", "-y"]

    rc, out, err = _run(cmd, timeout=600)  # 10 min timeout
    if rc != 0:
        return {"success": False, "error": f"apt upgrade failed: {err.strip()[:200]}"}

    # Count upgraded
    count = 0
    for line in out.split("\n"):
        if "upgraded" in line.lower() and "newly" in line.lower():
            parts = line.split()
            if parts and parts[0].isdigit():
                count = int(parts[0])
                break

    return {"success": True, "updated_count": count, "message": "System updated successfully"}


# ─── Cron Jobs ────────────────────────────────────────────────────────────────

def list_cron_jobs() -> dict:
    """List crontab entries for root.

    Returns:
        {"success": bool, "jobs": list[{"id": int, "schedule": str, "command": str}]}
    """
    rc, out, err = _run(["crontab", "-l"])
    if rc != 0:
        if "no crontab" in err.lower():
            return {"success": True, "jobs": []}
        return {"success": False, "error": err.strip()}

    jobs = []
    for i, line in enumerate(out.strip().split("\n")):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 5)
        if len(parts) >= 6:
            jobs.append({
                "id": i,
                "schedule": " ".join(parts[:5]),
                "command": parts[5],
            })

    return {"success": True, "jobs": jobs}


def add_cron_job(schedule: str, command: str) -> dict:
    """Add a cron job.

    Args:
        schedule: Cron expression (5 fields).
        command: Command to execute.

    Returns:
        {"success": bool, "message": str}
    """
    # Validate schedule
    parts = schedule.strip().split()
    if len(parts) != 5:
        return {"success": False, "error": f"Invalid cron schedule: {schedule}. Expected 5 fields."}

    if not command.strip():
        return {"success": False, "error": "command is required"}

    # Get existing crontab
    rc, existing, _ = _run(["crontab", "-l"])
    if rc != 0:
        existing = ""

    new_entry = f"{schedule} {command}\n"
    new_crontab = existing.rstrip("\n") + "\n" + new_entry

    # Write back
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
        f.write(new_crontab)
        tmp_path = f.name

    rc, _, err = _run(["crontab", tmp_path])
    _os.unlink(tmp_path) if _os.path.exists(tmp_path) else None

    if rc != 0:
        return {"success": False, "error": f"crontab failed: {err.strip()}"}
    return {"success": True, "message": "Cron job added"}


def remove_cron_job(job_id: int) -> dict:
    """Remove a cron job by line index.

    Args:
        job_id: Line index (from list_cron_jobs).

    Returns:
        {"success": bool, "message": str}
    """
    rc, out, _ = _run(["crontab", "-l"])
    if rc != 0:
        return {"success": False, "error": "No crontab found"}

    lines = out.strip().split("\n")
    if job_id < 0 or job_id >= len(lines):
        return {"success": False, "error": f"Invalid job_id: {job_id}"}

    lines.pop(job_id)
    new_crontab = "\n".join(lines) + "\n"

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
        f.write(new_crontab)
        tmp_path = f.name

    rc, _, err = _run(["crontab", tmp_path])
    _os.unlink(tmp_path) if _os.path.exists(tmp_path) else None

    if rc != 0:
        return {"success": False, "error": f"crontab failed: {err.strip()}"}
    return {"success": True, "message": "Cron job removed"}


# ─── Metrics History ──────────────────────────────────────────────────────────

import os as _os

METRICS_FILE = _os.path.join(_os.path.expanduser("~"), ".protech-nas/metrics.json")


def record_metrics() -> dict:
    """Record current system metrics (called periodically by scheduler).

    Returns:
        {"success": bool, "recorded_at": str}
    """
    _os.makedirs(_os.path.dirname(METRICS_FILE), exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
    }

    # Try to get temperature
    try:
        temp_str = open("/sys/class/thermal/thermal_zone0/temp").read().strip()
        entry["temperature"] = round(int(temp_str) / 1000.0, 1)
    except (FileNotFoundError, ValueError):
        entry["temperature"] = None

    # Load existing
    try:
        with open(METRICS_FILE) as f:
            metrics = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metrics = []

    metrics.append(entry)

    # Keep last 8640 entries (1 per 10s = 24h, or 1 per min = 6 days)
    metrics = metrics[-8640:]

    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f)

    return {"success": True, "recorded_at": entry["timestamp"]}


def get_metrics_history(hours: int = 24) -> dict:
    """Get historical metrics.

    Args:
        hours: Number of hours to look back (1-720).

    Returns:
        {"success": bool, "data": list[dict]}
    """
    hours = max(1, min(hours, 720))

    try:
        with open(METRICS_FILE) as f:
            metrics = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"success": True, "data": []}

    # Filter by time
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    filtered = [m for m in metrics if m.get("timestamp", "") >= cutoff]

    return {"success": True, "data": filtered}

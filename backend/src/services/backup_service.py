"""Backup service — manage backup tasks (rsync-based)."""

import subprocess
import json
import uuid
import os
import time
import fcntl
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

BACKUP_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".protech-nas/backup")
BACKUP_TASKS_FILE = os.path.join(BACKUP_CONFIG_DIR, "tasks.json")


def _ensure_config_dir():
    """Ensure the backup config directory exists."""
    os.makedirs(BACKUP_CONFIG_DIR, exist_ok=True)
    if not os.path.exists(BACKUP_TASKS_FILE):
        with open(BACKUP_TASKS_FILE, "w") as f:
            json.dump([], f)


def _load_tasks() -> list[dict]:
    """Load backup tasks from config file."""
    _ensure_config_dir()
    try:
        with open(BACKUP_TASKS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_tasks(tasks: list[dict]):
    """Save backup tasks to config file."""
    _ensure_config_dir()
    with open(BACKUP_TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2, default=str)


def _run(cmd: list[str], timeout: int = 3600) -> tuple[int, str, str]:
    """Run a command with extended timeout for backup operations."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


# ─── Backup Task CRUD ─────────────────────────────────────────────────────────

def list_backup_tasks() -> dict:
    """List all configured backup tasks.

    Returns:
        {
            "success": bool,
            "tasks": list[{
                "id": str,
                "name": str,
                "source": str,
                "destination": str,
                "schedule": str,       # cron expression
                "retention_days": int,
                "method": str,         # "rsync"
                "last_run": str | None,
                "last_status": str | None   # "success" / "failed" / None
            }]
        }
    """
    tasks = _load_tasks()
    return {"success": True, "tasks": tasks}


def create_backup_task(config: dict) -> dict:
    """Create a new backup task.

    Args:
        config: Task configuration:
            - name (str, required): Human-readable task name
            - source (str, required): Source directory path
            - destination (str, required): Destination directory path
            - schedule (str, optional): Cron expression (e.g. "0 2 * * *")
            - retention_days (int, optional): Days to keep backups (default 30)
            - method (str, optional): Backup method (default "rsync")

    Returns:
        {"success": bool, "task_id": str}
    """
    name = config.get("name", "").strip()
    source = config.get("source", "").strip()
    destination = config.get("destination", "").strip()
    schedule = config.get("schedule", "").strip()
    retention_days = config.get("retention_days", 30)
    method = config.get("method", "rsync")

    # Validation
    if not name:
        return {"success": False, "error": "name is required"}
    if not source:
        return {"success": False, "error": "source is required"}
    if not destination:
        return {"success": False, "error": "destination is required"}

    # Validate source exists
    if not os.path.isdir(source):
        return {"success": False, "error": f"Source directory does not exist: {source}"}

    # Validate method
    if method not in ("rsync",):
        return {"success": False, "error": f"Unsupported method: {method}. Currently supported: rsync"}

    # Validate schedule format (basic check)
    if schedule:
        parts = schedule.split()
        if len(parts) != 5:
            return {"success": False, "error": f"Invalid cron schedule: {schedule}. Expected 5 fields."}

    # Validate retention (0 = no auto-cleanup)
    if not isinstance(retention_days, int) or retention_days < 0:
        return {"success": False, "error": "retention_days must be 0 (no cleanup) or a positive integer"}

    # Create task
    task_id = str(uuid.uuid4())[:8]
    task = {
        "id": task_id,
        "name": name,
        "source": source,
        "destination": destination,
        "schedule": schedule,
        "retention_days": retention_days,
        "method": method,
        "last_run": None,
        "last_status": None,
        "created_at": datetime.now().isoformat(),
    }

    tasks = _load_tasks()
    tasks.append(task)
    _save_tasks(tasks)

    # Ensure destination directory exists
    os.makedirs(destination, exist_ok=True)

    return {"success": True, "task_id": task_id}


# ─── Backup Execution ─────────────────────────────────────────────────────────

def run_backup(task_id: str) -> dict:
    """Execute a backup task immediately.

    Args:
        task_id: The task ID to execute.

    Returns:
        {
            "success": bool,
            "duration_sec": float,
            "files_transferred": int,
            "size_mb": float
        }
    """
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    source = task["source"]
    destination = task["destination"]
    method = task.get("method", "rsync")

    # Verify source still exists
    if not os.path.isdir(source):
        _update_task_status(task_id, "failed")
        return {"success": False, "error": f"Source directory not found: {source}"}

    # Ensure destination exists
    os.makedirs(destination, exist_ok=True)

    # Lock to prevent concurrent execution of same task
    lock_file = os.path.join(BACKUP_CONFIG_DIR, f".lock-{task_id}")
    try:
        lock_fd = open(lock_file, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        return {"success": False, "error": f"Task {task_id} is already running"}

    start_time = time.time()

    try:
        if method == "rsync":
            result = _run_rsync(source, destination)
        else:
            result = {"success": False, "error": f"Unsupported method: {method}"}

        duration = round(time.time() - start_time, 1)

        if result["success"]:
            _update_task_status(task_id, "success")
            result["duration_sec"] = duration
            return result
        else:
            _update_task_status(task_id, "failed")
            result["duration_sec"] = duration
            return result
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        try:
            os.unlink(lock_file)
        except OSError:
            pass


def _run_rsync(source: str, destination: str) -> dict:
    """Execute rsync backup.

    Returns:
        {"success": bool, "files_transferred": int, "size_mb": float}
    """
    # Ensure source path ends with / for rsync content sync
    if not source.endswith("/"):
        source += "/"

    # Create timestamped subdirectory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest_dir = os.path.join(destination, timestamp)
    os.makedirs(dest_dir, exist_ok=True)

    # Find latest backup for --link-dest (incremental)
    link_dest_args = []
    existing = sorted(
        [d for d in os.listdir(destination) if os.path.isdir(os.path.join(destination, d)) and d != timestamp],
        reverse=True,
    )
    if existing:
        latest = os.path.join(destination, existing[0])
        link_dest_args = [f"--link-dest={latest}"]

    cmd = [
        "rsync", "-avz", "--delete",
        "--stats",
    ] + link_dest_args + [source, dest_dir]

    rc, out, err = _run(cmd, timeout=7200)  # 2 hour timeout

    if rc != 0 and rc != 24:  # 24 = some files vanished (non-fatal)
        return {"success": False, "error": f"rsync failed (exit {rc}): {err.strip()}", "files_transferred": 0, "size_mb": 0}

    # Parse rsync stats
    files_transferred = 0
    size_mb = 0.0

    for line in out.split("\n"):
        if "Number of regular files transferred:" in line:
            try:
                files_transferred = int(line.split(":")[1].strip().replace(",", ""))
            except (ValueError, IndexError):
                pass
        elif "Total transferred file size:" in line:
            try:
                size_str = line.split(":")[1].strip()
                # Parse bytes value
                bytes_val = int(size_str.split()[0].replace(",", ""))
                size_mb = round(bytes_val / (1024 * 1024), 1)
            except (ValueError, IndexError):
                pass

    return {"success": True, "files_transferred": files_transferred, "size_mb": size_mb}


def _update_task_status(task_id: str, status: str):
    """Update a task's last_run and last_status."""
    tasks = _load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["last_run"] = datetime.now().isoformat()
            task["last_status"] = status
            break
    _save_tasks(tasks)


def update_backup_task(task_id: str, config: dict) -> dict:
    """Update an existing backup task.

    Args:
        task_id: Task ID to update.
        config: Partial config to update (same keys as create).

    Returns:
        {"success": bool, "message": str}
    """
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    # Update allowed fields
    updatable = ("name", "source", "destination", "schedule", "retention_days", "method")
    for key in updatable:
        if key in config and config[key] is not None:
            task[key] = config[key]

    # Validate schedule if changed
    if config.get("schedule"):
        parts = config["schedule"].split()
        if len(parts) != 5:
            return {"success": False, "error": f"Invalid cron schedule: {config['schedule']}"}

    _save_tasks(tasks)
    return {"success": True, "message": f"Task {task_id} updated"}


def delete_backup_task(task_id: str) -> dict:
    """Delete a backup task (does not delete backup data).

    Args:
        task_id: Task ID to delete.

    Returns:
        {"success": bool, "message": str}
    """
    tasks = _load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]

    if len(tasks) == original_len:
        return {"success": False, "error": f"Task {task_id} not found"}

    _save_tasks(tasks)
    return {"success": True, "message": f"Task {task_id} deleted (backup data preserved)"}


def get_backup_history(task_id: str) -> dict:
    """Get execution history for a backup task.

    Args:
        task_id: Task ID.

    Returns:
        {"success": bool, "history": list[dict]}
    """
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    destination = task.get("destination", "")
    if not destination or not os.path.isdir(destination):
        return {"success": True, "history": []}

    # Each subdirectory in destination is a backup run (YYYY-MM-DD_HHMMSS)
    history = []
    try:
        for entry in sorted(os.listdir(destination), reverse=True)[:50]:
            full_path = os.path.join(destination, entry)
            if os.path.isdir(full_path):
                stat = os.stat(full_path)
                # Calculate size
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(full_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        try:
                            total_size += os.path.getsize(fp)
                        except OSError:
                            pass

                history.append({
                    "version": entry,
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_mb": round(total_size / (1024 * 1024), 1),
                })
    except OSError:
        pass

    return {"success": True, "history": history}


def restore_backup(task_id: str, version: str, target_path: str = None) -> dict:
    """Restore a specific backup version.

    Args:
        task_id: Task ID.
        version: Backup version (directory name, e.g. "2026-07-20_020000").
        target_path: Where to restore. If None, restores to original source.

    Returns:
        {"success": bool, "restored_to": str, "files_count": int}
    """
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    destination = task.get("destination", "")
    backup_dir = os.path.join(destination, version)

    if not os.path.isdir(backup_dir):
        return {"success": False, "error": f"Backup version not found: {version}"}

    restore_to = target_path or task.get("source", "")
    if not restore_to:
        return {"success": False, "error": "No target path specified"}

    os.makedirs(restore_to, exist_ok=True)

    # rsync from backup to target
    src = backup_dir.rstrip("/") + "/"
    cmd = ["rsync", "-avz", "--delete", src, restore_to]
    rc, out, err = _run(cmd, timeout=7200)

    if rc != 0:
        return {"success": False, "error": f"Restore failed: {err.strip()}"}

    # Count files
    files_count = 0
    for line in out.split("\n"):
        if "Number of regular files transferred:" in line:
            try:
                files_count = int(line.split(":")[1].strip().replace(",", ""))
            except (ValueError, IndexError):
                pass

    return {"success": True, "restored_to": restore_to, "files_count": files_count}


def schedule_backup(task_id: str, cron_expr: str) -> dict:
    """Update the schedule for a backup task.

    Args:
        task_id: Task ID.
        cron_expr: Cron expression (e.g. "0 2 * * *"). Empty string to disable.

    Returns:
        {"success": bool, "next_run": str}
    """
    if cron_expr:
        parts = cron_expr.split()
        if len(parts) != 5:
            return {"success": False, "error": f"Invalid cron expression: {cron_expr}. Expected 5 fields."}

    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return {"success": False, "error": f"Task {task_id} not found"}

    task["schedule"] = cron_expr
    _save_tasks(tasks)

    # Calculate next run (simplified)
    if cron_expr:
        next_run = "See system cron for exact next run time"
    else:
        next_run = "Manual only (no schedule)"

    return {"success": True, "next_run": next_run}


# ─── Btrfs Snapshots ──────────────────────────────────────────────────────────

def list_snapshots() -> dict:
    """List Btrfs snapshots.

    Returns:
        {"success": bool, "snapshots": list[{"path": str, "created": str}]}
    """
    rc, out, err = _run(["btrfs", "subvolume", "list", "-s", "/"], timeout=10)
    if rc == 127:
        return {"success": False, "error": "btrfs-progs not installed"}
    if rc != 0:
        # May not be a Btrfs filesystem
        return {"success": True, "snapshots": [], "note": "No Btrfs snapshots found or not a Btrfs filesystem"}

    snapshots = []
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        # Format: ID <id> gen <gen> cgen <cgen> top level <tl> otime <time> path <path>
        parts = line.split()
        path = ""
        otime = ""
        for i, p in enumerate(parts):
            if p == "path" and i + 1 < len(parts):
                path = parts[i + 1]
            if p == "otime" and i + 1 < len(parts):
                otime = parts[i + 1]
        if path:
            snapshots.append({"path": path, "created": otime})

    return {"success": True, "snapshots": snapshots}


def create_snapshot(subvol: str, dest: str = None) -> dict:
    """Create a Btrfs readonly snapshot.

    Args:
        subvol: Source subvolume path.
        dest: Destination path (auto-generated if None).

    Returns:
        {"success": bool, "snapshot_path": str}
    """
    if not subvol or not os.path.exists(subvol):
        return {"success": False, "error": f"Subvolume not found: {subvol}"}

    if not dest:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dest = f"{subvol}/.snapshots/{timestamp}"

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    rc, out, err = _run(["btrfs", "subvolume", "snapshot", "-r", subvol, dest])
    if rc == 127:
        return {"success": False, "error": "btrfs-progs not installed"}
    if rc != 0:
        return {"success": False, "error": f"Snapshot failed: {err.strip()}"}

    return {"success": True, "snapshot_path": dest}


def delete_snapshot(path: str) -> dict:
    """Delete a Btrfs snapshot.

    Args:
        path: Snapshot path to delete.

    Returns:
        {"success": bool, "message": str}
    """
    if not path:
        return {"success": False, "error": "path is required"}

    rc, _, err = _run(["btrfs", "subvolume", "delete", path])
    if rc == 127:
        return {"success": False, "error": "btrfs-progs not installed"}
    if rc != 0:
        return {"success": False, "error": f"Delete failed: {err.strip()}"}

    return {"success": True, "message": f"Snapshot deleted: {path}"}

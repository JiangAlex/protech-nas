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
    Path(path).mkdir(parents=True, exist_ok=True)

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

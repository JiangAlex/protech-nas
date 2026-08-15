"""Versioning service — file version control operations.

This module provides snapshot-based versioning for files stored on ProTech NAS.
Versions are stored as copies in a dedicated versioning directory.
"""

import os
import shutil
import uuid
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Configuration ────────────────────────────────────────────────────────────

# Version storage root — outside normal file operations to prevent accidental deletion
VERSION_ROOT = os.path.join(os.path.expanduser("~"), ".protech-nas/versions")

# Maximum versions to keep per file (oldest are pruned)
MAX_VERSIONS_PER_FILE = 50

# Metadata file for each versioned file
METADATA_DIR = os.path.join(os.path.expanduser("~"), ".protech-nas/version_metadata")


# ─── Security Helpers ─────────────────────────────────────────────────────────

def _is_safe_path(path: str) -> bool:
    """Check if path is within allowed roots (prevents path traversal)."""
    from .file_service import _is_safe_path as file_is_safe
    return file_is_safe(path)


def _get_version_path(original_path: str) -> str:
    """Generate a unique directory path for this file's versions.

    Uses a hash of the original path to avoid path length issues and
    provide some privacy (original paths are not directly visible).
    """
    path_hash = hashlib.sha256(original_path.encode()).hexdigest()[:16]
    return os.path.join(VERSION_ROOT, path_hash)


def _ensure_dirs():
    """Ensure version and metadata directories exist."""
    os.makedirs(VERSION_ROOT, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)


# ─── Version Metadata ─────────────────────────────────────────────────────────

class VersionMetadata:
    """Handle version metadata storage in JSON."""

    def __init__(self, original_path: str):
        self.original_path = original_path
        path_hash = hashlib.sha256(original_path.encode()).hexdigest()[:16]
        self.metadata_file = os.path.join(METADATA_DIR, f"{path_hash}.json")
        self.versions = []
        self._load()

    def _load(self):
        """Load metadata from disk."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    self.versions = data.get("versions", [])
            except (json.JSONDecodeError, OSError):
                self.versions = []

    def _save(self):
        """Save metadata to disk."""
        _ensure_dirs()
        with open(self.metadata_file, "w") as f:
            json.dump({"original_path": self.original_path, "versions": self.versions}, f, indent=2)

    def add_version(self, version_id: str, version_path: str, size: int, checksum: str, comment: str = ""):
        """Add a new version entry."""
        self.versions.append({
            "version_id": version_id,
            "version_path": version_path,
            "size": size,
            "checksum": checksum,
            "comment": comment,
            "created_at": datetime.now().isoformat(),
        })
        self._save()

    def remove_version(self, version_id: str) -> Optional[dict]:
        """Remove a version entry by ID."""
        for i, v in enumerate(self.versions):
            if v["version_id"] == version_id:
                removed = self.versions.pop(i)
                self._save()
                return removed
        return None

    def get_version(self, version_id: str) -> Optional[dict]:
        """Get a specific version by ID."""
        for v in self.versions:
            if v["version_id"] == version_id:
                return v
        return None

    def prune_old_versions(self, keep: int = MAX_VERSIONS_PER_FILE):
        """Remove oldest versions beyond the keep limit."""
        while len(self.versions) > keep:
            oldest = self.versions.pop(0)
            # Delete the stored version file
            if os.path.exists(oldest["version_path"]):
                try:
                    os.unlink(oldest["version_path"])
                except OSError:
                    pass
            self._save()


# ─── Core Versioning Operations ───────────────────────────────────────────────

def _compute_checksum(file_path: str) -> str:
    """Compute SHA256 checksum of a file."""
    sha = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except OSError:
        return ""


def create_snapshot(original_path: str, comment: str = "") -> dict:
    """Create a new version snapshot of a file.

    Args:
        original_path: Path to the file to snapshot.
        comment: Optional comment describing this version.

    Returns:
        {
            "success": bool,
            "version_id": str,
            "version_path": str,
            "size": int,
            "checksum": str,
            "created_at": str
        }
    """
    if not original_path:
        return {"success": False, "error": "original_path is required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path} is outside allowed directories"}

    real_path = os.path.realpath(original_path)

    if not os.path.exists(real_path):
        return {"success": False, "error": f"File not found: {original_path}"}

    if os.path.isdir(real_path):
        return {"success": False, "error": "Directories are not supported for versioning"}

    # Generate version ID and paths
    version_id = str(uuid.uuid4())[:8]
    version_base = _get_version_path(original_path)
    version_dir = os.path.join(version_base, version_id)

    try:
        _ensure_dirs()
        os.makedirs(version_dir, exist_ok=True)

        # Copy the file to version storage
        filename = os.path.basename(real_path)
        version_path = os.path.join(version_dir, filename)
        shutil.copy2(real_path, version_path)

        # Get file size and checksum
        size = os.path.getsize(version_path)
        checksum = _compute_checksum(version_path)

        # Store metadata
        metadata = VersionMetadata(original_path)
        metadata.add_version(version_id, version_path, size, checksum, comment)
        metadata.prune_old_versions()

        return {
            "success": True,
            "version_id": version_id,
            "version_path": version_path,
            "size": size,
            "checksum": checksum,
            "created_at": datetime.now().isoformat(),
        }
    except PermissionError:
        return {"success": False, "error": "Permission denied"}
    except OSError as e:
        return {"success": False, "error": str(e)}


def list_versions(original_path: str) -> dict:
    """List all versions of a file.

    Args:
        original_path: Path to the original file.

    Returns:
        {
            "success": bool,
            "original_path": str,
            "versions": [
                {
                    "version_id": str,
                    "size": int,
                    "checksum": str,
                    "comment": str,
                    "created_at": str
                }
            ],
            "total": int
        }
    """
    if not original_path:
        return {"success": False, "error": "original_path is required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path}"}

    metadata = VersionMetadata(original_path)

    # Return version summaries (without the full path for security)
    version_summaries = []
    for v in metadata.versions:
        version_summaries.append({
            "version_id": v["version_id"],
            "size": v["size"],
            "checksum": v["checksum"],
            "comment": v.get("comment", ""),
            "created_at": v["created_at"],
        })

    return {
        "success": True,
        "original_path": original_path,
        "versions": version_summaries,
        "total": len(version_summaries),
    }


def get_version(original_path: str, version_id: str) -> dict:
    """Get details about a specific version.

    Args:
        original_path: Path to the original file.
        version_id: ID of the version to retrieve.

    Returns:
        {
            "success": bool,
            "version": dict with version details,
            "can_restore": bool
        }
    """
    if not original_path or not version_id:
        return {"success": False, "error": "original_path and version_id are required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path}"}

    metadata = VersionMetadata(original_path)
    version = metadata.get_version(version_id)

    if not version:
        return {"success": False, "error": f"Version not found: {version_id}"}

    return {
        "success": True,
        "version": version,
        "can_restore": os.path.exists(version["version_path"]),
    }


def restore_version(original_path: str, version_id: str) -> dict:
    """Restore a file to a specific version.

    This creates a backup of the current file before restoring,
    in case you need to undo the restore.

    Args:
        original_path: Path to the original file.
        version_id: ID of the version to restore.

    Returns:
        {
            "success": bool,
            "restored_to": str,
            "backup_path": str or None,
            "message": str
        }
    """
    if not original_path or not version_id:
        return {"success": False, "error": "original_path and version_id are required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path}"}

    real_path = os.path.realpath(original_path)

    if not os.path.exists(real_path):
        return {"success": False, "error": f"Original file not found: {original_path}"}

    metadata = VersionMetadata(original_path)
    version = metadata.get_version(version_id)

    if not version:
        return {"success": False, "error": f"Version not found: {version_id}"}

    if not os.path.exists(version["version_path"]):
        return {"success": False, "error": "Version file is missing from storage"}

    try:
        # Create a backup of current file first
        backup_path = None
        if os.path.exists(real_path):
            backup_dir = os.path.join(os.path.dirname(real_path), ".version_backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_filename = f".{os.path.basename(real_path)}.backup_{version_id}"
            backup_path = os.path.join(backup_dir, backup_filename)
            shutil.copy2(real_path, backup_path)

        # Restore the version
        shutil.copy2(version["version_path"], real_path)

        return {
            "success": True,
            "restored_to": real_path,
            "backup_path": backup_path,
            "message": f"Restored to version {version_id}",
        }
    except PermissionError:
        return {"success": False, "error": "Permission denied"}
    except OSError as e:
        return {"success": False, "error": str(e)}


def delete_version(original_path: str, version_id: str) -> dict:
    """Delete a specific version.

    Args:
        original_path: Path to the original file.
        version_id: ID of the version to delete.

    Returns:
        {"success": bool, "message": str}
    """
    if not original_path or not version_id:
        return {"success": False, "error": "original_path and version_id are required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path}"}

    metadata = VersionMetadata(original_path)
    removed = metadata.remove_version(version_id)

    if not removed:
        return {"success": False, "error": f"Version not found: {version_id}"}

    return {
        "success": True,
        "message": f"Deleted version {version_id}",
    }


def get_version_file(original_path: str, version_id: str) -> dict:
    """Get the versioned file for download.

    Args:
        original_path: Path to the original file.
        version_id: ID of the version to retrieve.

    Returns:
        {
            "success": bool,
            "version_path": str,
            "filename": str,
            "size": int
        }
    """
    if not original_path or not version_id:
        return {"success": False, "error": "original_path and version_id are required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path}"}

    metadata = VersionMetadata(original_path)
    version = metadata.get_version(version_id)

    if not version:
        return {"success": False, "error": f"Version not found: {version_id}"}

    if not os.path.exists(version["version_path"]):
        return {"success": False, "error": "Version file is missing from storage"}

    return {
        "success": True,
        "version_path": version["version_path"],
        "filename": os.path.basename(version["version_path"]),
        "size": version["size"],
    }


def compare_versions(original_path: str, version_id_a: str, version_id_b: str) -> dict:
    """Compare two versions of a file.

    Args:
        original_path: Path to the original file.
        version_id_a: First version ID.
        version_id_b: Second version ID.

    Returns:
        {
            "success": bool,
            "version_a": dict,
            "version_b": dict,
            "same_content": bool,
            "size_diff": int
        }
    """
    if not original_path or not version_id_a or not version_id_b:
        return {"success": False, "error": "original_path, version_id_a, and version_id_b are required"}

    if not _is_safe_path(original_path):
        return {"success": False, "error": f"Access denied: {original_path}"}

    metadata = VersionMetadata(original_path)
    version_a = metadata.get_version(version_id_a)
    version_b = metadata.get_version(version_id_b)

    if not version_a:
        return {"success": False, "error": f"Version not found: {version_id_a}"}
    if not version_b:
        return {"success": False, "error": f"Version not found: {version_id_b}"}

    return {
        "success": True,
        "version_a": version_a,
        "version_b": version_b,
        "same_content": version_a["checksum"] == version_b["checksum"],
        "size_diff": version_a["size"] - version_b["size"],
    }

"""File service — file manager operations (browse, upload, download, mkdir, delete)."""

import os
import mimetypes
import shutil
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

# Allowed root directories — all file operations must stay within these
ALLOWED_ROOTS = ["/data", "/home", "/srv", "/mnt", "/media"]

# Maximum upload file size (2 GB)
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024


# ─── Security Helpers ─────────────────────────────────────────────────────────

def _is_safe_path(path: str) -> bool:
    """Check if path is within allowed roots (prevents path traversal)."""
    try:
        real = os.path.realpath(path)
    except (OSError, ValueError):
        return False
    return any(real.startswith(root) for root in ALLOWED_ROOTS)


def _sanitize_filename(name: str) -> str:
    """Remove dangerous characters from filename."""
    # Remove null bytes and path separators
    name = name.replace("\x00", "").replace("/", "_").replace("\\", "_")
    # Remove leading dots (hidden files attack)
    name = name.lstrip(".")
    # Limit length
    if len(name) > 255:
        name = name[:255]
    return name or "unnamed"


# ─── File Operations ──────────────────────────────────────────────────────────

def list_directory(path: str) -> dict:
    """List files and directories in the given path.

    Args:
        path: Directory path to list.

    Returns:
        {
            "success": bool,
            "path": str,
            "items": list[{
                "name": str,
                "type": "file" | "dir",
                "size": int,
                "modified": str (ISO),
                "permissions": str
            }]
        }
    """
    if not path:
        return {"success": False, "error": "path is required"}

    if not _is_safe_path(path):
        return {"success": False, "error": f"Access denied: {path} is outside allowed directories"}

    real_path = os.path.realpath(path)

    if not os.path.exists(real_path):
        return {"success": False, "error": f"Path does not exist: {path}"}

    if not os.path.isdir(real_path):
        return {"success": False, "error": f"Not a directory: {path}"}

    items = []
    try:
        with os.scandir(real_path) as entries:
            for entry in entries:
                try:
                    stat = entry.stat(follow_symlinks=False)
                    items.append({
                        "name": entry.name,
                        "type": "dir" if entry.is_dir(follow_symlinks=False) else "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:],
                    })
                except (OSError, PermissionError):
                    # Skip files we can't stat
                    continue
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {path}"}

    # Sort: directories first, then by name
    items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))

    return {"success": True, "path": real_path, "items": items}


def save_upload(filename: str, content: bytes, dest: str) -> dict:
    """Save uploaded file content to destination directory.

    Args:
        filename: Original filename (will be sanitized).
        content: File bytes.
        dest: Destination directory path.

    Returns:
        {"success": bool, "path": str, "size": int}
    """
    if not dest:
        return {"success": False, "error": "dest is required"}

    if not _is_safe_path(dest):
        return {"success": False, "error": f"Access denied: {dest} is outside allowed directories"}

    real_dest = os.path.realpath(dest)

    if not os.path.isdir(real_dest):
        return {"success": False, "error": f"Destination is not a directory: {dest}"}

    # Check file size
    if len(content) > MAX_UPLOAD_SIZE:
        return {"success": False, "error": f"File too large. Maximum: {MAX_UPLOAD_SIZE // (1024*1024)} MB"}

    # Sanitize filename
    safe_name = _sanitize_filename(filename)

    # Handle filename conflicts — add numeric suffix
    target = os.path.join(real_dest, safe_name)
    if os.path.exists(target):
        base, ext = os.path.splitext(safe_name)
        counter = 1
        while os.path.exists(target):
            target = os.path.join(real_dest, f"{base}_{counter}{ext}")
            counter += 1

    try:
        with open(target, "wb") as f:
            f.write(content)
        return {"success": True, "path": target, "size": len(content)}
    except OSError as e:
        return {"success": False, "error": str(e)}


def get_download_path(path: str) -> dict:
    """Validate and return the absolute path for downloading a file.

    Args:
        path: File path to download.

    Returns:
        {"success": bool, "absolute_path": str, "filename": str, "size": int}
    """
    if not path:
        return {"success": False, "error": "path is required"}

    if not _is_safe_path(path):
        return {"success": False, "error": f"Access denied: {path} is outside allowed directories"}

    real_path = os.path.realpath(path)

    if not os.path.exists(real_path):
        return {"success": False, "error": f"File not found: {path}"}

    if os.path.isdir(real_path):
        return {"success": False, "error": "Cannot download a directory. Use compress first."}

    try:
        size = os.path.getsize(real_path)
    except OSError:
        size = 0

    return {
        "success": True,
        "absolute_path": real_path,
        "filename": os.path.basename(real_path),
        "size": size,
    }


def make_directory(path: str) -> dict:
    """Create a new directory.

    Args:
        path: Full path of the directory to create.

    Returns:
        {"success": bool, "path": str}
    """
    if not path:
        return {"success": False, "error": "path is required"}

    if not _is_safe_path(path):
        return {"success": False, "error": f"Access denied: {path} is outside allowed directories"}

    real_path = os.path.realpath(path)

    if os.path.exists(real_path):
        return {"success": False, "error": f"Already exists: {path}"}

    # Check parent directory exists and is writable
    parent = os.path.dirname(real_path)
    if not os.path.isdir(parent):
        return {"success": False, "error": f"Parent directory does not exist: {parent}"}

    try:
        os.makedirs(real_path, exist_ok=False)
        return {"success": True, "path": real_path}
    except PermissionError:
        return {"success": False, "error": f"Permission denied: cannot create {path}"}
    except OSError as e:
        return {"success": False, "error": str(e)}


def delete_item(path: str) -> dict:
    """Delete a file or directory.

    Args:
        path: Path to delete.

    Returns:
        {"success": bool, "message": str}

    WARNING: This is irreversible unless a recycle bin is implemented.
    """
    if not path:
        return {"success": False, "error": "path is required"}

    if not _is_safe_path(path):
        return {"success": False, "error": f"Access denied: {path} is outside allowed directories"}

    real_path = os.path.realpath(path)

    # Extra safety: prevent deleting root of allowed directories
    if real_path in ALLOWED_ROOTS:
        return {"success": False, "error": "Cannot delete a root directory"}

    if not os.path.exists(real_path):
        return {"success": False, "error": f"Path not found: {path}"}

    try:
        if os.path.isdir(real_path):
            shutil.rmtree(real_path)
        else:
            os.unlink(real_path)
        return {"success": True, "message": f"Deleted: {real_path}"}
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {path}"}
    except OSError as e:
        return {"success": False, "error": str(e)}


def move_item(src: str, dst: str) -> dict:
    """Move or rename a file/directory.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        {"success": bool, "new_path": str}
    """
    if not src or not dst:
        return {"success": False, "error": "src and dst are required"}

    if not _is_safe_path(src):
        return {"success": False, "error": f"Access denied: {src}"}
    if not _is_safe_path(dst):
        return {"success": False, "error": f"Access denied: {dst}"}

    real_src = os.path.realpath(src)
    real_dst = os.path.realpath(dst)

    if not os.path.exists(real_src):
        return {"success": False, "error": f"Source not found: {src}"}

    if os.path.exists(real_dst):
        return {"success": False, "error": f"Destination already exists: {dst}"}

    # Prevent moving parent into child
    if real_dst.startswith(real_src + os.sep):
        return {"success": False, "error": "Cannot move a directory into itself"}

    try:
        shutil.move(real_src, real_dst)
        return {"success": True, "new_path": real_dst}
    except PermissionError:
        return {"success": False, "error": f"Permission denied"}
    except OSError as e:
        return {"success": False, "error": str(e)}


def copy_item(src: str, dst: str) -> dict:
    """Copy a file or directory.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        {"success": bool, "new_path": str}
    """
    if not src or not dst:
        return {"success": False, "error": "src and dst are required"}

    if not _is_safe_path(src):
        return {"success": False, "error": f"Access denied: {src}"}
    if not _is_safe_path(dst):
        return {"success": False, "error": f"Access denied: {dst}"}

    real_src = os.path.realpath(src)
    real_dst = os.path.realpath(dst)

    if not os.path.exists(real_src):
        return {"success": False, "error": f"Source not found: {src}"}

    if os.path.exists(real_dst):
        return {"success": False, "error": f"Destination already exists: {dst}"}

    try:
        if os.path.isdir(real_src):
            shutil.copytree(real_src, real_dst)
        else:
            # Ensure parent dir exists
            os.makedirs(os.path.dirname(real_dst), exist_ok=True)
            shutil.copy2(real_src, real_dst)
        return {"success": True, "new_path": real_dst}
    except PermissionError:
        return {"success": False, "error": "Permission denied"}
    except OSError as e:
        return {"success": False, "error": str(e)}


def get_file_info(path: str) -> dict:
    """Get detailed file/directory information.

    Args:
        path: File or directory path.

    Returns:
        {
            "success": bool,
            "name": str,
            "type": "file" | "dir",
            "size": int,
            "mime": str | None,
            "created": str,
            "modified": str,
            "permissions": str,
            "owner": str
        }
    """
    if not path:
        return {"success": False, "error": "path is required"}

    if not _is_safe_path(path):
        return {"success": False, "error": f"Access denied: {path}"}

    real_path = os.path.realpath(path)

    if not os.path.exists(real_path):
        return {"success": False, "error": f"Path not found: {path}"}

    try:
        stat = os.stat(real_path)
        is_dir = os.path.isdir(real_path)

        # Get MIME type
        mime = None
        if not is_dir:
            mime, _ = mimetypes.guess_type(real_path)

        # Get owner name
        import pwd
        try:
            owner = pwd.getpwuid(stat.st_uid).pw_name
        except KeyError:
            owner = str(stat.st_uid)

        return {
            "success": True,
            "name": os.path.basename(real_path),
            "type": "dir" if is_dir else "file",
            "size": stat.st_size,
            "mime": mime,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-4:],
            "owner": owner,
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {path}"}
    except OSError as e:
        return {"success": False, "error": str(e)}


import zipfile
import tarfile
import uuid
import json


# ─── Compression ──────────────────────────────────────────────────────────────

SHARE_LINKS_FILE = "/etc/protech-nas/share_links.json"


def compress(paths: list, format: str, dest: str) -> dict:
    """Compress files/directories into an archive.

    Args:
        paths: List of file/directory paths to compress.
        format: "zip" or "tar.gz".
        dest: Output archive path.

    Returns:
        {"success": bool, "archive_path": str, "size": int}
    """
    if not paths:
        return {"success": False, "error": "paths is required"}
    if format not in ("zip", "tar.gz"):
        return {"success": False, "error": f"Unsupported format: {format}. Use 'zip' or 'tar.gz'"}
    if not dest:
        return {"success": False, "error": "dest is required"}

    if not _is_safe_path(dest):
        return {"success": False, "error": f"Access denied: {dest}"}

    # Validate all paths
    for p in paths:
        if not _is_safe_path(p):
            return {"success": False, "error": f"Access denied: {p}"}
        if not os.path.exists(p):
            return {"success": False, "error": f"Path not found: {p}"}

    try:
        if format == "zip":
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in paths:
                    real_p = os.path.realpath(p)
                    if os.path.isfile(real_p):
                        zf.write(real_p, os.path.basename(real_p))
                    elif os.path.isdir(real_p):
                        for root, dirs, files in os.walk(real_p):
                            for f in files:
                                full = os.path.join(root, f)
                                arcname = os.path.relpath(full, os.path.dirname(real_p))
                                zf.write(full, arcname)
        elif format == "tar.gz":
            with tarfile.open(dest, "w:gz") as tf:
                for p in paths:
                    real_p = os.path.realpath(p)
                    tf.add(real_p, arcname=os.path.basename(real_p))

        size = os.path.getsize(dest)
        return {"success": True, "archive_path": dest, "size": size}
    except OSError as e:
        return {"success": False, "error": str(e)}


def extract(archive: str, dest: str) -> dict:
    """Extract an archive to a destination directory.

    Args:
        archive: Archive file path (.zip or .tar.gz).
        dest: Destination directory.

    Returns:
        {"success": bool, "extracted_path": str, "file_count": int}
    """
    if not archive or not dest:
        return {"success": False, "error": "archive and dest are required"}

    if not _is_safe_path(archive):
        return {"success": False, "error": f"Access denied: {archive}"}
    if not _is_safe_path(dest):
        return {"success": False, "error": f"Access denied: {dest}"}

    if not os.path.exists(archive):
        return {"success": False, "error": f"Archive not found: {archive}"}

    os.makedirs(dest, exist_ok=True)
    file_count = 0

    try:
        if archive.endswith(".zip"):
            with zipfile.ZipFile(archive, "r") as zf:
                # Zip Slip protection
                for member in zf.namelist():
                    member_path = os.path.realpath(os.path.join(dest, member))
                    if not member_path.startswith(os.path.realpath(dest)):
                        return {"success": False, "error": f"Zip Slip detected: {member}"}
                zf.extractall(dest)
                file_count = len(zf.namelist())
        elif archive.endswith(".tar.gz") or archive.endswith(".tgz"):
            with tarfile.open(archive, "r:gz") as tf:
                # Tar Slip protection
                for member in tf.getmembers():
                    member_path = os.path.realpath(os.path.join(dest, member.name))
                    if not member_path.startswith(os.path.realpath(dest)):
                        return {"success": False, "error": f"Path traversal detected: {member.name}"}
                tf.extractall(dest)
                file_count = len(tf.getmembers())
        else:
            return {"success": False, "error": "Unsupported archive format. Use .zip or .tar.gz"}

        return {"success": True, "extracted_path": dest, "file_count": file_count}
    except (zipfile.BadZipFile, tarfile.TarError) as e:
        return {"success": False, "error": f"Archive is corrupted: {str(e)}"}
    except OSError as e:
        return {"success": False, "error": str(e)}


# ─── Share Links ──────────────────────────────────────────────────────────────

def _load_share_links() -> list:
    try:
        with open(SHARE_LINKS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_share_links(links: list):
    os.makedirs(os.path.dirname(SHARE_LINKS_FILE), exist_ok=True)
    with open(SHARE_LINKS_FILE, "w") as f:
        json.dump(links, f, indent=2, default=str)


def create_share_link(path: str, expires_hours: int = 72, password: str = None) -> dict:
    """Create a public share link for a file.

    Args:
        path: File path to share.
        expires_hours: Hours until link expires.
        password: Optional password protection.

    Returns:
        {"success": bool, "link_id": str, "url": str, "expires_at": str}
    """
    if not path:
        return {"success": False, "error": "path is required"}
    if not _is_safe_path(path):
        return {"success": False, "error": f"Access denied: {path}"}
    if not os.path.exists(path):
        return {"success": False, "error": f"File not found: {path}"}
    if expires_hours < 1 or expires_hours > 720:
        return {"success": False, "error": "expires_hours must be between 1 and 720"}

    link_id = str(uuid.uuid4())[:12]
    expires_at = datetime.now().timestamp() + (expires_hours * 3600)

    link = {
        "id": link_id,
        "path": os.path.realpath(path),
        "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
        "password_hash": None,
        "created_at": datetime.now().isoformat(),
    }

    if password:
        import hashlib
        link["password_hash"] = hashlib.sha256(password.encode()).hexdigest()

    links = _load_share_links()
    links.append(link)
    _save_share_links(links)

    return {
        "success": True,
        "link_id": link_id,
        "url": f"/api/files/shared/{link_id}",
        "expires_at": link["expires_at"],
    }

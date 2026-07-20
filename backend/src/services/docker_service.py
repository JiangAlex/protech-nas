"""Docker service — manage containers and images via Docker SDK."""

import docker
from docker.errors import DockerException, NotFound, APIError


def _get_client():
    """Get Docker client, return None if unavailable."""
    try:
        return docker.from_env()
    except DockerException:
        return None


def list_containers(show_all: bool = True) -> dict:
    """List all Docker containers."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}

    containers = client.containers.list(all=show_all)
    result = []
    for c in containers:
        result.append({
            "id": c.short_id,
            "name": c.name,
            "image": str(c.image.tags[0]) if c.image.tags else str(c.image.short_id),
            "status": c.status,
            "state": c.attrs["State"]["Status"],
            "created": c.attrs["Created"],
            "ports": c.ports,
        })
    return {"success": True, "containers": result}


def start_container(container_id: str) -> dict:
    """Start a stopped container."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        container.start()
        return {"success": True, "message": f"Container {container_id} started"}
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def stop_container(container_id: str) -> dict:
    """Stop a running container."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        return {"success": True, "message": f"Container {container_id} stopped"}
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def remove_container(container_id: str, force: bool = False) -> dict:
    """Remove a container."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        container.remove(force=force)
        return {"success": True, "message": f"Container {container_id} removed"}
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def get_container_logs(container_id: str, tail: int = 100) -> dict:
    """Get container logs."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        return {"success": True, "logs": logs}
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def list_images() -> dict:
    """List all Docker images."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}

    images = client.images.list()
    result = []
    for img in images:
        result.append({
            "id": img.short_id,
            "tags": img.tags,
            "size_mb": round(img.attrs["Size"] / (1024**2), 1),
            "created": img.attrs["Created"],
        })
    return {"success": True, "images": result}


def pull_image(image: str, tag: str = "latest") -> dict:
    """Pull a Docker image."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        client.images.pull(image, tag=tag)
        return {"success": True, "message": f"Pulled {image}:{tag}"}
    except APIError as e:
        return {"success": False, "error": str(e)}

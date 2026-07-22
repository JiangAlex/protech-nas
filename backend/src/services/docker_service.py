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


def create_container(config: dict) -> dict:
    """Create and start a new Docker container.

    Args:
        config: Container configuration dict with keys:
            - image (str, required): Image name with tag
            - name (str, optional): Container name
            - ports (dict, optional): Port mapping {"80/tcp": 8080}
            - volumes (dict, optional): Volume binds {"/host/path": {"bind": "/container/path", "mode": "rw"}}
            - environment (dict, optional): Env vars {"KEY": "VALUE"}
            - restart_policy (str, optional): "no" | "always" | "on-failure" | "unless-stopped"

    Returns:
        {"success": bool, "container_id": str, "name": str}
    """
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}

    image = config.get("image", "")
    if not image:
        return {"success": False, "error": "image is required"}

    name = config.get("name")
    ports = config.get("ports")
    volumes = config.get("volumes")
    environment = config.get("environment")
    restart_policy_name = config.get("restart_policy", "no")

    # Validate restart policy
    valid_policies = ("no", "always", "on-failure", "unless-stopped")
    if restart_policy_name not in valid_policies:
        return {"success": False, "error": f"Invalid restart_policy. Allowed: {', '.join(valid_policies)}"}

    # Build restart policy dict
    restart_policy = {"Name": restart_policy_name}
    if restart_policy_name == "on-failure":
        restart_policy["MaximumRetryCount"] = 5

    try:
        container = client.containers.run(
            image=image,
            name=name,
            ports=ports,
            volumes=volumes,
            environment=environment,
            restart_policy=restart_policy,
            detach=True,
        )
        return {
            "success": True,
            "container_id": container.short_id,
            "name": container.name,
        }
    except docker.errors.ImageNotFound:
        return {"success": False, "error": f"Image not found: {image}. Pull it first."}
    except APIError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def restart_container(container_id: str) -> dict:
    """Restart a container.

    Args:
        container_id: Container ID or name.

    Returns:
        {"success": bool, "message": str}
    """
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        container.restart(timeout=10)
        return {"success": True, "message": f"Container {container_id} restarted"}
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def remove_image(image_id: str, force: bool = False) -> dict:
    """Remove a Docker image.

    Args:
        image_id: Image ID or tag.
        force: Force removal even if used by containers.

    Returns:
        {"success": bool, "message": str}
    """
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        client.images.remove(image_id, force=force)
        return {"success": True, "message": f"Image {image_id} removed"}
    except NotFound:
        return {"success": False, "error": f"Image {image_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def get_container_stats(container_id: str) -> dict:
    """Get real-time resource usage for a container.

    Returns:
        {"success": bool, "cpu_percent": float, "memory_mb": float, "memory_limit_mb": float, "memory_percent": float}
    """
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        if container.status != "running":
            return {"success": False, "error": f"Container {container_id} is not running"}
        stats = container.stats(stream=False)

        # CPU calculation
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)
        cpu_percent = round((cpu_delta / system_delta) * num_cpus * 100, 2) if system_delta > 0 else 0.0

        # Memory
        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 1)
        memory_mb = round(mem_usage / (1024 ** 2), 1)
        memory_limit_mb = round(mem_limit / (1024 ** 2), 1)
        memory_percent = round((mem_usage / mem_limit) * 100, 1) if mem_limit > 0 else 0.0

        return {
            "success": True,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "memory_limit_mb": memory_limit_mb,
            "memory_percent": memory_percent,
        }
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def inspect_container(container_id: str) -> dict:
    """Get full container configuration."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        container = client.containers.get(container_id)
        return {"success": True, "config": container.attrs}
    except NotFound:
        return {"success": False, "error": f"Container {container_id} not found"}


def prune_images() -> dict:
    """Remove all dangling (unused) images."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        result = client.images.prune()
        deleted = len(result.get("ImagesDeleted") or [])
        reclaimed = result.get("SpaceReclaimed", 0)
        return {
            "success": True,
            "deleted_count": deleted,
            "space_reclaimed_mb": round(reclaimed / (1024 ** 2), 1),
        }
    except APIError as e:
        return {"success": False, "error": str(e)}


def list_networks() -> dict:
    """List all Docker networks."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    networks = client.networks.list()
    result = []
    for n in networks:
        result.append({
            "id": n.short_id,
            "name": n.name,
            "driver": n.attrs.get("Driver", ""),
            "scope": n.attrs.get("Scope", ""),
        })
    return {"success": True, "networks": result}


def create_network(name: str, driver: str = "bridge") -> dict:
    """Create a Docker network."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    if driver not in ("bridge", "overlay", "host", "macvlan"):
        return {"success": False, "error": f"Invalid driver: {driver}"}
    try:
        n = client.networks.create(name, driver=driver)
        return {"success": True, "network_id": n.short_id}
    except APIError as e:
        return {"success": False, "error": str(e)}


def remove_network(network_id: str) -> dict:
    """Remove a Docker network."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        network = client.networks.get(network_id)
        if network.name in ("bridge", "host", "none"):
            return {"success": False, "error": f"Cannot remove default network: {network.name}"}
        network.remove()
        return {"success": True, "message": f"Network {network_id} removed"}
    except NotFound:
        return {"success": False, "error": f"Network {network_id} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


def list_volumes() -> dict:
    """List all Docker volumes."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    volumes = client.volumes.list()
    result = []
    for v in volumes:
        result.append({
            "name": v.name,
            "driver": v.attrs.get("Driver", ""),
            "mountpoint": v.attrs.get("Mountpoint", ""),
            "created": v.attrs.get("CreatedAt", ""),
        })
    return {"success": True, "volumes": result}


def create_volume(name: str, driver: str = "local") -> dict:
    """Create a Docker volume."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        v = client.volumes.create(name=name, driver=driver)
        return {"success": True, "name": v.name}
    except APIError as e:
        return {"success": False, "error": str(e)}


def remove_volume(name: str) -> dict:
    """Remove a Docker volume. WARNING: Data will be lost."""
    client = _get_client()
    if not client:
        return {"success": False, "error": "Docker is not available"}
    try:
        v = client.volumes.get(name)
        v.remove(force=False)
        return {"success": True, "message": f"Volume {name} removed"}
    except NotFound:
        return {"success": False, "error": f"Volume {name} not found"}
    except APIError as e:
        return {"success": False, "error": str(e)}


# ─── Docker Compose ───────────────────────────────────────────────────────────

import subprocess as _subprocess
import tempfile
import os as _os


def deploy_compose(yaml_content: str, project_name: str) -> dict:
    """Deploy a Docker Compose project from YAML content.

    Args:
        yaml_content: docker-compose.yml content as string.
        project_name: Project name for compose.

    Returns:
        {"success": bool, "services": list[str], "message": str}
    """
    if not yaml_content.strip():
        return {"success": False, "error": "YAML content is empty"}
    if not project_name or not project_name.replace("-", "").replace("_", "").isalnum():
        return {"success": False, "error": "Invalid project name (alphanumeric, hyphens, underscores only)"}

    # Security: basic check for dangerous options
    lower_yaml = yaml_content.lower()
    if "privileged: true" in lower_yaml:
        return {"success": False, "error": "Privileged containers are not allowed"}

    # Write to temp file
    compose_dir = f"{_os.path.expanduser('~')}/.protech-nas/compose/{project_name}"
    _os.makedirs(compose_dir, exist_ok=True)
    compose_file = _os.path.join(compose_dir, "docker-compose.yml")

    try:
        with open(compose_file, "w") as f:
            f.write(yaml_content)
    except IOError as e:
        return {"success": False, "error": str(e)}

    # Deploy
    r = _subprocess.run(
        ["docker", "compose", "-p", project_name, "-f", compose_file, "up", "-d"],
        capture_output=True, text=True, timeout=300
    )

    if r.returncode != 0:
        return {"success": False, "error": f"Compose deploy failed: {r.stderr.strip()[:300]}"}

    # Extract service names from output
    services = []
    for line in r.stderr.split("\n"):  # compose outputs to stderr
        if "Started" in line or "Running" in line or "Created" in line:
            parts = line.split()
            if parts:
                services.append(parts[-1])

    return {"success": True, "services": services, "message": f"Project {project_name} deployed"}


def list_compose_projects() -> dict:
    """List all Docker Compose projects.

    Returns:
        {"success": bool, "projects": list[{"name": str, "status": str, "services": int}]}
    """
    try:
        r = _subprocess.run(
            ["docker", "compose", "ls", "--format", "json"],
            capture_output=True, text=True, timeout=10
        )
    except Exception as e:
        return {"success": False, "error": str(e)}

    if r.returncode != 0:
        return {"success": False, "error": r.stderr.strip()}

    projects = []
    try:
        import json as _json
        data = _json.loads(r.stdout)
        for item in data:
            projects.append({
                "name": item.get("Name", ""),
                "status": item.get("Status", ""),
                "config_files": item.get("ConfigFiles", ""),
            })
    except (_json.JSONDecodeError, TypeError):
        # Fallback: parse text output
        for line in r.stdout.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 2:
                projects.append({"name": parts[0], "status": " ".join(parts[1:]), "config_files": ""})

    return {"success": True, "projects": projects}


def remove_compose_project(name: str, remove_volumes: bool = False) -> dict:
    """Stop and remove a Docker Compose project.

    Args:
        name: Project name.
        remove_volumes: Also remove named volumes.

    Returns:
        {"success": bool, "message": str}
    """
    compose_dir = f"{_os.path.expanduser('~')}/.protech-nas/compose/{name}"
    compose_file = _os.path.join(compose_dir, "docker-compose.yml")

    cmd = ["docker", "compose", "-p", name]
    if _os.path.exists(compose_file):
        cmd += ["-f", compose_file]
    cmd += ["down"]
    if remove_volumes:
        cmd.append("--volumes")

    try:
        r = _subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if r.returncode != 0:
        return {"success": False, "error": r.stderr.strip()[:200]}

    return {"success": True, "message": f"Project {name} removed"}

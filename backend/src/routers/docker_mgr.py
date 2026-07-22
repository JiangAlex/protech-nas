"""Docker management router — containers, images, logs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.docker_service import (
    list_containers, start_container, stop_container, remove_container,
    get_container_logs, list_images, pull_image,
    create_container, restart_container, remove_image,
    get_container_stats, inspect_container, prune_images,
    list_networks, create_network, remove_network,
    list_volumes, create_volume, remove_volume,
    deploy_compose, list_compose_projects, remove_compose_project
)

router = APIRouter(prefix="/api/docker", tags=["docker"])


class PullImageRequest(BaseModel):
    image: str
    tag: Optional[str] = "latest"


@router.get("/containers")
async def get_containers(all: bool = Query(True), user=Depends(get_current_user)):
    """List all Docker containers."""
    return list_containers(show_all=all)


@router.post("/containers/{container_id}/start")
async def post_start(container_id: str, user=Depends(get_current_user)):
    """Start a container."""
    result = start_container(container_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/containers/{container_id}/stop")
async def post_stop(container_id: str, user=Depends(get_current_user)):
    """Stop a container."""
    result = stop_container(container_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/containers/{container_id}")
async def delete_container(container_id: str, force: bool = False, user=Depends(get_current_user)):
    """Remove a container."""
    result = remove_container(container_id, force=force)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/containers/{container_id}/logs")
async def get_logs(container_id: str, tail: int = Query(100), user=Depends(get_current_user)):
    """Get container logs."""
    return get_container_logs(container_id, tail=tail)


@router.get("/images")
async def get_images(user=Depends(get_current_user)):
    """List all Docker images."""
    return list_images()


@router.post("/images/pull")
async def post_pull_image(req: PullImageRequest, user=Depends(get_current_user)):
    """Pull a Docker image."""
    result = pull_image(req.image, req.tag)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class CreateContainerRequest(BaseModel):
    image: str
    name: Optional[str] = None
    ports: Optional[dict] = None
    volumes: Optional[dict] = None
    environment: Optional[dict] = None
    restart_policy: Optional[str] = "no"


@router.post("/containers/create")
async def post_create_container(req: CreateContainerRequest, user=Depends(get_current_user)):
    """Create and start a new container."""
    result = create_container(req.model_dump(exclude_none=True))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/containers/{container_id}/restart")
async def post_restart(container_id: str, user=Depends(get_current_user)):
    """Restart a container."""
    result = restart_container(container_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/images/{image_id:path}")
async def delete_image(image_id: str, force: bool = False, user=Depends(get_current_user)):
    """Delete a Docker image."""
    result = remove_image(image_id, force=force)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class NetworkCreate(BaseModel):
    name: str
    driver: Optional[str] = "bridge"


class VolumeCreate(BaseModel):
    name: str
    driver: Optional[str] = "local"


@router.get("/containers/{container_id}/stats")
async def get_stats(container_id: str, user=Depends(get_current_user)):
    """Get container real-time resource usage."""
    result = get_container_stats(container_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/containers/{container_id}/inspect")
async def get_inspect(container_id: str, user=Depends(get_current_user)):
    """Get full container configuration."""
    result = inspect_container(container_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/images/prune")
async def post_prune_images(user=Depends(get_current_user)):
    """Remove all dangling images."""
    result = prune_images()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/networks")
async def get_networks(user=Depends(get_current_user)):
    """List Docker networks."""
    return list_networks()


@router.post("/networks")
async def post_network(req: NetworkCreate, user=Depends(get_current_user)):
    """Create a Docker network."""
    result = create_network(req.name, req.driver)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/networks/{network_id}")
async def delete_network(network_id: str, user=Depends(get_current_user)):
    """Remove a Docker network."""
    result = remove_network(network_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/volumes")
async def get_volumes(user=Depends(get_current_user)):
    """List Docker volumes."""
    return list_volumes()


@router.post("/volumes")
async def post_volume(req: VolumeCreate, user=Depends(get_current_user)):
    """Create a Docker volume."""
    result = create_volume(req.name, req.driver)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/volumes/{name}")
async def delete_volume(name: str, user=Depends(get_current_user)):
    """Remove a Docker volume."""
    result = remove_volume(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─── Docker Compose ──────────────────────────────────────────────────────────


class ComposeDeployRequest(BaseModel):
    yaml_content: str
    project_name: str


@router.post("/compose/deploy")
async def post_compose_deploy(req: ComposeDeployRequest, user=Depends(get_current_user)):
    """Deploy a Docker Compose project from YAML content."""
    result = deploy_compose(req.yaml_content, req.project_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/compose/projects")
async def get_compose_projects(user=Depends(get_current_user)):
    """List all Docker Compose projects."""
    return list_compose_projects()


@router.delete("/compose/projects/{name}")
async def delete_compose_project(
    name: str, remove_volumes: bool = False, user=Depends(get_current_user)
):
    """Remove a Docker Compose project."""
    result = remove_compose_project(name, remove_volumes=remove_volumes)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

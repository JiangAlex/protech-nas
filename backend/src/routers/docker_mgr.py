"""Docker management router — containers, images, logs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user
from ..services.docker_service import (
    list_containers, start_container, stop_container, remove_container,
    get_container_logs, list_images, pull_image
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

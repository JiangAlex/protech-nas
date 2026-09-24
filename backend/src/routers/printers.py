"""Printers router — network printer sharing (CUPS/IPP) API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..auth import get_current_user
from ..services.printer_service import (
    discover_printers, list_printers, add_printer, set_printer_shared,
    remove_printer, list_jobs, cancel_job, print_test_page,
)

router = APIRouter(prefix="/api/printers", tags=["printers"])


class PrinterCreate(BaseModel):
    name: str
    device_uri: str
    driver: str = "everywhere"
    shared: bool = True


class PrinterShare(BaseModel):
    shared: bool


@router.get("")
async def get_printers(user=Depends(get_current_user)):
    """List configured printers."""
    result = list_printers()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/discover")
async def get_discover(user=Depends(get_current_user)):
    """Discover connected (USB/network) printer devices."""
    result = discover_printers()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("")
async def post_printer(req: PrinterCreate, user=Depends(get_current_user)):
    """Add a printer and share it over the network."""
    result = add_printer(req.name, req.device_uri, req.driver, req.shared)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/{name}/share")
async def put_share(name: str, req: PrinterShare, user=Depends(get_current_user)):
    """Enable or disable network sharing for a printer."""
    result = set_printer_shared(name, req.shared)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/{name}")
async def delete_printer(name: str, user=Depends(get_current_user)):
    """Remove a printer."""
    result = remove_printer(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{name}/jobs")
async def get_jobs(name: str, user=Depends(get_current_user)):
    """List the print queue for a printer."""
    result = list_jobs(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/jobs/{job_id}/cancel")
async def post_cancel_job(job_id: str, user=Depends(get_current_user)):
    """Cancel a print job."""
    result = cancel_job(job_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{name}/test")
async def post_test(name: str, user=Depends(get_current_user)):
    """Print a CUPS test page."""
    result = print_test_page(name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

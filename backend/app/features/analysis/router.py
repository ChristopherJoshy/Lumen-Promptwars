"""Analysis HTTP surface: submit, status, report. Fusion lives in service.py."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.features.analysis import service

router = APIRouter()


@router.get("/status")
async def status() -> dict[str, str]:
    return {"pipeline": "skeleton"}


@router.get("/report/{case_id}")
async def report(case_id: str) -> dict:
    """Serve the cached verdict dict; unknown cases are 404, never fallback."""
    case = service.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Unknown or expired case.")
    return case


@router.get("/report/{case_id}/signals")
async def signals(case_id: str) -> dict:
    """Serve {name, finding} signal rows for the report evidence panel."""
    rows = service.list_signals(case_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Unknown or expired case.")
    return {"case_id": case_id, "signals": rows}


@router.get("/report/{case_id}/forensics/{name}")
async def forensics_heatmap(case_id: str, name: str) -> FileResponse:
    """Stream a forensic heatmap PNG; unknown names or cases are 404."""
    path = service.forensics_path(case_id, name)
    if path is None:
        raise HTTPException(status_code=404, detail="Unknown case or heatmap.")
    return FileResponse(path, media_type="image/png")

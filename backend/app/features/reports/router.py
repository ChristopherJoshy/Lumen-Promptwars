"""Reports HTTP surface: evidentiary export download."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.features.reports.evidentiary_export import export

router = APIRouter()


@router.get("/{case_id}/export")
async def export_report(case_id: str) -> Response:
    """Download the signed JSON dossier; unknown cases are 404."""
    try:
        payload = await export(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown or expired case.")
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="lumen-{case_id[:12]}.json"'},
    )

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


@router.get("/usage")
async def usage() -> dict:
    """Usage counts by verdict/modality; {} when the ledger is disabled."""
    from app.db import usage as usage_ledger

    return await usage_ledger.usage_stats()


@router.post("/report/{case_id}/ask")
async def ask_about_case(case_id: str, body: dict) -> dict:
    """Answer one follow-up question about a case (grounded in its signals)."""
    from app.features.analysis.agents import muse_client

    case = service.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Unknown or expired case.")
    question = str((body or {}).get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=422, detail="Ask a non-empty question.")
    if len(question) > 500:
        raise HTTPException(status_code=422, detail="Keep the question under 500 characters.")
    import json as _json

    system = (
        "You answer follow-up questions about one Lumen media-verdict report. "
        "Ground every claim in the case JSON below; say 'not in this report' "
        "when the answer is not there. Plain language, 2-5 sentences, no new "
        "verdict. Return JSON ONLY: {\"answer\": str}."
    )
    try:
        result = await muse_client.respond(
            system,
            [{"type": "input_text", "text": f"question: {question}\ncase: {_json.dumps(case, default=str)[:6000]}"}],
            max_output_tokens=800,
        )
    except muse_client.MuseError as exc:
        raise HTTPException(status_code=502, detail=f"Answer failed: {exc}") from exc
    if "answer" not in result:
        raise HTTPException(status_code=502, detail="Answer came back unparsable.")
    return {"answer": str(result["answer"])}

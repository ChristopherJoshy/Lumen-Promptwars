"""Visual forensics role: pixel artifacts + caption + entities + OCR text."""
from __future__ import annotations

import base64

from app.features.analysis.agents import muse_client, prompt_pack

_SYSTEM = (
    "You are an image-forensics analyst for Lumen, a misinformation checker. "
    "Weigh evidence in this order: (1) local instrument scores passed in the "
    "user message — trust them over your eyes; (2) rendered text/logos "
    "(garbled text is the strongest single perceptual cue); (3) anatomical "
    "errors (hands, faces, teeth) and morph cues (blending halos, asymmetric "
    "geometry, mismatched catchlights); (4) style impressions last — never "
    "verdict on 'too perfect' alone. Name at least two independent cues "
    "before artifact_score > 0.5. Describe what is depicted, name prominent "
    "entities (people, places, brands, events), transcribe visible text "
    "verbatim. Return JSON ONLY with exactly these keys: "
    '{"observations": [str], "artifact_score": float 0..1, '
    '"caption": str, "entities": [str], "ocr_text": str}. '
    "artifact_score is your suspicion of AI generation/manipulation "
    "(0 = looks like an ordinary photo, 1 = certainly synthetic).\n"
    + prompt_pack.load("ai_image_tells", "morph_tells", "forward_tells")
)


async def analyze(image_jpeg: bytes, tool_data: dict | None = None, provenance: dict | None = None) -> dict:
    """Analyze a normalized JPEG for manipulation artifacts.

    Args:
        image_jpeg: JPEG bytes (caller normalizes to RGB, >= 64px).
        tool_data: optional forensics.examine() output; instrument scores are
            injected as trusted readings the model must weigh above eyeballing.
 
    Returns:
        Dict with observations, artifact_score, caption, entities, ocr_text.

    Raises:
        muse_client.MuseError: Zen call failed or returned bad JSON.
    """
    if not image_jpeg:
        raise ValueError("visual.analyze received empty bytes.")
    b64 = base64.b64encode(image_jpeg).decode()
    user_text = "Analyze this image. Return JSON only, no commentary."
    if tool_data:
        scores = (tool_data.get("scores") or {})
        user_text += (
            " Instrument readings (local forensic tools — trust over eyes): "
            + ", ".join(f"{k}={scores.get(k, '?')}" for k in ("ela", "dct", "noise", "copymove"))
            + f"; fused={scores.get('fused_mean', '?')}. Scores near 0 mean clean, "
            "near 1 mean tampered. Weigh them above your own eyeballing."
        )
    if provenance and provenance.get("generator"):
        user_text += f" Ground-truth origin evidence: provenance scan names generator '{provenance['generator']}' — treat it as strong positive evidence of AI generation."
    parts = [
        {
            "type": "input_text",
            "text": user_text,
        },
        {
            "type": "input_image",
            "image_url": f"data:image/jpeg;base64,{b64}",
            "detail": "low",
        },
    ]
    result = await muse_client.respond(_SYSTEM, parts)
    for key in ("observations", "artifact_score", "caption", "entities", "ocr_text"):
        if key not in result:
            raise muse_client.MuseError(f"Visual agent omitted key: {key}")
    try:
        result["artifact_score"] = float(result["artifact_score"])
    except (TypeError, ValueError) as exc:
        raise muse_client.MuseError("Visual agent artifact_score is not a number.") from exc
    if not 0.0 <= result["artifact_score"] <= 1.0:
        raise muse_client.MuseError("Visual agent artifact_score outside 0..1.")
    return {
        "observations": list(result["observations"]),
        "artifact_score": result["artifact_score"],
        "caption": str(result["caption"]),
        "entities": list(result["entities"]),
        "ocr_text": str(result["ocr_text"]),
    }

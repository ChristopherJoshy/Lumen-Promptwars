"""Sole owner of the Zen key: Responses API calls for every agent.

Step 0 probe (2026-09-05): text-only, vision (input_image/image_url,
detail low, 256px JPEG), and audio (input_audio/audio_url,
data:audio/wav;base64) all return HTTP 200 with output_text on
muse-spark-1.3-contributor-free. Tiny 1x1 JPEGs 500 upstream, so callers
must send normalized images (>= 64px, JPEG re-encode). Text-only needs
max_output_tokens >= 800: reasoning tokens consume ~100-500 before output.
"""
from __future__ import annotations

import json

import httpx

from app.core.config import settings


class MuseError(Exception):
    """Raised when the Zen Responses call fails or returns unusable output."""


def _extract_output_text(payload: dict) -> str:
    """Walk output[] message items tolerantly to find model text."""
    chunks: list[str] = []
    output = payload.get("output")
    if not isinstance(output, list):
        raise MuseError(f"Responses payload has no output[]: {str(payload)[:300]}")
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                for key in ("output_text", "text"):
                    val = block.get(key)
                    if isinstance(val, str) and val.strip():
                        chunks.append(val)
        for key in ("output_text", "text"):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                chunks.append(val)
    text = "".join(chunks).strip()
    if not text:
        raise MuseError(f"Responses output[] carried no text: {str(payload)[:300]}")
    return text


def _strip_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


async def respond(
    system: str,
    user_parts: list[dict],
    *,
    json_only: bool = True,
    max_output_tokens: int = 2000,
    reasoning_effort: str = "low",
) -> dict:
    """Call the Zen Responses API and return parsed JSON (or raw text).

    Args:
        system: System prompt framing the agent role.
        user_parts: Content blocks (input_text / input_image / input_audio).
        json_only: Strip fences and json.loads the model text.
        max_output_tokens: Token budget (default 2000; reasoning eats the headroom).
        reasoning_effort: Thinking level; "low" everywhere (probe 2026-09-05:
            the endpoint accepts reasoning.effort and returns 200).

    Returns:
        Parsed dict when json_only, else ``{"text": ...}``.

    Raises:
        MuseError: Missing key, transport/5xx failure, empty output, bad JSON.
    """
    api_key = settings.opencode_zen_api_key
    if not api_key:
        raise MuseError("opencode_zen_api_key is not configured (backend/.env).")
    url = settings.opencode_zen_base_url.rstrip("/") + "/responses"
    body = {
        "model": settings.muse_model,
        "instructions": system,
        "input": [{"role": "user", "content": user_parts}],
        "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": reasoning_effort},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error: str = ""
    async with httpx.AsyncClient(timeout=settings.agent_timeout_s) as client:
        for attempt in range(2):
            try:
                resp = await client.post(url, headers=headers, json=body)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                continue
            if resp.status_code in (429,) or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                continue
            if resp.status_code in (401, 403):
                raise MuseError(f"Zen auth failed (HTTP {resp.status_code}): check key/quota.")
            if resp.status_code >= 400:
                raise MuseError(f"Zen request failed (HTTP {resp.status_code}): {resp.text[:300]}")
            try:
                payload = resp.json()
            except ValueError as exc:
                raise MuseError(f"Zen returned non-JSON: {resp.text[:300]}") from exc
            text = _extract_output_text(payload)
            if not json_only:
                return {"text": text}
            try:
                parsed = json.loads(_strip_fences(text))
            except json.JSONDecodeError as exc:
                raise MuseError(f"Model returned non-JSON: {text[:300]}") from exc
            if not isinstance(parsed, dict):
                raise MuseError(f"Model JSON was not an object: {text[:300]}")
            return parsed
    raise MuseError(f"Zen call failed after retry: {last_error[:300]}")

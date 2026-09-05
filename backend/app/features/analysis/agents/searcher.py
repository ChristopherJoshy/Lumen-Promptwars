"""Web-evidence role: Exa (keyed) + DDGS (keyless), India-first labeling."""
from __future__ import annotations

import asyncio

import httpx

from app.core.config import settings

_INDIA_MARKERS = ("alt news", "altnews", "boom", "factly", "pibfactcheck", "pib")


def _build_queries(caption: str, entities: list[str], ocr_text: str) -> list[str]:
    queries: list[str] = []
    primary = " ".join([caption.strip()] + [e for e in entities[:3] if e.strip()]).strip()
    if primary:
        queries.append(primary[:300])
    fallback = " ".join(
        [ocr_text.strip()[:200]] + [e for e in entities[:3] if e.strip()]
    ).strip()
    if fallback and fallback != primary:
        queries.append(fallback[:300])
    if not queries and caption.strip():
        queries.append(caption.strip()[:300])
    return queries[:2]


def _normalize_hit(title: str, url: str, snippet: str) -> dict:
    return {"title": title or "", "url": url or "", "snippet": snippet or ""}


def _is_india_hit(title: str, url: str) -> bool:
    blob = f"{title} {url}".lower()
    return any(marker in blob for marker in _INDIA_MARKERS)


def _ddg_text(query: str) -> list[dict]:
    """Thin sync wrapper so tests can monkeypatch DDG without threads."""
    from ddgs import DDGS

    with DDGS(timeout=15) as ddgs:
        return list(ddgs.text(query, region="in-en", max_results=5) or [])


async def _exa_search(query: str) -> list[dict]:
    if not settings.exa_api_key:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.exa.ai/search",
            headers={"Authorization": f"Bearer {settings.exa_api_key}"},
            json={
                "query": query,
                "type": "auto",
                "numResults": 5,
                "contents": {"highlights": {"maxCharacters": 2000}},
            },
        )
    if resp.status_code in (401, 402, 403, 429):
        raise RuntimeError(f"Exa search failed (HTTP {resp.status_code}): quota/auth.")
    if resp.status_code >= 400:
        raise RuntimeError(f"Exa search failed (HTTP {resp.status_code}).")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise RuntimeError("Exa returned non-JSON.") from exc
    hits: list[dict] = []
    for item in payload.get("results", []) or []:
        highlights = ""
        contents = item.get("contents") or {}
        hl = contents.get("highlights") or []
        if isinstance(hl, list) and hl:
            highlights = str(hl[0])[:2000]
        hits.append(
            _normalize_hit(
                str(item.get("title", "")),
                str(item.get("url", "")),
                highlights or str(item.get("text", ""))[:2000],
            )
        )
    return hits


async def search(caption: str, entities: list[str], ocr_text: str) -> dict:
    """Search the web for the depicted claim; label Indian fact-checkers.

    Args:
        caption: Model caption of the content.
        entities: Named entities from the perceptual agent.
        ocr_text: Visible/transcribed text.

    Returns:
        Dict with exa_hits, ddg_hits, india_hits, warnings. DDG failure
        degrades to Exa-only with the error in warnings (keyless
        metasearch is flaky by nature). Exa auth/quota errors raise loudly.

    Raises:
        RuntimeError: Exa call failed when an Exa key is configured.
    """
    queries = _build_queries(caption or "", entities or [], ocr_text or "")
    warnings: list[str] = []
    if not settings.exa_api_key:
        warnings.append("exa_api_key not configured; Exa skipped, DDG only.")
    exa_hits: list[dict] = []
    ddg_hits: list[dict] = []
    if not queries:
        return {"exa_hits": [], "ddg_hits": [], "india_hits": [], "warnings": warnings}

    async def exa_all() -> list[dict]:
        out: list[dict] = []
        for query in queries:
            out.extend(await _exa_search(query))
        return out

    async def ddg_all() -> list[dict]:
        out: list[dict] = []
        for query in queries:
            try:
                raw = await asyncio.to_thread(_ddg_text, query)
            except Exception as exc:
                warnings.append(f"ddg failed for {query[:60]!r}: {type(exc).__name__}")
                continue
            for item in raw:
                out.append(
                    _normalize_hit(
                        str(item.get("title", "")),
                        str(item.get("href", "") or item.get("url", "")),
                        str(item.get("body", ""))[:2000],
                    )
                )
        return out

    exa_result, ddg_result = await asyncio.gather(exa_all(), ddg_all())
    exa_hits = exa_result
    ddg_hits = ddg_result

    seen: set[str] = set()
    deduped: list[dict] = []
    for hit in exa_hits + ddg_hits:
        url = hit.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(hit)
    india_hits = [h for h in deduped if _is_india_hit(h["title"], h["url"])]
    return {"exa_hits": exa_hits, "ddg_hits": ddg_hits, "india_hits": india_hits, "warnings": warnings}

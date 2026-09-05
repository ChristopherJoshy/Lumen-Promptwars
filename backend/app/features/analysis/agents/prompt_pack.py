"""Knowledge-pack loader: researched tells feed agent system prompts.

Packs live in agents/knowledge/*.md (distilled from web research, Step 0).
Budget-capped so system prompts stay under ~2500 tokens total.
"""

from __future__ import annotations

from pathlib import Path

_PACK_DIR = Path(__file__).resolve().parent / "knowledge"


def load(*names: str, budget_chars: int = 3000) -> str:
    """Concatenate packs newest-first, truncated to budget_chars.

    Raises FileNotFoundError naming the missing pack — a missing pack is a
    wiring bug, never silently skipped (loud-failure rule).
    """
    chunks: list[str] = []
    for name in names:
        path = _PACK_DIR / f"{name}.md"
        if not path.is_file():
            raise FileNotFoundError(f"Knowledge pack missing: {path}")
        chunks.append(f"--- {name} ---\n{path.read_text(encoding='utf-8').strip()}")
    text = "\n\n".join(chunks)
    if len(text) > budget_chars:
        text = text[:budget_chars].rstrip() + "\n[truncated to budget]"
    return text

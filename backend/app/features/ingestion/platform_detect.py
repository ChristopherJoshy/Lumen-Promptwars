"""Platform detection via regex/domain matching (checkpoint 3)."""
from __future__ import annotations

from urllib.parse import urlparse

_YOUTUBE = ("youtube.com", "youtu.be", "music.youtube.com")
_INSTAGRAM = ("instagram.com", "instagr.am")
_TIKTOK = ("tiktok.com", "vt.tiktok.com", "vm.tiktok.com")
_X = ("x.com", "twitter.com", "mobile.twitter.com")
_FACEBOOK = ("facebook.com", "fb.com", "fb.watch")
_TELEGRAM = ("t.me", "telegram.me", "telegram.org")


def detect_platform(url: str) -> str:
    """Map a URL to its platform name.

    Args:
        url: Candidate link URL.

    Returns:
        One of ``youtube | instagram | tiktok | x | facebook | telegram | generic``.
    """
    host = urlparse(url.strip()).netloc.lower().split("@")[-1].split(":")[0]
    if not host:
        return "generic"
    h = host[4:] if host.startswith("www.") else host
    if h in _YOUTUBE or h.endswith(tuple("." + d for d in _YOUTUBE)):
        return "youtube"
    if h in _INSTAGRAM or h.endswith(tuple("." + d for d in _INSTAGRAM)):
        return "instagram"
    if h in _TIKTOK or h.endswith(tuple("." + d for d in _TIKTOK)):
        return "tiktok"
    if h in _X or h.endswith(tuple("." + d for d in _X)):
        return "x"
    if h in _FACEBOOK or h.endswith(tuple("." + d for d in _FACEBOOK)):
        return "facebook"
    if h in _TELEGRAM or h.endswith(tuple("." + d for d in _TELEGRAM)):
        return "telegram"
    return "generic"

"""Pure-code temporal-integrity check: claimed date vs earliest-seen."""
from __future__ import annotations


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    for width in (8, 6, 4):
        if len(digits) >= width:
            try:
                year = int(digits[:4])
            except ValueError:
                continue
            if 1990 <= year <= 2030:
                return year
    return None


def check(meta_dates: dict, hits: list[dict], claimed_date: str | None) -> dict:
    """Compare claimed date against earliest-seen-elsewhere evidence.

    Args:
        meta_dates: Mapping that may carry exif/upload dates.
        hits: Search hits (each may carry published dates in future shapes).
        claimed_date: Link upload date, or None for WhatsApp receipts where
            no declared date exists (then earliest-seen is itself the finding).

    Returns:
        Dict with earliest_seen, flag, note. No dates anywhere -> flag
        False with a note saying so.
    """
    candidates: list[str] = []
    for key in ("exif_date", "upload_date", "published", "created"):
        value = meta_dates.get(key) if isinstance(meta_dates, dict) else None
        if value:
            candidates.append(str(value))
    for hit in hits or []:
        if isinstance(hit, dict):
            for key in ("published", "date", "upload_date"):
                if hit.get(key):
                    candidates.append(str(hit[key]))
    earliest = candidates[0] if candidates else None
    if not claimed_date and not earliest:
        return {
            "earliest_seen": None,
            "flag": False,
            "note": "No claimed or seen dates available; nothing to contradict.",
        }
    if not claimed_date:
        return {
            "earliest_seen": earliest,
            "flag": False,
            "note": f"No claimed date; earliest-seen-elsewhere is {earliest}.",
        }
    claimed_year = _parse_year(claimed_date)
    earliest_year = _parse_year(earliest)
    if claimed_year and earliest_year and earliest_year < claimed_year:
        return {
            "earliest_seen": earliest,
            "flag": True,
            "note": f"Claimed {claimed_date} but seen earlier ({earliest}); recycled content suspected.",
        }
    return {
        "earliest_seen": earliest,
        "flag": False,
        "note": "No temporal contradiction found.",
    }

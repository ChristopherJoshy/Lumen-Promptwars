"""Analysis schemas: submission in, verdict report out."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Verdict = Literal["verified", "contradiction_detected", "likely_synthetic", "insufficient_evidence"]


class Submission(BaseModel):
    media_type: Literal["image", "audio", "video"]
    source: Literal["upload", "link", "whatsapp"]


class Report(BaseModel):
    case_id: str
    verdict: Verdict
    explanation: str = ""

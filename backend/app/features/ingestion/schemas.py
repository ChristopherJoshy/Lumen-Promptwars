"""Ingestion schemas."""
from pydantic import BaseModel


class LinkSubmit(BaseModel):
    url: str

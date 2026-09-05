"""Async DB session. Postgres when DATABASE_URL is set, else local SQLite.

Why: this machine has no Docker, so bare `uvicorn --reload` must boot
without Postgres. Alembic migrations own the Postgres schema; the SQLite
fallback only needs `init_db()` table creation for local iteration.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    if settings.database_url:
        return settings.database_url
    return "sqlite+aiosqlite:///./lumen_dev.db"


engine = create_async_engine(_database_url(), future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    from app.features.analysis import models as _analysis_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        yield session

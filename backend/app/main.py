"""Lumen API entrypoint: app factory, lifespan-managed DB, v1 router."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import init_db


def _allowed_origins() -> list[str]:
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.frontend_url not in origins:
        origins.append(settings.frontend_url)
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # creates tables on SQLite fallback; Alembic owns Postgres
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(v1_router, prefix="/api/v1")
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()

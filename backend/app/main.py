"""Lumen API entrypoint: app factory, lifespan-managed DB, v1 router."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import init_db

_SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "SAMEORIGIN",
}


def _security_headers(response):
    """Stamp anti-clickjacking/MIME-sniffing headers; returns the response."""
    for name, value in _SECURITY_HEADERS.items():
        response.headers[name] = value
    return response


class _SecurityHeadersMiddleware:
    """Pure ASGI middleware: same headers on every response, no exceptions."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def sender(message) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                for name, value in _SECURITY_HEADERS.items():
                    headers.setdefault(name.encode("latin-1"), value.encode("latin-1"))
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, sender)


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
    app.add_middleware(_SecurityHeadersMiddleware)
    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app

app = create_app()

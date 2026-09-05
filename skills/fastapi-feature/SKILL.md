# FastAPI feature skill

Checklist for adding a backend feature (`backend/app/features/<name>/`).

## Layout (feature owns all four)

- `router.py` — HTTP surface only, no business logic
- `schemas.py` — pydantic in/out models
- `service.py` — orchestration, async throughout
- `models.py` — SQLAlchemy 2.0 async models (if persisted)

## Rules

- Mount in `backend/app/api/v1/router.py`; never a flat top-level
  `routers/` or `models/` folder.
- Top-of-file docstring: role in the pipeline. Comments explain *why*,
  never *what*.
- Full type hints, mypy-clean. No bare `except`; surface real errors.
- Tests mirror the feature path; run `pytest -q` before yielding.
- Config comes from `app.core.config.settings` (pydantic-settings) — no new
  env-var plumbing beside it.

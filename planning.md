# Lumen — planning.md

## Understanding

Single-repo web platform: FastAPI backend (async, Taskiq+Redis jobs,
Postgres, S3 storage) + Next.js 15 frontend (SSR report page). Five-signal
fusion (forensics, provenance, authenticity-contradiction, context-trace,
temporal-integrity) per submission; LLM explains the verdict in plain
language; heatmap artifact stored with the case; WebSocket streams stage
progress; WhatsApp (Twilio) reuses the same pipeline as upload/link.

## Open questions / ambiguities

1. Auth library choice left open (email+OAuth, any lib) — default: JWT email
   auth first, OAuth only if time allows.
2. Generic reverse search provider unspecified (Fact Check API is primary) —
   default: stub interface, cheapest keyless option first.
3. LLM provider/model unspecified — default: env-swappable wrapper, cheapest
   chat model, structured-signal-input only (never raw media).
4. Video detector explicitly stretch — ship audio→image→provenance→
   contradiction→fact-check→explain→export before touching video.
5. Local dev has no Docker on this machine — decision: Docker Compose stays
   the prod/submission target, but backend supports SQLite + local-disk-S3-shim
   + inline-task fallback so `uvicorn --reload` + `next dev` run bare.

## Build order (checkpoint per line; commit each)

1. ✅ Repo scaffold + compose + AGENTS.md + .gitignore + .env examples.
2. Backend skeleton: app factory, lifespan DB, pydantic-settings config,
   Alembic baseline. (no Docker needed to boot)
3. Ingestion: upload → storage; `link_extractor.py` yt-dlp wrapper + platform
   detect; cassette/mocked tests (never live Instagram in CI); retention
   comment at top of file.
4. Taskiq + WebSocket progress, proven with a no-op job first.
5. Audio forensics, Indic-first (Malayalam/Hindi/Tamil/Telugu before English).
6. WhatsApp bot: signature validation + media download + same pipeline +
   TwiML fast-ack + 16 MB fallback reply; sandbox join-code README note.
7. Image forensics + `tests/fixtures/` set (keep repo < 10 MB — fetch large
   sets at test time, never commit).
8. Provenance (C2PA + EXIF).
9. `contradiction.py` (authenticity + temporal), agree/conflict unit tests.
10. `fact_check_lookup.py` with India-signatory labeling.
11. LLM explanation (structured signals in, 2–4 sentences out).
12. `evidentiary_export.py` signed PDF/JSON (states "documentation aid, not
    legal certification").
13. Video detector (stretch).
14. Frontend: /analyze → ProgressStream → SSR /report/[id]; community
    annotations; auth; dashboard.
15. README: setup, demo script, honest limitations (IG/X reliability,
    sandbox join code, video maturity). No oversell.

## Size/branch discipline (submission rules)

Public repo, exactly one branch (`main`), < 10 MB: never commit
`node_modules`, `.venv`, `*.pt/*.bin/*.onnx`, media fixtures, `.env`
secrets, or volume dirs — `.gitignore` already excludes them.

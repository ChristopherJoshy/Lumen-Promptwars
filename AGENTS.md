# Lumen — AGENTS.md (Pi-native project instructions)

Lumen helps journalists, researchers, and citizens check suspicious media
(images, audio, video, links, WhatsApp forwards) for signs of AI generation
or manipulation. A user submits content, five signals are fused
(forensics, provenance, authenticity-contradiction, context-trace, temporal
integrity), and a shareable SSR verdict report explains the result in plain
language. Positioning: **Indic languages first** (Malayalam, Hindi, Tamil,
Telugu), **WhatsApp as a first-class intake**, Indian fact-checkers first
(PIB, Alt News, BOOM, Factly via Google Fact Check Tools API), takedown-ready
export aligned with India's Feb 2026 IT rules. Optimize every decision for
"a Malayalam-speaking user forwards a suspicious WhatsApp voice note".

## Stack constraints (do not substitute without asking)

- Backend: Python 3.12+, FastAPI, async throughout.
- Queue: Taskiq + Redis. No Celery/Django/Flask. No second backend language
  (PyO3 extension if raw speed is ever needed, not a new service).
- DB: PostgreSQL via SQLAlchemy 2.0 async + Alembic. Local dev MAY use
  SQLite fallback (see `backend/.env.example`).
- Cache/pubsub: Redis (Taskiq broker + WebSocket progress).
- Storage: S3-compatible (MinIO in compose, R2 in prod). Never treat local
  disk as source of truth; stream uploads, never buffer full video in memory.
- Frontend: Next.js 15 App Router, TypeScript strict, Tailwind, shadcn/ui.
  `/report/[id]` MUST stay a server component (link-preview cards).
- Realtime: native FastAPI WebSockets, per-job progress channel.
- Link ingestion: `yt-dlp` as a Python library. NEVER use Meta oEmbed for
  extraction (terms restrict it to front-end embedding display).
- Detection (v1): image/video/audio verdicts come from the Muse agentic
  pipeline (`backend/app/features/analysis/agents/`); local-weight
  checkpoints are superseded, no `.pt/.onnx` weights ship with the repo.
- WhatsApp: Twilio API (sandbox for dev). Webhook validates
  `X-Twilio-Signature`, enqueues a Taskiq job, returns TwiML fast — no inline
  processing. 16 MB media limit → reply "use web upload instead".
- Context: Exa (keyed) + DDGS/DuckDuckGo (keyless, in-en) web evidence,
  India signatories (PIB, Alt News, BOOM, Factly) labeled distinctly;
  Google Fact Check Tools API is a future enrichment, not the v1 path.

## How to work (Pi workflow)

- Multi-file work: `todo init` a phased plan first; one slice per task.
- Research before editing: reuse existing patterns; second convention beside
  an existing one is prohibited. `lsp references` before touching exports.
- Implement: fix source, never suppress symptoms or fabricate fallback data.
  A detector that can't load fails loudly — never a fake "insufficient
  evidence". Migrate every caller; delete obsolete code, no shims.
- No mocks allowed in shipped code or live paths: every signal, score,
  transcript, and verdict must come from a real tool or model call.
  Mocks exist ONLY inside `backend/tests/` to isolate units. A path that
  cannot run its real tool raises loudly instead of returning placeholder data.
- Verify before yielding: run the thing (backend tests, `next lint` /
  `tsc --noEmit`, or a throwaway smoke script). No routine `git` calls for
  validation. New tests only for genuinely uncertain edges; never assert
  implementation details or pad with parameter rows.
- Commit per logical checkpoint, Conventional Commits (see
  `skills/commit-conventions/SKILL.md`). Small reviewable diffs; stub with
  `NotImplementedError` + docstring rather than one giant commit.
- Commit discipline: commit AND push after every small logical change — one
  Conventional Commit per sub-step, never accumulate unpushed work across
  steps, never batch multiple steps into one commit.
- Maintain `changes.md` with every change. Never modify without asking:
  applied Alembic migrations, `.env`/secrets.
- Python MUST run inside `backend/.venv` — never install or run with the
  system interpreter (`pip install`, `pytest`, `uvicorn` outside the venv
  are prohibited). Create once: `python -m venv backend/.venv`.

## Commands

- Dev stack (prod-like): `docker compose up`
- Backend setup: `backend/.venv/Scripts/pip install -r backend/requirements.txt`
- Backend dev (no Docker): `backend/.venv/Scripts/uvicorn app.main:app --reload --port 8000 --app-dir backend`
- Frontend dev: `cd frontend && npm install && npm run dev` (port 3000)
- Backend tests (from repo root): `backend/.venv/Scripts/python -m pytest backend/tests -q`
- Frontend checks: `cd frontend && npx tsc --noEmit` (`npm run build` for the full production check; `next lint` no longer exists in Next 16)
- Migrations: `cd backend && .venv/Scripts/alembic upgrade head` (new: `.venv/Scripts/alembic revision --autogenerate -m "..."`; applied ones append-only)

## Layout (feature-based, never flat top-level routers//models/)

`backend/app/{main.py,core,db,features/{analysis,ingestion,whatsapp_bot,context_search,reports,community,users},api/v1/router.py,worker.py}`
`frontend/{app/(marketing),app/analyze,app/report/[id],app/dashboard,features,components/ui,lib,types}`

## Codebase skills (`skills/<name>/SKILL.md` — read before touching the area)

- `detector-module` — adding any forensic detector (contract, fixtures, loud
  failures). Every detector must be structurally identical.
- `fastapi-feature` — adding a backend feature (layout, docstrings, tests).
- `nextjs-report-page` — report/frontend work (SSR page, client components).
- `whatsapp-webhook` — webhook handler contract + risk review.
- `commit-conventions` — message format, push discipline, never-commit list.

## Legal/ethical (bake in)

- Link/WhatsApp media: transient analysis only — no re-download or
  redistribution through Lumen. Same retention rule for forwards.
- Evidentiary export must state it is a documentation aid, not a legal
  certification. Report page carries a probabilistic-aid disclaimer.

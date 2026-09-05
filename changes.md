# changes.md — Lumen changelog (maintained every commit)

Format: `## <date> — <scope>` + bullets. Newest first. One line per change.

## 2026-09-05 — design overhaul

- Frontend on latest: Next 16.3.4, React 19.2.8, Tailwind v4, TS 7
- Dossier theme (trust blue + ink, verdict colors only saturated meaning)
- Pages: marketing hero with specimen card, analyze dropzone + progress,
  SSR report with verdict masthead, dashboard empty state, WhatsApp showcase
- WhatsApp `format_verdict()` + 3 tests; reply = verdict + reason + link
- `npm run build` green (6 routes, report SSR); backend 5 passed


- Python MUST run inside `backend/.venv` (AGENTS.md rule); system pip banned
- Backend skeleton tests pass (2 passed: health, analysis status)
- Frontend Next.js skeleton installed (`npm install` clean)
- Repo scaffold: AGENTS.md (Pi-native), planning.md, docker-compose.yml
- Backend FastAPI skeleton boots (health, v1 stubs, SQLite fallback)
- `.gitignore` + `.env.example` files (backend, frontend)
- Codebase skills: detector-module, commit-conventions, fastapi-feature,
  nextjs-report-page, whatsapp-webhook

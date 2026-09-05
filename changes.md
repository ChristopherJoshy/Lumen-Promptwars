# changes.md — Lumen changelog (maintained every commit)

Format: `## <date> — <scope>` + bullets. Newest first. One line per change.

## 2026-09-05 — foundation

- Python MUST run inside `backend/.venv` (AGENTS.md rule); system pip banned
- Backend skeleton tests pass (2 passed: health, analysis status)
- Frontend Next.js skeleton installed (`npm install` clean)
- Repo scaffold: AGENTS.md (Pi-native), planning.md, docker-compose.yml
- Backend FastAPI skeleton boots (health, v1 stubs, SQLite fallback)
- `.gitignore` + `.env.example` files (backend, frontend)
- Codebase skills: detector-module, commit-conventions, fastapi-feature,
  nextjs-report-page, whatsapp-webhook

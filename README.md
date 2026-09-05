# Lumen

Check suspicious media (image, audio, video, link, WhatsApp forward) for
signs of AI generation or manipulation. Indic-languages-first, WhatsApp as a
first-class intake, Indian fact-checkers first.

Live: frontend https://lumen-promptwars.vercel.app ·
API https://lumen-promptwars.onrender.com (`/health`, `/api/v1/...`).

## Quickstart (no Docker)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open http://localhost:3000 (web) and http://localhost:8000/health (api).

## How detection works (agentic-v1)

Six roles, one pipeline (`backend/app/features/analysis/agents/`): visual
forensics, voice forensics (Malayalam/Hindi/Tamil/Telugu first-class),
metadata reader, Exa + DDGS web evidence (India hits labeled), temporal
integrity, and a fusion judge. Per-call budgets: ≤6 low-detail frames, 2000
output tokens (judge 4096 — reasoning eats the headroom), Exa 5 highlights +
DDG 5 per query. Supported links: YouTube, Instagram, TikTok, X, Facebook,
Telegram, generic. WhatsApp parity: image/video/voice-note/link forwards ride
the identical pipeline
with `source="whatsapp"` (16 MB cap → "use web upload instead"; web cap 25
MB; audio 12 MB / 180 s; video 120 s). Unresolved extractions (e.g.
Instagram/X datacenter blocks) never verify — they cap at
`insufficient_evidence` with the platform named. Lumen is a probabilistic
aid, not proof; Zen 429/5xx retries once, quota failures surface loudly,
DDG flakiness degrades to Exa-only and is recorded in `warnings`.

## Prod-like stack

```bash
cp backend/.env.example backend/.env
docker compose up
```

## Layout

`backend/app/features/*` (one folder per domain), `frontend/app/*`,
`skills/*` (codebase checklists), `AGENTS.md` (agent instructions),
`planning.md` (build order), `changes.md` (changelog).

## Known limitations

- Submissions run inline (no queue yet): typical image ~30 s; large videos
  may exceed the 60 s free-tier request cap — use short clips for now.
- Instagram/X extraction reliability depends on datacenter blocks; failures
  return a clear "upload directly instead" error, never a silent hang.
- WhatsApp runs against Twilio's sandbox number: each tester must send the
  one-time join code before messaging it.

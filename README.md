# Lumen

Check suspicious media (image, audio, video, link, WhatsApp forward) for
signs of AI generation or manipulation. Indic-languages-first, WhatsApp as a
first-class intake, Indian fact-checkers first.

## Quickstart (no Docker)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open http://localhost:3000 (web) and http://localhost:8000/health (api).

## Prod-like stack

```bash
cp backend/.env.example backend/.env
docker compose up
```

## Layout

`backend/app/features/*` (one folder per domain), `frontend/app/*`,
`skills/*` (codebase checklists), `AGENTS.md` (agent instructions),
`planning.md` (build order), `changes.md` (changelog).

## Known limitations (v1 skeleton)

- Detectors not yet implemented (audio first, checkpoint 5); pipeline stubs
  raise `NotImplementedError` loudly rather than faking verdicts.
- Instagram/X extraction reliability depends on datacenter blocks; failures
  return a clear "upload directly instead" error, never a silent hang.
- WhatsApp runs against Twilio's sandbox number: each tester must send the
  one-time join code before messaging it.
- Video detector is a stretch goal; maturity will lag audio/image.

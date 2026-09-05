# changes.md — Lumen changelog (maintained every commit)

Format: `## <date> — <scope>` + bullets. Newest first. One line per change.

## 2026-09-05 — readme showcase overhaul

- README rewritten as detailed showcase: badges, live frontend/API links,
- mermaid architecture, agent table, API reference, WhatsApp setup, deploy map

## 2026-09-05 — forensic graph, voice, scan-lab UI, instant cache, usage

- Local numeric forensics (`agents/forensics.py`: ELA/DCT/noise/copy-move,
  sha-keyed heatmaps in `storage/forensics/`); visual agent weighs instruments
- LangGraph cases (`agents/graph.py`: fetch→perceive→retrieve→adjudicate,
  AsyncSqliteSaver per-content threads; pipeline `analyze_*` are wrappers)
- Sarvam voice across 22 Indian languages (auto-detect `unknown`, translate
  mode, transcript ground truth); non-WAV transcoded to 16 kHz mono for Zen
- Knowledge packs + skills (ai-image/morph/forward tells) feed system prompts;
  judge applies a score-fusion table; audio prompt covers code-mixing
- Report API (`/analysis/report/{id}`, `/signals`, `/forensics/{name}`,
  `/usage`); hex-key validation, allowlisted heatmap streaming
- Scan-lab frontend: probability dial + bands, reason cards, source chips,
  voice transcripts, heatmap gallery, scanline intake; report stays server-side
- Instant repeats: dHash near-dup (Hamming ≤ 8), transcript match for voice,
  tracker-stripped link keys; MongoDB usage ledger (best-effort, local-off)
- Deploy: `frontend/vercel.json` (Root Directory `frontend/`), `render.yaml`
  backend blueprint; live verified: photo verified 0.86, Hindi clip 0.85
- Suite at 36 passed; `tsc` + `next build` green (6 routes)
- Prod live: Vercel serves the scan-lab (root workspace build), Render CORS
  allows the Vercel origin, `/usage` reads Atlas; ingestion submit routes
  remain skeleton (report APIs serve cache only)
## 2026-09-05 — agentic verdict pipeline

- Muse Spark 1.3 multiagent pipeline live (`agents/`: muse_client, visual,
  audio Indic-first, meta, searcher Exa+DDGS, temporal, links, judge, pipeline
  `agentic-v1` with disk cache, temporal override, unresolved-link cap)
- Detectors delegate (image/video/audio → pipeline, JSON artifact evidence);
  WhatsApp inbound matrix (image/video/voice-note/link/help) + format_failure
- Deps: pillow, ddgs, imageio-ffmpeg, yt-dlp; platform matrix 7-way; 23
  backend tests green (parser tolerance, india hits, override, caps, routing)
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

## 2026-09-05 — accuracy + hardening + debate display

- Six pixel instruments (ghost + blockiness join ELA/DCT/noise/copy-move)
- SynthID/origin scan (C2PA, PNG parameters, EXIF generator tags) wired to visual/judge/signals
- Audio forensics (clip ratio, silence gaps, dynamic range) in voice verdicts
- Debate critic (single round, judge last word, dissent on report) + temperature 0 + reasoning low
- Ask-the-agent Q&A grounded in case signals; staged scan status with elapsed time
- Raw-byte uploads (multipart removed after prod 500), magic-byte sniff gate, 20/min rate limit, security headers, link SSRF guard
- No-mocks rule in AGENTS.md; suite at 70 passed

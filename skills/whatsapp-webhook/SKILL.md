# WhatsApp webhook skill

Checklist for anything touching `backend/app/features/whatsapp_bot/`.

## Handler contract (`router.py`)

1. Parse Twilio form fields (`From`, `Body`, `NumMedia`, `MediaUrl0`).
2. Validate `X-Twilio-Signature` against the auth token — never trust the
   payload unvalidated.
3. Enqueue the Taskiq job immediately; return minimal TwiML fast.
4. No download/analysis inline (Twilio expects a fast response).

## Media + tasks

- `media.py`: Basic-Auth download of `MediaUrl0`; feeds the **same** analysis
  pipeline as direct upload (no forked detection path). Over 16 MB → reply
  "use web upload instead", never silent failure.
- `tasks.py`: reply via `client.py` — traffic-light label + one plain-language
  sentence + `/report/[id]` link. Detail lives on the web, not in chat.
- Treat forwards as user-submitted content: same transient-retention rule as
  uploads/links.

## Risk review (before done)

SSRF on `MediaUrl0`, unbounded download size, signature bypass, reply
spoofing — re-read the handler for all four before yielding.

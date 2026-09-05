# Next.js report page skill

Checklist for report-facing frontend work (`frontend/app/report/[id]/`).

## Rules

- `page.tsx` stays a **server component** (SSR for social link previews) —
  no `"use client"` on the page itself; interactive pieces go in
  `features/report/components/` as client components.
- Data loads via `features/report/api.ts`; shared fetch/WS helpers live in
  `lib/` (`api-client.ts`, `websocket.ts`); no domain logic in
  `components/ui/` (shadcn primitives only).
- TypeScript strict; no `any` without an inline justification comment.
- Shows: traffic-light verdict, plain-language explanation, evidence panel,
  context timeline (fact-checker hits distinct from generic matches),
  temporal banner only when flagged, probabilistic-aid disclaimer.
- Verify with `npm run lint && npx tsc --noEmit`, then view the page in the
  running dev server before yielding.

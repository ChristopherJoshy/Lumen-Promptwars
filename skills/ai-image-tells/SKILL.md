# AI-image-tells skill

Checklist for judging possibly AI-generated images (diffusion-era).
Source pack: `backend/app/features/analysis/agents/knowledge/ai_image_tells.md`.

## Checklist (run before scoring)

1. Hands/limbs: count fingers, check finger-object fusion, joint plausibility.
2. Text/logos: read every rendered word closely; flag pseudo-script, swaps.
3. Faces: skin-vs-hair detail mismatch, earrings/glasses asymmetry, pupils.
4. Light/geometry: shadow directions, reflections, repeated textures.
5. Instruments first: ELA/DCT/noise/copy-move scores outrank eyeballing —
   uniform error response suggests fully synthetic; hot regions mean splice.
6. Corroborate: one cue is weak; name at least two independent cues before
   artifact_score > 0.5. Never verdict on style ("too perfect") alone.

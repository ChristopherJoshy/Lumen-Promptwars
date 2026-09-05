# Morph-tells skill

Checklist for single-image face-morphing detection (portraits, ID photos,
politician headshots, viral "arrest" images).
Source pack: `backend/app/features/analysis/agents/knowledge/morph_tells.md`.

## Checklist (run before scoring)

1. Boundaries: ghost contours on jawline/hairline/ears; noise mismatch
   between face and neck/hair regions.
2. Geometry: inter-eye vs nose-mouth proportions; face-outline vs eye-line
   agreement; ear symmetry.
3. Eyes/teeth: pupil roundness, matching catchlights, tooth merging.
4. Texture: flat-vs-noisy skin patches (cheeks vs forehead); pore gaps.
5. Corroboration: two independent cues (boundary + geometry, or eyes +
   texture) required before artifact_score > 0.5.
6. ID-style portraits with clean backgrounds get extra geometry scrutiny.

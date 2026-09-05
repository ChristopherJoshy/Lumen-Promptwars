# Face-morph tells (single-image morphing attack detection)

Distilled from S-MAD research (Laplacian-residual and geometry methods).
Applies to portraits: ID photos, politician headshots, viral "arrest" images.

## Blending boundaries

- Ghost contours along jawline, hairline, ear edges (double-edge halos).
- High-frequency noise mismatch: face region smoother/grainier than neck/hair.
- Laplacian-residual spikes at nostrils, lip corners, eyelid folds.

## Geometry inconsistencies

- Inter-eye distance vs nose-mouth proportions outside normal range.
- Face outline vs eye line disagree (landmark groups contradict each other).
- Ears asymmetric in shape/position beyond natural variation.

## Eyes and teeth (high-signal)

- Pupils non-circular; corneal reflections differ left vs right eye.
- Iris texture flat or hyper-detailed relative to skin.
- Teeth: uniform Chiclet rows, merged molars, lip-teeth boundary smear.

## Skin texture

- Entropy heatmap flat on cheeks but noisy on forehead (or vice versa).
- Pores vanish in patches while stubble/beard stays sharp nearby.
- Makeup-like airbrushing localized to central face only.

## Corroboration rule

- One morph cue alone is weak; two independent cues (boundary + geometry,
  or eyes + texture) are required before raising artifact_score above 0.5.
- ID-style portraits with clean backgrounds deserve extra geometry scrutiny.

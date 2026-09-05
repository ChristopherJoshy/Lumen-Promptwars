import type { Verdict } from "@/types";

/** Single source for verdict copy + color so every surface agrees. */
export const VERDICTS: Record<
  Verdict,
  { label: string; headline: string; dot: string; ring: string; wash: string }
> = {
  verified: {
    label: "Verified",
    headline: "No signs of AI generation or manipulation found",
    dot: "bg-verified",
    ring: "ring-verified/30",
    wash: "bg-verified/10",
  },
  contradiction_detected: {
    label: "Contradiction detected",
    headline: "The file claims to be untouched, but the pixels disagree",
    dot: "bg-contradiction",
    ring: "ring-contradiction/30",
    wash: "bg-contradiction/10",
  },
  likely_synthetic: {
    label: "Likely synthetic",
    headline: "Multiple signals point to AI generation or manipulation",
    dot: "bg-synthetic",
    ring: "ring-synthetic/30",
    wash: "bg-synthetic/10",
  },
  insufficient_evidence: {
    label: "Insufficient evidence",
    headline: "No clear signal either way — treat with caution",
    dot: "bg-ink-soft",
    ring: "ring-ink-soft/30",
    wash: "bg-ink-soft/10",
  },
};

/** Fused manipulation-probability bands: single source of truth for meters. */
export const SCORE_BANDS = [
  { max: 0.3, key: "low", word: "Low", blurb: "reads like an ordinary capture" },
  { max: 0.55, key: "unclear", word: "Unclear", blurb: "mixed signals, no winner" },
  { max: 0.7, key: "elevated", word: "Elevated", blurb: "several signs agree" },
  { max: 1.01, key: "high", word: "High", blurb: "strong manipulation signs" },
] as const;

export function bandForScore(score: number): (typeof SCORE_BANDS)[number] {
  return SCORE_BANDS.find((b) => score < b.max) ?? SCORE_BANDS[0];
}

/** One-line mechanism gloss per local instrument (plain verbs, jargon last). */
export const TOOL_LABELS: Record<string, { name: string; gloss: string; mechanism: string }> = {
  ela: {
    name: "ELA",
    gloss: "recompression glow check",
    mechanism:
      "Re-saves the image and amplifies the difference: regions compressed differently from the rest glow brighter.",
  },
  dct: {
    name: "DCT grid",
    gloss: "block-pattern check",
    mechanism:
      "Measures JPEG block-energy variance: spliced regions break the camera's uniform block rhythm.",
  },
  noise: {
    name: "Noise grain",
    gloss: "grain-mismatch check",
    mechanism:
      "Compares sensor grain across regions: pasted content carries a different grain signature.",
  },
  copymove: {
    name: "Copy-move",
    gloss: "clone-region check",
    mechanism: "Hunts duplicated pixel blocks: cloned areas stamped twice inside one frame.",
  },
  ghost: {
    name: "Ghost",
    gloss: "double-compression check",
    mechanism: "Re-saves at several qualities: spliced regions bottom out at a different quality than the background.",
  },
  blockiness: {
    name: "Blockiness",
    gloss: "grid-alignment check",
    mechanism: "Checks JPEG grid edges: pasted content breaks the camera's 8-pixel block rhythm.",
  },
  spectrum: {
    name: "Spectrum",
    gloss: "frequency-fingerprint check",
    mechanism: "Reads the image's frequency fingerprint: generators leave sharp high-frequency peaks that cameras don't.",
  },
};

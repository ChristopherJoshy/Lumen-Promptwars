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

import { bandForScore } from "@/lib/verdict";
import type { Verdict } from "@/types";

const CIRCLE = 2 * Math.PI * 54;

/** Fused manipulation-probability readout: dial + banded meter + caption. */
export function ScoreLedger({
  fusedMean,
  verdict,
}: {
  fusedMean: number | null;
  verdict: Verdict;
}) {
  if (fusedMean == null || Number.isNaN(fusedMean)) {
    return (
      <section aria-label="Manipulation score" className="rounded-3xl border border-gridline bg-console p-6 sm:p-8">
        <p className="font-mono text-5xl text-fog">—</p>
        <p className="mt-2 text-sm text-fog">
          No instrument score for this case — verdict rests on context only.
        </p>
      </section>
    );
  }
  const band = bandForScore(fusedMean);
  const conflict = fusedMean >= 0.7 && verdict !== "likely_synthetic";
  return (
    <section aria-label="Manipulation score" className="rounded-3xl border border-gridline bg-console p-6 sm:p-8">
      <div className="flex flex-wrap items-center gap-6">
        <div
          role="meter"
          aria-valuemin={0}
          aria-valuemax={1}
          aria-valuenow={Number(fusedMean.toFixed(2))}
          aria-label={`Fused manipulation probability ${fusedMean.toFixed(2)}, band ${band.word}`}
          className="relative size-32 shrink-0"
        >
          <svg viewBox="0 0 120 120" className="size-32 -rotate-90" aria-hidden>
            <circle cx="60" cy="60" r="54" fill="none" strokeWidth="10" className="stroke-gridline" />
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={CIRCLE.toFixed(1)}
              strokeDashoffset={(CIRCLE * (1 - Math.min(1, Math.max(0, fusedMean)))).toFixed(1)}
              className="lab-dial-ring stroke-scan"
            />
          </svg>
          <p className="absolute inset-0 flex items-center justify-center font-mono text-2xl text-foam tabular-nums">
            {fusedMean.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="font-lab text-sm font-semibold tracking-widest text-fog uppercase">
            Manipulation probability · {band.word}
          </p>
          <p className="mt-1 text-sm text-fog">{band.blurb}.</p>
          <p className="mt-3 text-xs leading-relaxed text-fog">
            Fused from 6 local instruments (ELA, DCT, noise, copy-move, ghost, blockiness). Higher means more
            likely synthetic or spliced. The judge&apos;s verdict below wins over this number —
            the score alone never decides.
          </p>
        </div>
      </div>
      <div className="mt-6" aria-hidden>
        <div className="flex h-3 overflow-hidden rounded-full">
          <div className="w-[30%] bg-lab-verified/40" />
          <div className="lab-hatch w-[25%] bg-fog/30 text-fog/60" />
          <div className="lab-hatch w-[15%] bg-lab-contradiction/40 text-lab-contradiction/70" />
          <div className="w-[30%] bg-lab-synthetic/50" />
        </div>
        <div className="relative mt-1 h-4 font-mono text-[11px] text-fog">
          <span className="absolute left-0">0</span>
          <span className="absolute left-[30%] -translate-x-1/2">0.30</span>
          <span className="absolute left-[55%] -translate-x-1/2">0.55</span>
          <span className="absolute left-[70%] -translate-x-1/2 text-fuse-hi">0.70</span>
          <span className="absolute right-0">1.0</span>
          <span
            className="absolute top-0 size-2 -translate-x-1/2 rounded-full bg-foam"
            style={{ left: `${Math.min(100, Math.max(0, fusedMean * 100))}%` }}
          />
        </div>
      </div>
      {conflict && (
        <p className="mt-4 rounded-2xl border border-fuse-hi/50 bg-fuse-hi/10 p-4 text-sm leading-relaxed text-foam">
          Instruments read high ({fusedMean.toFixed(2)}) but perceptual and context checks
          disagree — verdict set to{" "}
          {verdict === "insufficient_evidence" ? "Insufficient evidence" : verdict}. See the
          reasons below.
        </p>
      )}
    </section>
  );
}

import { TOOL_LABELS } from "@/lib/verdict";
import type { CaseSignals } from "./api";
import { DebateNote, type DebateInfo } from "./debate-note";

export interface ProvenanceInfo {
  generator?: string | null;
  c2pa?: boolean;
  markers?: string[];
}
const TOOL_ORDER = ["ela", "dct", "noise", "copymove"] as const;

/** Plain-language reasons: instrument rows first, then the judge's own words. */
export function WhyLedger({
  reasons,
  signals,
  debate,
  provenance,
}: {
  reasons: string[];
  signals?: CaseSignals;
  debate?: DebateInfo;
  provenance?: ProvenanceInfo;
}) {
  const scores = signals?.forensics?.scores;
  const perceptual = signals?.perceptual;
  return (
    <section aria-label="Why this verdict" className="mt-8">
      <h2 className="font-lab text-xl font-semibold tracking-tight text-foam">
        Why this verdict
      </h2>
      {scores && (
        <ol className="mt-4 space-y-3">
          {TOOL_ORDER.map((key, i) => {
            const tool = TOOL_LABELS[key];
            const score = scores[key];
            return (
              <li key={key}>
                <details
                  open={i === 0}
                  className="group rounded-2xl border border-gridline bg-console px-5 py-4"
                >
                  <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                    <span className="font-mono text-xs tracking-widest text-fog uppercase">
                      Forensic · {tool.name}
                      {typeof score === "number" ? ` ${score.toFixed(2)}` : ""}
                    </span>
                    <span className="mt-1 block font-semibold text-foam">{tool.gloss}</span>
                  </summary>
                  <p className="mt-2 text-sm leading-relaxed text-fog">{tool.mechanism}</p>
                  {typeof score === "number" && (
                    <div
                      role="meter"
                      aria-valuemin={0}
                      aria-valuemax={1}
                      aria-valuenow={Number(score.toFixed(2))}
                      aria-label={`${tool.name} score ${score.toFixed(2)}`}
                      className="mt-3 h-2 overflow-hidden rounded-full bg-gridline"
                    >
                      <div
                        className="lab-bar-fill lab-fused-gradient h-full rounded-full"
                        style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }}
                      />
                    </div>
                  )}
                </details>
              </li>
            );
          })}
        </ol>
      )}
      {perceptual?.artifact_score != null && (
        <p className="mt-4 text-sm leading-relaxed text-fog">
          Trained-eye read: artifact score {Number(perceptual.artifact_score).toFixed(2)}
          {(perceptual.observations?.length ?? 0) > 0 &&
            ` — ${perceptual.observations?.[0]}`}
        </p>
      )}
      <DebateNote debate={debate} />
      {(provenance?.generator || provenance?.c2pa) && (
        <p className="mt-4 text-sm leading-relaxed text-fog">
          {provenance.generator ? `Origin tag: ${provenance.generator}` : ""}
          {provenance.generator && provenance.c2pa ? " · " : ""}
          {provenance.c2pa ? "C2PA manifest present" : ""}
        </p>
      )}
      <div className="mt-4 space-y-3">
        {reasons.map((reason, i) => (
          <details
            key={i}
            className="rounded-2xl border border-gridline bg-console px-5 py-4"
          >
            <summary className="cursor-pointer list-none font-semibold text-foam [&::-webkit-details-marker]:hidden">
              <span className="mr-2 font-mono text-xs text-scan">R{i + 1}</span>
              {reason.length > 140 ? `${reason.slice(0, 140)}…` : reason}
            </summary>
            {reason.length > 140 && (
              <p className="mt-2 text-sm leading-relaxed text-fog">{reason}</p>
            )}
          </details>
        ))}
        {reasons.length === 0 && (
          <p className="text-sm text-fog">No written reasons recorded for this case.</p>
        )}
      </div>
    </section>
  );
}

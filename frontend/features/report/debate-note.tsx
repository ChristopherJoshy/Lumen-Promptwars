/** Independent-critic note: quiet line when uncontested, card on dissent. */

export interface DebateInfo {
  agreed?: boolean | null;
  counter_reasons?: string[];
  suggested_verdict?: string;
  note?: string;
}

export function DebateNote({ debate }: { debate?: DebateInfo }) {
  if (!debate) return null;
  if (debate.agreed === true) {
    return (
      <p className="mt-4 text-sm text-fog">
        An independent critic reviewed this verdict uncontested.
      </p>
    );
  }
  if (debate.agreed === false) {
    const reasons = debate.counter_reasons ?? [];
    const suggested = (debate.suggested_verdict || "unknown").replace(/_/g, " ");
    return (
      <div className="mt-4 rounded-2xl border border-gridline bg-console px-5 py-4">
        <p className="font-semibold text-foam">
          One analyst dissented{" "}
          <span className="font-normal text-fog">(suggested: {suggested})</span>
        </p>
        {reasons.length > 0 && (
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-fog">
            {reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  if (debate.note) {
    return <p className="mt-4 text-sm text-fog">{debate.note}</p>;
  }
  return null;
}

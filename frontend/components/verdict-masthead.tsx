import { VERDICTS } from "@/lib/verdict";
import { cn } from "@/lib/utils";
import type { Verdict } from "@/types";

/** Full-width verdict masthead: the one bold moment on report surfaces. */
export function VerdictMasthead({
  verdict,
  caseId,
  explanation,
}: {
  verdict: Verdict;
  caseId: string;
  explanation: string;
}) {
  const v = VERDICTS[verdict];
  return (
    <section aria-label="Verdict" className={cn("rounded-3xl p-8 ring-8 sm:p-10", v.wash, v.ring)}>
      <div className="flex items-center gap-3">
        <span aria-hidden className={cn("size-4 rounded-full", v.dot)} />
        <p className="text-lg font-bold">{v.label}</p>
      </div>
      <p className="mt-3 max-w-2xl font-display text-3xl italic leading-snug sm:text-4xl">
        {v.headline}
      </p>
      {explanation && <p className="mt-4 max-w-2xl leading-relaxed">{explanation}</p>}
      <p className="mt-6 font-mono text-xs text-ink-soft">case {caseId}</p>
    </section>
  );
}

import { AlertTriangle, BadgeCheck, FlaskConical, HelpCircle } from "lucide-react";
import { VERDICTS } from "@/lib/verdict";
import { cn } from "@/lib/utils";
import type { Verdict } from "@/types";

const ICONS = {
  verified: BadgeCheck,
  contradiction_detected: AlertTriangle,
  likely_synthetic: FlaskConical,
  insufficient_evidence: HelpCircle,
} as const;

const LAB_TEXT = {
  verified: "text-lab-verified",
  contradiction_detected: "text-lab-contradiction",
  likely_synthetic: "text-lab-synthetic",
  insufficient_evidence: "text-fog",
} as const;

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
  const Icon = ICONS[verdict];
  return (
    <section
      aria-label="Verdict"
      className="rounded-3xl border border-gridline bg-console-2 p-8 shadow-[0_0_64px_-18px_var(--color-scan)] sm:p-10"
    >
      <div className="flex items-center gap-3">
        <span aria-hidden className={cn("size-4 rounded-full", v.dot, "shadow-[0_0_12px_2px_currentColor]", LAB_TEXT[verdict])} />
        <Icon aria-hidden className={cn("size-5", LAB_TEXT[verdict])} />
        <p className="font-lab text-lg font-bold tracking-wide">{v.label}</p>
      </div>
      <p className="mt-3 max-w-2xl font-lab text-3xl font-semibold leading-snug tracking-tight text-foam sm:text-4xl">
        {v.headline}
      </p>
      {explanation && <p className="mt-4 max-w-2xl leading-relaxed text-fog">{explanation}</p>}
      <p className="mt-6 font-mono text-xs text-fog">case {caseId}</p>
    </section>
  );
}

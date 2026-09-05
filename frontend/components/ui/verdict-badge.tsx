import { VERDICTS } from "@/lib/verdict";
import { cn } from "@/lib/utils";
import type { Verdict } from "@/types";

/** Traffic-light verdict marker: dot + label, color always paired with text. */
export function VerdictBadge({ verdict, className }: { verdict: Verdict; className?: string }) {
  const v = VERDICTS[verdict];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full py-1 pl-3 pr-4 text-sm font-semibold ring-4",
        v.wash,
        v.ring,
        className,
      )}
    >
      <span aria-hidden className={cn("size-2.5 rounded-full", v.dot)} />
      {v.label}
    </span>
  );
}

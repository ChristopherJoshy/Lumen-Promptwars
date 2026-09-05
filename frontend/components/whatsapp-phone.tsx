import { CheckCheck } from "lucide-react";

/** Stylized WhatsApp verdict reply: shows the bot's message design. */
export function WhatsAppPhone({ lines }: { lines: string[] }) {
  return (
    <div
      aria-label="WhatsApp verdict preview"
      className="w-full max-w-xs rounded-[2rem] border border-line bg-white p-3 shadow-[0_24px_60px_-24px_rgba(12,74,110,0.35)]"
    >
      <div className="rounded-[1.6rem] bg-paper p-3">
        <div className="mb-2 flex items-center gap-2 border-b border-line pb-2">
          <span className="grid size-8 place-items-center rounded-full bg-verified font-bold text-white">
            L
          </span>
          <div>
            <p className="text-sm font-semibold leading-none">Lumen Verdicts</p>
            <p className="mt-1 flex items-center gap-1 text-xs text-verified">
              online <CheckCheck className="size-3.5" aria-hidden />
            </p>
          </div>
        </div>
        <div className="space-y-2 text-[13px] leading-relaxed">
          {lines.map((line, i) => (
            <p
              key={i}
              className={
                i === 0
                  ? "rounded-lg rounded-tl-none bg-white p-2 shadow-sm"
                  : "rounded-lg rounded-tl-none bg-white p-2 text-ink-soft shadow-sm"
              }
            >
              {line}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}

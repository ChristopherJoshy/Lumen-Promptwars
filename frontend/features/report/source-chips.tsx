import { ExternalLink } from "lucide-react";
import type { CaseSignals } from "./api";

type Hit = { title?: string; url?: string; snippet?: string };

/** Source-traceable context: India fact-checkers first, real outbound links. */
export function SourceChips({ search }: { search?: CaseSignals["search"] }) {
  const seen = new Set<string>();
  const hits: Hit[] = [];
  for (const hit of [...(search?.india_hits ?? []), ...(search?.exa_hits ?? []), ...(search?.ddg_hits ?? [])]) {
    const url = hit?.url ?? "";
    if (!url || seen.has(url)) continue;
    seen.add(url);
    hits.push(hit);
    if (hits.length >= 8) break;
  }
  return (
    <section aria-label="Sources and context" className="mt-8">
      <h2 className="font-lab text-xl font-semibold tracking-tight text-foam">
        Sources &amp; context
      </h2>
      {hits.length === 0 ? (
        <p className="mt-3 text-sm leading-relaxed text-fog">
          No external context found. This verdict rests on pixels and audio only.
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {hits.map((hit) => (
            <li key={hit.url}>
              <a
                href={hit.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Source: ${hit.title || hit.url} (opens in new tab)`}
                className="flex items-center gap-2 rounded-2xl border border-gridline bg-console px-4 py-3 text-sm text-foam transition-colors duration-150 hover:border-scan"
              >
                <ExternalLink className="size-4 shrink-0 text-scan" aria-hidden />
                <span className="truncate">{hit.title || hit.url}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

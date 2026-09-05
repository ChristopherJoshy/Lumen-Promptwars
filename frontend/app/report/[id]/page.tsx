import Link from "next/link";
import { FileDown } from "lucide-react";
import { VerdictBadge } from "@/components/ui/verdict-badge";
import { VerdictMasthead } from "@/components/verdict-masthead";
import { getReport, getSignals } from "@/features/report/api";

// Server component: SSR so shared links render proper preview cards.
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = await getReport(id);
  return {
    title: `Verdict: ${report.verdict}`,
    description: report.explanation || "Lumen media-verification report.",
    openGraph: { title: `Lumen verdict: ${report.verdict}`, description: report.explanation },
  };
}

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = await getReport(id);
  const signals = await getSignals(id);

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <VerdictMasthead verdict={report.verdict} caseId={report.case_id} explanation={report.explanation} />

      <section aria-label="Evidence" className="mt-10">
        <h2 className="text-2xl font-bold tracking-tight">Why this verdict</h2>
        <ul className="mt-4">
          {signals.map((s) => (
            <li key={s.name} className="grid gap-1 border-t border-line py-4 sm:grid-cols-[12rem_1fr] sm:gap-6">
              <span className="font-semibold">{s.name}</span>
              <span className="leading-relaxed text-ink-soft">{s.finding}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Export" className="mt-10 rounded-3xl border border-line bg-white p-6">
        <h2 className="text-xl font-bold">Need this taken down?</h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
          Export a timestamped, hash-signed dossier formatted for a takedown request under
          India&apos;s IT rules. It documents the analysis — it is not a legal certification.
        </p>
        <Link
          href={`/api/v1/reports/${report.case_id}/export`}
          className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-full border border-line px-6 text-sm font-semibold transition-colors duration-200 hover:border-primary hover:text-primary"
        >
          <FileDown className="size-4" aria-hidden />
          Export evidentiary report
        </Link>
      </section>

      <div className="mt-8">
        <VerdictBadge verdict={report.verdict} />
      </div>
    </main>
  );
}

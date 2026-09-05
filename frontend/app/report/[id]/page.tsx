import Link from "next/link";
import { notFound } from "next/navigation";
import { FileDown } from "lucide-react";
import { VerdictBadge } from "@/components/ui/verdict-badge";
import { VerdictMasthead } from "@/components/verdict-masthead";
import { getFullReport } from "@/features/report/api";
import { ScoreLedger } from "@/features/report/score-ledger";
import { WhyLedger } from "@/features/report/why-ledger";
import { SourceChips } from "@/features/report/source-chips";
import { VoiceBlock } from "@/features/report/voice-block";
import { AskAgent } from "@/features/report/ask-agent";
import { ForensicGallery } from "@/features/report/forensic-gallery";

// Server component: SSR so shared links render proper preview cards.
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = await getFullReport(id);
  return {
    title: `Verdict: ${report?.verdict ?? "unknown"}`,
    description: report?.explanation || "Lumen media-verification report.",
    openGraph: {
      title: `Lumen verdict: ${report?.verdict ?? "unknown"}`,
      description: report?.explanation,
    },
  };
}

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = await getFullReport(id);
  if (!report) notFound();

  const fusedMean = report.signals?.forensics?.scores?.fused_mean ?? null;
  const isAudio = report.signals?.modality === "audio";

  return (
    <div className="lab-surface bg-abyss text-foam">
      <main className="mx-auto max-w-3xl px-4 py-12">
        <VerdictMasthead verdict={report.verdict} caseId={report.case_id} explanation={report.explanation} />

        <div className="mt-6">
          <ScoreLedger fusedMean={fusedMean} verdict={report.verdict} />
        </div>

        <WhyLedger reasons={report.reasons ?? []} signals={report.signals} debate={report.signals?.debate} provenance={report.signals?.provenance} />

        {report.signals?.forensics && (
          <ForensicGallery caseId={report.case_id} scores={report.signals.forensics.scores} />
        )}

        {isAudio && <VoiceBlock sarvam={report.signals?.sarvam} audioTools={report.signals?.perceptual?.audio_tools} />}

        <AskAgent caseId={report.case_id} />

        <SourceChips search={report.signals?.search} />

        <section aria-label="Method and limits" className="mt-8 rounded-3xl border border-gridline bg-console p-6">
          <h2 className="font-lab text-xl font-semibold tracking-tight">Method &amp; limits</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-relaxed text-fog">
            <li>Seven local instruments score pixels; origin tags checked; a vision model reads content; web search traces context.</li>
            <li>Heatmaps highlight regions to inspect — they are not proof of fakery.</li>
            <li>This report is a probabilistic documentation aid, not a legal certification.</li>
          </ul>
          <p className="mt-3 font-mono text-xs text-fog">
            {report.model_version ?? "lumen"} · sha {report.evidence?.sha256?.slice(0, 12) ?? "—"}
            {report.cached ? " · served from cache" : ""}
            {report.duplicate_of ? ` · near-duplicate of ${report.duplicate_of.slice(0, 12)}` : ""}
          </p>
        </section>
        <section aria-label="Export" className="mt-8 rounded-3xl border border-gridline bg-console p-6">
          <h2 className="text-xl font-bold">Need this taken down?</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-fog">
            Export a timestamped, hash-signed dossier formatted for a takedown request under
            India&apos;s IT rules. It documents the analysis — it is not a legal certification.
          </p>
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/reports/${report.case_id}/export`}
            className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-full border border-gridline px-6 text-sm font-semibold transition-colors duration-200 hover:border-scan hover:text-scan"
          >
            <FileDown className="size-4" aria-hidden />
            Export evidentiary report
          </a>
        </section>

        <div className="mt-8">
          <VerdictBadge verdict={report.verdict} />
        </div>
      </main>
    </div>
  );
}

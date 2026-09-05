import { getReport } from "@/features/report/api";

// Server component: SSR so shared links render proper preview cards.
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = await getReport(id);
  return {
    title: `Lumen verdict: ${report.verdict}`,
    description: report.explanation,
    openGraph: { title: `Lumen verdict: ${report.verdict}`, description: report.explanation },
  };
}

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = await getReport(id);
  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", padding: "0 1rem" }}>
      <p style={{ fontSize: 12, color: "#666" }}>
        Probabilistic analysis aid, not legal or forensic proof.
      </p>
      <h1>{report.verdict}</h1>
      <p>{report.explanation}</p>
    </main>
  );
}

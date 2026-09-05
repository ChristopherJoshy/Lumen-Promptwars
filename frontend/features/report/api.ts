import { api } from "@/lib/api-client";
import type { Report } from "@/types";

export interface SignalFinding {
  name: string;
  finding: string;
}

export async function getReport(id: string): Promise<Report> {
  try {
    return await api<Report>(`/api/v1/analysis/report/${id}`);
  } catch {
    // Skeleton fallback until the fusion pipeline lands (checkpoint 4+).
    return { case_id: id, verdict: "insufficient_evidence", explanation: "" };
  }
}

export async function getSignals(id: string): Promise<SignalFinding[]> {
  try {
    return await api<SignalFinding[]>(`/api/v1/analysis/report/${id}/signals`);
  } catch {
    return [
      { name: "Forensic detection", finding: "Detector pipeline pending — no score yet." },
      { name: "Provenance", finding: "Not yet parsed for this case." },
      { name: "Context trace", finding: "Fact-check lookup not yet run." },
    ];
  }
}

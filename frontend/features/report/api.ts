import { api } from "@/lib/api-client";
import type { Report } from "@/types";

export async function getReport(id: string): Promise<Report> {
  try {
    return await api<Report>(`/api/v1/analysis/report/${id}`);
  } catch {
    // Skeleton fallback until the fusion pipeline lands (checkpoint 4+).
    return { case_id: id, verdict: "insufficient_evidence", explanation: "" };
  }
}

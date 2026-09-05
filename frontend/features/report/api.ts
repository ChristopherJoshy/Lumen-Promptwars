import { api } from "@/lib/api-client";
import type { Report, Verdict } from "@/types";

export interface SignalFinding {
  name: string;
  finding: string;
}

export async function getReport(id: string): Promise<Report> {
  const full = await getFullReport(id);
  if (!full) return { case_id: id, verdict: "insufficient_evidence", explanation: "" };
  return { case_id: full.case_id, verdict: full.verdict, explanation: full.explanation };
}

export async function getSignals(id: string): Promise<SignalFinding[]> {
  try {
    const res = await api<{ signals: SignalFinding[] }>(`/api/v1/analysis/report/${id}/signals`);
    return res.signals;
  } catch {
    return [
      { name: "Forensic detection", finding: "Detector pipeline pending — no score yet." },
      { name: "Provenance", finding: "Not yet parsed for this case." },
      { name: "Context trace", finding: "Fact-check lookup not yet run." },
    ];
  }
}
export interface ForensicsScores {
  ela?: number;
  dct?: number;
  noise?: number;
  copymove?: number;
  fused_mean?: number;
}

export interface CaseSignals {
  modality?: string;
  perceptual?: {
    artifact_score?: number;
    observations?: string[];
    caption?: string;
    ocr_text?: string;
    transcript_hint?: string;
    language_guess?: string;
    entities?: string[];
    frames?: number;
    audio_tools?: { clip_ratio?: number; silence_gaps?: number; dynamic_range_db?: number };
  };
  forensics?: {
    scores?: ForensicsScores;
    artifacts?: Record<string, string>;
    note?: string;
  };
  sarvam?: {
    result?: { transcript?: string; detected_language?: string; translated_en?: string };
    warning?: string | null;
  };
  search?: {
    exa_hits?: { title?: string; url?: string; snippet?: string }[];
    ddg_hits?: { title?: string; url?: string; snippet?: string }[];
    india_hits?: { title?: string; url?: string; snippet?: string }[];
    warnings?: string[];
  };
  temporal?: { flag?: boolean; note?: string };
  debate?: {
    agreed?: boolean | null;
    counter_reasons?: string[];
    suggested_verdict?: string;
    note?: string;
  };
  provenance?: { generator?: string | null; c2pa?: boolean; markers?: string[] };
}

export interface FullReport {
  case_id: string;
  verdict: Verdict;
  explanation: string;
  confidence?: number;
  reasons?: string[];
  signals?: CaseSignals;
  model_version?: string;
  evidence?: { sha256?: string; caption?: string };
  cached?: boolean | string;
  duplicate_of?: string;
}

export async function getFullReport(id: string): Promise<FullReport | null> {
  try {
    return await api<FullReport>(`/api/v1/analysis/report/${id}`);
  } catch {
    return null;
  }
}

export type Verdict =
  | "verified"
  | "contradiction_detected"
  | "likely_synthetic"
  | "insufficient_evidence";

export interface Report {
  case_id: string;
  verdict: Verdict;
  explanation: string;
}

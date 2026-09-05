// Per-job progress channel (checkpoint 4 wires the backend WebSocket).
export function progressSocket(jobId: string): WebSocket {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  return new WebSocket(`${base}/api/v1/analysis/progress/${jobId}`);
}

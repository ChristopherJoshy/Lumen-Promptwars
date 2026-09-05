"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { progressSocket } from "@/lib/websocket";

/** Subscribes to the per-job channel; motion answers the user's submission. */
export function ProgressStream({ jobId }: { jobId: string | null }) {
  const [stage, setStage] = useState<string | null>(null);
  const socket = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const ws = progressSocket(jobId);
    socket.current = ws;
    ws.onmessage = (e: MessageEvent<string>) => setStage(e.data);
    return () => ws.close();
  }, [jobId]);

  if (!jobId) return null;

  return (
    <div role="status" className="flex items-center gap-3 rounded-2xl border border-line bg-white p-4">
      <Loader2 className="size-5 animate-spin text-primary" aria-hidden />
      <p className="text-sm font-medium">{stage ?? "Queued — analysis starting…"}</p>
    </div>
  );
}

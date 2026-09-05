"use client";

import { useEffect, useState } from "react";

/** Report error boundary: retry when the backend is unreachable mid-read. */
export default function ReportError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const flip = () => setOnline(navigator.onLine);
    window.addEventListener("online", flip);
    window.addEventListener("offline", flip);
    return () => {
      window.removeEventListener("online", flip);
      window.removeEventListener("offline", flip);
    };
  }, []);
  return (
    <div className="lab-surface bg-abyss text-foam">
      <main className="mx-auto max-w-3xl px-4 py-12">
        <section
          role="alert"
          aria-label="Report failed to load"
          className="rounded-3xl border border-lab-synthetic/50 bg-console p-8"
        >
          <h1 className="font-lab text-2xl font-semibold">Couldn&apos;t load this report</h1>
          <p className="mt-2 text-sm leading-relaxed text-fog">
            {!online
              ? "You look offline — reconnect and retry."
              : "The analysis server didn't answer. Your case may have expired after a redeploy, or the network dropped."}
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-4 inline-flex min-h-11 items-center rounded-full bg-scan px-6 text-sm font-semibold text-abyss"
          >
            Try again
          </button>
          <p className="mt-3 font-mono text-xs text-fog">{error.message.slice(0, 160)}</p>
        </section>
      </main>
    </div>
  );
}

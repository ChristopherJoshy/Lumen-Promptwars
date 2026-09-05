"use client";

import { useState } from "react";
import { MessageCircleQuestion, SendHorizonal } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Ask-the-agent: grounded follow-up Q&A about this exact report. */
export function AskAgent({ caseId }: { caseId: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setError("");
    setAnswer("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/analysis/report/${caseId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q.slice(0, 500) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: unknown = await res.json();
      const text =
        data && typeof data === "object" && "answer" in data && typeof data.answer === "string"
          ? data.answer
          : "";
      if (!text) throw new Error("empty");
      setAnswer(text);
    } catch {
      setError("Couldn't get an answer — try again in a moment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Ask about this report" className="mt-8 rounded-3xl border border-gridline bg-console p-6">
      <h2 className="flex items-center gap-2 font-lab text-xl font-semibold tracking-tight text-foam">
        <MessageCircleQuestion className="size-5 text-scan" aria-hidden />
        Ask about this report
      </h2>
      <form onSubmit={(e) => void ask(e)} className="mt-3 flex flex-col gap-3 sm:flex-row">
        <label htmlFor="agent-question" className="sr-only">
          Your question about this verdict
        </label>
        <input
          id="agent-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Why didn't the clean instruments clear this image?"
          maxLength={500}
          disabled={busy}
          className="h-11 flex-1 rounded-full border border-gridline bg-abyss px-4 text-sm text-foam outline-none placeholder:text-fog/70 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="inline-flex min-h-11 items-center gap-2 rounded-full bg-scan px-5 text-sm font-semibold text-abyss transition-opacity duration-150 disabled:opacity-50"
        >
          <SendHorizonal className="size-4" aria-hidden />
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>
      {busy && (
        <p role="status" className="mt-3 text-sm text-scan">
          Reading the case file…
        </p>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-lab-synthetic">
          {error}
        </p>
      )}
      {answer && <p className="mt-3 text-sm leading-relaxed text-foam">{answer}</p>}
      <p className="mt-2 text-xs text-fog">
        Answers come only from this report — the agent says so when something isn&apos;t in it.
      </p>
    </section>
  );
}

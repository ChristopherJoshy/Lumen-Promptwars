"use client";

import { useState } from "react";
import { TOOL_LABELS } from "@/lib/verdict";
import type { ForensicsScores } from "./api";

const NAMES = ["ela", "dct", "noise", "copymove"] as const;
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Interactive heatmap gallery: native radios + opacity slider, CSS blend only. */
export function ForensicGallery({
  caseId,
  scores,
}: {
  caseId: string;
  scores?: ForensicsScores;
}) {
  const [mode, setMode] = useState<"heat" | "split">("heat");
  const [mix, setMix] = useState(85);
  return (
    <section aria-label="Forensic heatmaps" className="mt-8">
      <h2 className="font-lab text-xl font-semibold tracking-tight text-foam">
        Forensic heatmaps
      </h2>
      <fieldset className="mt-3 flex flex-wrap items-center gap-4 text-sm text-fog">
        <legend className="sr-only">Heatmap display mode</legend>
        {(["heat", "split"] as const).map((m) => (
          <label key={m} className="flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name="heatmap-mode"
              value={m}
              checked={mode === m}
              onChange={() => setMode(m)}
              className="size-4 accent-cyan-400"
            />
            {m === "heat" ? "Full heat" : "Split scan"}
          </label>
        ))}
        <label className="flex items-center gap-2">
          Glow
          <input
            type="range"
            min={20}
            max={100}
            value={mix}
            onChange={(e) => setMix(Number(e.target.value))}
            aria-label="Heatmap glow opacity"
            className="w-32 accent-cyan-400"
          />
        </label>
      </fieldset>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {NAMES.map((name) => {
          const tool = TOOL_LABELS[name];
          const score = scores?.[name];
          const src = `${API_BASE}/api/v1/analysis/report/${caseId}/forensics/${name}`;
          return (
            <figure
              key={name}
              className="relative overflow-hidden rounded-2xl border border-gridline bg-abyss"
            >
              <div aria-hidden className="lab-grid absolute inset-0 opacity-40" />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={src}
                alt={`${tool.name} heatmap (${tool.gloss})${typeof score === "number" ? `, score ${score.toFixed(2)}` : ""}`}
                loading="lazy"
                width={512}
                height={512}
                style={
                  mode === "split"
                    ? { clipPath: `inset(0 ${100 - mix}% 0 0)`, opacity: mix / 100 }
                    : { opacity: mix / 100, mixBlendMode: "screen" }
                }
                className="relative aspect-square w-full object-contain"
              />
              <div aria-hidden className="lab-scanbar pointer-events-none absolute left-0 h-20 w-full bg-gradient-to-b from-transparent via-scan/30 to-transparent" />
              <figcaption className="relative border-t border-gridline px-4 py-3">
                <span className="font-mono text-xs tracking-widest text-scan uppercase">
                  {tool.name}
                  {typeof score === "number" ? ` · ${score.toFixed(2)}` : ""}
                </span>
                <span className="mt-0.5 block text-xs text-fog">{tool.gloss}</span>
              </figcaption>
            </figure>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-fog">
        Analysis highlights, not proof of fakery — bright regions mark where to look, not
        what to conclude.
      </p>
    </section>
  );
}

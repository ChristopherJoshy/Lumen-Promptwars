"use client";

import { useState } from "react";
import { Link2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProgressStream } from "@/components/progress-stream";
import { submitLink, uploadFile } from "@/features/analysis/api";

export default function AnalyzePage() {
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  async function onFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    try {
      const res = await uploadFile(file);
      setJobId((res as { job_id?: string }).job_id ?? "local-preview");
      setNotice("");
    } catch {
      setNotice("Upload failed — check the file type and try again.");
    }
  }

  async function onLink(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    try {
      const res = await submitLink(url);
      setJobId((res as { job_id?: string }).job_id ?? "local-preview");
      setNotice("");
    } catch {
      setNotice(
        "Couldn't fetch this link automatically — try downloading the media and uploading it directly.",
      );
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-4xl font-bold tracking-tight">
        Check <span className="font-display font-normal italic">something suspicious.</span>
      </h1>
      <p className="mt-3 max-w-xl leading-relaxed text-ink-soft">
        Upload a file or paste a link. Large videos stay on your device until you confirm —
        nothing is stored beyond analysis plus a short cache.
      </p>

      <div className="mt-8 space-y-4">
        <label
          className="flex cursor-pointer flex-col items-center gap-2 rounded-3xl border-2 border-dashed border-line bg-white px-6 py-12 text-center transition-colors duration-200 hover:border-primary"
        >
          <UploadCloud className="size-8 text-primary" aria-hidden />
          <span className="font-semibold">Drop an image, voice note, or video here</span>
          <span className="text-sm text-ink-soft">jpg · png · webp · mp3 · wav · m4a · mp4 · mov · webm</span>
          <input
            type="file"
            className="sr-only"
            accept="image/*,audio/*,video/*"
            onChange={(e) => void onFiles(e.target.files)}
          />
        </label>

        <form
          onSubmit={(e) => void onLink(e)}
          className="flex flex-col gap-3 rounded-3xl border border-line bg-white p-4 sm:flex-row"
        >
          <label htmlFor="link-url" className="sr-only">
            Media link to check
          </label>
          <div className="flex flex-1 items-center gap-2 rounded-full border border-line px-4">
            <Link2 className="size-4 shrink-0 text-ink-soft" aria-hidden />
            <input
              id="link-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste a YouTube, Instagram, X, TikTok, or Facebook link"
              inputMode="url"
              className="h-11 w-full bg-transparent text-base outline-none placeholder:text-ink-soft/70"
            />
          </div>
          <Button type="submit">Check link</Button>
        </form>

        {notice && (
          <p role="alert" className="rounded-2xl bg-synthetic/10 p-4 text-sm font-medium text-synthetic">
            {notice}
          </p>
        )}

        <ProgressStream jobId={jobId} />
      </div>
    </main>
  );
}

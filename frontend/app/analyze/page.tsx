"use client";

import { useRef, useState } from "react";
import { Link2, ScanLine, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProgressStream } from "@/components/progress-stream";
import { submitLink, uploadFile } from "@/features/analysis/api";
import { cn } from "@/lib/utils";

const ACCEPT = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "audio/mpeg",
  "audio/wav",
  "audio/x-m4a",
  "audio/ogg",
  "audio/mp4",
  "video/mp4",
  "video/webm",
  "video/quicktime",
];
const MAX_MB = 25;

function validate(file: File): string | null {
  if (!ACCEPT.includes(file.type)) return `“${file.type || "unknown type"}” isn't analyzable — use jpg, png, webp, mp3, wav, m4a, mp4, mov, or webm.`;
  if (file.size > MAX_MB * 1024 * 1024)
    return `That file is ${(file.size / 1048576).toFixed(1)} MB — uploads cap at ${MAX_MB} MB.`;
  return null;
}

export default function AnalyzePage() {
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function submit(file: File) {
    const problem = validate(file);
    if (problem) {
      setNotice(problem);
      return;
    }
    setBusy(true);
    setNotice("");
    setFileName(file.name);
    try {
      const res = await uploadFile(file);
      setJobId((res as { job_id?: string }).job_id ?? "local-preview");
    } catch {
      setNotice("Upload failed — check the file type and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function onLink(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || busy) return;
    setBusy(true);
    setNotice("");
    setFileName(url.trim());
    try {
      const res = await submitLink(url);
      setJobId((res as { job_id?: string }).job_id ?? "local-preview");
    } catch {
      setNotice(
        "Couldn't fetch this link automatically — try downloading the media and uploading it directly.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="lab-surface bg-abyss text-foam">
      <main className="mx-auto max-w-3xl px-4 py-12">
        <p className="font-mono text-xs tracking-widest text-scan uppercase">Forensic intake</p>
        <h1 className="mt-2 font-lab text-4xl font-semibold tracking-tight">
          Check <span className="text-fog">something suspicious.</span>
        </h1>
        <p className="mt-3 max-w-xl leading-relaxed text-fog">
          Upload a file or paste a link. Nothing is stored beyond analysis plus a short cache.
        </p>

        <div className="mt-8 space-y-4">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const file = e.dataTransfer.files?.[0];
              if (file && !busy) void submit(file);
            }}
            className={cn(
              "relative flex cursor-pointer flex-col items-center gap-2 overflow-hidden rounded-3xl border-2 border-dashed px-6 py-12 text-center transition-colors duration-200",
              dragging ? "border-scan bg-console-2" : "border-gridline bg-console hover:border-scan",
              busy && "pointer-events-none opacity-70",
            )}
          >
            <span aria-hidden className="lab-grid absolute inset-0 opacity-30" />
            {busy ? (
              <span aria-hidden className="lab-scanbar absolute left-0 h-20 w-full bg-gradient-to-b from-transparent via-scan/40 to-transparent" />
            ) : null}
            <UploadCloud className="relative size-8 text-scan" aria-hidden />
            <span className="relative font-semibold">
              {dragging ? "Release to scan" : "Drop an image, voice note, or video here"}
            </span>
            <span className="relative text-sm text-fog">jpg · png · webp · mp3 · wav · m4a · mp4 · mov · webm · max 25 MB</span>
            <input
              ref={inputRef}
              type="file"
              className="sr-only"
              accept="image/*,audio/*,video/*"
              disabled={busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void submit(file);
                e.target.value = "";
              }}
            />
          </label>

          <form
            onSubmit={(e) => void onLink(e)}
            className="flex flex-col gap-3 rounded-3xl border border-gridline bg-console p-4 sm:flex-row"
          >
            <label htmlFor="link-url" className="sr-only">
              Media link to check
            </label>
            <div className="flex flex-1 items-center gap-2 rounded-full border border-gridline px-4">
              <Link2 className="size-4 shrink-0 text-fog" aria-hidden />
              <input
                id="link-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste a YouTube, Instagram, X, TikTok, or Facebook link"
                inputMode="url"
                disabled={busy}
                className="h-11 w-full bg-transparent text-base text-foam outline-none placeholder:text-fog/70"
              />
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Scanning…" : "Check link"}
            </Button>
          </form>

          {busy && (
            <p role="status" aria-busy="true" className="flex items-center gap-2 text-sm text-scan">
              <ScanLine className="size-4 animate-pulse" aria-hidden />
              Scanning {fileName || "your submission"} through four instruments plus context trace…
            </p>
          )}

          {notice && (
            <p role="alert" className="rounded-2xl border border-lab-synthetic/50 bg-lab-synthetic/10 p-4 text-sm font-medium text-foam">
              {notice}
            </p>
          )}

          <ProgressStream jobId={jobId} />
        </div>
      </main>
    </div>
  );
}

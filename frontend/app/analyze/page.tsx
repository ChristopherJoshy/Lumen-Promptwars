"use client";

import { useState } from "react";
import { submitLink, uploadFile } from "@/features/analysis/api";

export default function AnalyzePage() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<string>("");

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setResult(JSON.stringify(await uploadFile(file)));
  }

  async function onLink(e: React.FormEvent) {
    e.preventDefault();
    setResult(JSON.stringify(await submitLink(url)));
  }

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Analyze</h1>
      <input type="file" onChange={onUpload} />
      <form onSubmit={onLink} style={{ marginTop: "1rem" }}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a YouTube / Instagram / X / TikTok link"
          style={{ width: "70%" }}
        />
        <button type="submit">Check link</button>
      </form>
      {result && <pre>{result}</pre>}
    </main>
  );
}

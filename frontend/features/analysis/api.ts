import { api } from "@/lib/api-client";

export async function uploadFile(file: File): Promise<unknown> {
  const form = new FormData();
  form.append("file", file);
  return api("/api/v1/ingestion/upload", { method: "POST", body: form });
}

export async function submitLink(url: string): Promise<unknown> {
  return api("/api/v1/ingestion/link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

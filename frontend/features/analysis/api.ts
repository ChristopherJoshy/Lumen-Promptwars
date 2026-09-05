import { api } from "@/lib/api-client";

export async function uploadFile(file: File): Promise<unknown> {
  return api("/api/v1/ingestion/upload", {
    method: "POST",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
}

export async function submitLink(url: string): Promise<unknown> {
  return api("/api/v1/ingestion/link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

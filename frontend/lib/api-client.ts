const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail || `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  // Verdicts change on re-analysis: never serve a cached report page.
  const res = await fetch(`${base}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    let detail = "";
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        const raw = body.detail;
        detail = typeof raw === "string" ? raw : JSON.stringify(raw);
      }
    } catch {
      detail = "";
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

/** Human sentence for an upload/link failure (server detail wins). */
export function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 413) return "That file is over the 25 MB cap — try a shorter clip or smaller image.";
    if (err.status === 415) return "That file type isn't analyzable — use jpg, png, webp, mp3, wav, m4a, mp4, mov, or webm.";
    if (err.status === 429) return "Too many checks at once — wait a minute and try again.";
    if (err.detail) return err.detail;
  }
  return fallback;
}

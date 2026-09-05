const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  // Verdicts change on re-analysis: never serve a cached report page.
  const res = await fetch(`${base}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return (await res.json()) as T;
}

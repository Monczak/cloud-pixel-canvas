const DEFAULT_API = "http://localhost:8000";

export function getApiBase(): string {
  if (typeof window === "undefined") return DEFAULT_API;
  const envApi = (import.meta as any).env?.VITE_API_BASE;
  return envApi ? envApi.replace(/\/$/, "") : DEFAULT_API;
}

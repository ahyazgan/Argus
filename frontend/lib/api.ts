// Basit API istemcisi - JWT'yi localStorage'dan okur, /api/v1 onekini ekler.

const BASE =
  (typeof window !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const TOKEN_KEY = "argus_token";
const REFRESH_KEY = "argus_refresh";

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function isAuthed(): boolean {
  return !!getToken();
}

type Options = {
  method?: string;
  body?: unknown;
  form?: Record<string, string>;
  raw?: boolean;
};

export async function api<T = any>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(opts.form).toString();
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(`${BASE}/api/v1${path}`, {
    method: opts.method || (body ? "POST" : "GET"),
    headers,
    body,
  });

  if (res.status === 401) {
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Oturum süresi doldu");
  }

  if (!res.ok) {
    let detail = `Hata ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function apiBase() {
  return BASE;
}

let csrf = "";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

export function apiUrl(path: string): string {
  const endpoint = path.startsWith("/api/")
    ? path
    : `/api/${path.replace(/^\/+/, "")}`;
  return API_BASE_URL ? new URL(endpoint, `${API_BASE_URL}/`).toString() : endpoint;
}

export function apiHref(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return apiUrl(path);
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = options.method || "GET";
  if (method !== "GET") {
    let res: Response;
    try {
      res = await fetch(apiUrl("auth/csrf/"), { credentials: "include" });
    } catch {
      throw new Error("Unable to reach the server to prepare this request.");
    }
    if (!res.ok) throw new Error("Unable to prepare this request. Please try again.");
    const bootstrap = await res.json().catch(() => null);
    if (!bootstrap || typeof bootstrap.csrfToken !== "string" || !bootstrap.csrfToken)
      throw new Error("Unable to prepare this request. Please try again.");
    csrf = bootstrap.csrfToken;
  }
  const res = await fetch(apiUrl(path), {
    ...options,
    credentials: "include",
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(method !== "GET" ? { "X-CSRFToken": csrf } : {}),
      ...options.headers,
    },
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => undefined);
  if (!res.ok) {
    if (res.status === 403 && !path.startsWith("auth/")) {
      const session = await fetch(apiUrl("auth/me/"), { credentials: "include" });
      if (!session.ok) window.dispatchEvent(new Event("session-expired"));
    }
    const fallback = res.status === 413
      ? "The server rejected the file as too large. Choose a smaller file."
      : `The request failed (HTTP ${res.status}).`;
    const message = data && typeof data === "object"
      ? typeof data.detail === "string" ? data.detail : Object.entries(data)
          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : JSON.stringify(value)}`)
          .join("\n")
      : "";
    throw new ApiError(message || fallback, res.status);
  }
  if (data === undefined) throw new ApiError("The server returned an unreadable response. Please try again.", res.status);
  return data as T;
}
export const post = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });

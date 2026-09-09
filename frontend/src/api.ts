let csrf = "";
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = options.method || "GET";
  if (method !== "GET") {
    const res = await fetch("/api/auth/csrf/", { credentials: "same-origin" });
    csrf = (await res.json()).csrfToken;
  }
  const res = await fetch(`/api/${path}`, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(method !== "GET" ? { "X-CSRFToken": csrf } : {}),
      ...options.headers,
    },
  });
  const data = await res
    .json()
    .catch(() => ({ detail: "The server returned an unexpected response." }));
  if (!res.ok) {
    if (res.status === 403 && !path.startsWith("auth/")) {
      const session = await fetch("/api/auth/me/");
      if (!session.ok) window.dispatchEvent(new Event("session-expired"));
    }
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : Object.entries(data)
            .map(
              ([k, v]) =>
                `${k}: ${Array.isArray(v) ? v.join(", ") : JSON.stringify(v)}`,
            )
            .join("\n"),
    );
  }
  return data as T;
}
export const post = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(data) });

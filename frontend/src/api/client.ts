function normalizeApiBaseUrl(value: string | undefined): string {
  if (!value) {
    return "";
  }

  return value.replace(/\/+$/, "");
}

export const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_AUTHSTATUS_API_BASE_URL ||
    import.meta.env.VITE_API_BASE_URL
);

const CSRF_COOKIE_NAME = "carequeue_csrf";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const CSRF_PROTECTED_METHODS = new Set([
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
]);

function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const prefix = `${encodeURIComponent(name)}=`;

  for (const cookie of document.cookie.split(";")) {
    const trimmedCookie = cookie.trim();

    if (trimmedCookie.startsWith(prefix)) {
      return decodeURIComponent(
        trimmedCookie.slice(prefix.length)
      );
    }
  }

  return null;
}

function getRequestMethod(
  input: RequestInfo | URL,
  init: RequestInit
): string {
  if (init.method) {
    return init.method.toUpperCase();
  }

  if (input instanceof Request) {
    return input.method.toUpperCase();
  }

  return "GET";
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const method = getRequestMethod(input, init);
  const headers = new Headers(init.headers);

  if (CSRF_PROTECTED_METHODS.has(method)) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME);

    if (csrfToken) {
      headers.set(CSRF_HEADER_NAME, csrfToken);
    }
  }

  return fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });
}
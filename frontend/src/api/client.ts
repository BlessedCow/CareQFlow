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
const SESSION_EXPIRES_HEADER_NAME =
  "X-CareQueue-Session-Expires-At";
const SESSION_EXPIRATION_CHANNEL_NAME =
  "carequeue-session-expiration";
const SESSION_LOGOUT_CHANNEL_NAME =
  "carequeue-session-logout";

type SessionExpirationListener = (expiresAt: string) => void;

type SessionLogoutListener = () => void;

const sessionExpirationListeners = new Set<SessionExpirationListener>();

const sessionLogoutListeners = new Set<SessionLogoutListener>();

const sessionExpirationChannel =
  typeof BroadcastChannel === "undefined"
    ? null
    : new BroadcastChannel(SESSION_EXPIRATION_CHANNEL_NAME);

const sessionLogoutChannel =
    typeof BroadcastChannel === "undefined"
      ? null
      : new BroadcastChannel(SESSION_LOGOUT_CHANNEL_NAME);

export function subscribeToSessionExpiration(
  listener: SessionExpirationListener
): () => void {
  sessionExpirationListeners.add(listener);

  return () => {
    sessionExpirationListeners.delete(listener);
  };
}

export function subscribeToSessionLogout(
  listener: SessionLogoutListener
): () => void {
  sessionLogoutListeners.add(listener);

  return () => {
    sessionLogoutListeners.delete(listener);
  };
}

export function broadcastSessionLogout(): void {
  sessionLogoutChannel?.postMessage("logout");
}

function notifySessionExpirationListeners(
  expiresAt: string
): void {
  for (const listener of sessionExpirationListeners) {
    listener(expiresAt);
  }
}

function notifySessionLogoutListeners(): void {
  for (const listener of sessionLogoutListeners) {
    listener();
  }
}

sessionExpirationChannel?.addEventListener(
  "message",
  (event: MessageEvent<unknown>) => {
    if (typeof event.data !== "string") {
      return;
    }

    notifySessionExpirationListeners(event.data);
  }
);

sessionLogoutChannel?.addEventListener(
  "message",
  (event: MessageEvent<unknown>) => {
    if (event.data !== "logout") {
      return;
    }

    notifySessionLogoutListeners();
  }
);

function notifySessionExpiration(response: Response): void {
  const expiresAt = response.headers.get(
    SESSION_EXPIRES_HEADER_NAME
  );

  if (!expiresAt) {
    return;
  }

  notifySessionExpirationListeners(expiresAt);
  sessionExpirationChannel?.postMessage(expiresAt);
}
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

  const response = await fetch(input, {
    ...init,
    headers,
    credentials: "include",
  });

  notifySessionExpiration(response);

  return response;
}
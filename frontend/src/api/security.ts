import { API_BASE_URL, authenticatedFetch } from "./client";

export interface CurrentUser {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  password_changed_at: string;
  must_change_password: boolean;
}

export interface SessionInfo {
  expires_at: string;
}

export interface AuthSession {
  user: CurrentUser;
  session: SessionInfo;
}

type LoginResponse = AuthSession;
type CurrentUserResponse = AuthSession;

interface UserListResponse {
  users: CurrentUser[];
}

interface CreateUserPayload {
  username: string;
  role: string;
}

interface UpdateUserPayload {
  role?: string;
  is_active?: boolean;
}

export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<PasswordUpdateResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/change-password`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }
  );

  if (!response.ok) {
    let message = "Unable to change password.";

    try {
      const data = (await response.json()) as { detail?: string };

      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep the generic message when the response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as PasswordUpdateResponse;
}

export async function resetUserPassword(
  userId: number
): Promise<AdminPasswordResetResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/users/${userId}/reset-password`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    let message = "Unable to reset password.";

    try {
      const data = (await response.json()) as { detail?: string };

      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep the generic message when the response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as AdminPasswordResetResponse;
}

export interface PasswordUpdateResponse {
  password_changed: boolean;
  sessions_revoked: number;
}

export interface AdminPasswordResetResponse {
  password_reset: boolean;
  temporary_password: string;
  sessions_revoked: number;
  must_change_password: boolean;
}

export interface AdminUserCreateResponse {
  user: CurrentUser;
  temporary_password: string;
}

export interface AuditEvent {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  resource_type: string;
  resource_id: number | null;
  metadata: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditEventListResponse {
  events: AuditEvent[];
  page: number;
  page_size: number;
  total: number;
}

interface FetchAuditEventsOptions {
  page?: number;
  pageSize?: number;
  action?: string;
  username?: string;
}

export async function loginUser(
  username: string,
  password: string
): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/security/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Invalid username or password.");
  }

  const data = (await response.json()) as LoginResponse;

  return data;
}

export async function fetchCurrentUser(): Promise<AuthSession> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/security/me`);

  if (!response.ok) {
    throw new Error("Session expired.");
  }

  const data = (await response.json()) as CurrentUserResponse;

  return data;
}

export async function renewCurrentSession(): Promise<SessionInfo> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/session/renew`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Unable to renew session.");
  }

  return (await response.json()) as SessionInfo;
}

export async function fetchUsers(): Promise<CurrentUser[]> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/users`
  );

  if (!response.ok) {
    throw new Error("Unable to load users.");
  }

  const data = (await response.json()) as UserListResponse;

  return data.users;
}

export async function createUser(
  payload: CreateUserPayload
): Promise<AdminUserCreateResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/users`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    let message = "Unable to create user.";

    try {
      const data = (await response.json()) as { detail?: string };

      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep the generic message when the response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as AdminUserCreateResponse;
}

export async function updateUser(
  userId: number,
  payload: UpdateUserPayload
): Promise<CurrentUser> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/users/${userId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error("Unable to update user.");
  }

  return (await response.json()) as CurrentUser;
}

export async function fetchAuditEvents({
  page = 1,
  pageSize = 50,
  action = "",
  username = "",
}: FetchAuditEventsOptions = {}): Promise<AuditEventListResponse> {
  const searchParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  if (action.trim()) {
    searchParams.set("action", action.trim());
  }

  if (username.trim()) {
    searchParams.set("username", username.trim());
  }

  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/audit-events?${searchParams.toString()}`
  );

  if (!response.ok) {
    throw new Error("Unable to load audit events.");
  }

  return (await response.json()) as AuditEventListResponse;
}

export async function logoutUser(): Promise<void> {
  await authenticatedFetch(`${API_BASE_URL}/api/security/logout`, {
    method: "POST",
  });
}

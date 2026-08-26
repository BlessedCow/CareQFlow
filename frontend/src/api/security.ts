import { API_BASE_URL, authenticatedFetch } from "./client";

export interface CurrentUser {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  password_changed_at: string;
  must_change_password: boolean;
  mfa_enabled: boolean;
  walkthrough_status: "pending" | "completed" | "skipped";
  walkthrough_step?: string | null;
}

export interface SessionInfo {
  expires_at: string;
}

export interface AuthSession {
  user: CurrentUser;
  session: SessionInfo;
}

export interface MfaLoginChallenge {
  mfa_required: true;
  mfa_challenge_token: string;
  expires_at: string;
}

export type LoginResult = AuthSession | MfaLoginChallenge;

type LoginResponse = LoginResult;
type CurrentUserResponse = AuthSession;

export function isMfaLoginChallenge(
  result: LoginResult
): result is MfaLoginChallenge {
  return "mfa_required" in result && result.mfa_required === true;
}

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

export async function resetUserMfa(
  userId: number
): Promise<AdminMfaResetResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/users/${userId}/reset-mfa`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    let message = "Unable to reset MFA.";

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

  return (await response.json()) as AdminMfaResetResponse;
}

export async function fetchMfaStatus(): Promise<MfaStatusResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/mfa/status`
  );

  if (!response.ok) {
    throw new Error("Unable to load MFA status.");
  }

  return (await response.json()) as MfaStatusResponse;
}

export async function revokeTrustedDevices(): Promise<TrustedDeviceRevokeResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/mfa/trusted-devices`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    let message = "Unable to revoke remembered devices.";

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

  return (await response.json()) as TrustedDeviceRevokeResponse;
}

export async function startMfaEnrollment(
  currentPassword: string
): Promise<MfaEnrollmentStartResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/mfa/enroll`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        current_password: currentPassword,
      }),
    }
  );

  if (!response.ok) {
    let message = "Unable to start MFA enrollment.";

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

  return (await response.json()) as MfaEnrollmentStartResponse;
}

export async function confirmMfaEnrollment(
  code: string
): Promise<MfaEnrollmentConfirmResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/mfa/enroll/confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code,
      }),
    }
  );

  if (!response.ok) {
    let message = "Unable to confirm MFA enrollment.";

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

  return (await response.json()) as MfaEnrollmentConfirmResponse;
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

export interface AdminMfaResetResponse {
  mfa_reset: boolean;
  sessions_revoked: number;
  mfa_enabled: boolean;
}

export interface MfaStatusResponse {
  enabled: boolean;
  enrollment_pending: boolean;
}

export interface TrustedDeviceRevokeResponse {
  trusted_devices_revoked: number;
}

export interface WalkthroughStatusResponse {
  walkthrough_status: "pending" | "completed" | "skipped";
  walkthrough_step: string | null;
}

export interface MfaEnrollmentStartResponse {
  secret: string;
  provisioning_uri: string;
}

export interface MfaEnrollmentConfirmResponse {
  enabled: boolean;
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
): Promise<LoginResult> {
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

export async function verifyMfaLogin(
  challengeToken: string,
  code: string,
  rememberDevice: boolean
): Promise<AuthSession> {
  const response = await fetch(
    `${API_BASE_URL}/api/security/login/mfa/verify`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        challenge_token: challengeToken,
        code,
        remember_device: rememberDevice,
      }),
    }
  );

  if (!response.ok) {
    let message = "Invalid authentication code.";

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

  return (await response.json()) as AuthSession;
}

export async function fetchCurrentUser(): Promise<AuthSession> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/security/me`);

  if (!response.ok) {
    throw new Error("Session expired.");
  }

  const data = (await response.json()) as CurrentUserResponse;

  return data;
}

export async function updateWalkthroughStep(
  walkthroughStep: string | null
): Promise<WalkthroughStatusResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/walkthrough/step`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        walkthrough_step: walkthroughStep,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Unable to save walkthrough progress.");
  }

  return (await response.json()) as WalkthroughStatusResponse;
}

export async function completeWalkthrough(): Promise<WalkthroughStatusResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/walkthrough/complete`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Unable to complete walkthrough.");
  }

  return (await response.json()) as WalkthroughStatusResponse;
}

export async function skipWalkthrough(): Promise<WalkthroughStatusResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/walkthrough/skip`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Unable to skip walkthrough.");
  }

  return (await response.json()) as WalkthroughStatusResponse;
}

export async function restartUserWalkthrough(
  userId: number
): Promise<WalkthroughStatusResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/users/${userId}/walkthrough/restart`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    let message = "Unable to restart walkthrough.";

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

  return (await response.json()) as WalkthroughStatusResponse;
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

export async function recordSessionActivity(): Promise<SessionInfo> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/session/activity`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Unable to record session activity.");
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

import { API_BASE_URL, authenticatedFetch } from "./client";

export interface ApplicationHealth {
  status: "ok";
}

export interface SystemInfo {
  app: string;
  version: string;
}

export interface DatabaseReadiness {
  status: "ok" | "unavailable";
}

export type EndpointAccess =
  | "public"
  | "initial_setup"
  | "authenticated"
  | "admin_ur"
  | "admin";

export type EndpointStatus = "operational" | "unavailable" | "registered";

export interface ApiEndpointStatus {
  path: string;
  methods: string[];
  group: string;
  access: EndpointAccess;
  status: EndpointStatus;
  probeable: boolean;
}

interface EndpointListResponse {
  endpoints: ApiEndpointStatus[];
}

export interface BackupFile {
  filename: string;
  size_bytes: number;
  created_at: string;
}

interface BackupListResponse {
  backups: BackupFile[];
}

export interface BackupRetentionResult {
  retention_days: number;
  minimum_count: number;
  deleted: string[];
  protected: string[];
  failed: string[];
}

export interface BackupCreateResponse {
  backup: BackupFile;
  verified: boolean;
  retention: BackupRetentionResult;
}

export interface BackupVerifyResponse {
  filename: string;
  verified: boolean;
}

export interface StagedRecovery {
  backup_filename: string;
  staged_filename: string;
  staged_at: string;
}

export interface RecoveryStatusResponse {
  pending: boolean;
  recovery: StagedRecovery | null;
}

export interface RecoveryStageResponse {
  recovery: StagedRecovery;
  staged: boolean;
}

export interface RecoveryCancelResponse {
  recovery: StagedRecovery;
  canceled: boolean;
}

export interface AuditIntegrityResponse {
  valid: boolean;
  status: "valid" | "invalid" | "not_initialized";
  checked_events: number;
  legacy_events: number;
  failed_event_id: number | null;
  reason: string | null;
}

export interface SecurityMonitoringSummaryResponse {
  window_hours: number;
  failed_logins: number;
  locked_logins: number;
  failed_mfa: number;
  total_failures: number;
  distinct_failure_ips: number;
  distinct_failure_usernames: number;
  max_failures_single_username: number;
  max_failures_single_ip: number;
  severity: "normal" | "elevated" | "high";
}

async function getErrorMessage(
  response: Response,
  fallbackMessage: string
): Promise<string> {
  try {
    const data = (await response.json()) as {
      detail?: string;
    };

    return data.detail || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function fetchApplicationHealth(): Promise<ApplicationHealth> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/health/live`);

  if (!response.ok) {
    throw new Error("The CareQFlow API is unavailable.");
  }

  return (await response.json()) as ApplicationHealth;
}

export async function fetchSystemInfo(): Promise<SystemInfo> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/info`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load system information."
      )
    );
  }

  return (await response.json()) as SystemInfo;
}

export async function fetchDatabaseReadiness(): Promise<DatabaseReadiness> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/health/ready`);

  if (response.status === 503) {
    return {
      status: "unavailable",
    };
  }

  if (!response.ok) {
    throw new Error("Unable to check database readiness.");
  }

  return (await response.json()) as DatabaseReadiness;
}

export async function fetchApiEndpoints(): Promise<ApiEndpointStatus[]> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/endpoints`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to load API endpoint status.")
    );
  }

  const data = (await response.json()) as EndpointListResponse;

  return data.endpoints;
}

export async function verifyAuditIntegrity(): Promise<AuditIntegrityResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/audit-events/verify-integrity`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to verify audit log integrity."
      )
    );
  }

  return (await response.json()) as AuditIntegrityResponse;
}

export async function fetchSecurityMonitoringSummary(
  hours = 24
): Promise<SecurityMonitoringSummaryResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/security/monitoring/summary?hours=${hours}`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load security monitoring summary."
      )
    );
  }

  return (await response.json()) as SecurityMonitoringSummaryResponse;
}

export async function fetchRestorePoints(): Promise<BackupFile[]> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/backups`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to load restore points.")
    );
  }

  const data = (await response.json()) as BackupListResponse;

  return data.backups;
}

export async function createRestorePoint(): Promise<BackupCreateResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/backups`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to create the restore point.")
    );
  }

  return (await response.json()) as BackupCreateResponse;
}

export async function verifyRestorePoint(
  filename: string
): Promise<BackupVerifyResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/backups/verify`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to verify the restore point.")
    );
  }

  return (await response.json()) as BackupVerifyResponse;
}

export async function fetchRecoveryStatus(): Promise<RecoveryStatusResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/backups/recovery`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load database recovery status."
      )
    );
  }

  return (await response.json()) as RecoveryStatusResponse;
}

export async function stageDatabaseRecovery(
  filename: string
): Promise<RecoveryStageResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/backups/recovery/stage`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        filename,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to stage the selected restore point."
      )
    );
  }

  return (await response.json()) as RecoveryStageResponse;
}

export async function cancelDatabaseRecovery(): Promise<RecoveryCancelResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/backups/recovery`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to cancel the staged database recovery."
      )
    );
  }

  return (await response.json()) as RecoveryCancelResponse;
}

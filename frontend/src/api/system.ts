import { API_BASE_URL, authenticatedFetch } from "./client";

export interface ApplicationHealth {
  status: "ok";
  app: string;
  version: string;
}

export interface DatabaseReadiness {
  status: "ok" | "unavailable";
}

export type EndpointAccess =
  | "public"
  | "authenticated"
  | "admin";

export type EndpointStatus =
  | "operational"
  | "unavailable"
  | "registered";

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

export interface BackupCreateResponse {
  backup: BackupFile;
  verified: boolean;
}

export interface BackupVerifyResponse {
  filename: string;
  verified: boolean;
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
    throw new Error("The CareQueue API is unavailable.");
  }

  return (await response.json()) as ApplicationHealth;
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

export async function fetchApiEndpoints(): Promise<
  ApiEndpointStatus[]
> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/admin/system/endpoints`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load API endpoint status."
      )
    );
  }

  const data = (await response.json()) as EndpointListResponse;

  return data.endpoints;
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

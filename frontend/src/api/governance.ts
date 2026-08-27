import { API_BASE_URL, authenticatedFetch } from "./client";

export type GovernanceDeploymentMode = "self_hosted" | "managed";

export interface GovernanceAttestation {
  id: number;
  attestation_version: number;
  organization_name: string;
  deployment_mode: GovernanceDeploymentMode;
  accepted_by_user_id: number;
  accepted_by_username: string;
  accepted_at: string;
  app_version: string;
  document_revision: string | null;
}

export interface GovernanceStatus {
  required_version: number;
  required_document_revision: string;
  current: boolean;
  attestation: GovernanceAttestation | null;
}

export interface GovernanceAcceptancePayload {
  organization_name: string;
  deployment_mode: GovernanceDeploymentMode;
  acknowledge_privacy_security_responsibility: true;
  acknowledge_required_agreements: true;
  acknowledge_authorized_access: true;
  acknowledge_device_and_export_safeguards: true;
  acknowledge_test_data_requirements: true;
}

export async function fetchGovernanceStatus(): Promise<GovernanceStatus> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/governance/status`
  );

  if (!response.ok) {
    throw new Error("Unable to load governance status.");
  }

  return (await response.json()) as GovernanceStatus;
}

export async function fetchGovernanceAttestationHistory(): Promise<
  GovernanceAttestation[]
> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/governance/attestations`
  );

  if (!response.ok) {
    throw new Error("Unable to load governance attestation history.");
  }

  return (await response.json()) as GovernanceAttestation[];
}


export async function acceptGovernanceAttestation(
  payload: GovernanceAcceptancePayload
): Promise<GovernanceAttestation> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/governance/attestations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    let message = "Unable to complete governance attestation.";

    try {
      const data = (await response.json()) as {
        detail?: string;
      };

      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep the generic message when the response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as GovernanceAttestation;
}

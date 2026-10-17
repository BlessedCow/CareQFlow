import { API_BASE_URL, authenticatedFetch } from "./client";

export interface AuthDecisionSnapshot {
  id: number;
  auth_id: number;
  auth_event_id: number | null;
  facility: string;
  insurance: string | null;
  insurance_plan: string | null;
  loc: string;
  auth_type: string;
  outcome: string;
  requested_days: number;
  approved_days: number;
  denied_days: number;
  decision_at: string;
  denial_reason_category: string | null;
  denial_source: string | null;
  days_at_current_loc: number | null;
  total_treatment_days: number | null;
  source: string;
  snapshot_role: string;
  review_type: string;
  parent_snapshot_id: number | null;
  root_snapshot_id: number | null;
  follow_up_decision_at: string | null;
  reviewed_from: string | null;
  reviewed_to: string | null;
  reviewed_loc: string | null;
  retro_reason: string | null;
  context_derivation_version: number;
  context_provenance: string;
  created_at: string;
  updated_at: string;
}

interface AuthDecisionSnapshotListResponse {
  snapshots: AuthDecisionSnapshot[];
}

export async function fetchAuthDecisionSnapshots(
  authId: string
): Promise<AuthDecisionSnapshot[]> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/auths/${authId}/decision-snapshots`
  );

  if (!response.ok) {
    let message = "Unable to load decision history.";

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

  const data = (await response.json()) as AuthDecisionSnapshotListResponse;

  return data.snapshots;
}

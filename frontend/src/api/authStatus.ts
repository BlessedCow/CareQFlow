import { format, parseISO } from "date-fns";
import { API_BASE_URL, authenticatedFetch } from "./client";

import { AuthRequest } from "../types/auth";

function mapApiAuthToAuthRequest(item: any): AuthRequest {
  const authDate = item.auth_start_date || item.start_date || item.created_at;

  return {
    id: String(item.id),
    patientId: item.client_name ?? "Unknown Client",
    memberId: item.member_id ?? "",
    authNumber: item.auth_number ?? "",
    groupNumber: item.group_number ?? "",
    dateOfBirth: item.date_of_birth ?? "",
    facility: item.facility ?? "Unknown Facility",
    status: item.status ?? "Pending",
    payer: item.insurance ?? "Unknown Insurance",
    date: authDate ? parseISO(authDate.slice(0, 10)) : new Date(),
    dateStr: authDate
      ? authDate.slice(0, 10)
      : format(new Date(), "yyyy-MM-dd"),
    requestedDays: Number(
      item.requested_days ?? item.los_requested ?? item.requestedDays ?? 0
    ),
    approvedDays: Number(
      item.approved_days ?? item.days_approved ?? item.approvedDays ?? 0
    ),
    urSpecialist: item.ur_specialist ?? "Unassigned",
    loc: item.loc ?? "",
    authType: item.auth_type ?? "",
    submissionMethods: item.submission_methods ?? "",
    reviewDueDate: item.review_due_date ?? "",
    authEndDate: item.auth_end_date ?? "",
    programmingDays: item.programming_days ?? "",
    submittedAt: item.submitted_at ?? null,
    decisionAt: item.decision_at ?? null,
  };
}

export async function fetchAuthRequests(): Promise<AuthRequest[]> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/auths`);

  if (!response.ok) {
    throw new Error(
      `Failed to fetch authorization records: ${response.status}`
    );
  }

  const data = await response.json();
  return data.auths.map(mapApiAuthToAuthRequest);
}

export async function deleteAuthRequest(id: string): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/auths/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(
      `Failed to delete authorization record: ${response.status}`
    );
  }
}

export interface CreateAuthRequestPayload {
  client_name: string;
  member_id?: string;
  auth_number?: string;
  group_number?: string;
  date_of_birth?: string;
  facility: string;
  loc: string;
  status: string;
  insurance: string;
  auth_type: string;
  submission_methods: string;
  requested_days?: number;
  approved_days?: number;
  auth_start_date?: string;
  auth_end_date?: string;
  programming_days?: string;
  review_due_date?: string;
  insurance_phone?: string;
  insurance_fax?: string;
  portal_name?: string;
  fax_numbers?: string;
  care_manager_enabled?: boolean;
  care_manager_details?: string;
  submitted_at?: string | null;
  decision_at?: string | null;
}

export type UpdateAuthRequestPayload = Partial<CreateAuthRequestPayload>;

export async function createAuthRequest(
  payload: CreateAuthRequestPayload
): Promise<AuthRequest> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/auths`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to create authorization record: ${response.status}`
    );
  }

  const data = await response.json();
  return mapApiAuthToAuthRequest(data);
}

export async function updateAuthRequest(
  id: string,
  payload: UpdateAuthRequestPayload
): Promise<AuthRequest> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/auths/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to update authorization record: ${response.status}`
    );
  }

  const data = await response.json();
  return mapApiAuthToAuthRequest(data);
}

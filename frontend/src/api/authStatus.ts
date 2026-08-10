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
    denialReasonCategory: item.denial_reason_category ?? "",
    denialReasonNotes: item.denial_reason_notes ?? "",
    denialPreventionNotes: item.denial_prevention_notes ?? "",
    deniedDays: Number(item.denied_days ?? 0),
    denialDate: item.denial_date ?? "",
    denialThroughDate: item.denial_through_date ?? "",
    denialLevelOfCare: item.denial_level_of_care ?? "",
    denialSource: item.denial_source ?? "",
    p2pRequested: Boolean(item.p2p_requested),
    p2pScheduledAt: item.p2p_scheduled_at ?? "",
    p2pDeadline: item.p2p_deadline ?? "",
    p2pOutcome: item.p2p_outcome ?? "",
    p2pReviewer: item.p2p_reviewer ?? "",
    p2pNotes: item.p2p_notes ?? "",
    appealSubmitted: Boolean(item.appeal_submitted),
    appealDeadline: item.appeal_deadline ?? "",
    appealOutcome: item.appeal_outcome ?? "",
    appealNotes: item.appeal_notes ?? "",
    retroRequested: Boolean(item.retro_requested),
    retroDeadline: item.retro_deadline ?? "",
    retroOutcome: item.retro_outcome ?? "",
    retroNotes: item.retro_notes ?? "",
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
  denial_reason_category?: string;
  denial_reason_notes?: string;
  denial_prevention_notes?: string;
  denied_days?: number;
  denial_date?: string;
  denial_through_date?: string;
  denial_level_of_care?: string;
  denial_source?: string;
  p2p_requested?: boolean;
  p2p_scheduled_at?: string;
  p2p_deadline?: string;
  p2p_outcome?: string;
  p2p_reviewer?: string;
  p2p_notes?: string;
  appeal_submitted?: boolean;
  appeal_deadline?: string;
  appeal_outcome?: string;
  appeal_notes?: string;
  retro_requested?: boolean;
  retro_deadline?: string;
  retro_outcome?: string;
  retro_notes?: string;
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

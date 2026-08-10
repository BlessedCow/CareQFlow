import { format, parseISO } from "date-fns";
import { API_BASE_URL, authenticatedFetch } from "./client";

import {
  AuthRequest,
  DenialReason,
  Facility,
  LOC,
  Payer,
  Status,
} from "../types/auth";


interface BackendAuthRecord {
  id: number;
  facility: string;
  client_name: string;
  member_id: string;
  auth_number: string;
  group_number: string;
  date_of_birth: string;
  loc: string;
  insurance: string;
  insurance_phone: string;
  insurance_fax: string;
  submission_methods: string;
  portal_name: string;
  fax_numbers: string;
  live_call_type: string;
  scheduled_call_at: string;
  care_manager_enabled: boolean;
  care_manager_details: string;
  notes_links: string;
  auth_type: string;
  status: string;
  discharge_clinical_needed: boolean;
  no_pa_required: boolean;
  progress_made: boolean;
  facility_informed: boolean;
  waiting_on_clinicals: boolean;
  los_requested: string;
  days_approved: string;
  auth_start_date: string;
  auth_end_date: string;
  programming_days: string;
  review_due_date: string;
  created_at: string;
  updated_at: string;
}

interface BackendAuthListResponse {
  auths: BackendAuthRecord[];
}

function normalizeStatus(status: string): Status {
  const cleanStatus = status.trim().toLowerCase();

  if (cleanStatus === "completed") return "Completed";
  if (cleanStatus === "discharged") return "Discharged";
  if (cleanStatus === "no pa required") return "No PA Required";
  if (cleanStatus.includes("approved")) return "Approved";
  if (cleanStatus.includes("denied")) return "Denied";
  if (cleanStatus.includes("p2p")) return "P2P";
  if (cleanStatus.includes("appeal")) return "Appealed";

  return "Pending";
}

function normalizeLoc(loc: string): LOC {
  const cleanLoc = loc.trim().toLowerCase();

  if (cleanLoc.includes("detox") || cleanLoc === "dtx") return "Detox";
  if (cleanLoc.includes("residential") || cleanLoc === "rtc")
    return "Residential";
  if (cleanLoc === "php") return "PHP";
  if (cleanLoc === "iop") return "IOP";
  if (cleanLoc === "op") return "OP";

  return "OP";
}

function normalizePayer(insurance: string): Payer {
  const cleanInsurance = insurance.trim().toLowerCase();

  if (cleanInsurance.includes("bcbs") || cleanInsurance.includes("blue"))
    return "BCBS";
  if (cleanInsurance.includes("aetna")) return "Aetna";
  if (cleanInsurance.includes("cigna")) return "Cigna";
  if (cleanInsurance.includes("uhc") || cleanInsurance.includes("united"))
    return "UHC";
  if (cleanInsurance.includes("optum")) return "Optum";
  if (cleanInsurance.includes("magellan")) return "Magellan";

  return "Optum";
}

function normalizeFacility(facility: string): Facility {
  return facility as Facility;
}

function parseNumber(value: string): number {
  const parsed = Number.parseInt(value, 10);

  if (Number.isNaN(parsed)) {
    return 0;
  }

  return parsed;
}

function mapDenialReason(record: BackendAuthRecord): DenialReason | undefined {
  if (normalizeStatus(record.status) !== "Denied") {
    return undefined;
  }

  if (record.waiting_on_clinicals) {
    return "Clinicals Not Submitted";
  }

  if (!record.progress_made) {
    return "Lack of Progress";
  }

  return "Other";
}

function getRecordDate(record: BackendAuthRecord): string {
  return record.auth_start_date || record.created_at.slice(0, 10);
}

function toAuthRequest(record: BackendAuthRecord): AuthRequest {
  const dateStr = getRecordDate(record);
  const status = normalizeStatus(record.status);
  const requestedDays = parseNumber(record.los_requested);
  const approvedDays = parseNumber(record.days_approved);

  return {
    id: String(record.id),
    patientId: record.client_name || record.member_id || `Auth ${record.id}`,
    memberId: record.member_id ?? "",
    authNumber: record.auth_number ?? "",
    groupNumber: record.group_number ?? "",
    dateOfBirth: record.date_of_birth ?? "",
    date: parseISO(dateStr),
    dateStr,
    facility: normalizeFacility(record.facility),
    payer: normalizePayer(record.insurance),
    loc: normalizeLoc(record.loc),
    status,
    requestedDays,
    approvedDays,
    denialReason: mapDenialReason(record),
    urSpecialist: record.care_manager_enabled
      ? "Care Manager Assigned"
      : "Unassigned",
    daysToDecision: status === "Pending" ? 0 : 1,
  };
}

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

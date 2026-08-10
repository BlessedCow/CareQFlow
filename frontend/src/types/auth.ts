export type Status =
  | "Pending"
  | "Approved"
  | "Denied"
  | "P2P"
  | "Appealed"
  | "No PA Required"
  | "Completed"
  | "Discharged";

export type LOC = "Detox" | "Residential" | "PHP" | "IOP" | "OP" | string;

export type Payer =
  | "BCBS"
  | "Aetna"
  | "Cigna"
  | "UHC"
  | "Optum"
  | "Magellan"
  | string;

export type Facility = string;

export type DenialReason =
  | "Lack of Progress"
  | "Medical Necessity"
  | "Clinicals Not Submitted"
  | "Administrative"
  | "Other";

export interface AuthRequest {
  id: string;
  patientId: string;
  memberId: string;
  authNumber: string;
  groupNumber: string;
  dateOfBirth: string;
  date: Date;
  dateStr: string;
  facility: Facility;
  payer: Payer;
  loc: LOC;
  status: Status;
  requestedDays: number;
  approvedDays: number;
  denialReason?: DenialReason;
  urSpecialist: string;
  daysToDecision?: number;
  authType?: string;
  submissionMethods?: string;
  reviewDueDate?: string;
  authEndDate?: string;
  programmingDays?: string;
  submittedAt?: string | null;
  decisionAt?: string | null;
}

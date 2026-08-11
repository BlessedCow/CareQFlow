import type { CreateAuthRequestPayload } from "../../api/authStatus";
import type { AuthRequest } from "../../types/auth";

export interface DenialFormState {
  denialReasonCategory: string;
  denialDate: string;
  denialThroughDate: string;
  denialLevelOfCare: string;
  denialSource: string;
  denialReasonNotes: string;
  denialPreventionNotes: string;
}

export interface P2PFormState {
  p2pRequested: boolean;
  p2pScheduledAt: string;
  p2pDeadline: string;
  p2pOutcome: string;
  p2pReviewer: string;
  p2pNotes: string;
}

export interface AppealFormState {
  appealSubmitted: boolean;
  appealDeadline: string;
  appealOutcome: string;
  appealNotes: string;
}

export interface RetroFormState {
  retroRequested: boolean;
  retroDeadline: string;
  retroOutcome: string;
  retroNotes: string;
}

export const DENIAL_REASON_OPTIONS = [
  "",
  "Not Medically Necessary",
  "Insufficient Clinical Documentation",
  "Lack of Progress",
  "Detox Scores Too Low",
  "Lower LOC Recommended",
  "Downcertified to Lower LOC",
  "No Active Treatment Needs",
  "Administrative Issue",
  "Timely Filing / Late Submission",
  "Benefit Issue",
  "Other",
];

export const DENIAL_LEVEL_OF_CARE_OPTIONS = [
  "",
  "DTX",
  "RTC",
  "PHP",
  "IOP",
  "Other",
];

export const DENIAL_SOURCE_OPTIONS = [
  "",
  "Initial Auth",
  "Concurrent Auth",
  "Retro Auth",
  "Appeal",
  "Other",
];

export const P2P_OUTCOME_OPTIONS = [
  "",
  "Pending",
  "Approved",
  "Denied",
  "Upheld",
  "Overturned",
  "Withdrawn",
  "Other",
];

export const APPEAL_OUTCOME_OPTIONS = [
  "",
  "Pending",
  "Submitted",
  "Approved",
  "Denied",
  "Upheld",
  "Overturned",
  "Withdrawn",
  "Other",
];

export const RETRO_OUTCOME_OPTIONS = [
  "",
  "Pending",
  "Submitted",
  "Approved",
  "Denied",
  "Partially Approved",
  "Withdrawn",
  "Other",
];

export type FollowUpType = "Denial" | "P2P" | "Appeal" | "Retro Auth";

export interface FollowUpListItem {
  auth: AuthRequest;
  type: FollowUpType;
  dueDate: string;
  reason: string;
  outcome: string;
}

export function getDenialFormFromAuth(auth: AuthRequest): DenialFormState {
  return {
    denialReasonCategory: auth.denialReasonCategory ?? "",
    denialDate: auth.denialDate ?? "",
    denialThroughDate: auth.denialThroughDate ?? "",
    denialLevelOfCare: auth.denialLevelOfCare ?? "",
    denialSource: auth.denialSource ?? "",
    denialReasonNotes: auth.denialReasonNotes ?? "",
    denialPreventionNotes: auth.denialPreventionNotes ?? "",
  };
}

export function buildDenialPayload(
  form: DenialFormState
): Partial<CreateAuthRequestPayload> {
  return {
    status: "Denied",
    denial_reason_category: form.denialReasonCategory,
    denied_days: 0,
    denial_date: form.denialDate,
    denial_through_date: form.denialThroughDate,
    denial_level_of_care: form.denialLevelOfCare,
    denial_source: form.denialSource,
    denial_reason_notes: form.denialReasonNotes,
    denial_prevention_notes: form.denialPreventionNotes,
  };
}

export function buildClearDenialPayload(): Partial<CreateAuthRequestPayload> {
  return {
    status: "In Progress",
    denial_reason_category: "",
    denied_days: 0,
    denial_date: "",
    denial_through_date: "",
    denial_level_of_care: "",
    denial_source: "",
    denial_reason_notes: "",
    denial_prevention_notes: "",
  };
}

export function getP2PFormFromAuth(auth: AuthRequest): P2PFormState {
  return {
    p2pRequested: Boolean(auth.p2pRequested),
    p2pScheduledAt: auth.p2pScheduledAt ?? "",
    p2pDeadline: auth.p2pDeadline ?? "",
    p2pOutcome: auth.p2pOutcome ?? "",
    p2pReviewer: auth.p2pReviewer ?? "",
    p2pNotes: auth.p2pNotes ?? "",
  };
}

export function buildP2PPayload(
  form: P2PFormState
): Partial<CreateAuthRequestPayload> {
  return {
    p2p_requested: form.p2pRequested,
    p2p_scheduled_at: form.p2pScheduledAt,
    p2p_deadline: form.p2pDeadline,
    p2p_outcome: form.p2pOutcome,
    p2p_reviewer: form.p2pReviewer,
    p2p_notes: form.p2pNotes,
  };
}

export function buildClearP2PPayload(): Partial<CreateAuthRequestPayload> {
  return {
    p2p_requested: false,
    p2p_scheduled_at: "",
    p2p_deadline: "",
    p2p_outcome: "",
    p2p_reviewer: "",
    p2p_notes: "",
  };
}

export function getAppealFormFromAuth(auth: AuthRequest): AppealFormState {
  return {
    appealSubmitted: Boolean(auth.appealSubmitted),
    appealDeadline: auth.appealDeadline ?? "",
    appealOutcome: auth.appealOutcome ?? "",
    appealNotes: auth.appealNotes ?? "",
  };
}

export function buildAppealPayload(
  form: AppealFormState
): Partial<CreateAuthRequestPayload> {
  return {
    appeal_submitted: form.appealSubmitted,
    appeal_deadline: form.appealDeadline,
    appeal_outcome: form.appealOutcome,
    appeal_notes: form.appealNotes,
  };
}

export function buildClearAppealPayload(): Partial<CreateAuthRequestPayload> {
  return {
    appeal_submitted: false,
    appeal_deadline: "",
    appeal_outcome: "",
    appeal_notes: "",
  };
}

export function getRetroFormFromAuth(auth: AuthRequest): RetroFormState {
  return {
    retroRequested: Boolean(auth.retroRequested),
    retroDeadline: auth.retroDeadline ?? "",
    retroOutcome: auth.retroOutcome ?? "",
    retroNotes: auth.retroNotes ?? "",
  };
}

export function buildRetroPayload(
  form: RetroFormState
): Partial<CreateAuthRequestPayload> {
  return {
    retro_requested: form.retroRequested,
    retro_deadline: form.retroDeadline,
    retro_outcome: form.retroOutcome,
    retro_notes: form.retroNotes,
  };
}

export function buildClearRetroPayload(): Partial<CreateAuthRequestPayload> {
  return {
    retro_requested: false,
    retro_deadline: "",
    retro_outcome: "",
    retro_notes: "",
  };
}

export function getFollowUpItems(data: AuthRequest[]): FollowUpListItem[] {
  return data
    .flatMap((auth) => {
      const items: FollowUpListItem[] = [];

      if (auth.status === "Denied" || auth.denialReasonCategory) {
        items.push({
          auth,
          type: "Denial",
          dueDate: auth.denialThroughDate || auth.denialDate || "",
          reason: auth.denialReasonCategory || "Denial recorded",
          outcome: auth.denialSource || "",
        });
      }

      if (auth.p2pRequested) {
        items.push({
          auth,
          type: "P2P",
          dueDate:
            getDateFromDateTime(auth.p2pScheduledAt) || auth.p2pDeadline || "",
          reason: "P2P requested",
          outcome: auth.p2pOutcome || "",
        });
      }

      if (auth.appealSubmitted) {
        items.push({
          auth,
          type: "Appeal",
          dueDate: auth.appealDeadline || "",
          reason: "Appeal submitted",
          outcome: auth.appealOutcome || "",
        });
      }

      if (auth.retroRequested) {
        items.push({
          auth,
          type: "Retro Auth",
          dueDate: auth.retroDeadline || "",
          reason: "Retro auth requested",
          outcome: auth.retroOutcome || "",
        });
      }

      return items;
    })
    .sort((firstItem, secondItem) => {
      const firstDate = firstItem.dueDate || "9999-12-31";
      const secondDate = secondItem.dueDate || "9999-12-31";

      return firstDate.localeCompare(secondDate);
    });
}

export function formatDate(value: string) {
  if (!value) {
    return "No due date";
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString();
}

export function confirmClear(label: string) {
  return window.confirm(
    `Clear ${label} details for this authorization? This will also remove the synced timeline event.`
  );
}

export function isOverdue(value: string) {
  if (!value) {
    return false;
  }

  const dueDate = new Date(`${value}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return !Number.isNaN(dueDate.getTime()) && dueDate < today;
}

function getDateFromDateTime(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "";
}

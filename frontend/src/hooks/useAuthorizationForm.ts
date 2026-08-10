import { useEffect, useState } from "react";

import type { AuthRequest } from "../types/auth";
import { calculateAuthEndDate } from "../utils/authSchedule";

export interface NewAuthFormState {
  clientName: string;
  memberId: string;
  authNumber: string;
  groupNumber: string;
  dateOfBirth: string;
  facility: string;
  loc: string;
  status: string;
  startDate: string;
  endDate: string;
  programmingDays: string;
  reviewDueDate: string;
  requestedDays: string;
  approvedDays: string;
  insurance: string;
  authType: string;
  submissionMethod: string;
  phoneNumber: string;
  phoneExtension: string;
  faxNumber: string;
  webPortal: string;
  webPortalUrl: string;
  hasCareManager: boolean;
  careManagerName: string;
  careManagerContactType: string;
  careManagerPhone: string;
  careManagerFax: string;
  careManagerNotes: string;
  denialReasonCategory: string;
  denialReasonNotes: string;
  denialPreventionNotes: string;
  deniedDays: string;
  denialDate: string;
  denialLevelOfCare: string;
  denialSource: string;
  p2pRequested: boolean;
  p2pScheduledAt: string;
  p2pDeadline: string;
  p2pOutcome: string;
  p2pReviewer: string;
  p2pNotes: string;
  appealSubmitted: boolean;
  appealDeadline: string;
  appealOutcome: string;
  appealNotes: string;
  retroRequested: boolean;
  retroDeadline: string;
  retroOutcome: string;
  retroNotes: string;
}

export const DEFAULT_AUTH_FORM: NewAuthFormState = {
  clientName: "",
  memberId: "",
  authNumber: "",
  groupNumber: "",
  dateOfBirth: "",
  facility: "",
  loc: "DTX",
  status: "Pending",
  startDate: "",
  endDate: "",
  programmingDays: "7 days/week",
  reviewDueDate: "",
  requestedDays: "",
  approvedDays: "",
  insurance: "",
  authType: "Initial",
  submissionMethod: "",
  phoneNumber: "",
  phoneExtension: "",
  faxNumber: "",
  webPortal: "",
  webPortalUrl: "",
  hasCareManager: false,
  careManagerName: "",
  careManagerContactType: "",
  careManagerPhone: "",
  careManagerFax: "",
  careManagerNotes: "",
  denialReasonCategory: "",
  denialReasonNotes: "",
  denialPreventionNotes: "",
  deniedDays: "",
  denialDate: "",
  denialLevelOfCare: "",
  denialSource: "",
  p2pRequested: false,
  p2pScheduledAt: "",
  p2pDeadline: "",
  p2pOutcome: "",
  p2pReviewer: "",
  p2pNotes: "",
  appealSubmitted: false,
  appealDeadline: "",
  appealOutcome: "",
  appealNotes: "",
  retroRequested: false,
  retroDeadline: "",
  retroOutcome: "",
  retroNotes: "",
};

function normalizeFormLoc(loc: string): string {
  const normalizedLoc = loc.trim().toLowerCase();

  if (normalizedLoc === "dtx" || normalizedLoc.includes("detox")) {
    return "DTX";
  }

  if (
    normalizedLoc === "rtc" ||
    normalizedLoc.includes("residential")
  ) {
    return "RTC";
  }

  if (normalizedLoc === "php") {
    return "PHP";
  }

  if (normalizedLoc === "iop") {
    return "IOP";
  }

  return loc;
}

export function getAuthFormFromAuth(auth: AuthRequest): NewAuthFormState {
  return {
    clientName: auth.patientId,
    memberId: auth.memberId,
    authNumber: auth.authNumber,
    groupNumber: auth.groupNumber,
    dateOfBirth: auth.dateOfBirth,
    facility: auth.facility,
    loc: normalizeFormLoc(auth.loc),
    status: auth.status,
    startDate: auth.dateStr || "",
    endDate: auth.authEndDate ?? "",
    programmingDays: auth.programmingDays ?? "",
    reviewDueDate: auth.reviewDueDate ?? "",
    requestedDays: String(auth.requestedDays ?? ""),
    approvedDays: String(auth.approvedDays ?? ""),
    insurance: auth.payer,
    authType: auth.authType ?? "Initial",
    submissionMethod: auth.submissionMethods ?? "",
    phoneNumber: "",
    phoneExtension: "",
    faxNumber: "",
    webPortal: "",
    webPortalUrl: "",
    hasCareManager: false,
    careManagerName: "",
    careManagerContactType: "",
    careManagerPhone: "",
    careManagerFax: "",
    careManagerNotes: "",
    denialReasonCategory: auth.denialReasonCategory ?? "",
    denialReasonNotes: auth.denialReasonNotes ?? "",
    denialPreventionNotes: auth.denialPreventionNotes ?? "",
    deniedDays: String(auth.deniedDays ?? ""),
    denialDate: auth.denialDate ?? "",
    denialLevelOfCare: auth.denialLevelOfCare ?? "",
    denialSource: auth.denialSource ?? "",
    p2pRequested: Boolean(auth.p2pRequested),
    p2pScheduledAt: auth.p2pScheduledAt ?? "",
    p2pDeadline: auth.p2pDeadline ?? "",
    p2pOutcome: auth.p2pOutcome ?? "",
    p2pReviewer: auth.p2pReviewer ?? "",
    p2pNotes: auth.p2pNotes ?? "",
    appealSubmitted: Boolean(auth.appealSubmitted),
    appealDeadline: auth.appealDeadline ?? "",
    appealOutcome: auth.appealOutcome ?? "",
    appealNotes: auth.appealNotes ?? "",
    retroRequested: Boolean(auth.retroRequested),
    retroDeadline: auth.retroDeadline ?? "",
    retroOutcome: auth.retroOutcome ?? "",
    retroNotes: auth.retroNotes ?? "",
  };
}

export function getLocChangeAuthFormFromCurrentForm(
  currentForm: NewAuthFormState
): NewAuthFormState {
  return {
    ...currentForm,
    status: "Pending",
    authType: "Concurrent",
    startDate: "",
    endDate: "",
    reviewDueDate: "",
    requestedDays: "",
    approvedDays: "",
  };
}

export function useAuthorizationForm() {
  const [newAuthForm, setNewAuthForm] =
    useState<NewAuthFormState>(DEFAULT_AUTH_FORM);

  const resetNewAuthForm = () => {
    setReviewDueDateWasEdited(false);
    setNewAuthForm(DEFAULT_AUTH_FORM);
  };

  const [reviewDueDateWasEdited, setReviewDueDateWasEdited] = useState(false);

  const handleNewAuthFieldChange = (
    field: keyof NewAuthFormState,
    value: string | boolean
  ) => {
    if (field === "reviewDueDate") {
      setReviewDueDateWasEdited(true);
    }

    setNewAuthForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  };

  useEffect(() => {
    const approvedDays = Number(newAuthForm.approvedDays);

    const coveredDays =
      Number.isFinite(approvedDays) && approvedDays > 0
        ? newAuthForm.approvedDays.trim()
        : newAuthForm.requestedDays.trim();

    const calculatedAuthEndDate = calculateAuthEndDate(
      newAuthForm.startDate,
      coveredDays,
      newAuthForm.programmingDays || "7 days/week"
    );
    if (!calculatedAuthEndDate) {
      return;
    }

    setNewAuthForm((currentForm) => {
      if (currentForm.endDate === calculatedAuthEndDate) {
        return currentForm;
      }

      return {
        ...currentForm,
        endDate: calculatedAuthEndDate,
        reviewDueDate: reviewDueDateWasEdited
          ? currentForm.reviewDueDate
          : calculatedAuthEndDate,
      };
    });
  }, [
    newAuthForm.startDate,
    newAuthForm.requestedDays,
    newAuthForm.approvedDays,
    newAuthForm.programmingDays,
    reviewDueDateWasEdited,
  ]);

  const loadAuthIntoForm = (auth: AuthRequest) => {
    setReviewDueDateWasEdited(false);
    setNewAuthForm(getAuthFormFromAuth(auth));
  };

  const loadLocChangeAuthForm = () => {
    setReviewDueDateWasEdited(false);
    setNewAuthForm((currentForm) =>
      getLocChangeAuthFormFromCurrentForm(currentForm)
    );
  };

  return {
    newAuthForm,
    setNewAuthForm,
    resetNewAuthForm,
    handleNewAuthFieldChange,
    loadAuthIntoForm,
    loadLocChangeAuthForm,
  };
}

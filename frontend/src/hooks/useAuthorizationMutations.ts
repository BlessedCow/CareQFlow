import { useState } from "react";

import {
  createAuthRequest,
  deleteAuthRequest,
  updateAuthRequest,
  type CreateAuthRequestPayload,
} from "../api/authStatus";
import type { AuthRequest } from "../types/auth";
import type { NewAuthFormState } from "./useAuthorizationForm";

function buildAuthorizationPayload(
  form: NewAuthFormState
): CreateAuthRequestPayload {
  const careManagerDetails = [
    form.careManagerName ? `Name: ${form.careManagerName}` : "",
    form.careManagerContactType
      ? `Contact Type: ${form.careManagerContactType}`
      : "",
    form.careManagerPhone ? `Phone: ${form.careManagerPhone}` : "",
    form.careManagerFax ? `Fax: ${form.careManagerFax}` : "",
    form.careManagerNotes ? `Notes: ${form.careManagerNotes}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  return {
    client_name: form.clientName,
    member_id: form.memberId,
    auth_number: form.authNumber,
    group_number: form.groupNumber,
    date_of_birth: form.dateOfBirth,
    facility: form.facility,
    loc: form.loc,
    status: form.status,
    auth_start_date: form.startDate,
    auth_end_date: form.endDate,
    programming_days: form.programmingDays,
    review_due_date: form.reviewDueDate,
    requested_days: Number(form.requestedDays) || 0,
    approved_days: Number(form.approvedDays) || 0,
    insurance: form.insurance,
    auth_type: form.authType,
    submission_methods: form.submissionMethod,
    insurance_phone: form.phoneExtension
      ? `${form.phoneNumber} ext. ${form.phoneExtension}`
      : form.phoneNumber,
    insurance_fax: form.faxNumber,
    fax_numbers: form.faxNumber,
    portal_name: form.webPortal,
    care_manager_enabled: form.hasCareManager,
    care_manager_details: careManagerDetails,
    denial_reason_category: form.denialReasonCategory,
    denial_reason_notes: form.denialReasonNotes,
    denial_prevention_notes: form.denialPreventionNotes,
    denied_days: Number(form.deniedDays) || 0,
    denial_date: form.denialDate,
    denial_level_of_care: form.denialLevelOfCare,
    denial_source: form.denialSource,
    p2p_requested: form.p2pRequested,
    p2p_scheduled_at: form.p2pScheduledAt,
    p2p_deadline: form.p2pDeadline,
    p2p_outcome: form.p2pOutcome,
    p2p_reviewer: form.p2pReviewer,
    p2p_notes: form.p2pNotes,
    appeal_submitted: form.appealSubmitted,
    appeal_deadline: form.appealDeadline,
    appeal_outcome: form.appealOutcome,
    appeal_notes: form.appealNotes,
    retro_requested: form.retroRequested,
    retro_deadline: form.retroDeadline,
    retro_outcome: form.retroOutcome,
    retro_notes: form.retroNotes,
  };
}

interface SaveAuthorizationArgs {
  editingAuthId: string | null;
  form: NewAuthFormState;
}

export function useAuthorizationMutations() {
  const [isCreatingAuth, setIsCreatingAuth] = useState(false);
  const [deletingAuthId, setDeletingAuthId] = useState<string | null>(null);

  const saveAuthorization = async ({
    editingAuthId,
    form,
  }: SaveAuthorizationArgs): Promise<AuthRequest> => {
    setIsCreatingAuth(true);

    try {
      const payload = buildAuthorizationPayload(form);

      if (editingAuthId) {
        return await updateAuthRequest(editingAuthId, payload);
      }

      return await createAuthRequest(payload);
    } finally {
      setIsCreatingAuth(false);
    }
  };

  const removeAuthorization = async (auth: AuthRequest) => {
    setDeletingAuthId(auth.id);

    try {
      await deleteAuthRequest(auth.id);
    } finally {
      setDeletingAuthId(null);
    }
  };

  return {
    isCreatingAuth,
    deletingAuthId,
    saveAuthorization,
    removeAuthorization,
  };
}

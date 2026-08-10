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

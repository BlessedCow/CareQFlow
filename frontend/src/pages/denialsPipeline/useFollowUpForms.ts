import { useEffect, useState } from "react";

import { updateAuthRequest } from "../../api/authStatus";
import type { AuthRequest } from "../../types/auth";
import {
  buildAppealPayload,
  buildClearAppealPayload,
  buildClearDenialPayload,
  buildClearP2PPayload,
  buildClearRetroPayload,
  buildDenialPayload,
  buildP2PPayload,
  buildRetroPayload,
  confirmClear,
  getAppealFormFromAuth,
  getDenialFormFromAuth,
  getP2PFormFromAuth,
  getRetroFormFromAuth,
  type AppealFormState,
  type DenialFormState,
  type P2PFormState,
  type RetroFormState,
} from "./followUpModels";

interface UseFollowUpFormsArgs {
  selectedAuth: AuthRequest | null;
  onAuthUpdated: (auth: AuthRequest) => void;
}

export function useFollowUpForms({
  selectedAuth,
  onAuthUpdated,
}: UseFollowUpFormsArgs) {
  const [denialForm, setDenialForm] = useState<DenialFormState | null>(null);
  const [isSavingDenial, setIsSavingDenial] = useState(false);
  const [denialError, setDenialError] = useState<string | null>(null);

  const [p2pForm, setP2PForm] = useState<P2PFormState | null>(null);
  const [isSavingP2P, setIsSavingP2P] = useState(false);
  const [p2pError, setP2PError] = useState<string | null>(null);

  const [appealForm, setAppealForm] = useState<AppealFormState | null>(null);
  const [isSavingAppeal, setIsSavingAppeal] = useState(false);
  const [appealError, setAppealError] = useState<string | null>(null);

  const [retroForm, setRetroForm] = useState<RetroFormState | null>(null);
  const [isSavingRetro, setIsSavingRetro] = useState(false);
  const [retroError, setRetroError] = useState<string | null>(null);

  useEffect(() => {
    setDenialForm(selectedAuth ? getDenialFormFromAuth(selectedAuth) : null);
    setP2PForm(selectedAuth ? getP2PFormFromAuth(selectedAuth) : null);
    setAppealForm(selectedAuth ? getAppealFormFromAuth(selectedAuth) : null);
    setRetroForm(selectedAuth ? getRetroFormFromAuth(selectedAuth) : null);

    setDenialError(null);
    setP2PError(null);
    setAppealError(null);
    setRetroError(null);
  }, [selectedAuth]);

  const handleDenialFieldChange = (
    field: keyof DenialFormState,
    value: string
  ) => {
    setDenialForm((currentForm) => {
      if (!currentForm) {
        return currentForm;
      }

      return {
        ...currentForm,
        [field]: value,
      };
    });
  };

  const handleP2PFieldChange = (
    field: keyof P2PFormState,
    value: string | boolean
  ) => {
    setP2PForm((currentForm) => {
      if (!currentForm) {
        return currentForm;
      }

      return {
        ...currentForm,
        [field]: value,
      };
    });
  };

  const handleAppealFieldChange = (
    field: keyof AppealFormState,
    value: string | boolean
  ) => {
    setAppealForm((currentForm) => {
      if (!currentForm) {
        return currentForm;
      }

      return {
        ...currentForm,
        [field]: value,
      };
    });
  };

  const handleRetroFieldChange = (
    field: keyof RetroFormState,
    value: string | boolean
  ) => {
    setRetroForm((currentForm) => {
      if (!currentForm) {
        return currentForm;
      }

      return {
        ...currentForm,
        [field]: value,
      };
    });
  };

  const handleSaveDenial = async () => {
    if (!selectedAuth || !denialForm) {
      return;
    }

    setIsSavingDenial(true);
    setDenialError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildDenialPayload(denialForm)
      );

      onAuthUpdated(updatedAuth);
      setDenialForm(null);
    } catch (error) {
      setDenialError(
        error instanceof Error
          ? error.message
          : "Unable to save denial details."
      );
    } finally {
      setIsSavingDenial(false);
    }
  };

  const handleSaveP2P = async () => {
    if (!selectedAuth || !p2pForm) {
      return;
    }

    setIsSavingP2P(true);
    setP2PError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildP2PPayload(p2pForm)
      );

      onAuthUpdated(updatedAuth);
      setP2PForm(null);
    } catch (error) {
      setP2PError(
        error instanceof Error ? error.message : "Unable to save P2P details."
      );
    } finally {
      setIsSavingP2P(false);
    }
  };

  const handleSaveAppeal = async () => {
    if (!selectedAuth || !appealForm) {
      return;
    }

    setIsSavingAppeal(true);
    setAppealError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildAppealPayload(appealForm)
      );

      onAuthUpdated(updatedAuth);
      setAppealForm(null);
    } catch (error) {
      setAppealError(
        error instanceof Error
          ? error.message
          : "Unable to save appeal details."
      );
    } finally {
      setIsSavingAppeal(false);
    }
  };

  const handleSaveRetro = async () => {
    if (!selectedAuth || !retroForm) {
      return;
    }

    setIsSavingRetro(true);
    setRetroError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildRetroPayload(retroForm)
      );

      onAuthUpdated(updatedAuth);
      setRetroForm(null);
    } catch (error) {
      setRetroError(
        error instanceof Error
          ? error.message
          : "Unable to save retro auth details."
      );
    } finally {
      setIsSavingRetro(false);
    }
  };

  const handleClearDenial = async () => {
    if (!selectedAuth || !confirmClear("denial")) {
      return;
    }

    setIsSavingDenial(true);
    setDenialError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildClearDenialPayload()
      );

      onAuthUpdated(updatedAuth);
      setDenialForm(null);
    } catch (error) {
      setDenialError(
        error instanceof Error
          ? error.message
          : "Unable to clear denial details."
      );
    } finally {
      setIsSavingDenial(false);
    }
  };

  const handleClearP2P = async () => {
    if (!selectedAuth || !confirmClear("P2P")) {
      return;
    }

    setIsSavingP2P(true);
    setP2PError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildClearP2PPayload()
      );

      onAuthUpdated(updatedAuth);
      setP2PForm(null);
    } catch (error) {
      setP2PError(
        error instanceof Error ? error.message : "Unable to delete P2P details."
      );
    } finally {
      setIsSavingP2P(false);
    }
  };

  const handleClearAppeal = async () => {
    if (!selectedAuth || !confirmClear("appeal")) {
      return;
    }

    setIsSavingAppeal(true);
    setAppealError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildClearAppealPayload()
      );

      onAuthUpdated(updatedAuth);
      setAppealForm(null);
    } catch (error) {
      setAppealError(
        error instanceof Error
          ? error.message
          : "Unable to delete appeal details."
      );
    } finally {
      setIsSavingAppeal(false);
    }
  };

  const handleClearRetro = async () => {
    if (!selectedAuth || !confirmClear("retro auth")) {
      return;
    }

    setIsSavingRetro(true);
    setRetroError(null);

    try {
      const updatedAuth = await updateAuthRequest(
        selectedAuth.id,
        buildClearRetroPayload()
      );

      onAuthUpdated(updatedAuth);
      setRetroForm(null);
    } catch (error) {
      setRetroError(
        error instanceof Error
          ? error.message
          : "Unable to delete retro auth details."
      );
    } finally {
      setIsSavingRetro(false);
    }
  };

  return {
    denialForm,
    denialError,
    isSavingDenial,
    p2pForm,
    p2pError,
    isSavingP2P,
    appealForm,
    appealError,
    isSavingAppeal,
    retroForm,
    retroError,
    isSavingRetro,
    handleDenialFieldChange,
    handleP2PFieldChange,
    handleAppealFieldChange,
    handleRetroFieldChange,
    handleSaveDenial,
    handleSaveP2P,
    handleSaveAppeal,
    handleSaveRetro,
    handleClearDenial,
    handleClearP2P,
    handleClearAppeal,
    handleClearRetro,
  };
}
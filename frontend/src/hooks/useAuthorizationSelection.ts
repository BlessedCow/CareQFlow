import { useState } from "react";

import type { AuthEvent } from "../api/authEvents";
import type { AuthRequest } from "../types/auth";
import type { NewAuthFormState } from "./useAuthorizationForm";

interface UseAuthorizationSelectionArgs {
  resetNewAuthForm: () => void;
  loadAuthIntoForm: (auth: AuthRequest) => void;
  loadLocChangeAuthForm: () => void;
  resetTimelineEventForm: () => void;
  clearAuthEvents: () => void;
  loadAuthEvents: (authId: string) => Promise<void>;
}

export function useAuthorizationSelection({
  resetNewAuthForm,
  loadAuthIntoForm,
  loadLocChangeAuthForm,
  resetTimelineEventForm,
  clearAuthEvents,
  loadAuthEvents,
}: UseAuthorizationSelectionArgs) {
  const [showAddAuthForm, setShowAddAuthForm] = useState(false);
  const [viewingAuth, setViewingAuth] = useState<AuthRequest | null>(null);
  const [editingAuthId, setEditingAuthId] = useState<string | null>(null);

  const handleShowAddAuthForm = () => {
    resetNewAuthForm();
    clearAuthEvents();
    setViewingAuth(null);
    setEditingAuthId(null);
    setShowAddAuthForm(true);
  };

  const handleCancelAuthForm = () => {
    setShowAddAuthForm(false);
    setEditingAuthId(null);
    resetNewAuthForm();
    clearAuthEvents();
  };

  const handleStartViewAuth = async (auth: AuthRequest) => {
    setViewingAuth(auth);
    setShowAddAuthForm(false);
    setEditingAuthId(null);
    resetNewAuthForm();
    await loadAuthEvents(auth.id);
  };

  const handleCloseViewAuth = () => {
    setViewingAuth(null);
    clearAuthEvents();
  };

  const handleStartEditAuth = async (auth: AuthRequest) => {
    loadAuthIntoForm(auth);
    setEditingAuthId(auth.id);
    setViewingAuth(null);
    setShowAddAuthForm(true);
    await loadAuthEvents(auth.id);
  };

  const handleStartLocChangeAuthorization = () => {
    loadLocChangeAuthForm();
    resetTimelineEventForm();
    setEditingAuthId(null);
    setViewingAuth(null);
    setShowAddAuthForm(true);
  };

  const handleAuthSaved = () => {
    setShowAddAuthForm(false);
    setEditingAuthId(null);
    resetNewAuthForm();
    clearAuthEvents();
  };

  const handleAuthDeleted = (
    deletedAuthId: string,
    authEvents: AuthEvent[]
  ) => {
    setViewingAuth((currentAuth) =>
      currentAuth?.id === deletedAuthId ? null : currentAuth
    );

    if (editingAuthId === deletedAuthId) {
      setEditingAuthId(null);
      setShowAddAuthForm(false);
      resetNewAuthForm();
    }

    if (authEvents.length > 0) {
      clearAuthEvents();
    }
  };

  const clearAuthorizationSelection = () => {
    setShowAddAuthForm(false);
    setViewingAuth(null);
    setEditingAuthId(null);
    resetNewAuthForm();
    resetTimelineEventForm();
    clearAuthEvents();
  };

  return {
    showAddAuthForm,
    setShowAddAuthForm,
    viewingAuth,
    setViewingAuth,
    editingAuthId,
    setEditingAuthId,
    handleShowAddAuthForm,
    handleCancelAuthForm,
    handleStartViewAuth,
    handleCloseViewAuth,
    handleStartEditAuth,
    handleStartLocChangeAuthorization,
    handleAuthSaved,
    handleAuthDeleted,
    clearAuthorizationSelection
  };
}

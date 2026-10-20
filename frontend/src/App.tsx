import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

// API
import {
  fetchAuthRequests,
  voidAuthRequest,
  restoreAuthRequest,
  requestAuthDeleteChallenge,
} from "./api/authStatus";
import {
  broadcastSessionLogout,
  subscribeToSessionExpiration,
  subscribeToSessionLogout,
} from "./api/client";

// Governance
import { fetchGovernanceStatus, type GovernanceStatus } from "./api/governance";
import { resolveGovernanceAccess } from "./governance/resolveGovernanceAccess";

// Security
import {
  completeWalkthrough,
  fetchCurrentUser,
  logoutUser,
  skipWalkthrough,
  updateWalkthroughStep,
  type AuthSession,
  type CurrentUser,
} from "./api/security";

// Components
import { LoginPage } from "./components/LoginPage";
import { GovernanceAttestationPage } from "./components/GovernanceAttestationPage";
import { RequiredPasswordChangePage } from "./components/RequiredPasswordChangePage";
import { SessionTimeoutManager } from "./components/SessionTimeoutManager";
import { Walkthrough } from "./components/walkthrough/Walkthrough";

// Pages
import { DashboardPage } from "./pages/DashboardPage";
import { SettingsPage } from "./pages/SettingsPage";
import { AuthorizationsPage } from "./pages/AuthorizationsPage";
import { VoidedAuthorizationsPage } from "./pages/VoidedAuthorizationsPage";
import { CalendarRoutePage } from "./pages/CalendarRoutePage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import { AdminSystemPage } from "./pages/AdminSystemPage";
import { DenialsPipelinePage } from "./pages/DenialsPipelinePage";
import { DenialInsightsPage } from "./pages/DenialInsightsPage";

// Hooks
import { useDashboardCardSettings } from "./hooks/useDashboardCardSettings";
import { useRegisteredOptions } from "./hooks/useRegisteredOptions";
import { useAuthorizationFilters } from "./hooks/useAuthorizationFilters";
import { useAuthorizationEvents } from "./hooks/useAuthorizationEvents";
import { useAuthorizationForm } from "./hooks/useAuthorizationForm";
import { useAuthorizationSelection } from "./hooks/useAuthorizationSelection";
import { useAuthorizationMutations } from "./hooks/useAuthorizationMutations";
import { useWorkflowViewMode } from "./hooks/useWorkflowViewMode";
import { useSessionTimerPreference } from "./hooks/useSessionTimerPreference";
import { useSessionActivity } from "./hooks/useSessionActivity";
import { useThemePreference } from "./hooks/useThemePreference";

// AppShell
import { AppShell } from "./components/layout/AppShell";

// Types
import type { AppPage } from "./types/navigation";
import { AuthRequest } from "./types/auth";

function App() {
  const { darkMode, setDarkMode } = useThemePreference();
  const [activePage, setActivePage] = useState<AppPage>("dashboard");
  const [detailsReturnPage, setDetailsReturnPage] =
    useState<AppPage>("authorizations");
  const [selectedDenialFollowUpAuthId, setSelectedDenialFollowUpAuthId] =
    useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [sessionExpiresAt, setSessionExpiresAt] = useState<string | null>(null);
  const [sessionWarningVisible, setSessionWarningVisible] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [governanceStatus, setGovernanceStatus] =
    useState<GovernanceStatus | null>(null);
  const [governanceError, setGovernanceError] = useState<string | null>(null);

  useSessionActivity(currentUser !== null && !sessionWarningVisible);

  const {
    dashboardCardSettings,
    handleToggleDashboardCard,
    handleResetDashboardCards,
  } = useDashboardCardSettings();
  const [authRequests, setAuthRequests] = useState<AuthRequest[]>([]);
  const activeAuthRequests = useMemo(
    () => authRequests.filter((record) => !record.isVoided),
    [authRequests]
  );
  const [pendingAction, setPendingAction] = useState<{
    type: "void" | "delete";
    auth: AuthRequest;
  } | null>(null);
  const [actionReason, setActionReason] = useState("");
  const [actionMfaCode, setActionMfaCode] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const {
    registeredFacilities,
    registeredInsurances,
    registeredWebPortals,
    newFacilityName,
    setNewFacilityName,
    newInsuranceName,
    setNewInsuranceName,
    newWebPortalName,
    setNewWebPortalName,
    facilityOptions,
    insuranceOptions,
    isLoadingRegisteredOptions,
    registeredOptionsError,
    savingCategory,
    deletingOptionId,
    isProtectedOption,
    handleAddFacility,
    handleRemoveFacility,
    handleAddInsurance,
    handleRemoveInsurance,
    handleAddWebPortal,
    handleRemoveWebPortal,
  } = useRegisteredOptions(
    authRequests,
    Boolean(
      currentUser &&
        !currentUser.must_change_password &&
        governanceStatus?.current
    )
  );

  const governanceAccessState = resolveGovernanceAccess({
    currentUser,
    governanceStatus,
    governanceError,
    isCheckingSession,
  });

  const { workflowViewMode, setWorkflowViewMode } = useWorkflowViewMode();

  const { showSessionTimer, setShowSessionTimer } = useSessionTimerPreference();

  const {
    dateRange,
    setDateRange,
    selectedFacility,
    setSelectedFacility,
    selectedInsurance,
    setSelectedInsurance,
    selectedLoc,
    setSelectedLoc,
    selectedWorkQueue,
    setSelectedWorkQueue,
    filteredData,
    comparisonFilteredData,
    comparisonPeriodLabel,
    handleClearFilters,
  } = useAuthorizationFilters({
    authRequests: activeAuthRequests,
    facilityOptions,
    insuranceOptions,
  });

  const [isLoadingAuths, setIsLoadingAuths] = useState(true);
  const [authsError, setAuthsError] = useState<string | null>(null);
  const {
    isCreatingAuth,
    deletingAuthId,
    saveAuthorization,
    removeAuthorization,
  } = useAuthorizationMutations();

  const {
    authEvents,
    isLoadingAuthEvents,
    isSavingAuthEvent,
    authEventsError,
    editingAuthEventId,
    confirmingDeleteAuthEventId,
    timelineEventForm,
    resetTimelineEventForm,
    clearAuthEvents,
    loadAuthEvents,
    handleTimelineEventFieldChange,
    handleAddTimelineEvent,
    handleStartEditTimelineEvent,
    handleCancelEditTimelineEvent,
    handleUpdateTimelineEvent,
    handleStartDeleteTimelineEvent,
    handleCancelDeleteTimelineEvent,
    handleConfirmDeleteTimelineEvent,
    handleStartContinuedStay,
  } = useAuthorizationEvents();

  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      try {
        const authSession = await fetchCurrentUser();

        if (isMounted) {
          setCurrentUser(authSession.user);
          setSessionExpiresAt(authSession.session.expires_at);
        }
      } catch {
        if (isMounted) {
          setCurrentUser(null);
          setSessionExpiresAt(null);
        }
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    }

    void restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    if (!currentUser || currentUser.must_change_password) {
      setGovernanceStatus(null);
      setGovernanceError(null);

      return () => {
        isMounted = false;
      };
    }

    async function loadGovernanceStatus() {
      try {
        setGovernanceError(null);

        const status = await fetchGovernanceStatus();

        if (isMounted) {
          setGovernanceStatus(status);
        }
      } catch (error) {
        if (isMounted) {
          setGovernanceStatus(null);
          setGovernanceError(
            error instanceof Error
              ? error.message
              : "Unable to load governance status."
          );
        }
      }
    }

    void loadGovernanceStatus();

    return () => {
      isMounted = false;
    };
  }, [currentUser]);

  useEffect(() => {
    return subscribeToSessionExpiration((expiresAt) => {
      setSessionExpiresAt((currentExpiration) => {
        if (!currentExpiration) {
          return expiresAt;
        }

        const currentTime = Date.parse(currentExpiration);
        const updatedTime = Date.parse(expiresAt);

        if (Number.isNaN(currentTime) || Number.isNaN(updatedTime)) {
          return currentExpiration;
        }

        return updatedTime > currentTime ? expiresAt : currentExpiration;
      });
    });
  }, []);
  const {
    newAuthForm,
    resetNewAuthForm,
    handleNewAuthFieldChange,
    loadAuthIntoForm,
    loadLocChangeAuthForm,
  } = useAuthorizationForm();

  useEffect(() => {
    let isMounted = true;

    if (
      !currentUser ||
      currentUser.must_change_password ||
      !governanceStatus?.current
    ) {
      setIsLoadingAuths(false);
      setAuthsError(null);

      return () => {
        isMounted = false;
      };
    }

    async function loadAuthRequests() {
      try {
        setIsLoadingAuths(true);
        setAuthsError(null);

        const records = await fetchAuthRequests();

        if (isMounted) {
          setAuthRequests(records);
        }
      } catch (error) {
        if (isMounted) {
          setAuthsError(
            error instanceof Error
              ? error.message
              : "Unable to load authorization records."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingAuths(false);
        }
      }
    }

    void loadAuthRequests();

    return () => {
      isMounted = false;
    };
  }, [currentUser, governanceStatus?.current]);

  const {
    showAddAuthForm,
    viewingAuth,
    editingAuthId,
    handleShowAddAuthForm,
    handleCancelAuthForm,
    handleStartViewAuth,
    handleCloseViewAuth,
    handleStartEditAuth,
    handleStartLocChangeAuthorization,
    handleAuthSaved,
    handleAuthDeleted,
    clearAuthorizationSelection,
  } = useAuthorizationSelection({
    resetNewAuthForm,
    loadAuthIntoForm,
    loadLocChangeAuthForm,
    resetTimelineEventForm,
    clearAuthEvents,
    loadAuthEvents,
  });

  const refreshAuthRequests = async () => {
    const records = await fetchAuthRequests();
    setAuthRequests(records);

    if (editingAuthId) {
      const updatedAuth = records.find((auth) => auth.id === editingAuthId);

      if (updatedAuth) {
        loadAuthIntoForm(updatedAuth);
      }
    }
  };

  const openAuthorizationAction = (
    type: "void" | "delete",
    auth: AuthRequest
  ) => {
    if (type === "delete" && currentUser?.role !== "Admin") return;
    if (
      type === "void" &&
      (auth.isVoided || !["Admin", "UR"].includes(currentUser?.role ?? ""))
    )
      return;
    setPendingAction({ type, auth });
    setActionReason("");
    setActionMfaCode("");
    setActionError(null);
  };

  const handleAuthorizationAction = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    if (!pendingAction || actionBusy) return;
    const reason = actionReason.trim();
    if (reason.length < 3 || reason.length > 500) {
      setActionError("Reason must be 3 to 500 characters.");
      return;
    }
    setActionBusy(true);
    setActionError(null);
    try {
      if (pendingAction.type === "void") {
        await voidAuthRequest(pendingAction.auth.id, reason);
      } else {
        if (currentUser?.role !== "Admin")
          throw new Error("Admin access required.");
        if (!/^\d{6}$/.test(actionMfaCode))
          throw new Error("Enter a six-digit MFA code.");
        const challenge = await requestAuthDeleteChallenge(
          pendingAction.auth.id
        );
        await removeAuthorization(pendingAction.auth, {
          reason,
          code: actionMfaCode,
          challenge_token: challenge.challenge_token,
        });
        handleAuthDeleted(pendingAction.auth.id, authEvents);
      }
      await refreshAuthRequests();
      setPendingAction(null);
      setActionMfaCode("");
      setActionReason("");
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Authorization action failed."
      );
    } finally {
      setActionBusy(false);
    }
  };

  const handleRestoreAuth = async (auth: AuthRequest) => {
    if (currentUser?.role !== "Admin") return;
    setAuthsError(null);
    try {
      await restoreAuthRequest(auth.id);
      await refreshAuthRequests();
    } catch (error) {
      setAuthsError(
        error instanceof Error
          ? error.message
          : "Unable to restore authorization."
      );
    }
  };

  useEffect(() => {
    if (!registeredFacilities.includes(newAuthForm.facility)) {
      handleNewAuthFieldChange("facility", registeredFacilities[0] ?? "");
    }

    if (!registeredInsurances.includes(newAuthForm.insurance)) {
      handleNewAuthFieldChange("insurance", registeredInsurances[0] ?? "");
    }

    if (!registeredWebPortals.includes(newAuthForm.webPortal)) {
      handleNewAuthFieldChange("webPortal", registeredWebPortals[0] ?? "");
    }
  }, [
    registeredFacilities,
    registeredInsurances,
    registeredWebPortals,
    newAuthForm.facility,
    newAuthForm.insurance,
    newAuthForm.webPortal,
  ]);

  const handleOpenAuthDetails = async (auth: AuthRequest) => {
    setDetailsReturnPage(activePage);
    setActivePage("authorizations");
    await handleStartViewAuth(auth);
  };

  const handleBackFromAuthDetails = () => {
    handleCloseViewAuth();
    setActivePage(detailsReturnPage);
  };

  const handleOpenDenialFollowUp = (auth: AuthRequest) => {
    setSelectedDenialFollowUpAuthId(auth.id);
    handleCloseViewAuth();
    setActivePage("denials-pipeline");
  };

  const handleCreateAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthsError(null);

    try {
      const savedAuth = await saveAuthorization({
        editingAuthId,
        form: newAuthForm,
      });

      setAuthRequests((currentAuths) => {
        if (editingAuthId) {
          return currentAuths.map((auth) =>
            auth.id === savedAuth.id ? savedAuth : auth
          );
        }

        return [savedAuth, ...currentAuths];
      });

      handleAuthSaved();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to save authorization.";
      setAuthsError(message);
    }
  };

  const handleLogin = (authSession: AuthSession) => {
    setCurrentUser(authSession.user);
    setSessionExpiresAt(authSession.session.expires_at);
    setSessionWarningVisible(false);
    setGovernanceStatus(null);
    setGovernanceError(null);
    setActivePage("dashboard");
  };

  const clearAuthenticatedState = useCallback(() => {
    setCurrentUser(null);
    setSessionExpiresAt(null);
    setSessionWarningVisible(false);
    setGovernanceStatus(null);
    setGovernanceError(null);
    setAuthRequests([]);
    setSelectedDenialFollowUpAuthId(null);
    clearAuthorizationSelection();
    setActivePage("dashboard");
  }, [clearAuthorizationSelection]);

  useEffect(() => {
    return subscribeToSessionLogout(() => {
      clearAuthenticatedState();
    });
  }, [clearAuthenticatedState]);

  const handleRequiredPasswordChanged = async () => {
    try {
      await logoutUser();
    } finally {
      broadcastSessionLogout();
      clearAuthenticatedState();
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } finally {
      broadcastSessionLogout();
      clearAuthenticatedState();
    }
  };

  const handleSessionExpired = useCallback(() => {
    clearAuthenticatedState();
  }, [clearAuthenticatedState]);

  const handleMfaEnabledChange = useCallback((enabled: boolean) => {
    setCurrentUser((currentValue) =>
      currentValue
        ? {
            ...currentValue,
            mfa_enabled: enabled,
          }
        : currentValue
    );
  }, []);

  const handleWalkthroughStepChange = useCallback(async (stepId: string) => {
    const result = await updateWalkthroughStep(stepId);

    setCurrentUser((currentValue) =>
      currentValue
        ? {
            ...currentValue,
            walkthrough_status: result.walkthrough_status,
            walkthrough_step: result.walkthrough_step,
          }
        : currentValue
    );
  }, []);

  const handleWalkthroughComplete = useCallback(async () => {
    const result = await completeWalkthrough();

    setCurrentUser((currentValue) =>
      currentValue
        ? {
            ...currentValue,
            walkthrough_status: result.walkthrough_status,
            walkthrough_step: result.walkthrough_step,
          }
        : currentValue
    );
  }, []);

  const handleWalkthroughSkip = useCallback(async () => {
    const result = await skipWalkthrough();

    setCurrentUser((currentValue) =>
      currentValue
        ? {
            ...currentValue,
            walkthrough_status: result.walkthrough_status,
            walkthrough_step: result.walkthrough_step,
          }
        : currentValue
    );
  }, []);

  if (governanceAccessState === "loading") {
    return (
      <div
        className={
          darkMode ? "min-h-screen bg-gray-950" : "min-h-screen bg-gray-50"
        }
      />
    );
  }

  if (governanceAccessState === "unauthenticated") {
    return <LoginPage darkMode={darkMode} onLogin={handleLogin} />;
  }

  if (governanceAccessState === "password_change_required" && currentUser) {
    return (
      <RequiredPasswordChangePage
        darkMode={darkMode}
        username={currentUser.username}
        onPasswordChanged={handleRequiredPasswordChanged}
        onLogout={handleLogout}
      />
    );
  }

  if (governanceAccessState === "error") {
    return (
      <main
        className={
          darkMode
            ? "flex min-h-screen items-center justify-center bg-gray-950 px-4 text-gray-100"
            : "flex min-h-screen items-center justify-center bg-gray-50 px-4 text-gray-900"
        }
      >
        <div className="w-full max-w-lg text-center">
          <h1 className="mb-2 text-xl font-semibold">
            Unable to load governance status
          </h1>

          <p className="mb-6 text-sm opacity-75">
            {governanceError ?? "Unable to load governance status."}
          </p>

          <button
            type="button"
            onClick={() => void handleLogout()}
            className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700"
          >
            Sign out
          </button>
        </div>
      </main>
    );
  }

  if (
    governanceAccessState === "attestation_required" &&
    governanceStatus &&
    currentUser
  ) {
    return (
      <>
        <GovernanceAttestationPage
          darkMode={darkMode}
          username={currentUser.username}
          requiredVersion={governanceStatus.required_version}
          canAccept={currentUser.role === "Admin"}
          onAccepted={(attestation) => {
            setGovernanceStatus({
              required_version: governanceStatus.required_version,
              required_document_revision:
                governanceStatus.required_document_revision,
              current: true,
              attestation,
            });
          }}
          onLogout={handleLogout}
        />

        {sessionExpiresAt && (
          <SessionTimeoutManager
            darkMode={darkMode}
            expiresAt={sessionExpiresAt}
            showTimer={showSessionTimer}
            onSessionRenewed={setSessionExpiresAt}
            onSessionExpired={handleSessionExpired}
            onWarningVisibilityChange={setSessionWarningVisible}
            onLogout={() => {
              void handleLogout();
            }}
          />
        )}
      </>
    );
  }

  const handlePasswordChanged = async () => {
    try {
      await logoutUser();
    } finally {
      broadcastSessionLogout();
      clearAuthenticatedState();
    }
  };

  if (governanceAccessState !== "ready" || !currentUser) {
    return null;
  }

  const canManageAuthorizations =
    currentUser.role === "Admin" || currentUser.role === "UR";

  const canManageUsers = currentUser.role === "Admin";

  return (
    <>
      <AppShell
        activePage={activePage}
        darkMode={darkMode}
        currentUser={currentUser}
        canManageUsers={canManageUsers}
        onPageChange={setActivePage}
        onToggleDarkMode={() => setDarkMode((currentValue) => !currentValue)}
        onLogout={handleLogout}
      >
        {activePage === "dashboard" && (
          <DashboardPage
            darkMode={darkMode}
            workflowViewMode={workflowViewMode}
            isLoadingAuths={isLoadingAuths}
            authsError={authsError}
            dateRange={dateRange}
            setDateRange={setDateRange}
            selectedFacility={selectedFacility}
            setSelectedFacility={setSelectedFacility}
            facilities={facilityOptions}
            selectedInsurance={selectedInsurance}
            setSelectedInsurance={setSelectedInsurance}
            insurances={insuranceOptions}
            selectedLoc={selectedLoc}
            setSelectedLoc={setSelectedLoc}
            selectedWorkQueue={selectedWorkQueue}
            setSelectedWorkQueue={setSelectedWorkQueue}
            onClearFilters={handleClearFilters}
            dashboardCardSettings={dashboardCardSettings}
            filteredData={filteredData}
            comparisonFilteredData={comparisonFilteredData}
            comparisonPeriodLabel={comparisonPeriodLabel}
            onViewAuth={handleOpenAuthDetails}
          />
        )}

        {activePage === "calendar" && (
          <CalendarRoutePage
            darkMode={darkMode}
            isLoadingAuths={isLoadingAuths}
            authsError={authsError}
            dateRange={dateRange}
            setDateRange={setDateRange}
            selectedFacility={selectedFacility}
            setSelectedFacility={setSelectedFacility}
            facilities={facilityOptions}
            selectedInsurance={selectedInsurance}
            setSelectedInsurance={setSelectedInsurance}
            insurances={insuranceOptions}
            selectedLoc={selectedLoc}
            setSelectedLoc={setSelectedLoc}
            selectedWorkQueue={selectedWorkQueue}
            setSelectedWorkQueue={setSelectedWorkQueue}
            onClearFilters={handleClearFilters}
            filteredData={filteredData}
            onSelectAuth={handleOpenAuthDetails}
          />
        )}

        {activePage === "authorizations" && (
          <AuthorizationsPage
            darkMode={darkMode}
            isLoadingAuths={isLoadingAuths}
            authsError={authsError}
            dateRange={dateRange}
            setDateRange={setDateRange}
            selectedFacility={selectedFacility}
            setSelectedFacility={setSelectedFacility}
            facilities={facilityOptions}
            selectedInsurance={selectedInsurance}
            setSelectedInsurance={setSelectedInsurance}
            insurances={insuranceOptions}
            selectedLoc={selectedLoc}
            setSelectedLoc={setSelectedLoc}
            selectedWorkQueue={selectedWorkQueue}
            setSelectedWorkQueue={setSelectedWorkQueue}
            onClearFilters={handleClearFilters}
            filteredData={filteredData}
            showAddAuthForm={showAddAuthForm}
            viewingAuth={viewingAuth}
            editingAuthId={editingAuthId}
            newAuthForm={newAuthForm}
            isCreatingAuth={isCreatingAuth}
            registeredFacilities={registeredFacilities}
            registeredInsurances={registeredInsurances}
            registeredWebPortals={registeredWebPortals}
            authEvents={authEvents}
            workflowViewMode={workflowViewMode}
            canManageAuthorizations={canManageAuthorizations}
            authEventsError={authEventsError}
            isLoadingAuthEvents={isLoadingAuthEvents}
            isSavingAuthEvent={isSavingAuthEvent}
            editingAuthEventId={editingAuthEventId}
            confirmingDeleteAuthEventId={confirmingDeleteAuthEventId}
            timelineEventForm={timelineEventForm}
            deletingAuthId={deletingAuthId}
            onShowAddAuthForm={handleShowAddAuthForm}
            onCancelAuthForm={handleCancelAuthForm}
            onCloseViewAuth={handleBackFromAuthDetails}
            onStartLocChangeAuthorization={handleStartLocChangeAuthorization}
            onFieldChange={handleNewAuthFieldChange}
            onSubmitAuth={handleCreateAuth}
            onViewAuth={(auth) => {
              setDetailsReturnPage("authorizations");
              void handleStartViewAuth(auth);
            }}
            onEditAuth={handleStartEditAuth}
            onManageDenialFollowUp={handleOpenDenialFollowUp}
            onDeleteAuth={(auth) => openAuthorizationAction("delete", auth)}
            onVoidAuth={(auth) => openAuthorizationAction("void", auth)}
            canDeleteAuthorizations={canManageUsers}
            onTimelineEventFieldChange={handleTimelineEventFieldChange}
            onAddTimelineEvent={async () => {
              if (!editingAuthId) {
                return;
              }

              await handleAddTimelineEvent(editingAuthId);
              await refreshAuthRequests();
            }}
            onAddTimelineEventAndReturn={async () => {
              if (!editingAuthId) {
                return;
              }

              await handleAddTimelineEvent(editingAuthId);
              await refreshAuthRequests();
              handleCancelAuthForm();
            }}
            onStartEditTimelineEvent={handleStartEditTimelineEvent}
            onCancelEditTimelineEvent={handleCancelEditTimelineEvent}
            onUpdateTimelineEvent={async (eventId, payload) => {
              if (!editingAuthId) {
                return;
              }

              await handleUpdateTimelineEvent(editingAuthId, eventId, payload);
              await refreshAuthRequests();
            }}
            onUpdateTimelineEventAndReturn={async (eventId, payload) => {
              if (!editingAuthId) {
                return;
              }

              await handleUpdateTimelineEvent(editingAuthId, eventId, payload);
              await refreshAuthRequests();
              handleCancelAuthForm();
            }}
            onStartDeleteTimelineEvent={handleStartDeleteTimelineEvent}
            onCancelDeleteTimelineEvent={handleCancelDeleteTimelineEvent}
            onConfirmDeleteTimelineEvent={async (eventId) => {
              if (!editingAuthId) {
                return;
              }

              await handleConfirmDeleteTimelineEvent(editingAuthId, eventId);
              await refreshAuthRequests();
            }}
            onStartContinuedStay={() =>
              handleStartContinuedStay({
                programmingDays: newAuthForm.programmingDays,
                authEndDate: newAuthForm.endDate,
                requestedDays: newAuthForm.requestedDays,
                approvedDays: newAuthForm.approvedDays,
              })
            }
          />
        )}

        {activePage === "denials-pipeline" && (
          <DenialsPipelinePage
            data={activeAuthRequests}
            darkMode={darkMode}
            selectedAuthId={selectedDenialFollowUpAuthId}
            canManageAuthorizations={canManageAuthorizations}
            onSelectAuth={(auth) => {
              setSelectedDenialFollowUpAuthId(auth.id);
            }}
            onClearSelectedAuth={() => {
              setSelectedDenialFollowUpAuthId(null);
            }}
            onAuthUpdated={(updatedAuth) => {
              setAuthRequests((currentAuths) =>
                currentAuths.map((auth) =>
                  auth.id === updatedAuth.id ? updatedAuth : auth
                )
              );
              setSelectedDenialFollowUpAuthId(null);
            }}
          />
        )}

        {activePage === "denial-insights" && canManageAuthorizations && (
          <DenialInsightsPage
            darkMode={darkMode}
            canShowEvidenceCalculation={currentUser.role === "Admin"}
          />
        )}

        {(activePage === "voided-authorizations" ||
          (activePage === "authorizations" &&
            detailsReturnPage === "voided-authorizations")) && (
          <div hidden={activePage !== "voided-authorizations"}>
            <VoidedAuthorizationsPage
              records={authRequests}
              darkMode={darkMode}
              isAdmin={canManageUsers}
              onView={handleOpenAuthDetails}
              onRestore={(auth) => {
                void handleRestoreAuth(auth);
              }}
              onDelete={(auth) => openAuthorizationAction("delete", auth)}
            />
          </div>
        )}
        {activePage === "settings" && (
          <SettingsPage
            darkMode={darkMode}
            currentUser={currentUser}
            onMfaEnabledChange={handleMfaEnabledChange}
            showSessionTimer={showSessionTimer}
            onShowSessionTimerChange={setShowSessionTimer}
            newFacilityName={newFacilityName}
            setNewFacilityName={setNewFacilityName}
            registeredFacilities={registeredFacilities}
            onAddFacility={handleAddFacility}
            onRemoveFacility={handleRemoveFacility}
            newInsuranceName={newInsuranceName}
            setNewInsuranceName={setNewInsuranceName}
            registeredInsurances={registeredInsurances}
            onAddInsurance={handleAddInsurance}
            onRemoveInsurance={handleRemoveInsurance}
            newWebPortalName={newWebPortalName}
            setNewWebPortalName={setNewWebPortalName}
            registeredWebPortals={registeredWebPortals}
            onAddWebPortal={handleAddWebPortal}
            onRemoveWebPortal={handleRemoveWebPortal}
            dashboardCardSettings={dashboardCardSettings}
            onToggleDashboardCard={handleToggleDashboardCard}
            onResetDashboardCards={handleResetDashboardCards}
            workflowViewMode={workflowViewMode}
            onWorkflowViewModeChange={setWorkflowViewMode}
            onPasswordChanged={handlePasswordChanged}
            isLoadingRegisteredOptions={isLoadingRegisteredOptions}
            registeredOptionsError={registeredOptionsError}
            savingCategory={savingCategory}
            deletingOptionId={deletingOptionId}
            isProtectedOption={isProtectedOption}
            canManageRegisteredOptions={canManageUsers}
          />
        )}

        {activePage === "adminUsers" && canManageUsers && (
          <AdminUsersPage darkMode={darkMode} currentUser={currentUser} />
        )}

        {activePage === "adminAudit" && canManageUsers && (
          <AdminAuditPage darkMode={darkMode} />
        )}

        {activePage === "adminSystem" && canManageUsers && (
          <AdminSystemPage darkMode={darkMode} />
        )}
      </AppShell>

      {pendingAction && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        >
          <form
            onSubmit={(event) => {
              void handleAuthorizationAction(event);
            }}
            role="dialog"
            aria-modal="true"
            aria-label={`${pendingAction.type} authorization`}
            className={`w-full max-w-md space-y-4 rounded-lg border p-6 shadow-xl ${
              darkMode
                ? "border-gray-700 bg-gray-900 text-white"
                : "border-gray-200 bg-white text-gray-900"
            }`}
          >
            <h2 className="text-xl font-semibold">
              {pendingAction.type === "void"
                ? "Void authorization"
                : "Permanently delete authorization"}
            </h2>
            <p className="text-sm">
              {pendingAction.auth.patientId} · {pendingAction.auth.facility}
            </p>
            {pendingAction.type === "delete" && (
              <p className="text-sm text-red-500">
                This permanently removes the record and its related data. This
                action cannot be undone.
              </p>
            )}
            <label className="block space-y-1 text-sm">
              Reason
              <textarea
                required
                minLength={3}
                maxLength={500}
                value={actionReason}
                onChange={(event) => setActionReason(event.target.value)}
                className="w-full rounded border border-gray-400 bg-transparent p-2"
                rows={3}
              />
            </label>
            {pendingAction.type === "delete" && (
              <label className="block space-y-1 text-sm">
                Six-digit authenticator code
                <input
                  required
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={actionMfaCode}
                  onChange={(event) => setActionMfaCode(event.target.value)}
                  className="w-full rounded border border-gray-400 bg-transparent p-2"
                />
              </label>
            )}
            {actionError && (
              <p role="alert" className="text-sm text-red-500">
                {actionError}
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                disabled={actionBusy}
                className="rounded border px-4 py-2"
                onClick={() => setPendingAction(null)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={actionBusy}
                className="rounded bg-red-700 px-4 py-2 text-white disabled:opacity-50"
              >
                {actionBusy
                  ? "Working..."
                  : pendingAction.type === "void"
                  ? "Confirm void"
                  : "Verify MFA and delete"}
              </button>
            </div>
          </form>
        </div>
      )}

      {currentUser.walkthrough_status === "pending" && (
        <Walkthrough
          darkMode={darkMode}
          role={currentUser.role}
          activePage={activePage}
          initialStepId={currentUser.walkthrough_step}
          onPageChange={setActivePage}
          onStepChange={handleWalkthroughStepChange}
          onComplete={handleWalkthroughComplete}
          onSkip={handleWalkthroughSkip}
        />
      )}

      {sessionExpiresAt && (
        <SessionTimeoutManager
          darkMode={darkMode}
          expiresAt={sessionExpiresAt}
          showTimer={showSessionTimer}
          onSessionRenewed={setSessionExpiresAt}
          onSessionExpired={handleSessionExpired}
          onWarningVisibilityChange={setSessionWarningVisible}
          onLogout={() => {
            void handleLogout();
          }}
        />
      )}
    </>
  );
}

export default App;

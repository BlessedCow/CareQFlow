import { useCallback, useEffect, useState, type FormEvent } from "react";

// API
import { fetchAuthRequests } from "./api/authStatus";
import {
  broadcastSessionLogout,
  subscribeToSessionExpiration,
  subscribeToSessionLogout,
} from "./api/client";

// Security
import {
  fetchCurrentUser,
  logoutUser,
  type AuthSession,
  type CurrentUser,
} from "./api/security";

// Components
import { LoginPage } from "./components/LoginPage";
import { RequiredPasswordChangePage } from "./components/RequiredPasswordChangePage";
import { SessionTimeoutManager } from "./components/SessionTimeoutManager";

// Pages
import { DashboardPage } from "./pages/DashboardPage";
import { SettingsPage } from "./pages/SettingsPage";
import { AuthorizationsPage } from "./pages/AuthorizationsPage";
import { CalendarRoutePage } from "./pages/CalendarRoutePage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import { AdminSystemPage } from "./pages/AdminSystemPage";
import { DenialsPipelinePage } from "./pages/DenialsPipelinePage";

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

// AppShell
import { AppShell } from "./components/layout/AppShell";

// Types
import type { AppPage } from "./types/navigation";
import { AuthRequest } from "./types/auth";

function App() {
  const [darkMode, setDarkMode] = useState(true);
  const [activePage, setActivePage] = useState<AppPage>("dashboard");
  const [selectedDenialFollowUpAuthId, setSelectedDenialFollowUpAuthId] =
    useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [sessionExpiresAt, setSessionExpiresAt] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useSessionActivity(currentUser !== null);

  const {
    dashboardCardSettings,
    handleToggleDashboardCard,
    handleResetDashboardCards,
  } = useDashboardCardSettings();
  const [authRequests, setAuthRequests] = useState<AuthRequest[]>([]);
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
    Boolean(currentUser && !currentUser.must_change_password)
  );

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
    authRequests,
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
    return subscribeToSessionExpiration((expiresAt) => {
      setSessionExpiresAt((currentExpiration) => {
        if (!currentExpiration) {
          return expiresAt;
        }
  
        const currentTime = Date.parse(currentExpiration);
        const updatedTime = Date.parse(expiresAt);
  
        if (
          Number.isNaN(currentTime) ||
          Number.isNaN(updatedTime)
        ) {
          return currentExpiration;
        }
  
        return updatedTime > currentTime
          ? expiresAt
          : currentExpiration;
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

    if (!currentUser || currentUser.must_change_password) {
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
  }, [currentUser]);

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

  const handleDeleteAuth = async (auth: AuthRequest) => {
    setAuthsError(null);

    try {
      await removeAuthorization(auth);

      setAuthRequests((currentAuths) =>
        currentAuths.filter((item) => item.id !== auth.id)
      );
      handleAuthDeleted(auth.id, authEvents);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to delete authorization.";
      setAuthsError(message);
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
    setActivePage("authorizations");
    await handleStartViewAuth(auth);
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
    setActivePage("dashboard");
  };

  const clearAuthenticatedState = useCallback(() => {
    setCurrentUser(null);
    setSessionExpiresAt(null);
    setAuthRequests([]);
    clearAuthEvents();
    handleCancelAuthForm();
    setActivePage("dashboard");
  }, [clearAuthEvents, handleCancelAuthForm]);

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

  if (isCheckingSession) {
    return (
      <div
        className={
          darkMode ? "min-h-screen bg-gray-950" : "min-h-screen bg-gray-50"
        }
      />
    );
  }

  if (!currentUser) {
    return <LoginPage darkMode={darkMode} onLogin={handleLogin} />;
  }

  if (currentUser.must_change_password) {
    return (
      <RequiredPasswordChangePage
        darkMode={darkMode}
        username={currentUser.username}
        onPasswordChanged={handleRequiredPasswordChanged}
        onLogout={handleLogout}
      />
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
            onCloseViewAuth={handleCloseViewAuth}
            onStartLocChangeAuthorization={handleStartLocChangeAuthorization}
            onFieldChange={handleNewAuthFieldChange}
            onSubmitAuth={handleCreateAuth}
            onViewAuth={handleStartViewAuth}
            onEditAuth={handleStartEditAuth}
            onManageDenialFollowUp={handleOpenDenialFollowUp}
            onDeleteAuth={handleDeleteAuth}
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
            data={authRequests}
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

      {sessionExpiresAt && (
        <SessionTimeoutManager
          darkMode={darkMode}
          expiresAt={sessionExpiresAt}
          showTimer={showSessionTimer}
          onSessionRenewed={setSessionExpiresAt}
          onSessionExpired={handleSessionExpired}
          onLogout={() => {
            void handleLogout();
          }}
        />
      )}
    </>
  );
}

export default App;

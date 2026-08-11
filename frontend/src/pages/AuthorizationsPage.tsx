import type { FormEvent } from "react";
import type { AuthEvent, UpdateAuthEventPayload } from "../api/authEvents";
import { AddAuthorizationForm } from "../components/AddAuthorizationForm";
import {
  AuthTimelineSection,
  type TimelineEventFormState,
} from "../components/AuthTimelineSection";
import { AuthorizationReadOnlyView } from "../components/AuthorizationReadOnlyView";
import { DataTable } from "../components/DataTable";
import Filters, {
  type LocFilter,
  type WorkQueueFilter,
} from "../components/Filters";
import type { NewAuthFormState } from "../hooks/useAuthorizationForm";
import type { WorkflowViewMode } from "../hooks/useWorkflowViewMode";
import type { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";

type DateRange = "7d" | "30d" | "90d" | "all";

interface AuthorizationsPageProps {
  darkMode: boolean;
  isLoadingAuths: boolean;
  authsError: string | null;
  dateRange: DateRange;
  setDateRange: (value: DateRange) => void;
  selectedFacility: string;
  setSelectedFacility: (value: string) => void;
  facilities: string[];
  selectedInsurance: string;
  setSelectedInsurance: (value: string) => void;
  insurances: string[];
  selectedWorkQueue: WorkQueueFilter;
  setSelectedWorkQueue: (value: WorkQueueFilter) => void;
  onClearFilters: () => void;
  workflowViewMode: WorkflowViewMode;
  canManageAuthorizations: boolean;
  filteredData: AuthRequest[];
  showAddAuthForm: boolean;
  viewingAuth: AuthRequest | null;
  editingAuthId: string | null;
  newAuthForm: NewAuthFormState;
  isCreatingAuth: boolean;
  registeredFacilities: string[];
  registeredInsurances: string[];
  selectedLoc: LocFilter;
  setSelectedLoc: (value: LocFilter) => void;
  registeredWebPortals: string[];
  authEvents: AuthEvent[];
  authEventsError: string | null;
  isLoadingAuthEvents: boolean;
  isSavingAuthEvent: boolean;
  editingAuthEventId: number | null;
  confirmingDeleteAuthEventId: number | null;
  timelineEventForm: TimelineEventFormState;
  deletingAuthId: string | null;
  onShowAddAuthForm: () => void;
  onCancelAuthForm: () => void;
  onCloseViewAuth: () => void;
  onStartLocChangeAuthorization: () => void;
  onFieldChange: (
    field: keyof NewAuthFormState,
    value: string | boolean
  ) => void;
  onSubmitAuth: (event: FormEvent<HTMLFormElement>) => void;
  onViewAuth: (auth: AuthRequest) => void;
  onEditAuth: (auth: AuthRequest) => void;
  onManageDenialFollowUp: (auth: AuthRequest) => void;
  onDeleteAuth: (auth: AuthRequest) => void;
  onTimelineEventFieldChange: (
    field: keyof TimelineEventFormState,
    value: string
  ) => void;
  onAddTimelineEvent: () => void;
  onAddTimelineEventAndReturn: () => void;
  onStartEditTimelineEvent: (event: AuthEvent) => void;
  onCancelEditTimelineEvent: () => void;
  onUpdateTimelineEvent: (
    eventId: number,
    payload: UpdateAuthEventPayload
  ) => void;
  onUpdateTimelineEventAndReturn: (
    eventId: number,
    payload: UpdateAuthEventPayload
  ) => void;
  onStartDeleteTimelineEvent: (eventId: number) => void;
  onCancelDeleteTimelineEvent: () => void;
  onConfirmDeleteTimelineEvent: (eventId: number) => void;
  onStartContinuedStay: () => void;
}

export function AuthorizationsPage({
  darkMode,
  isLoadingAuths,
  authsError,
  dateRange,
  setDateRange,
  selectedFacility,
  setSelectedFacility,
  facilities,
  selectedInsurance,
  setSelectedInsurance,
  insurances,
  selectedLoc,
  setSelectedLoc,
  selectedWorkQueue,
  setSelectedWorkQueue,
  onClearFilters,
  canManageAuthorizations,
  filteredData,
  showAddAuthForm,
  viewingAuth,
  editingAuthId,
  newAuthForm,
  isCreatingAuth,
  registeredFacilities,
  registeredInsurances,
  registeredWebPortals,
  authEvents,
  authEventsError,
  isLoadingAuthEvents,
  isSavingAuthEvent,
  editingAuthEventId,
  confirmingDeleteAuthEventId,
  timelineEventForm,
  deletingAuthId,
  workflowViewMode,
  onShowAddAuthForm,
  onCancelAuthForm,
  onCloseViewAuth,
  onStartLocChangeAuthorization,
  onFieldChange,
  onSubmitAuth,
  onViewAuth,
  onEditAuth,
  onManageDenialFollowUp,
  onDeleteAuth,
  onTimelineEventFieldChange,
  onAddTimelineEvent,
  onAddTimelineEventAndReturn,
  onStartEditTimelineEvent,
  onCancelEditTimelineEvent,
  onUpdateTimelineEvent,
  onUpdateTimelineEventAndReturn,
  onStartDeleteTimelineEvent,
  onCancelDeleteTimelineEvent,
  onConfirmDeleteTimelineEvent,
  onStartContinuedStay,
}: AuthorizationsPageProps) {
  const editingAuth = editingAuthId
    ? filteredData.find((auth) => auth.id === editingAuthId) ?? null
    : null;

  return (
    <>
      {isLoadingAuths && (
        <div
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-blue-900/60 bg-blue-950/30 text-blue-200"
              : "border-blue-200 bg-blue-50 text-blue-700"
          )}
        >
          Loading authorization records...
        </div>
      )}

      {authsError && (
        <div
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900/60 bg-red-950/30 text-red-200"
              : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          {authsError}
        </div>
      )}

      {!showAddAuthForm && !viewingAuth && (
        <Filters
          dateRange={dateRange}
          setDateRange={setDateRange}
          selectedFacility={selectedFacility}
          setSelectedFacility={setSelectedFacility}
          facilities={facilities}
          selectedInsurance={selectedInsurance}
          setSelectedInsurance={setSelectedInsurance}
          insurances={insurances}
          selectedLoc={selectedLoc}
          setSelectedLoc={setSelectedLoc}
          selectedWorkQueue={selectedWorkQueue}
          setSelectedWorkQueue={setSelectedWorkQueue}
          darkMode={darkMode}
          onClearFilters={onClearFilters}
        />
      )}

      <div
        className={cn(
          "flex flex-col overflow-hidden rounded-xl border p-5 shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div className="mb-4 flex shrink-0 items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">
              {showAddAuthForm
                ? editingAuthId
                  ? "Edit Authorization"
                  : newAuthForm.authType === "Concurrent"
                  ? "Add LOC Change"
                  : "Add Authorization"
                : viewingAuth
                ? "Authorization Details"
                : "Authorization Work Queue"}
            </h3>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              {showAddAuthForm
                ? editingAuthId
                  ? "Update authorization details and timeline events."
                  : newAuthForm.authType === "Concurrent"
                  ? "Create a new authorization record for a level of care change."
                  : "Create a new authorization record."
                : viewingAuth
                ? "Review authorization details and timeline history."
                : "View authorization records by facility and date range."}
            </p>
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            {canManageAuthorizations && showAddAuthForm && editingAuthId && (
              <button
                type="button"
                onClick={onStartLocChangeAuthorization}
                className={cn(
                  "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
                  darkMode
                    ? "border-emerald-800 bg-emerald-950/40 text-emerald-200 hover:bg-emerald-900/50"
                    : "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                )}
              >
                Start LOC Change
              </button>
            )}

            {(canManageAuthorizations || showAddAuthForm || viewingAuth) && (
              <button
                type="button"
                onClick={() => {
                  if (viewingAuth) {
                    onCloseViewAuth();
                    return;
                  }

                  if (showAddAuthForm) {
                    onCancelAuthForm();
                    return;
                  }

                  if (canManageAuthorizations) {
                    onShowAddAuthForm();
                  }
                }}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  darkMode
                    ? "bg-blue-600 text-white hover:bg-blue-500"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                )}
              >
                {showAddAuthForm
                  ? editingAuthId
                    ? "Close Edit"
                    : "Close Form"
                  : viewingAuth
                  ? "Back to List"
                  : "Add Authorization"}
              </button>
            )}
          </div>
        </div>

        {canManageAuthorizations && showAddAuthForm && (
          <>
            <AddAuthorizationForm
              form={newAuthForm}
              darkMode={darkMode}
              isCreatingAuth={isCreatingAuth}
              submitLabel={
                editingAuthId
                  ? "Save Changes"
                  : newAuthForm.authType === "Concurrent"
                  ? "Add LOC Change"
                  : "Add Authorization"
              }
              allowPdfIntake={
                !editingAuthId && newAuthForm.authType !== "Concurrent"
              }
              registeredFacilities={registeredFacilities}
              registeredInsurances={registeredInsurances}
              registeredWebPortals={registeredWebPortals}
              onFieldChange={onFieldChange}
              onSubmit={onSubmitAuth}
              onCancel={onCancelAuthForm}
            />

            {!editingAuthId &&
              newAuthForm.authType === "Concurrent" &&
              authEvents.length > 0 && (
                <div
                  className={cn(
                    "mt-4 rounded-2xl border p-4",
                    darkMode
                      ? "border-gray-800 bg-gray-950/60"
                      : "border-gray-200 bg-white"
                  )}
                >
                  <div className="mb-3">
                    <h4 className="text-sm font-semibold">
                      Previous LOC Timeline
                    </h4>
                    <p
                      className={cn(
                        "mt-1 text-xs",
                        darkMode ? "text-gray-400" : "text-gray-600"
                      )}
                    >
                      Reference the prior authorization dates while creating
                      this LOC change.
                    </p>
                  </div>

                  <div className="space-y-3">
                    {authEvents.map((event) => (
                      <div
                        key={event.id}
                        className={cn(
                          "rounded-xl border px-4 py-3 text-sm",
                          darkMode
                            ? "border-gray-800 bg-gray-900"
                            : "border-gray-200 bg-gray-50"
                        )}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="font-medium">
                            {event.eventType}
                            {event.outcome ? ` - ${event.outcome}` : ""}
                          </div>
                          <div
                            className={cn(
                              "text-xs",
                              darkMode ? "text-gray-400" : "text-gray-600"
                            )}
                          >
                            {event.eventDate}
                            {event.eventTime ? ` at ${event.eventTime}` : ""}
                          </div>
                        </div>

                        {event.notes && (
                          <p
                            className={cn(
                              "mt-2 whitespace-pre-wrap text-xs",
                              darkMode ? "text-gray-400" : "text-gray-600"
                            )}
                          >
                            {event.notes}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {editingAuthId && (
              <div className="mt-4">
                {authEventsError && (
                  <div
                    className={cn(
                      "mb-3 rounded-xl border px-4 py-3 text-sm",
                      darkMode
                        ? "border-red-900/70 bg-red-950/40 text-red-200"
                        : "border-red-200 bg-red-50 text-red-700"
                    )}
                  >
                    {authEventsError}
                  </div>
                )}

                {isLoadingAuthEvents ? (
                  <div
                    className={cn(
                      "rounded-2xl border p-4 text-sm",
                      darkMode
                        ? "border-gray-700 bg-gray-900 text-gray-300"
                        : "border-gray-200 bg-white text-gray-600"
                    )}
                  >
                    Loading authorization timeline...
                  </div>
                ) : (
                  <AuthTimelineSection
                    darkMode={darkMode}
                    events={authEvents}
                    eventForm={timelineEventForm}
                    isSavingEvent={isSavingAuthEvent}
                    editingEventId={editingAuthEventId}
                    confirmingDeleteEventId={confirmingDeleteAuthEventId}
                    onEventFieldChange={onTimelineEventFieldChange}
                    onAddEvent={onAddTimelineEvent}
                    onAddEventAndReturn={onAddTimelineEventAndReturn}
                    onStartEditEvent={onStartEditTimelineEvent}
                    onCancelEditEvent={onCancelEditTimelineEvent}
                    onUpdateEvent={onUpdateTimelineEvent}
                    onUpdateEventAndReturn={onUpdateTimelineEventAndReturn}
                    onStartDeleteEvent={onStartDeleteTimelineEvent}
                    onCancelDeleteEvent={onCancelDeleteTimelineEvent}
                    onConfirmDeleteEvent={onConfirmDeleteTimelineEvent}
                    onStartContinuedStay={onStartContinuedStay}
                    onManageDenialFollowUp={
                      editingAuth
                        ? () => onManageDenialFollowUp(editingAuth)
                        : undefined
                    }
                  />
                )}
              </div>
            )}
          </>
        )}

        {viewingAuth && (
          <div className="mt-4">
            <AuthorizationReadOnlyView
              auth={viewingAuth}
              darkMode={darkMode}
              events={authEvents}
              isLoadingEvents={isLoadingAuthEvents}
              eventsError={authEventsError}
              canEdit={canManageAuthorizations}
              onClose={onCloseViewAuth}
              onEdit={onEditAuth}
              onManageDenialFollowUp={onManageDenialFollowUp}
            />
          </div>
        )}

        {!showAddAuthForm && !viewingAuth && (
          <DataTable
            data={filteredData}
            darkMode={darkMode}
            onView={onViewAuth}
            onEdit={canManageAuthorizations ? onEditAuth : undefined}
            onDelete={canManageAuthorizations ? onDeleteAuth : undefined}
            deletingId={deletingAuthId}
            workflowViewMode={workflowViewMode}
          />
        )}
      </div>
    </>
  );
}

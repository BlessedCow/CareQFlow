import { useState } from "react";
import type { AuthEvent, UpdateAuthEventPayload } from "../api/authEvents";
import {
  formatEventTimestamp,
  sortAuthEventsNewestFirst,
} from "../utils/authEvents";
import { cn } from "../utils/cn";

export interface TimelineEventFormState {
  eventDate: string;
  eventTime: string;
  eventType: string;
  outcome: string;
  notes: string;
  requestedDays: string;
  approvedDays: string;
  authStartDate: string;
  authEndDate: string;
  reviewDueDate: string;
}

interface AuthTimelineSectionProps {
  darkMode: boolean;
  events: AuthEvent[];
  eventForm: TimelineEventFormState;
  isSavingEvent: boolean;
  editingEventId: number | null;
  confirmingDeleteEventId: number | null;
  onEventFieldChange: (
    field: keyof TimelineEventFormState,
    value: string
  ) => void;
  onAddEvent: () => void;
  onAddEventAndReturn: () => void;
  onStartEditEvent: (event: AuthEvent) => void;
  onCancelEditEvent: () => void;
  onUpdateEvent: (eventId: number, payload: UpdateAuthEventPayload) => void;
  onUpdateEventAndReturn: (
    eventId: number,
    payload: UpdateAuthEventPayload
  ) => void;
  onStartDeleteEvent: (eventId: number) => void;
  onCancelDeleteEvent: () => void;
  onConfirmDeleteEvent: (eventId: number) => void;
  onStartContinuedStay: () => void;
  onManageDenialFollowUp?: () => void;
}

const EVENT_TYPES = [
  "Initial Authorization",
  "Continued Stay",
  "Request Submitted",
  "Authorization Complete",
  "Discharge",
  "Payer Response",
  "Peer Review",
  "Appeal",
  "Additional Clinical Sent",
  "More Information Requested",
  "Review Scheduled",
  "Facility Updated",
  "Other",
];

const OUTCOMES = [
  "",
  "Pending",
  "Approved",
  "Denied",
  "Denied with Peer Review Option",
  "More Information Needed",
  "No PA Required",
  "Scheduled",
  "Completed",
  "Discharged",
  "Submitted",
  "Appeal Pending",
  "Appeal Approved",
  "Appeal Denied",
  "Upheld",
  "Overturned",
  "Other",
];

function isDeniedTimelineEvent(event: AuthEvent) {
  return event.outcome === "Denied";
}

function getTimelineEventTitle(event: AuthEvent) {
  const isInitialPendingAnchor =
    event.eventType === "Initial Authorization" && event.outcome === "Pending";

  if (isInitialPendingAnchor) {
    return event.eventType;
  }

  return event.outcome
    ? `${event.eventType} - ${event.outcome}`
    : event.eventType;
}

export function AuthTimelineSection({
  darkMode,
  events,
  eventForm,
  isSavingEvent,
  editingEventId,
  confirmingDeleteEventId,
  onEventFieldChange,
  onAddEvent,
  onAddEventAndReturn,
  onStartEditEvent,
  onCancelEditEvent,
  onUpdateEvent,
  onUpdateEventAndReturn,
  onStartDeleteEvent,
  onCancelDeleteEvent,
  onConfirmDeleteEvent,
  onStartContinuedStay,
  onManageDenialFollowUp,
}: AuthTimelineSectionProps) {
  const sortedEvents = sortAuthEventsNewestFirst(events);
  const [showTimelineNotes, setShowTimelineNotes] = useState(true);
  const hasTimelineNotes = sortedEvents.some((event) => event.notes?.trim());
  const normalizedOutcome = eventForm.outcome.trim().toLowerCase();

  const isTerminalOutcome = [
    "completed",
    "discharged",
    "no pa required",
  ].includes(normalizedOutcome);
  const handleSubmitEvent = (returnToList = false) => {
    if (!eventForm.eventDate.trim()) {
      return;
    }

    const payload = {
      event_type: eventForm.eventType,
      event_date: eventForm.eventDate,
      event_time: eventForm.eventTime,
      outcome: eventForm.outcome,
      notes: eventForm.notes.trim(),
      requested_days: Number(eventForm.requestedDays) || 0,
      approved_days: Number(eventForm.approvedDays) || 0,
      auth_start_date: eventForm.authStartDate,
      auth_end_date: eventForm.authEndDate,
      review_due_date: eventForm.reviewDueDate,
    };

    if (editingEventId) {
      if (returnToList) {
        onUpdateEventAndReturn(editingEventId, payload);
        return;
      }

      onUpdateEvent(editingEventId, payload);
      return;
    }

    if (returnToList) {
      onAddEventAndReturn();
      return;
    }

    onAddEvent();
  };

  return (
    <div
      className={cn(
        "rounded-2xl border p-4",
        darkMode
          ? "border-gray-700 bg-gray-900/50"
          : "border-gray-200 bg-gray-50"
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3
            className={cn(
              "text-sm font-semibold",
              darkMode ? "text-gray-100" : "text-gray-900"
            )}
          >
            Auth Timeline
          </h3>
          <p
            className={cn(
              "mt-1 text-xs",
              darkMode ? "text-gray-400" : "text-gray-500"
            )}
          >
            Track request dates, payer outcomes, peer reviews, appeals, and
            follow-up notes.
          </p>

          {hasTimelineNotes && (
            <button
              type="button"
              onClick={() =>
                setShowTimelineNotes((currentValue) => !currentValue)
              }
              className={cn(
                "rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-200 hover:bg-gray-800"
                  : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
              )}
            >
              {showTimelineNotes ? "Hide Notes" : "Show Notes"}
            </button>
          )}
        </div>
      </div>

      <div
        className={cn(
          "mb-3 rounded-xl border px-4 py-3 text-sm",
          editingEventId
            ? darkMode
              ? "border-blue-900/70 bg-blue-950/40 text-blue-200"
              : "border-blue-200 bg-blue-50 text-blue-700"
            : darkMode
            ? "border-gray-800 bg-gray-950 text-gray-400"
            : "border-gray-200 bg-white text-gray-600"
        )}
      >
        {editingEventId
          ? "Editing timeline event. Save changes or cancel edit before adding another event."
          : "Add a timeline event using the real request or outcome date, not necessarily today’s date."}
      </div>

      {!editingEventId && sortedEvents.length > 0 && (
        <div className="mb-3 space-y-2">
          <p
            className={cn(
              "text-xs",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Quick actions can reuse the latest timeline event date for continued
            stays or payer responses.
          </p>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onStartContinuedStay}
              className={cn(
                "rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                darkMode
                  ? "border-blue-800 bg-blue-950/40 text-blue-200 hover:bg-blue-900/50"
                  : "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
              )}
            >
              Start Continued Stay
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-4">
        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Event Date
          </label>
          <input
            type="date"
            value={eventForm.eventDate}
            onChange={(event) =>
              onEventFieldChange("eventDate", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Time Optional
          </label>
          <input
            type="time"
            value={eventForm.eventTime}
            onChange={(event) =>
              onEventFieldChange("eventTime", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Event Type
          </label>
          <select
            value={eventForm.eventType}
            onChange={(event) =>
              onEventFieldChange("eventType", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          >
            {EVENT_TYPES.map((eventType) => (
              <option key={eventType} value={eventType}>
                {eventType}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Outcome / Result
          </label>
          <select
            value={eventForm.outcome}
            onChange={(event) =>
              onEventFieldChange("outcome", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          >
            {OUTCOMES.map((outcome) => (
              <option key={outcome || "none"} value={outcome}>
                {outcome || "None"}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-5">
        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Start Date
          </label>
          <input
            type="date"
            value={eventForm.authStartDate}
            disabled={isTerminalOutcome}
            onChange={(event) =>
              onEventFieldChange("authStartDate", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            End Date
          </label>
          <input
            type="date"
            value={eventForm.authEndDate}
            disabled={isTerminalOutcome}
            onChange={(event) =>
              onEventFieldChange("authEndDate", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Next Review
          </label>
          <input
            type="date"
            value={eventForm.reviewDueDate}
            disabled={isTerminalOutcome}
            onChange={(event) =>
              onEventFieldChange("reviewDueDate", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Requested
          </label>
          <input
            type="number"
            min="0"
            value={eventForm.requestedDays}
            disabled={isTerminalOutcome}
            onChange={(event) =>
              onEventFieldChange("requestedDays", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>

        <div>
          <label
            className={cn(
              "mb-1 block text-xs font-medium",
              darkMode ? "text-gray-300" : "text-gray-600"
            )}
          >
            Approved
          </label>
          <input
            type="number"
            min="0"
            value={eventForm.approvedDays}
            disabled={isTerminalOutcome}
            onChange={(event) =>
              onEventFieldChange("approvedDays", event.target.value)
            }
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
            )}
          />
        </div>
      </div>

      <div className="mt-3">
        <label
          className={cn(
            "mb-1 block text-xs font-medium",
            darkMode ? "text-gray-300" : "text-gray-600"
          )}
        >
          Timeline Notes
        </label>
        <textarea
          value={eventForm.notes}
          onChange={(event) => onEventFieldChange("notes", event.target.value)}
          placeholder="Example: Insurance denied auth as not medically necessary. Peer review available at 555-555-5555."
          rows={3}
          className={cn(
            "w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors",
            darkMode
              ? "border-gray-700 bg-gray-950 text-gray-100 placeholder:text-gray-500 focus:border-blue-500"
              : "border-gray-300 bg-white text-gray-900 placeholder:text-gray-400 focus:border-blue-500"
          )}
        />
      </div>

      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={() => handleSubmitEvent()}
          disabled={isSavingEvent || !eventForm.eventDate.trim()}
          className={cn(
            "inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
            darkMode
              ? "bg-blue-600 text-white hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-400"
              : "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500"
          )}
        >
          {isSavingEvent
            ? "Saving Event..."
            : editingEventId
            ? "Save Timeline Event"
            : "+ Add Timeline Event"}
        </button>

        <button
          type="button"
          onClick={() => handleSubmitEvent(true)}
          disabled={isSavingEvent || !eventForm.eventDate.trim()}
          className={cn(
            "ml-3 inline-flex items-center rounded-lg border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
            darkMode
              ? "border-blue-800 bg-blue-950/40 text-blue-200 hover:bg-blue-900/50"
              : "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
          )}
        >
          {isSavingEvent ? "Saving Event..." : "Save Event & Return"}
        </button>

        {editingEventId && (
          <button
            type="button"
            onClick={onCancelEditEvent}
            className={cn(
              "ml-3 inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              darkMode
                ? "text-gray-300 hover:bg-gray-800"
                : "text-gray-700 hover:bg-gray-100"
            )}
          >
            Cancel Edit
          </button>
        )}
      </div>

      <div className="mt-5 space-y-3">
        {sortedEvents.length === 0 ? (
          <p
            className={cn(
              "text-sm",
              darkMode ? "text-gray-400" : "text-gray-500"
            )}
          >
            No timeline events added yet.
          </p>
        ) : (
          sortedEvents.map((event) => {
            const eventIsTerminal = [
              "Completed",
              "Discharged",
              "No PA Required",
            ].includes(event.outcome);

            return (
              <div
                key={event.id}
                className={cn(
                  "rounded-xl border p-3",
                  editingEventId === event.id
                    ? darkMode
                      ? "border-blue-800 bg-blue-950/30"
                      : "border-blue-300 bg-blue-50"
                    : darkMode
                    ? "border-gray-700 bg-gray-950"
                    : "border-gray-200 bg-white"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div
                      className={cn(
                        "text-sm font-semibold",
                        darkMode ? "text-gray-100" : "text-gray-900"
                      )}
                    >
                      {getTimelineEventTitle(event)}
                    </div>
                    <div
                      className={cn(
                        "mt-1 text-xs",
                        darkMode ? "text-gray-400" : "text-gray-500"
                      )}
                    >
                      {formatEventTimestamp(event.eventDate, event.eventTime)}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => onStartEditEvent(event)}
                      className={cn(
                        "text-xs font-medium transition-colors",
                        darkMode
                          ? "text-blue-400 hover:text-blue-300"
                          : "text-blue-600 hover:text-blue-700"
                      )}
                    >
                      {editingEventId === event.id ? "Editing" : "Edit"}
                    </button>

                    {confirmingDeleteEventId === event.id ? (
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "text-xs",
                            darkMode ? "text-gray-400" : "text-gray-500"
                          )}
                        >
                          Delete?
                        </span>

                        <button
                          type="button"
                          onClick={() => onConfirmDeleteEvent(event.id)}
                          className={cn(
                            "text-xs font-medium transition-colors",
                            darkMode
                              ? "text-red-400 hover:text-red-300"
                              : "text-red-600 hover:text-red-700"
                          )}
                        >
                          Yes
                        </button>

                        <button
                          type="button"
                          onClick={onCancelDeleteEvent}
                          className={cn(
                            "text-xs font-medium transition-colors",
                            darkMode
                              ? "text-gray-400 hover:text-gray-300"
                              : "text-gray-600 hover:text-gray-800"
                          )}
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => onStartDeleteEvent(event.id)}
                        className={cn(
                          "text-xs font-medium transition-colors",
                          darkMode
                            ? "text-red-400 hover:text-red-300"
                            : "text-red-600 hover:text-red-700"
                        )}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>

                {!eventIsTerminal &&
                  (event.authStartDate ||
                    event.authEndDate ||
                    event.reviewDueDate ||
                    event.requestedDays > 0 ||
                    event.approvedDays > 0) && (
                    <div
                      className={cn(
                        "mt-3 grid gap-2 rounded-lg border p-3 text-xs md:grid-cols-5",
                        darkMode
                          ? "border-gray-800 bg-gray-900 text-gray-300"
                          : "border-gray-200 bg-gray-50 text-gray-700"
                      )}
                    >
                      <div>
                        <span className="font-semibold">Start:</span>{" "}
                        {event.authStartDate || "—"}
                      </div>
                      <div>
                        <span className="font-semibold">End:</span>{" "}
                        {event.authEndDate || "—"}
                      </div>
                      <div>
                        <span className="font-semibold">Next Review:</span>{" "}
                        {event.reviewDueDate || "—"}
                      </div>
                      <div>
                        <span className="font-semibold">Requested:</span>{" "}
                        {event.requestedDays || "—"}
                      </div>
                      <div>
                        <span className="font-semibold">Approved:</span>{" "}
                        {event.approvedDays || "—"}
                      </div>
                    </div>
                  )}

                {showTimelineNotes && event.notes ? (
                  <p
                    className={cn(
                      "mt-2 whitespace-pre-wrap text-sm",
                      darkMode ? "text-gray-300" : "text-gray-700"
                    )}
                  >
                    {event.notes}
                  </p>
                ) : null}
                {onManageDenialFollowUp && isDeniedTimelineEvent(event) && (
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={onManageDenialFollowUp}
                      className={cn(
                        "rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                        darkMode
                          ? "border-amber-800 bg-amber-950/30 text-amber-200 hover:bg-amber-900/40"
                          : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
                      )}
                    >
                      Track Denial / P2P / Retro
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

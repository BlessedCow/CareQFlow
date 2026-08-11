import type { AuthEvent } from "../api/authEvents";
import type { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";
import { AuthorizationDocumentsSection } from "./AuthorizationDocumentsSection";
import {
  formatEventTimestamp,
  sortAuthEventsNewestFirst,
} from "../utils/authEvents";

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

interface AuthorizationReadOnlyViewProps {
  auth: AuthRequest;
  darkMode: boolean;
  events: AuthEvent[];
  isLoadingEvents: boolean;
  eventsError: string | null;
  canEdit: boolean;
  onClose: () => void;
  onEdit: (auth: AuthRequest) => void;
  onManageDenialFollowUp: (auth: AuthRequest) => void;
}

function formatValue(value?: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  return String(value);
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Not recorded";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatDateOnly(value?: string | null) {
  if (!value) {
    return "Not provided";
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString();
}

function hasDenialFollowUpWork(auth: AuthRequest) {
  return (
    auth.status === "Denied" ||
    auth.status === "P2P" ||
    auth.status === "Appealed" ||
    auth.authType === "Retro" ||
    Boolean(auth.denialReasonCategory) ||
    Boolean(auth.denialDate) ||
    Boolean(auth.denialReasonNotes) ||
    Boolean(auth.p2pRequested) ||
    Boolean(auth.appealSubmitted) ||
    Boolean(auth.retroRequested)
  );
}

function isDeniedTimelineEvent(event: AuthEvent) {
  return event.outcome === "Denied";
}

export function AuthorizationReadOnlyView({
  auth,
  darkMode,
  events,
  isLoadingEvents,
  eventsError,
  canEdit,
  onClose,
  onEdit,
  onManageDenialFollowUp,
}: AuthorizationReadOnlyViewProps) {
  const labelClass = cn(
    "text-xs font-medium uppercase tracking-wide",
    darkMode ? "text-gray-500" : "text-gray-500"
  );
  const valueClass = cn(
    "mt-1 text-sm font-medium",
    darkMode ? "text-gray-100" : "text-gray-900"
  );
  const sortedEvents = sortAuthEventsNewestFirst(events);
  const showDenialFollowUpAction =
    canEdit &&
    (hasDenialFollowUpWork(auth) || sortedEvents.some(isDeniedTimelineEvent));

  return (
    <section
      className={cn(
        "rounded-2xl border p-5 shadow-sm",
        darkMode ? "border-gray-700 bg-gray-900" : "border-gray-200 bg-white"
      )}
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2
            className={cn(
              "text-lg font-semibold",
              darkMode ? "text-gray-100" : "text-gray-900"
            )}
          >
            View Authorization
          </h2>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-500"
            )}
          >
            Read-only authorization details and timeline history.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canEdit && (
            <button
              type="button"
              onClick={() => onEdit(auth)}
              className={cn(
                "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                darkMode
                  ? "bg-blue-600 text-white hover:bg-blue-500"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              )}
            >
              Edit Auth
            </button>
          )}

          {showDenialFollowUpAction && (
            <button
              type="button"
              onClick={() => onManageDenialFollowUp(auth)}
              className={cn(
                "rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                darkMode
                  ? "border-amber-800 bg-amber-950/30 text-amber-200 hover:bg-amber-900/40"
                  : "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
              )}
            >
              Manage Denial / P2P / Retro
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className={cn(
              "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              darkMode
                ? "text-gray-300 hover:bg-gray-800"
                : "text-gray-700 hover:bg-gray-100"
            )}
          >
            Close
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <div className={labelClass}>Client</div>
          <div className={valueClass}>{auth.patientId}</div>
        </div>

        <div>
          <div className={labelClass}>Member ID</div>
          <div className={valueClass}>{formatValue(auth.memberId)}</div>
        </div>

        <div>
          <div className={labelClass}>Payer Auth / Reference Number</div>
          <div className={valueClass}>{formatValue(auth.authNumber)}</div>
        </div>

        <div>
          <div className={labelClass}>Group Number</div>
          <div className={valueClass}>{formatValue(auth.groupNumber)}</div>
        </div>

        <div>
          <div className={labelClass}>Date of Birth</div>
          <div className={valueClass}>{formatDateOnly(auth.dateOfBirth)}</div>
        </div>

        <div>
          <div className={labelClass}>Facility</div>
          <div className={valueClass}>{auth.facility}</div>
        </div>

        <div>
          <div className={labelClass}>Insurance</div>
          <div className={valueClass}>{auth.payer}</div>
        </div>

        <div>
          <div className={labelClass}>Level of Care</div>
          <div className={valueClass}>{formatValue(auth.loc)}</div>
        </div>

        <div>
          <div className={labelClass}>Auth Type</div>
          <div className={valueClass}>{formatValue(auth.authType)}</div>
        </div>

        <div>
          <div className={labelClass}>Programming Days</div>
          <div className={valueClass}>{formatValue(auth.programmingDays)}</div>
        </div>

        <div>
          <div className={labelClass}>Status</div>
          <div className={valueClass}>{auth.status}</div>
        </div>

        <div>
          <div className={labelClass}>Auth Start Date</div>
          <div className={valueClass}>{formatDateOnly(auth.dateStr)}</div>
        </div>

        <div>
          <div className={labelClass}>Review Due Date</div>
          <div className={valueClass}>{formatDateOnly(auth.reviewDueDate)}</div>
        </div>

        <div>
          <div className={labelClass}>Requested / Approved Days</div>
          <div className={valueClass}>
            {auth.requestedDays} /{" "}
            {auth.status === "Pending" ? "-" : auth.approvedDays}
          </div>
        </div>

        <div>
          <div className={labelClass}>Submitted Date</div>
          <div className={valueClass}>{formatDateTime(auth.submittedAt)}</div>
        </div>

        <div>
          <div className={labelClass}>Decision Date</div>
          <div className={valueClass}>{formatDateTime(auth.decisionAt)}</div>
        </div>

        <div className="md:col-span-3">
          <div className={labelClass}>Submission Method</div>
          <div className={valueClass}>
            {formatValue(auth.submissionMethods)}
          </div>
        </div>
      </div>

      <div
        className={cn("my-5 h-px", darkMode ? "bg-gray-800" : "bg-gray-200")}
      />

      <AuthorizationDocumentsSection
        authId={auth.id}
        darkMode={darkMode}
        canManage={canEdit}
      />

      <div
        className={cn("my-5 h-px", darkMode ? "bg-gray-800" : "bg-gray-200")}
      />

      <div>
        <h3
          className={cn(
            "text-sm font-semibold",
            darkMode ? "text-gray-100" : "text-gray-900"
          )}
        >
          Timeline Events
        </h3>

        {eventsError && (
          <div
            className={cn(
              "mt-3 rounded-xl border px-4 py-3 text-sm",
              darkMode
                ? "border-red-900/70 bg-red-950/40 text-red-200"
                : "border-red-200 bg-red-50 text-red-700"
            )}
          >
            {eventsError}
          </div>
        )}

        {isLoadingEvents ? (
          <p
            className={cn(
              "mt-3 text-sm",
              darkMode ? "text-gray-400" : "text-gray-500"
            )}
          >
            Loading timeline...
          </p>
        ) : sortedEvents.length === 0 ? (
          <p
            className={cn(
              "mt-3 text-sm",
              darkMode ? "text-gray-400" : "text-gray-500"
            )}
          >
            No timeline events recorded yet.
          </p>
        ) : (
          <div className="mt-3 space-y-3">
            {sortedEvents.map((event) => (
              <div
                key={event.id}
                className={cn(
                  "rounded-xl border p-3",
                  darkMode
                    ? "border-gray-700 bg-gray-950"
                    : "border-gray-200 bg-gray-50"
                )}
              >
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

                {event.notes ? (
                  <p
                    className={cn(
                      "mt-2 whitespace-pre-wrap text-sm",
                      darkMode ? "text-gray-300" : "text-gray-700"
                    )}
                  >
                    {event.notes}
                  </p>
                ) : null}
                {canEdit && isDeniedTimelineEvent(event) && (
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={() => onManageDenialFollowUp(auth)}
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
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

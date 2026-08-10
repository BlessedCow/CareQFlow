import type { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";

interface AuthorizationPipelineSummaryProps {
  auth: AuthRequest;
  darkMode: boolean;
}

function formatValue(value?: string | number | boolean | null) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Not provided";
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString();
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Not provided";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function AuthorizationPipelineSummary({
  auth,
  darkMode,
}: AuthorizationPipelineSummaryProps) {
  const labelClass = cn(
    "text-xs font-medium uppercase tracking-wide",
    darkMode ? "text-gray-500" : "text-gray-500"
  );
  const valueClass = cn(
    "mt-1 text-sm font-medium",
    darkMode ? "text-gray-100" : "text-gray-900"
  );
  const sectionClass = cn(
    "rounded-xl border p-4",
    darkMode ? "border-gray-800 bg-gray-950/40" : "border-gray-200 bg-gray-50"
  );

  return (
    <section className="space-y-4">
      <div>
        <h3
          className={cn(
            "text-sm font-semibold",
            darkMode ? "text-gray-100" : "text-gray-900"
          )}
        >
          Denial / P2P / Retro Pipeline
        </h3>
        <p
          className={cn(
            "mt-1 text-xs",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          Structured follow-up details used for denial review and prevention
          tracking.
        </p>
      </div>

      <div className={sectionClass}>
        <h4 className="mb-3 text-sm font-semibold">Denial Details</h4>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <div className={labelClass}>Reason Category</div>
            <div className={valueClass}>
              {formatValue(auth.denialReasonCategory)}
            </div>
          </div>
          <div>
            <div className={labelClass}>Denied Days</div>
            <div className={valueClass}>{formatValue(auth.deniedDays)}</div>
          </div>
          <div>
            <div className={labelClass}>Denial Date</div>
            <div className={valueClass}>{formatDate(auth.denialDate)}</div>
          </div>
          <div>
            <div className={labelClass}>Denied LOC</div>
            <div className={valueClass}>
              {formatValue(auth.denialLevelOfCare)}
            </div>
          </div>
          <div>
            <div className={labelClass}>Denial Source</div>
            <div className={valueClass}>{formatValue(auth.denialSource)}</div>
          </div>
          <div className="md:col-span-3">
            <div className={labelClass}>Reason Notes</div>
            <div className={valueClass}>
              {formatValue(auth.denialReasonNotes)}
            </div>
          </div>
          <div className="md:col-span-3">
            <div className={labelClass}>Prevention Notes</div>
            <div className={valueClass}>
              {formatValue(auth.denialPreventionNotes)}
            </div>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h4 className="mb-3 text-sm font-semibold">P2P</h4>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <div className={labelClass}>Requested</div>
            <div className={valueClass}>{formatValue(auth.p2pRequested)}</div>
          </div>
          <div>
            <div className={labelClass}>Scheduled</div>
            <div className={valueClass}>
              {formatDateTime(auth.p2pScheduledAt)}
            </div>
          </div>
          <div>
            <div className={labelClass}>Deadline</div>
            <div className={valueClass}>{formatDate(auth.p2pDeadline)}</div>
          </div>
          <div>
            <div className={labelClass}>Outcome</div>
            <div className={valueClass}>{formatValue(auth.p2pOutcome)}</div>
          </div>
          <div>
            <div className={labelClass}>Reviewer</div>
            <div className={valueClass}>{formatValue(auth.p2pReviewer)}</div>
          </div>
          <div className="md:col-span-3">
            <div className={labelClass}>Notes</div>
            <div className={valueClass}>{formatValue(auth.p2pNotes)}</div>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h4 className="mb-3 text-sm font-semibold">Appeal</h4>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <div className={labelClass}>Submitted</div>
            <div className={valueClass}>
              {formatValue(auth.appealSubmitted)}
            </div>
          </div>
          <div>
            <div className={labelClass}>Deadline</div>
            <div className={valueClass}>{formatDate(auth.appealDeadline)}</div>
          </div>
          <div>
            <div className={labelClass}>Outcome</div>
            <div className={valueClass}>{formatValue(auth.appealOutcome)}</div>
          </div>
          <div className="md:col-span-3">
            <div className={labelClass}>Notes</div>
            <div className={valueClass}>{formatValue(auth.appealNotes)}</div>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <h4 className="mb-3 text-sm font-semibold">Retro Auth</h4>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <div className={labelClass}>Requested</div>
            <div className={valueClass}>{formatValue(auth.retroRequested)}</div>
          </div>
          <div>
            <div className={labelClass}>Deadline</div>
            <div className={valueClass}>{formatDate(auth.retroDeadline)}</div>
          </div>
          <div>
            <div className={labelClass}>Outcome</div>
            <div className={valueClass}>{formatValue(auth.retroOutcome)}</div>
          </div>
          <div className="md:col-span-3">
            <div className={labelClass}>Notes</div>
            <div className={valueClass}>{formatValue(auth.retroNotes)}</div>
          </div>
        </div>
      </div>
    </section>
  );
}

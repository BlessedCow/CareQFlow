import type { NewAuthFormState } from "../hooks/useAuthorizationForm";
import { cn } from "../utils/cn";

interface AuthorizationPipelineFormSectionProps {
  form: NewAuthFormState;
  darkMode: boolean;
  onFieldChange: (
    field: keyof NewAuthFormState,
    value: string | boolean
  ) => void;
}

const DENIAL_REASON_OPTIONS = [
  "",
  "Medical Necessity",
  "Insufficient Clinical Documentation",
  "Lack of Progress",
  "Lower LOC Recommended",
  "No Active Treatment Needs",
  "Administrative Issue",
  "Timely Filing / Late Submission",
  "Benefit Issue",
  "Other",
];

const DENIAL_SOURCE_OPTIONS = [
  "",
  "Initial Auth",
  "Concurrent Auth",
  "Retro Auth",
  "Appeal",
  "Other",
];

const OUTCOME_OPTIONS = [
  "",
  "Pending",
  "Approved",
  "Denied",
  "Upheld",
  "Overturned",
  "Withdrawn",
  "Other",
];

export function AuthorizationPipelineFormSection({
  form,
  darkMode,
  onFieldChange,
}: AuthorizationPipelineFormSectionProps) {
  const inputClass = cn(
    "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
    darkMode
      ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
      : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
  );
  const labelTextClass = darkMode ? "text-gray-300" : "text-gray-700";
  const helpTextClass = darkMode ? "text-gray-400" : "text-gray-600";

  return (
    <section
      className={cn(
        "space-y-4 rounded-xl border p-4 md:col-span-2",
        darkMode ? "border-gray-800 bg-gray-950/40" : "border-gray-200 bg-white"
      )}
    >
      <div>
      <h3 className="text-sm font-semibold">Denials / P2P / Retro</h3>
        <p className={cn("mt-1 text-xs", helpTextClass)}>
          Track denial reasons, peer review work, appeal status, and retro auth
          follow-up.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Denial Reason Category</span>
          <select
            value={form.denialReasonCategory}
            onChange={(event) =>
              onFieldChange("denialReasonCategory", event.target.value)
            }
            className={inputClass}
          >
            {DENIAL_REASON_OPTIONS.map((option) => (
              <option key={option || "blank"} value={option}>
                {option || "Not selected"}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Denied Days</span>
          <input
            type="number"
            min="0"
            value={form.deniedDays}
            onChange={(event) =>
              onFieldChange("deniedDays", event.target.value)
            }
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Denial Date</span>
          <input
            type="date"
            value={form.denialDate}
            onChange={(event) =>
              onFieldChange("denialDate", event.target.value)
            }
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Denial Level of Care</span>
          <input
            type="text"
            value={form.denialLevelOfCare}
            onChange={(event) =>
              onFieldChange("denialLevelOfCare", event.target.value)
            }
            placeholder="RTC, PHP, IOP, DTX, etc."
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Denial Source</span>
          <select
            value={form.denialSource}
            onChange={(event) =>
              onFieldChange("denialSource", event.target.value)
            }
            className={inputClass}
          >
            {DENIAL_SOURCE_OPTIONS.map((option) => (
              <option key={option || "blank"} value={option}>
                {option || "Not selected"}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-3 rounded-lg border px-3 py-2 text-sm border-inherit">
          <input
            type="checkbox"
            checked={form.p2pRequested}
            onChange={(event) =>
              onFieldChange("p2pRequested", event.target.checked)
            }
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className={labelTextClass}>P2P requested</span>
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className={labelTextClass}>Denial Reason Notes</span>
          <textarea
            value={form.denialReasonNotes}
            onChange={(event) =>
              onFieldChange("denialReasonNotes", event.target.value)
            }
            rows={3}
            placeholder="What reason did the payer give for the denial?"
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className={labelTextClass}>Prevention Notes</span>
          <textarea
            value={form.denialPreventionNotes}
            onChange={(event) =>
              onFieldChange("denialPreventionNotes", event.target.value)
            }
            rows={3}
            placeholder="What documentation or workflow change could help avoid this denial later?"
            className={inputClass}
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>P2P Scheduled At</span>
          <input
            type="datetime-local"
            value={form.p2pScheduledAt}
            onChange={(event) =>
              onFieldChange("p2pScheduledAt", event.target.value)
            }
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>P2P Deadline</span>
          <input
            type="date"
            value={form.p2pDeadline}
            onChange={(event) =>
              onFieldChange("p2pDeadline", event.target.value)
            }
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>P2P Outcome</span>
          <select
            value={form.p2pOutcome}
            onChange={(event) =>
              onFieldChange("p2pOutcome", event.target.value)
            }
            className={inputClass}
          >
            {OUTCOME_OPTIONS.map((option) => (
              <option key={option || "blank"} value={option}>
                {option || "Not selected"}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>P2P Reviewer</span>
          <input
            type="text"
            value={form.p2pReviewer}
            onChange={(event) =>
              onFieldChange("p2pReviewer", event.target.value)
            }
            placeholder="Medical director or payer reviewer"
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className={labelTextClass}>P2P Notes</span>
          <textarea
            value={form.p2pNotes}
            onChange={(event) => onFieldChange("p2pNotes", event.target.value)}
            rows={3}
            className={inputClass}
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex items-center gap-3 rounded-lg border px-3 py-2 text-sm border-inherit">
          <input
            type="checkbox"
            checked={form.appealSubmitted}
            onChange={(event) =>
              onFieldChange("appealSubmitted", event.target.checked)
            }
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className={labelTextClass}>Appeal submitted</span>
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Appeal Deadline</span>
          <input
            type="date"
            value={form.appealDeadline}
            onChange={(event) =>
              onFieldChange("appealDeadline", event.target.value)
            }
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Appeal Outcome</span>
          <select
            value={form.appealOutcome}
            onChange={(event) =>
              onFieldChange("appealOutcome", event.target.value)
            }
            className={inputClass}
          >
            {OUTCOME_OPTIONS.map((option) => (
              <option key={option || "blank"} value={option}>
                {option || "Not selected"}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className={labelTextClass}>Appeal Notes</span>
          <textarea
            value={form.appealNotes}
            onChange={(event) =>
              onFieldChange("appealNotes", event.target.value)
            }
            rows={3}
            className={inputClass}
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex items-center gap-3 rounded-lg border px-3 py-2 text-sm border-inherit">
          <input
            type="checkbox"
            checked={form.retroRequested}
            onChange={(event) =>
              onFieldChange("retroRequested", event.target.checked)
            }
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className={labelTextClass}>Retro auth requested</span>
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Retro Deadline</span>
          <input
            type="date"
            value={form.retroDeadline}
            onChange={(event) =>
              onFieldChange("retroDeadline", event.target.value)
            }
            className={inputClass}
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className={labelTextClass}>Retro Outcome</span>
          <select
            value={form.retroOutcome}
            onChange={(event) =>
              onFieldChange("retroOutcome", event.target.value)
            }
            className={inputClass}
          >
            {OUTCOME_OPTIONS.map((option) => (
              <option key={option || "blank"} value={option}>
                {option || "Not selected"}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className={labelTextClass}>Retro Notes</span>
          <textarea
            value={form.retroNotes}
            onChange={(event) =>
              onFieldChange("retroNotes", event.target.value)
            }
            rows={3}
            className={inputClass}
          />
        </label>
      </div>
    </section>
  );
}

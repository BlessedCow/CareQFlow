import type { AuthRequest } from "../../types/auth";
import { cn } from "../../utils/cn";
import {
  APPEAL_OUTCOME_OPTIONS,
  DENIAL_LEVEL_OF_CARE_OPTIONS,
  DENIAL_REASON_OPTIONS,
  DENIAL_SOURCE_OPTIONS,
  P2P_OUTCOME_OPTIONS,
  RETRO_OUTCOME_OPTIONS,
  type AppealFormState,
  type DenialFormState,
  type P2PFormState,
  type RetroFormState,
} from "./followUpModels";

interface FollowUpFormSectionsProps {
  selectedAuth: AuthRequest | null;
  darkMode: boolean;
  denialForm: DenialFormState | null;
  denialError: string | null;
  isSavingDenial: boolean;
  p2pForm: P2PFormState | null;
  p2pError: string | null;
  isSavingP2P: boolean;
  appealForm: AppealFormState | null;
  appealError: string | null;
  isSavingAppeal: boolean;
  retroForm: RetroFormState | null;
  retroError: string | null;
  isSavingRetro: boolean;
  onClearSelectedAuth: () => void;
  onDenialFieldChange: (field: keyof DenialFormState, value: string) => void;
  onP2PFieldChange: (
    field: keyof P2PFormState,
    value: string | boolean
  ) => void;
  onAppealFieldChange: (
    field: keyof AppealFormState,
    value: string | boolean
  ) => void;
  onRetroFieldChange: (
    field: keyof RetroFormState,
    value: string | boolean
  ) => void;
  onSaveDenial: () => void;
  onSaveP2P: () => void;
  onSaveAppeal: () => void;
  onSaveRetro: () => void;
  onClearDenial: () => void;
  onClearP2P: () => void;
  onClearAppeal: () => void;
  onClearRetro: () => void;
}

export function FollowUpFormSections({
  selectedAuth,
  darkMode,
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
  onClearSelectedAuth,
  onDenialFieldChange,
  onP2PFieldChange,
  onAppealFieldChange,
  onRetroFieldChange,
  onSaveDenial,
  onSaveP2P,
  onSaveAppeal,
  onSaveRetro,
  onClearDenial,
  onClearP2P,
  onClearAppeal,
  onClearRetro,
}: FollowUpFormSectionsProps) {
  return (
    <>
      {selectedAuth && denialForm && (
        <section
          className={cn(
            "mb-6 rounded-xl border p-4",
            darkMode
              ? "border-gray-800 bg-gray-950"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="mb-4">
            <h3 className="text-lg font-semibold">
              Start / Update Denial Details
            </h3>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Record the denial reason, issued date, optional through date, and
              prevention notes for this authorization.
            </p>
          </div>

          {denialError && (
            <div
              role="alert"
              className={cn(
                "mb-4 rounded-lg border p-3 text-sm",
                darkMode
                  ? "border-red-900 bg-red-950/30 text-red-200"
                  : "border-red-200 bg-red-50 text-red-700"
              )}
            >
              {denialError}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Reason Category
              </span>
              <select
                value={denialForm.denialReasonCategory}
                onChange={(event) =>
                  onDenialFieldChange(
                    "denialReasonCategory",
                    event.target.value
                  )
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {DENIAL_REASON_OPTIONS.map((option) => (
                  <option key={option || "blank"} value={option}>
                    {option || "Not selected"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Denial Issued Date
              </span>
              <input
                type="date"
                value={denialForm.denialDate}
                onChange={(event) =>
                  onDenialFieldChange("denialDate", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Denied Through Date
              </span>
              <input
                type="date"
                value={denialForm.denialThroughDate}
                onChange={(event) =>
                  onDenialFieldChange("denialThroughDate", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
              <p
                className={cn(
                  "text-xs",
                  darkMode ? "text-gray-500" : "text-gray-500"
                )}
              >
                Optional. Use this only when the payer gives a denied-through
                date.
              </p>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Denied LOC
              </span>
              <select
                value={denialForm.denialLevelOfCare}
                onChange={(event) =>
                  onDenialFieldChange("denialLevelOfCare", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {DENIAL_LEVEL_OF_CARE_OPTIONS.map((option) => (
                  <option key={option || "blank"} value={option}>
                    {option || "Not selected"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Reason Notes
              </span>
              <textarea
                value={denialForm.denialReasonNotes}
                onChange={(event) =>
                  onDenialFieldChange("denialReasonNotes", event.target.value)
                }
                rows={3}
                placeholder="What reason did the payer give for the denial?"
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                )}
              />
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Prevention Notes
              </span>
              <textarea
                value={denialForm.denialPreventionNotes}
                onChange={(event) =>
                  onDenialFieldChange(
                    "denialPreventionNotes",
                    event.target.value
                  )
                }
                rows={3}
                placeholder="What documentation or workflow change could help avoid this denial later?"
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                )}
              />
            </label>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                void onClearDenial();
              }}
              disabled={isSavingDenial}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Delete Denial Details
            </button>
            <button
              type="button"
              onClick={onClearSelectedAuth}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              Back to Dashboard
            </button>

            <button
              type="button"
              onClick={() => {
                void onSaveDenial();
              }}
              disabled={isSavingDenial}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium text-white",
                isSavingDenial
                  ? "cursor-not-allowed bg-blue-400"
                  : "bg-blue-600 hover:bg-blue-700"
              )}
            >
              {isSavingDenial ? "Saving..." : "Save Denial Details"}
            </button>
          </div>
        </section>
      )}

      {selectedAuth && p2pForm && (
        <section
          className={cn(
            "mb-6 rounded-xl border p-4",
            darkMode
              ? "border-gray-800 bg-gray-950"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="mb-4">
            <h3 className="text-lg font-semibold">
              Start / Update P2P Details
            </h3>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Track peer review scheduling, follow-up date, outcome, reviewer,
              and notes for this authorization.
            </p>
          </div>

          {p2pError && (
            <div
              role="alert"
              className={cn(
                "mb-4 rounded-lg border p-3 text-sm",
                darkMode
                  ? "border-red-900 bg-red-950/30 text-red-200"
                  : "border-red-200 bg-red-50 text-red-700"
              )}
            >
              {p2pError}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-3 rounded-lg border px-3 py-2 text-sm border-inherit">
              <input
                type="checkbox"
                checked={p2pForm.p2pRequested}
                onChange={(event) =>
                  onP2PFieldChange("p2pRequested", event.target.checked)
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                P2P requested
              </span>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                P2P Scheduled At
              </span>
              <input
                type="datetime-local"
                value={p2pForm.p2pScheduledAt}
                onChange={(event) =>
                  onP2PFieldChange("p2pScheduledAt", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                P2P Follow-up Date
              </span>
              <input
                type="date"
                value={p2pForm.p2pDeadline}
                onChange={(event) =>
                  onP2PFieldChange("p2pDeadline", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
              <p
                className={cn(
                  "text-xs",
                  darkMode ? "text-gray-500" : "text-gray-500"
                )}
              >
                Optional. Use this only if you need a separate follow-up date
                beyond the scheduled peer review time.
              </p>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                P2P Outcome
              </span>
              <select
                value={p2pForm.p2pOutcome}
                onChange={(event) =>
                  onP2PFieldChange("p2pOutcome", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {P2P_OUTCOME_OPTIONS.map((option) => (
                  <option key={option || "blank"} value={option}>
                    {option || "Not selected"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                P2P Reviewer
              </span>
              <input
                type="text"
                value={p2pForm.p2pReviewer}
                onChange={(event) =>
                  onP2PFieldChange("p2pReviewer", event.target.value)
                }
                placeholder="Medical director or payer reviewer"
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                )}
              />
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                P2P Notes
              </span>
              <textarea
                value={p2pForm.p2pNotes}
                onChange={(event) =>
                  onP2PFieldChange("p2pNotes", event.target.value)
                }
                rows={3}
                placeholder="Add peer review details, call notes, or payer instructions."
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                )}
              />
            </label>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                void onClearP2P();
              }}
              disabled={isSavingP2P}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Delete P2P Details
            </button>
            <button
              type="button"
              onClick={onClearSelectedAuth}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              Back to Dashboard
            </button>

            <button
              type="button"
              onClick={() => {
                void onSaveP2P();
              }}
              disabled={isSavingP2P}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium text-white",
                isSavingP2P
                  ? "cursor-not-allowed bg-blue-400"
                  : "bg-blue-600 hover:bg-blue-700"
              )}
            >
              {isSavingP2P ? "Saving..." : "Save P2P Details"}
            </button>
          </div>
        </section>
      )}

      {selectedAuth && appealForm && (
        <section
          className={cn(
            "mb-6 rounded-xl border p-4",
            darkMode
              ? "border-gray-800 bg-gray-950"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="mb-4">
            <h3 className="text-lg font-semibold">
              Start / Update Appeal Details
            </h3>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Track appeal submission, deadline, outcome, and notes for this
              authorization.
            </p>
          </div>

          {appealError && (
            <div
              role="alert"
              className={cn(
                "mb-4 rounded-lg border p-3 text-sm",
                darkMode
                  ? "border-red-900 bg-red-950/30 text-red-200"
                  : "border-red-200 bg-red-50 text-red-700"
              )}
            >
              {appealError}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-3 rounded-lg border px-3 py-2 text-sm border-inherit">
              <input
                type="checkbox"
                checked={appealForm.appealSubmitted}
                onChange={(event) =>
                  onAppealFieldChange("appealSubmitted", event.target.checked)
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Appeal submitted
              </span>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Appeal Deadline
              </span>
              <input
                type="date"
                value={appealForm.appealDeadline}
                onChange={(event) =>
                  onAppealFieldChange("appealDeadline", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Appeal Outcome
              </span>
              <select
                value={appealForm.appealOutcome}
                onChange={(event) =>
                  onAppealFieldChange("appealOutcome", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {APPEAL_OUTCOME_OPTIONS.map((option) => (
                  <option key={option || "blank"} value={option}>
                    {option || "Not selected"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Appeal Notes
              </span>
              <textarea
                value={appealForm.appealNotes}
                onChange={(event) =>
                  onAppealFieldChange("appealNotes", event.target.value)
                }
                rows={3}
                placeholder="Add appeal submission details, documents sent, payer instructions, or outcome notes."
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                )}
              />
            </label>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                void onClearAppeal();
              }}
              disabled={isSavingAppeal}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Clear Appeal Details
            </button>

            <button
              type="button"
              onClick={onClearSelectedAuth}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              Back to Dashboard
            </button>

            <button
              type="button"
              onClick={() => {
                void onSaveAppeal();
              }}
              disabled={isSavingAppeal}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium text-white",
                isSavingAppeal
                  ? "cursor-not-allowed bg-blue-400"
                  : "bg-blue-600 hover:bg-blue-700"
              )}
            >
              {isSavingAppeal ? "Saving..." : "Save Appeal Details"}
            </button>
          </div>
        </section>
      )}

      {selectedAuth && retroForm && (
        <section
          className={cn(
            "mb-6 rounded-xl border p-4",
            darkMode
              ? "border-gray-800 bg-gray-950"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="mb-4">
            <h3 className="text-lg font-semibold">
              Start / Update Retro Auth Details
            </h3>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Track retro authorization submission, follow-up date, outcome, and
              notes for this authorization.
            </p>
          </div>

          {retroError && (
            <div
              role="alert"
              className={cn(
                "mb-4 rounded-lg border p-3 text-sm",
                darkMode
                  ? "border-red-900 bg-red-950/30 text-red-200"
                  : "border-red-200 bg-red-50 text-red-700"
              )}
            >
              {retroError}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-3 rounded-lg border px-3 py-2 text-sm border-inherit">
              <input
                type="checkbox"
                checked={retroForm.retroRequested}
                onChange={(event) =>
                  onRetroFieldChange("retroRequested", event.target.checked)
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Retro auth requested
              </span>
            </label>

            <label className="space-y-1 text-sm">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Retro Follow-up Date
              </span>
              <input
                type="date"
                value={retroForm.retroDeadline}
                onChange={(event) =>
                  onRetroFieldChange("retroDeadline", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
              <p
                className={cn(
                  "text-xs",
                  darkMode ? "text-gray-500" : "text-gray-500"
                )}
              >
                Optional. Use this to track when you want to follow up or submit
                the retro authorization by.
              </p>
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Retro Auth Outcome
              </span>
              <select
                value={retroForm.retroOutcome}
                onChange={(event) =>
                  onRetroFieldChange("retroOutcome", event.target.value)
                }
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              >
                {RETRO_OUTCOME_OPTIONS.map((option) => (
                  <option key={option || "blank"} value={option}>
                    {option || "Not selected"}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-sm md:col-span-2">
              <span className={darkMode ? "text-gray-300" : "text-gray-700"}>
                Retro Auth Notes
              </span>
              <textarea
                value={retroForm.retroNotes}
                onChange={(event) =>
                  onRetroFieldChange("retroNotes", event.target.value)
                }
                rows={3}
                placeholder="Add retro auth details, dates submitted, payer instructions, or outcome notes."
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
                )}
              />
            </label>
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                void onClearRetro();
              }}
              disabled={isSavingRetro}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Delete Retro Auth Details
            </button>

            <button
              type="button"
              onClick={onClearSelectedAuth}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              Back to Dashboard
            </button>

            <button
              type="button"
              onClick={() => {
                void onSaveRetro();
              }}
              disabled={isSavingRetro}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium text-white",
                isSavingRetro
                  ? "cursor-not-allowed bg-blue-400"
                  : "bg-blue-600 hover:bg-blue-700"
              )}
            >
              {isSavingRetro ? "Saving..." : "Save Retro Auth Details"}
            </button>
          </div>
        </section>
      )}
    </>
  );
}

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { updateAuthRequest } from "../api/authStatus";
import type { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";
import {
  APPEAL_OUTCOME_OPTIONS,
  DENIAL_LEVEL_OF_CARE_OPTIONS,
  DENIAL_REASON_OPTIONS,
  DENIAL_SOURCE_OPTIONS,
  P2P_OUTCOME_OPTIONS,
  RETRO_OUTCOME_OPTIONS,
  buildAppealPayload,
  buildClearAppealPayload,
  buildClearDenialPayload,
  buildClearP2PPayload,
  buildClearRetroPayload,
  buildDenialPayload,
  buildP2PPayload,
  buildRetroPayload,
  confirmClear,
  formatDate,
  getAppealFormFromAuth,
  getDenialFormFromAuth,
  getFollowUpItems,
  getP2PFormFromAuth,
  getRetroFormFromAuth,
  isOverdue,
  type AppealFormState,
  type DenialFormState,
  type P2PFormState,
  type RetroFormState,
} from "./denialsPipeline/followUpModels";

interface DenialsPipelinePageProps {
  data: AuthRequest[];
  darkMode: boolean;
  selectedAuthId: string | null;
  onSelectAuth: (auth: AuthRequest) => void;
  onClearSelectedAuth: () => void;
  onAuthUpdated: (auth: AuthRequest) => void;
}

export function DenialsPipelinePage({
  data,
  darkMode,
  selectedAuthId,
  onSelectAuth,
  onClearSelectedAuth,
  onAuthUpdated,
}: DenialsPipelinePageProps) {
  const denialCount = data.filter(
    (auth) => auth.status === "Denied" || auth.denialReasonCategory
  ).length;
  const p2pCount = data.filter((auth) => auth.p2pRequested).length;
  const appealCount = data.filter((auth) => auth.appealSubmitted).length;
  const retroCount = data.filter((auth) => auth.retroRequested).length;
  const selectedAuth = selectedAuthId
    ? data.find((auth) => auth.id === selectedAuthId) ?? null
    : null;
  const followUpItems = getFollowUpItems(data);
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
        error instanceof Error ? error.message : "Unable to clear P2P details."
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
          : "Unable to clear appeal details."
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
          : "Unable to clear retro auth details."
      );
    } finally {
      setIsSavingRetro(false);
    }
  };

  return (
    <div className="h-full overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold">Denials / P2P / Retro</h2>
        <p
          className={cn(
            "mt-1 text-sm",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          Focused workspace for denial follow-up, peer reviews, appeals, and
          retro authorization work.
        </p>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <SummaryCard label="Denials" value={denialCount} darkMode={darkMode} />
        <SummaryCard label="P2P" value={p2pCount} darkMode={darkMode} />
        <SummaryCard label="Appeals" value={appealCount} darkMode={darkMode} />
        <SummaryCard
          label="Retro Auths"
          value={retroCount}
          darkMode={darkMode}
        />
      </div>

      {selectedAuth && (
        <div
          className={cn(
            "mb-6 rounded-xl border p-4",
            darkMode
              ? "border-amber-800 bg-amber-950/30"
              : "border-amber-200 bg-amber-50"
          )}
        >
          <div className="text-sm font-semibold">Selected authorization</div>
          <div
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-amber-100" : "text-amber-800"
            )}
          >
            {selectedAuth.patientId} • {selectedAuth.facility} •{" "}
            {selectedAuth.payer} • {selectedAuth.loc}
          </div>
          <p
            className={cn(
              "mt-2 text-xs",
              darkMode ? "text-amber-200/80" : "text-amber-700"
            )}
          >
            Update denial, P2P, appeal, or retro auth details for this
            authorization.
          </p>
        </div>
      )}

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
                  handleDenialFieldChange(
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
                  handleDenialFieldChange("denialDate", event.target.value)
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
                  handleDenialFieldChange(
                    "denialThroughDate",
                    event.target.value
                  )
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
                  handleDenialFieldChange(
                    "denialLevelOfCare",
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
                  handleDenialFieldChange(
                    "denialReasonNotes",
                    event.target.value
                  )
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
                  handleDenialFieldChange(
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
                void handleClearDenial();
              }}
              disabled={isSavingDenial}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Clear Denial Details
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
                void handleSaveDenial();
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
                  handleP2PFieldChange("p2pRequested", event.target.checked)
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
                  handleP2PFieldChange("p2pScheduledAt", event.target.value)
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
                  handleP2PFieldChange("p2pDeadline", event.target.value)
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
                  handleP2PFieldChange("p2pOutcome", event.target.value)
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
                  handleP2PFieldChange("p2pReviewer", event.target.value)
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
                  handleP2PFieldChange("p2pNotes", event.target.value)
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
                void handleClearP2P();
              }}
              disabled={isSavingP2P}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Clear P2P Details
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
                void handleSaveP2P();
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
                  handleAppealFieldChange(
                    "appealSubmitted",
                    event.target.checked
                  )
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
                  handleAppealFieldChange("appealDeadline", event.target.value)
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
                  handleAppealFieldChange("appealOutcome", event.target.value)
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
                  handleAppealFieldChange("appealNotes", event.target.value)
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
                void handleClearAppeal();
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
                void handleSaveAppeal();
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
                  handleRetroFieldChange("retroRequested", event.target.checked)
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
                  handleRetroFieldChange("retroDeadline", event.target.value)
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
                  handleRetroFieldChange("retroOutcome", event.target.value)
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
                  handleRetroFieldChange("retroNotes", event.target.value)
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
                void handleClearRetro();
              }}
              disabled={isSavingRetro}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium",
                darkMode
                  ? "bg-red-950 text-red-200 hover:bg-red-900"
                  : "bg-red-50 text-red-700 hover:bg-red-100"
              )}
            >
              Clear Retro Auth Details
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
                void handleSaveRetro();
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

      {!selectedAuth && (
        <section
          className={cn(
            "mb-6 rounded-xl border p-4",
            darkMode
              ? "border-gray-800 bg-gray-950"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="mb-4">
            <h3 className="text-lg font-semibold">Follow-up Dashboard</h3>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Select a denial, P2P, appeal, or retro auth item to update its
              details.
            </p>
          </div>

          {followUpItems.length === 0 ? (
            <div
              className={cn(
                "rounded-lg border p-4 text-center text-sm",
                darkMode
                  ? "border-gray-800 bg-gray-900 text-gray-400"
                  : "border-gray-200 bg-gray-50 text-gray-600"
              )}
            >
              <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-gray-400" />
              <h3 className="text-lg font-semibold">Workspace ready</h3>
              <p
                className={cn(
                  "mx-auto mt-2 max-w-2xl text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Select an authorization from its detail view to manage denial
                follow-up, P2P, appeal, or retro authorization work here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {followUpItems.map((item) => {
                const overdue = isOverdue(item.dueDate);

                return (
                  <button
                    key={`${item.auth.id}-${item.type}`}
                    type="button"
                    onClick={() => onSelectAuth(item.auth)}
                    className={cn(
                      "w-full rounded-lg border p-4 text-left transition-colors",
                      darkMode
                        ? "border-gray-800 bg-gray-900 hover:bg-gray-800"
                        : "border-gray-200 bg-gray-50 hover:bg-gray-100"
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold">
                          {item.type}: {item.auth.patientId}
                        </div>
                        <div
                          className={cn(
                            "mt-1 text-xs",
                            darkMode ? "text-gray-400" : "text-gray-600"
                          )}
                        >
                          {item.auth.facility} • {item.auth.payer} •{" "}
                          {item.auth.loc}
                        </div>
                      </div>

                      <div
                        className={cn(
                          "rounded-full px-2.5 py-1 text-xs font-semibold",
                          overdue
                            ? darkMode
                              ? "bg-red-950 text-red-200"
                              : "bg-red-100 text-red-700"
                            : darkMode
                            ? "bg-gray-800 text-gray-300"
                            : "bg-gray-200 text-gray-700"
                        )}
                      >
                        {overdue ? "Overdue: " : "Due: "}
                        {formatDate(item.dueDate)}
                      </div>
                    </div>

                    <div
                      className={cn(
                        "mt-3 grid gap-3 text-xs md:grid-cols-2",
                        darkMode ? "text-gray-300" : "text-gray-700"
                      )}
                    >
                      <div>
                        <span
                          className={
                            darkMode ? "text-gray-500" : "text-gray-500"
                          }
                        >
                          Reason:
                        </span>{" "}
                        {item.reason || "Not recorded"}
                      </div>
                      <div>
                        <span
                          className={
                            darkMode ? "text-gray-500" : "text-gray-500"
                          }
                        >
                          Outcome:
                        </span>{" "}
                        {item.outcome || "Not recorded"}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  darkMode,
}: {
  label: string;
  value: number;
  darkMode: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4",
        darkMode ? "border-gray-800 bg-gray-950" : "border-gray-200 bg-white"
      )}
    >
      <div
        className={cn("text-sm", darkMode ? "text-gray-400" : "text-gray-500")}
      >
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

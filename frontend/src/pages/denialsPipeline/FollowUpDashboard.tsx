import { AlertTriangle } from "lucide-react";

import type { AuthRequest } from "../../types/auth";
import { cn } from "../../utils/cn";
import { formatDate, isOverdue, type FollowUpListItem } from "./followUpModels";

interface FollowUpDashboardProps {
  data: AuthRequest[];
  darkMode: boolean;
  selectedAuth: AuthRequest | null;
  followUpItems: FollowUpListItem[];
  onSelectAuth: (auth: AuthRequest) => void;
}

export function FollowUpDashboard({
  data,
  darkMode,
  selectedAuth,
  followUpItems,
  onSelectAuth,
}: FollowUpDashboardProps) {
  const denialCount = data.filter(
    (auth) => auth.status === "Denied" || auth.denialReasonCategory
  ).length;
  const p2pCount = data.filter((auth) => auth.p2pRequested).length;
  const appealCount = data.filter((auth) => auth.appealSubmitted).length;
  const retroCount = data.filter((auth) => auth.retroRequested).length;

  return (
    <>
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
                        <span className="text-gray-500">Reason:</span>{" "}
                        {item.reason || "Not recorded"}
                      </div>
                      <div>
                        <span className="text-gray-500">Outcome:</span>{" "}
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
    </>
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

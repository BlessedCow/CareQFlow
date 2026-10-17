import { useEffect, useMemo, useState } from "react";

import {
  fetchAuthDecisionSnapshots,
  type AuthDecisionSnapshot,
} from "../api/authDecisionSnapshots";
import { cn } from "../utils/cn";

interface DecisionHistorySectionProps {
  authId: string;
  darkMode: boolean;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not recorded";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatDateOnly(value: string | null) {
  if (!value) {
    return "Not recorded";
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString();
}

function reviewLabel(snapshot: AuthDecisionSnapshot) {
  switch (snapshot.review_type) {
    case "initial":
      return "Initial";
    case "concurrent":
      return "Concurrent";
    case "loc_change":
      return "LOC Change";
    case "p2p":
      return "Peer to Peer";
    case "appeal":
      return "Appeal";
    case "retro":
      return "Retro";
    default:
      return snapshot.review_type === "unknown"
        ? "Historical"
        : snapshot.review_type;
  }
}

function effectiveDecisionDate(snapshot: AuthDecisionSnapshot) {
  return snapshot.follow_up_decision_at ?? snapshot.decision_at;
}

function buildDecisionChains(
  snapshots: AuthDecisionSnapshot[]
): AuthDecisionSnapshot[][] {
  const roots = snapshots.filter(
    (snapshot) =>
      snapshot.snapshot_role === "root" || snapshot.snapshot_role === "legacy"
  );

  const assignedIds = new Set<number>();
  const chains = roots.map((root) => {
    assignedIds.add(root.id);

    const children = snapshots.filter((snapshot) => {
      if (snapshot.snapshot_role !== "follow_up") {
        return false;
      }

      if (snapshot.root_snapshot_id !== root.id) {
        return false;
      }

      assignedIds.add(snapshot.id);
      return true;
    });

    return [root, ...children].sort((left, right) => {
      return (
        new Date(effectiveDecisionDate(left)).getTime() -
        new Date(effectiveDecisionDate(right)).getTime()
      );
    });
  });

  for (const snapshot of snapshots) {
    if (!assignedIds.has(snapshot.id)) {
      chains.push([snapshot]);
    }
  }

  return chains;
}

function DecisionCard({
  snapshot,
  darkMode,
}: {
  snapshot: AuthDecisionSnapshot;
  darkMode: boolean;
}) {
  const isFollowUp = snapshot.snapshot_role === "follow_up";

  return (
    <article
      className={cn(
        "rounded-xl border p-4",
        isFollowUp && "ml-4 border-l-4 sm:ml-8",
        darkMode ? "border-gray-700 bg-gray-950" : "border-gray-200 bg-gray-50"
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{reviewLabel(snapshot)}</span>

            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                isFollowUp
                  ? darkMode
                    ? "bg-blue-950 text-blue-200"
                    : "bg-blue-100 text-blue-700"
                  : darkMode
                  ? "bg-gray-800 text-gray-200"
                  : "bg-gray-200 text-gray-700"
              )}
            >
              {isFollowUp ? "Follow-up" : "Root"}
            </span>
          </div>

          <div className="mt-1 text-sm font-medium">{snapshot.outcome}</div>
        </div>

        <div
          className={cn(
            "text-right text-xs",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          {formatDateTime(effectiveDecisionDate(snapshot))}
        </div>
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Level of Care
          </div>
          <div className="mt-1 font-medium">{snapshot.loc}</div>
        </div>

        <div>
          <div
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Requested
          </div>
          <div className="mt-1 font-medium">{snapshot.requested_days}</div>
        </div>

        <div>
          <div
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Approved
          </div>
          <div className="mt-1 font-medium">{snapshot.approved_days}</div>
        </div>

        <div>
          <div
            className={cn(
              "text-xs uppercase tracking-wide",
              darkMode ? "text-gray-500" : "text-gray-500"
            )}
          >
            Denied
          </div>
          <div className="mt-1 font-medium">{snapshot.denied_days}</div>
        </div>
      </div>

      {(snapshot.reviewed_from ||
        snapshot.reviewed_to ||
        snapshot.reviewed_loc ||
        snapshot.retro_reason) && (
        <div
          className={cn(
            "mt-4 rounded-lg border p-3 text-sm",
            darkMode
              ? "border-gray-800 bg-gray-900"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="font-medium">Reviewed service context</div>

          <div
            className={cn(
              "mt-2 text-xs",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            {formatDateOnly(snapshot.reviewed_from)}
            {" to "}
            {formatDateOnly(snapshot.reviewed_to)}
            {snapshot.reviewed_loc ? ` · ${snapshot.reviewed_loc}` : ""}
          </div>

          {snapshot.retro_reason && (
            <p className="mt-2 whitespace-pre-wrap">{snapshot.retro_reason}</p>
          )}
        </div>
      )}

      <div
        className={cn(
          "mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs",
          darkMode ? "text-gray-500" : "text-gray-500"
        )}
      >
        {snapshot.parent_snapshot_id !== null && (
          <span>Parent decision #{snapshot.parent_snapshot_id}</span>
        )}

        {snapshot.root_snapshot_id !== null && (
          <span>Root decision #{snapshot.root_snapshot_id}</span>
        )}

        <span>Context: {snapshot.context_provenance}</span>
      </div>
    </article>
  );
}

export function DecisionHistorySection({
  authId,
  darkMode,
}: DecisionHistorySectionProps) {
  const [snapshots, setSnapshots] = useState<AuthDecisionSnapshot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    setIsLoading(true);
    setError(null);

    void fetchAuthDecisionSnapshots(authId)
      .then((records) => {
        if (!cancelled) {
          setSnapshots(records);
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setSnapshots([]);
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load decision history."
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [authId]);

  const chains = useMemo(() => buildDecisionChains(snapshots), [snapshots]);

  return (
    <div
      className={cn(
        "mt-5 rounded-xl border p-4",
        darkMode ? "border-gray-700 bg-gray-900" : "border-gray-200 bg-white"
      )}
    >
      <div>
        <h3 className="text-sm font-semibold">Decision History</h3>
        <p
          className={cn(
            "mt-1 text-xs",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          Immutable authorization decisions and their P2P, appeal, and Retro
          lineage. This is separate from the operational timeline below.
        </p>
      </div>

      {error && (
        <div
          className={cn(
            "mt-4 rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900/60 bg-red-950/40 text-red-200"
              : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          {error}
        </div>
      )}

      {isLoading ? (
        <p
          className={cn(
            "mt-4 text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          Loading decision history...
        </p>
      ) : snapshots.length === 0 ? (
        <p
          className={cn(
            "mt-4 text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          No immutable decision snapshots recorded yet.
        </p>
      ) : (
        <div className="mt-4 space-y-5">
          {chains.map((chain) => (
            <div key={chain[0].id} className="space-y-3">
              {chain.map((snapshot) => (
                <DecisionCard
                  key={snapshot.id}
                  snapshot={snapshot}
                  darkMode={darkMode}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

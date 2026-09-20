import { useMemo, useState } from "react";
import { AlertTriangle, Search } from "lucide-react";

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

type FollowUpFilter = "Denial" | "P2P" | "Appeal" | "Retro Auth";

export function FollowUpDashboard({
  data,
  darkMode,
  selectedAuth,
  followUpItems,
  onSelectAuth,
}: FollowUpDashboardProps) {
  const [selectedFilters, setSelectedFilters] = useState<Set<FollowUpFilter>>(
    new Set()
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const denialCount = data.filter((auth) => auth.status === "Denied").length;
  const p2pCount = data.filter((auth) => auth.p2pRequested).length;
  const appealCount = data.filter((auth) => auth.appealSubmitted).length;
  const retroCount = data.filter((auth) => auth.retroRequested).length;

  const toggleFilter = (filter: FollowUpFilter) => {
    setSelectedFilters((current) => {
      const next = new Set(current);

      if (next.has(filter)) {
        next.delete(filter);
      } else {
        next.add(filter);
      }

      return next;
    });
  };

  const filteredFollowUpItems = useMemo(() => {
    const normalizedSearch = searchQuery.trim().toLowerCase();

    return followUpItems.filter((item) => {
      if (
        selectedFilters.size > 0 &&
        !selectedFilters.has(item.type as FollowUpFilter)
      ) {
        return false;
      }

      if (normalizedSearch) {
        const searchableValues = [
          item.auth.patientId,
          item.auth.facility,
          item.auth.payer,
          item.auth.insurancePlan ?? "",
          item.auth.loc,
        ];

        if (
          !searchableValues.some((value) =>
            value.toLowerCase().includes(normalizedSearch)
          )
        ) {
          return false;
        }
      }

      if (startDate && (!item.dueDate || item.dueDate < startDate)) {
        return false;
      }

      if (endDate && (!item.dueDate || item.dueDate > endDate)) {
        return false;
      }

      return true;
    });
  }, [endDate, followUpItems, searchQuery, selectedFilters, startDate]);

  return (
    <>
      <div
        data-walkthrough="denials-summary"
        className="mb-6 grid gap-4 md:grid-cols-4"
      >
        <SummaryCard
          label="Denials"
          value={denialCount}
          darkMode={darkMode}
          selected={selectedFilters.has("Denial")}
          onClick={() => toggleFilter("Denial")}
        />
        <SummaryCard
          label="P2P"
          value={p2pCount}
          darkMode={darkMode}
          selected={selectedFilters.has("P2P")}
          onClick={() => toggleFilter("P2P")}
        />
        <SummaryCard
          label="Appeals"
          value={appealCount}
          darkMode={darkMode}
          selected={selectedFilters.has("Appeal")}
          onClick={() => toggleFilter("Appeal")}
        />
        <SummaryCard
          label="Retro Auths"
          value={retroCount}
          darkMode={darkMode}
          selected={selectedFilters.has("Retro Auth")}
          onClick={() => toggleFilter("Retro Auth")}
        />
      </div>

      {!selectedAuth && (
        <section
          data-walkthrough="denials-follow-up-dashboard"
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

          <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]">
            <label className="relative">
              <Search
                className={cn(
                  "pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2",
                  darkMode ? "text-gray-500" : "text-gray-400"
                )}
              />
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search client, facility, insurance, or LOC"
                className={cn(
                  "w-full rounded-lg border py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100 placeholder:text-gray-500"
                    : "border-gray-300 bg-white text-gray-900 placeholder:text-gray-400"
                )}
              />
            </label>

            <label className="flex items-center gap-2 text-sm">
              <span className={darkMode ? "text-gray-400" : "text-gray-600"}>
                From
              </span>
              <input
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                className={cn(
                  "rounded-lg border px-3 py-2 text-sm",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </label>

            <label className="flex items-center gap-2 text-sm">
              <span className={darkMode ? "text-gray-400" : "text-gray-600"}>
                To
              </span>
              <input
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                className={cn(
                  "rounded-lg border px-3 py-2 text-sm",
                  darkMode
                    ? "border-gray-700 bg-gray-900 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </label>
          </div>

          {filteredFollowUpItems.length === 0 ? (
            <div
              className={cn(
                "rounded-lg border p-4 text-center text-sm",
                darkMode
                  ? "border-gray-800 bg-gray-900 text-gray-400"
                  : "border-gray-200 bg-gray-50 text-gray-600"
              )}
            >
              <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-gray-400" />
              <h3 className="text-lg font-semibold">No matching items</h3>
              <p
                className={cn(
                  "mx-auto mt-2 max-w-2xl text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                No follow-up items match the current filters.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredFollowUpItems.map((item) => {
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
  selected,
  onClick,
}: {
  label: string;
  value: number;
  darkMode: boolean;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "rounded-xl border p-4 text-left transition-colors",
        selected
          ? darkMode
            ? "border-blue-500 bg-blue-950/40"
            : "border-blue-500 bg-blue-50"
          : darkMode
          ? "border-gray-800 bg-gray-950 hover:bg-gray-900"
          : "border-gray-200 bg-white hover:bg-gray-50"
      )}
    >
      <div
        className={cn(
          "text-sm",
          selected
            ? darkMode
              ? "text-blue-300"
              : "text-blue-700"
            : darkMode
            ? "text-gray-400"
            : "text-gray-500"
        )}
      >
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </button>
  );
}

import { useCallback, useEffect, useState } from "react";

import {
  fetchDenialInsights,
  type DenialInsightsDimension,
  type DenialInsightsResponse,
} from "../api/denialInsights";
import { cn } from "../utils/cn";

interface DenialInsightsPageProps {
  darkMode: boolean;
}

const DIMENSION_OPTIONS: {
  value: DenialInsightsDimension;
  label: string;
}[] = [
  { value: "insurance", label: "Insurance" },
  { value: "insurance_plan", label: "Insurance Plan" },
  { value: "facility", label: "Facility" },
  { value: "loc", label: "Level of Care" },
  { value: "auth_type", label: "Review Type" },
  { value: "outcome", label: "Decision Outcome" },
  {
    value: "denial_reason_category",
    label: "Denial Reason Category",
  },
  { value: "denial_source", label: "Denial Source" },
];

function formatRate(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return `${(value * 100).toFixed(1)}%`;
}

function formatSampleState(value: string): string {
  switch (value) {
    case "standard":
      return "Standard";
    case "preliminary":
      return "Preliminary";
    default:
      return "Insufficient";
  }
}

export function DenialInsightsPage({ darkMode }: DenialInsightsPageProps) {
  const [dimension, setDimension] =
    useState<DenialInsightsDimension>("insurance");
  const [result, setResult] = useState<DenialInsightsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadInsights = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchDenialInsights({
        dimensions: [dimension],
      });

      setResult(response);
    } catch (loadError) {
      setResult(null);
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load denial insights."
      );
    } finally {
      setIsLoading(false);
    }
  }, [dimension]);

  useEffect(() => {
    void loadInsights();
  }, [loadInsights]);

  return (
    <div className="space-y-6">
      <section
        className={cn(
          "rounded-xl border p-6 shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Denial Insights</h2>

            <p
              className={cn(
                "mt-1 max-w-3xl text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Review observed authorization decision patterns from historical
              decision snapshots. These associations do not establish payer
              policy or causation.
            </p>
          </div>

          <label className="w-full space-y-2 md:w-64">
            <span className="text-sm font-medium">Group by</span>

            <select
              value={dimension}
              onChange={(event) =>
                setDimension(event.target.value as DenialInsightsDimension)
              }
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            >
              {DIMENSION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {error && (
        <div
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900/60 bg-red-950/40 text-red-200"
              : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          {error}
        </div>
      )}

      {isLoading ? (
        <section
          className={cn(
            "rounded-xl border p-6 text-sm shadow-sm",
            darkMode
              ? "border-gray-800 bg-gray-900 text-gray-400"
              : "border-gray-200 bg-white text-gray-600"
          )}
        >
          Loading denial insights...
        </section>
      ) : result ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              {
                label: "Decisions",
                value: String(result.summary.decision_count),
              },
              {
                label: "Observed denial rate",
                value: formatRate(result.summary.observed_denial_rate),
              },
              {
                label: "Observed partial rate",
                value: formatRate(result.summary.observed_partial_rate),
              },
              {
                label: "Observed adverse rate",
                value: formatRate(result.summary.observed_adverse_rate),
              },
            ].map((item) => (
              <div
                key={item.label}
                className={cn(
                  "rounded-xl border p-5 shadow-sm",
                  darkMode
                    ? "border-gray-800 bg-gray-900"
                    : "border-gray-200 bg-white"
                )}
              >
                <div
                  className={cn(
                    "text-sm",
                    darkMode ? "text-gray-400" : "text-gray-600"
                  )}
                >
                  {item.label}
                </div>

                <div className="mt-2 text-2xl font-semibold">{item.value}</div>
              </div>
            ))}
          </section>

          <section
            className={cn(
              "rounded-xl border shadow-sm",
              darkMode
                ? "border-gray-800 bg-gray-900"
                : "border-gray-200 bg-white"
            )}
          >
            <div className="flex items-center justify-between border-b border-inherit p-6">
              <div>
                <h2 className="text-lg font-semibold">Observed patterns</h2>

                <p
                  className={cn(
                    "mt-1 text-sm",
                    darkMode ? "text-gray-400" : "text-gray-600"
                  )}
                >
                  {result.groups.length} grouped result
                  {result.groups.length === 1 ? "" : "s"}
                </p>
              </div>

              <button
                type="button"
                onClick={() => void loadInsights()}
                disabled={isLoading}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium",
                  darkMode
                    ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                )}
              >
                Refresh
              </button>
            </div>

            {result.groups.length === 0 ? (
              <div
                className={cn(
                  "p-6 text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                No decision snapshots are available for this analysis.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1050px] text-left text-sm">
                  <thead
                    className={cn(
                      "border-b",
                      darkMode
                        ? "border-gray-800 text-gray-400"
                        : "border-gray-200 text-gray-600"
                    )}
                  >
                    <tr>
                      <th className="px-6 py-3 font-medium">Group</th>
                      <th className="px-6 py-3 font-medium">Decisions</th>
                      <th className="px-6 py-3 font-medium">Denied</th>
                      <th className="px-6 py-3 font-medium">Partial</th>
                      <th className="px-6 py-3 font-medium">Adverse</th>
                      <th className="px-6 py-3 font-medium">Sample</th>
                      <th className="px-6 py-3 font-medium">Comparison</th>
                    </tr>
                  </thead>

                  <tbody>
                    {result.groups.map((group, index) => {
                      const evaluation = result.evaluations[index];

                      return (
                        <tr
                          key={`${dimension}-${
                            group.dimensions[dimension] ?? index
                          }`}
                          className={cn(
                            "border-b last:border-b-0",
                            darkMode ? "border-gray-800" : "border-gray-200"
                          )}
                        >
                          <td className="px-6 py-4 font-medium">
                            {group.dimensions[dimension] ?? "Unknown"}
                          </td>

                          <td className="px-6 py-4">{group.decision_count}</td>

                          <td className="px-6 py-4">
                            {formatRate(group.observed_denial_rate)}
                          </td>

                          <td className="px-6 py-4">
                            {formatRate(group.observed_partial_rate)}
                          </td>

                          <td className="px-6 py-4">
                            {formatRate(group.observed_adverse_rate)}
                          </td>

                          <td className="px-6 py-4">
                            {formatSampleState(group.sample_state)}
                          </td>

                          <td className="px-6 py-4">
                            <div>
                              {evaluation?.triggered
                                ? "Elevated vs baseline"
                                : "Not flagged"}
                            </div>

                            {evaluation && (
                              <div
                                className={cn(
                                  "mt-1 max-w-md text-xs",
                                  darkMode ? "text-gray-500" : "text-gray-500"
                                )}
                              >
                                {evaluation.reason}
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}

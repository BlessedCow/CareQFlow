import { useCallback, useEffect, useState } from "react";

import {
  fetchDenialInsights,
  type DenialInsightsDimension,
  type DenialInsightsResponse,
} from "../api/denialInsights";
import { cn } from "../utils/cn";

interface DenialInsightsPageProps {
  darkMode: boolean;
  canShowEvidenceCalculation?: boolean;
}

const DIMENSION_OPTIONS: {
  value: DenialInsightsDimension;
  label: string;
}[] = [
  { value: "insurance", label: "Insurance" },
  { value: "insurance_plan", label: "Insurance Plan" },
  { value: "facility", label: "Facility" },
  { value: "loc", label: "Level of Care" },
  {
    value: "days_at_current_loc",
    label: "Days at Current LOC",
  },
  {
    value: "total_treatment_days",
    label: "Total Treatment Days",
  },
  {
    value: "clinical_instrument",
    label: "Clinical Assessment",
  },
  {
    value: "clinical_latest_score",
    label: "Latest Clinical Score",
  },
  {
    value: "clinical_score_age_days",
    label: "Clinical Score Age",
  },
  {
    value: "clinical_score_change",
    label: "Clinical Score Change",
  },
  {
    value: "clinical_score_trend",
    label: "Clinical Score Trend",
  },
  {
    value: "clinical_assessment_count",
    label: "Clinical Assessment Count",
  },
  {
    value: "clinical_min_score",
    label: "Clinical Minimum Score",
  },
  {
    value: "clinical_max_score",
    label: "Clinical Maximum Score",
  },
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

function formatInterval(
  interval: {
    lower: number;
    upper: number;
  } | null
): string {
  if (!interval) {
    return "—";
  }

  return `${(interval.lower * 100).toFixed(1)}% to ${(
    interval.upper * 100
  ).toFixed(1)}%`;
}

function formatPoints(points: number, maximum: number): string {
  return `${points.toFixed(1)} / ${maximum.toFixed(0)}`;
}

export function DenialInsightsPage({
  darkMode,
  canShowEvidenceCalculation = false,
}: DenialInsightsPageProps) {
  const [dimensions, setDimensions] = useState<DenialInsightsDimension[]>([
    "insurance",
  ]);
  const [result, setResult] = useState<DenialInsightsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEvidenceCalculation, setShowEvidenceCalculation] = useState(false);

  const toggleDimension = (dimension: DenialInsightsDimension) => {
    setDimensions((current) => {
      if (current.includes(dimension)) {
        if (current.length === 1) {
          return current;
        }

        return current.filter((item) => item !== dimension);
      }

      if (current.length >= 5) {
        return current;
      }

      return [...current, dimension];
    });
  };

  const loadInsights = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchDenialInsights({
        dimensions,
        ...(canShowEvidenceCalculation && showEvidenceCalculation
          ? {
              include_evidence_calculation: true,
            }
          : {}),
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
  }, [dimensions, canShowEvidenceCalculation, showEvidenceCalculation]);

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
              <span className="mt-1 block">
                Evidence strength describes the amount, stability, separation,
                and completeness of historical evidence. It does not represent
                the probability of denial.
              </span>
            </p>
          </div>

          <div className="w-full md:max-w-2xl">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-medium">Group by</span>

              <span
                className={cn(
                  "text-xs",
                  darkMode ? "text-gray-500" : "text-gray-500"
                )}
              >
                {dimensions.length} of 5 selected
              </span>
            </div>

            <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {DIMENSION_OPTIONS.map((option) => {
                const checked = dimensions.includes(option.value);
                const disabled = !checked && dimensions.length >= 5;

                return (
                  <label
                    key={option.value}
                    className={cn(
                      "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
                      checked
                        ? darkMode
                          ? "border-gray-600 bg-gray-800"
                          : "border-gray-400 bg-gray-50"
                        : darkMode
                        ? "border-gray-800 bg-gray-950"
                        : "border-gray-200 bg-white",
                      disabled && "cursor-not-allowed opacity-50",
                      !disabled && "cursor-pointer"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggleDimension(option.value)}
                    />

                    <span>{option.label}</span>
                  </label>
                );
              })}
            </div>

            <p
              className={cn(
                "mt-2 text-xs",
                darkMode ? "text-gray-500" : "text-gray-500"
              )}
            >
              Select up to five dimensions. At least one dimension must remain
              selected.
            </p>
          </div>
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

              <div className="flex items-center gap-3">
                {canShowEvidenceCalculation && (
                  <label
                    className={cn(
                      "flex items-center gap-2 text-sm",
                      darkMode ? "text-gray-300" : "text-gray-700"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={showEvidenceCalculation}
                      onChange={(event) =>
                        setShowEvidenceCalculation(event.target.checked)
                      }
                    />

                    <span>Show evidence calculation</span>
                  </label>
                )}

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
                      {dimensions.map((dimension) => {
                        const option = DIMENSION_OPTIONS.find(
                          (item) => item.value === dimension
                        );

                        return (
                          <th key={dimension} className="px-6 py-3 font-medium">
                            {option?.label ?? dimension}
                          </th>
                        );
                      })}
                      <th className="px-6 py-3 font-medium">Decisions</th>
                      <th className="px-6 py-3 font-medium">Denied</th>
                      <th className="px-6 py-3 font-medium">Partial</th>
                      <th className="px-6 py-3 font-medium">Adverse</th>
                      <th className="px-6 py-3 font-medium">Sample</th>
                      <th className="px-6 py-3 font-medium">
                        Evidence Strength
                      </th>
                      <th className="px-6 py-3 font-medium">95% Interval</th>
                      <th className="px-6 py-3 font-medium">Comparison</th>
                    </tr>
                  </thead>

                  <tbody>
                    {result.groups.map((group, index) => {
                      const evaluation = result.evaluations[index];

                      return (
                        <tr
                          key={dimensions
                            .map(
                              (dimension) =>
                                `${dimension}:${
                                  group.dimensions[dimension] ?? "Unknown"
                                }`
                            )
                            .join("|")}
                        >
                          {dimensions.map((dimension, dimensionIndex) => (
                            <td
                              key={dimension}
                              className={cn(
                                "px-6 py-4",
                                dimensionIndex === 0 && "font-medium"
                              )}
                            >
                              {group.dimensions[dimension] ?? "Unknown"}
                            </td>
                          ))}

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

                          <td className="px-6 py-4 align-top">
                            {evaluation?.evidence_strength ? (
                              <div className="space-y-1">
                                <div className="font-medium">
                                  {evaluation.evidence_strength.level}
                                </div>

                                <div
                                  className={cn(
                                    "text-xs",
                                    darkMode ? "text-gray-400" : "text-gray-500"
                                  )}
                                >
                                  {evaluation.evidence_strength.score}/100
                                </div>

                                <div
                                  className={cn(
                                    "text-xs",
                                    darkMode ? "text-gray-500" : "text-gray-500"
                                  )}
                                >
                                  n={evaluation.evidence_strength.sample_size}
                                  {" · "}
                                  baseline n=
                                  {
                                    evaluation.evidence_strength
                                      .baseline_sample_size
                                  }
                                </div>

                                {showEvidenceCalculation &&
                                  evaluation.evidence_strength.calculation && (
                                    <div
                                      className={cn(
                                        "mt-3 space-y-1 rounded-lg border p-3 text-xs",
                                        darkMode
                                          ? "border-gray-700 bg-gray-950"
                                          : "border-gray-200 bg-gray-50"
                                      )}
                                    >
                                      <div>
                                        Sample strength:{" "}
                                        {formatPoints(
                                          evaluation.evidence_strength
                                            .calculation.sample_strength.points,
                                          evaluation.evidence_strength
                                            .calculation.sample_strength
                                            .maximum_points
                                        )}
                                      </div>

                                      <div>
                                        Baseline separation:{" "}
                                        {formatPoints(
                                          evaluation.evidence_strength
                                            .calculation.baseline_separation
                                            .points,
                                          evaluation.evidence_strength
                                            .calculation.baseline_separation
                                            .maximum_points
                                        )}
                                      </div>

                                      <div>
                                        Rate stability:{" "}
                                        {formatPoints(
                                          evaluation.evidence_strength
                                            .calculation.rate_stability.points,
                                          evaluation.evidence_strength
                                            .calculation.rate_stability
                                            .maximum_points
                                        )}
                                      </div>

                                      <div>
                                        Data completeness:{" "}
                                        {formatPoints(
                                          evaluation.evidence_strength
                                            .calculation.data_completeness
                                            .points,
                                          evaluation.evidence_strength
                                            .calculation.data_completeness
                                            .maximum_points
                                        )}
                                      </div>

                                      <div
                                        className={cn(
                                          "mt-2 border-t pt-2 font-medium",
                                          darkMode
                                            ? "border-gray-700"
                                            : "border-gray-200"
                                        )}
                                      >
                                        Final score:{" "}
                                        {
                                          evaluation.evidence_strength
                                            .calculation.final_score
                                        }
                                        /100
                                      </div>

                                      <div>
                                        Sample cap:{" "}
                                        {
                                          evaluation.evidence_strength
                                            .calculation.sample_cap
                                        }
                                      </div>

                                      <div>
                                        Calculation version:{" "}
                                        {
                                          evaluation.evidence_strength
                                            .calculation.version
                                        }
                                      </div>
                                    </div>
                                  )}
                              </div>
                            ) : (
                              "—"
                            )}
                          </td>

                          <td className="px-6 py-4 align-top">
                            {evaluation?.evidence_strength
                              ? formatInterval(
                                  evaluation.evidence_strength
                                    .wilson_95_interval
                                )
                              : "—"}
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

import { API_BASE_URL, authenticatedFetch } from "./client";

export type DenialInsightsDimension =
  | "facility"
  | "insurance"
  | "insurance_plan"
  | "loc"
  | "auth_type"
  | "outcome"
  | "denial_reason_category"
  | "denial_source"
  | "source";

export interface DenialInsightsSummary {
  decision_count: number;
  approved_count: number;
  partial_count: number;
  denied_count: number;
  adverse_count: number;
  unclassified_count: number;
  observed_denial_rate: number | null;
  observed_partial_rate: number | null;
  observed_adverse_rate: number | null;
  requested_days: number;
  approved_days: number;
  denied_days: number;
}

export interface DenialInsightsGroup extends DenialInsightsSummary {
  dimensions: Record<string, string>;
  sample_state: "insufficient" | "preliminary" | "standard";
}

export interface DenialInsightsEvaluation {
  triggered: boolean;
  dimensions: Record<string, string>;
  decision_count: number;
  baseline_decision_count: number;
  observed_denial_rate: number | null;
  baseline_denial_rate: number | null;
  absolute_rate_difference: number | null;
  relative_rate_increase: number | null;
  minimum_sample_size: number;
  minimum_denial_rate: number;
  minimum_relative_increase: number;
  reason: string;
}

export interface DenialInsightsResponse {
  dimensions: string[];
  filters: Record<string, string>;
  baseline_filters: Record<string, string>;
  start_at: string | null;
  end_at: string | null;
  summary: DenialInsightsSummary;
  baseline: DenialInsightsGroup;
  groups: DenialInsightsGroup[];
  evaluations: DenialInsightsEvaluation[];
}

export interface DenialInsightsQuery {
  dimensions: DenialInsightsDimension[];
  filters?: Record<string, string>;
  baseline_filters?: Record<string, string>;
  start_at?: string | null;
  end_at?: string | null;
  preliminary_minimum?: number;
  standard_minimum?: number;
  rule_thresholds?: {
    minimum_sample_size?: number;
    minimum_denial_rate?: number;
    minimum_relative_increase?: number;
  };
}

export async function fetchDenialInsights(
  payload: DenialInsightsQuery
): Promise<DenialInsightsResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/denial-insights/query`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    let message = "Unable to load denial insights.";

    try {
      const data = (await response.json()) as {
        detail?: string;
      };

      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep the generic message when the response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as DenialInsightsResponse;
}

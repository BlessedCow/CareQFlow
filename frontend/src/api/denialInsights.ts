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
  | "source"
  | "days_at_current_loc"
  | "total_treatment_days"
  | "clinical_instrument"
  | "clinical_latest_score"
  | "clinical_score_age_days"
  | "clinical_score_change"
  | "clinical_score_trend"
  | "clinical_assessment_count"
  | "clinical_min_score"
  | "clinical_max_score";

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

export interface EvidenceStrengthCalculation {
  version: string;
  sample_strength: {
    points: number;
    maximum_points: number;
    effective_sample_size: number;
    standard_sample_size: number;
  };
  baseline_separation: {
    points: number;
    maximum_points: number;
    absolute_rate_difference: number | null;
    full_points_difference: number;
  };
  rate_stability: {
    points: number;
    maximum_points: number;
    wilson_interval_width: number | null;
  };
  data_completeness: {
    points: number;
    maximum_points: number;
    ratio: number;
  };
  uncapped_score: number;
  sample_cap: number;
  final_score: number;
}

export interface EvidenceStrength {
  score: number;
  level: string;
  sample_size: number;
  baseline_sample_size: number;
  wilson_95_interval: {
    lower: number;
    upper: number;
  } | null;
  calculation?: EvidenceStrengthCalculation;
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
  evidence_strength: EvidenceStrength;
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
  include_evidence_calculation?: boolean;
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

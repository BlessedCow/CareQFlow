import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchDenialInsights } from "../../api/denialInsights";
import { DenialInsightsPage } from "../DenialInsightsPage";

vi.mock("../../api/denialInsights", () => ({
  fetchDenialInsights: vi.fn(),
}));

const mockedFetchDenialInsights = vi.mocked(fetchDenialInsights);

function responseFor(dimensions: string[] = ["insurance"]) {
  return {
    dimensions,
    filters: {},
    baseline_filters: {},
    start_at: null,
    end_at: null,
    summary: {
      decision_count: 10,
      approved_count: 5,
      partial_count: 1,
      denied_count: 4,
      adverse_count: 5,
      unclassified_count: 0,
      observed_denial_rate: 0.4,
      observed_partial_rate: 0.1,
      observed_adverse_rate: 0.5,
      requested_days: 50,
      approved_days: 30,
      denied_days: 20,
    },
    follow_up_metrics: {
      p2p: {
        eligible_count: 5,
        initiated_count: 4,
        pending_count: 1,
        resolved_count: 3,
        approved_count: 0,
        denied_count: 0,
        upheld_count: 2,
        overturned_count: 1,
        partially_approved_count: 0,
        overturn_rate: 1 / 3,
      },
      appeal: {
        eligible_count: 3,
        initiated_count: 2,
        pending_count: 0,
        resolved_count: 2,
        approved_count: 0,
        denied_count: 1,
        upheld_count: 0,
        overturned_count: 1,
        partially_approved_count: 0,
        overturn_rate: 0.5,
      },
      retro: {
        eligible_count: 2,
        initiated_count: 1,
        pending_count: 0,
        resolved_count: 1,
        approved_count: 1,
        denied_count: 0,
        upheld_count: 0,
        overturned_count: 0,
        partially_approved_count: 0,
        overturn_rate: null,
      },
    },
    retro_root_metrics: {
      decision_count: 3,
      approved_count: 1,
      partial_count: 1,
      denied_count: 1,
      adverse_count: 2,
      unclassified_count: 0,
      observed_denial_rate: 1 / 3,
      observed_partial_rate: 1 / 3,
      observed_adverse_rate: 2 / 3,
      requested_days: 15,
      approved_days: 5,
      denied_days: 5,
    },
    baseline: {
      dimensions: {},
      decision_count: 10,
      approved_count: 5,
      partial_count: 1,
      denied_count: 4,
      adverse_count: 5,
      unclassified_count: 0,
      observed_denial_rate: 0.4,
      observed_partial_rate: 0.1,
      observed_adverse_rate: 0.5,
      requested_days: 50,
      approved_days: 30,
      denied_days: 20,
      sample_state: "preliminary" as const,
    },
    groups: [
      {
        dimensions: {
          insurance: "Payer A",
          loc: "RTC",
          days_at_current_loc: "11",
        },
        decision_count: 5,
        approved_count: 2,
        partial_count: 1,
        denied_count: 2,
        adverse_count: 3,
        unclassified_count: 0,
        observed_denial_rate: 0.4,
        observed_partial_rate: 0.2,
        observed_adverse_rate: 0.6,
        requested_days: 25,
        approved_days: 15,
        denied_days: 10,
        sample_state: "preliminary" as const,
      },
    ],
    evaluations: [
      {
        triggered: false,
        dimensions: {
          insurance: "Payer A",
        },
        decision_count: 5,
        baseline_decision_count: 10,
        observed_denial_rate: 0.4,
        baseline_denial_rate: 0.4,
        absolute_rate_difference: 0,
        relative_rate_increase: 0,
        minimum_sample_size: 5,
        minimum_denial_rate: 0.2,
        minimum_relative_increase: 0.25,
        reason:
          "Observed denial rate does not exceed the selected baseline by the configured amount.",
        evidence_strength: {
          score: 62,
          level: "Moderate",
          sample_size: 5,
          baseline_sample_size: 10,
          wilson_95_interval: {
            lower: 0.1176,
            upper: 0.7693,
          },
        },
      },
    ],
  };
}

describe("DenialInsightsPage", () => {
  beforeEach(() => {
    mockedFetchDenialInsights.mockReset();
    mockedFetchDenialInsights.mockResolvedValue(responseFor());
  });

  it("queries by insurance by default", async () => {
    render(<DenialInsightsPage darkMode={false} />);

    await waitFor(() => {
      expect(mockedFetchDenialInsights).toHaveBeenCalledWith({
        dimensions: ["insurance"],
      });
    });
  });

  it("supports multiple dimensions", async () => {
    render(<DenialInsightsPage darkMode={false} />);

    await screen.findByText("Payer A");

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Level of Care",
      })
    );

    await waitFor(() => {
      expect(mockedFetchDenialInsights).toHaveBeenLastCalledWith({
        dimensions: ["insurance", "loc"],
      });
    });
  });

  it("does not allow the final dimension to be removed", async () => {
    render(<DenialInsightsPage darkMode={false} />);

    await screen.findByText("Payer A");

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Insurance",
      })
    );

    expect(
      screen.getByRole("checkbox", {
        name: "Insurance",
      })
    ).toBeChecked();

    expect(mockedFetchDenialInsights).toHaveBeenCalledTimes(1);
  });

  it("limits selection to five dimensions", async () => {
    render(<DenialInsightsPage darkMode={false} />);

    await screen.findByText("Payer A");

    for (const label of [
      "Insurance Plan",
      "Facility",
      "Level of Care",
      "Days at Current LOC",
    ]) {
      fireEvent.click(
        screen.getByRole("checkbox", {
          name: label,
        })
      );
    }

    await waitFor(() => {
      expect(screen.getByText("5 of 5 selected")).toBeInTheDocument();
    });

    expect(
      screen.getByRole("checkbox", {
        name: "Total Treatment Days",
      })
    ).toBeDisabled();
  });

  it("renders one column for each selected dimension", async () => {
    mockedFetchDenialInsights.mockResolvedValue(
      responseFor(["insurance", "loc"])
    );

    render(<DenialInsightsPage darkMode={false} />);

    await screen.findByText("Payer A");

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Level of Care",
      })
    );

    expect(
      await screen.findByRole("columnheader", {
        name: "Insurance",
      })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("columnheader", {
        name: "Level of Care",
      })
    ).toBeInTheDocument();

    expect(screen.getByText("RTC")).toBeInTheDocument();
  });

  it("shows evidence strength to denial insights users", async () => {
    render(<DenialInsightsPage darkMode={false} />);

    expect(await screen.findByText("Moderate")).toBeInTheDocument();

    expect(screen.getByText("62/100")).toBeInTheDocument();

    expect(screen.getByText("11.8% to 76.9%")).toBeInTheDocument();
  });

  it("does not show the calculation toggle to non admins", async () => {
    render(
      <DenialInsightsPage darkMode={false} canShowEvidenceCalculation={false} />
    );

    await screen.findByText("Moderate");

    expect(
      screen.queryByRole("checkbox", {
        name: "Show evidence calculation",
      })
    ).not.toBeInTheDocument();
  });

  it("allows admins to request evidence calculation", async () => {
    mockedFetchDenialInsights
      .mockResolvedValueOnce(responseFor())
      .mockResolvedValueOnce({
        ...responseFor(),
        evaluations: [
          {
            ...responseFor().evaluations[0],
            evidence_strength: {
              ...responseFor().evaluations[0].evidence_strength,
              calculation: {
                version: "1.0",
                sample_strength: {
                  points: 20,
                  maximum_points: 40,
                  effective_sample_size: 10,
                  standard_sample_size: 20,
                },
                baseline_separation: {
                  points: 12,
                  maximum_points: 30,
                  absolute_rate_difference: 0.1,
                  full_points_difference: 0.25,
                },
                rate_stability: {
                  points: 10,
                  maximum_points: 20,
                  wilson_interval_width: 0.4,
                },
                data_completeness: {
                  points: 10,
                  maximum_points: 10,
                  ratio: 1,
                },
                uncapped_score: 52,
                sample_cap: 49,
                final_score: 49,
              },
            },
          },
        ],
      });

    render(<DenialInsightsPage darkMode={false} canShowEvidenceCalculation />);

    await screen.findByText("Moderate");

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Show evidence calculation",
      })
    );

    await waitFor(() => {
      expect(mockedFetchDenialInsights).toHaveBeenLastCalledWith({
        dimensions: ["insurance"],
        include_evidence_calculation: true,
      });
    });

    expect(await screen.findByText(/Sample strength:/)).toBeInTheDocument();

    expect(screen.getByText(/Calculation version:/)).toBeInTheDocument();
  });

  it("shows follow-up and standalone Retro metrics", async () => {
    render(<DenialInsightsPage darkMode={false} />);

    expect(
      await screen.findByText("Follow-up outcomes")
    ).toBeInTheDocument();

    expect(screen.getByText("Peer to Peer")).toBeInTheDocument();
    expect(screen.getByText("Appeal")).toBeInTheDocument();
    expect(screen.getByText("Retro Follow-up")).toBeInTheDocument();

    expect(
      screen.getByText("Standalone Retro decisions")
    ).toBeInTheDocument();

    expect(screen.getByText("33.3%")).toBeInTheDocument();
  });

});

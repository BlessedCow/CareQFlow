import { beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedFetch } from "../client";
import { fetchDenialInsights } from "../denialInsights";

vi.mock("../client", () => ({
  API_BASE_URL: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

const mockedAuthenticatedFetch = vi.mocked(authenticatedFetch);

describe("denial insights API", () => {
  beforeEach(() => {
    mockedAuthenticatedFetch.mockReset();
  });

  it("posts a denial insights query", async () => {
    const responseBody = {
      dimensions: ["insurance"],
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
        sample_state: "preliminary",
      },
      groups: [],
      evaluations: [],
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    await expect(
      fetchDenialInsights({
        dimensions: ["insurance"],
        filters: {
          loc: "RTC",
        },
        rule_thresholds: {
          minimum_sample_size: 10,
          minimum_denial_rate: 0.3,
          minimum_relative_increase: 0.5,
        },
      })
    ).resolves.toEqual(responseBody);

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/denial-insights/query",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dimensions: ["insurance"],
          filters: {
            loc: "RTC",
          },
          rule_thresholds: {
            minimum_sample_size: 10,
            minimum_denial_rate: 0.3,
            minimum_relative_increase: 0.5,
          },
        }),
      }
    );
  });

  it("returns the backend detail when the query fails", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Unsupported analytics dimension.",
        }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(
      fetchDenialInsights({
        dimensions: ["insurance"],
      })
    ).rejects.toThrow("Unsupported analytics dimension.");
  });

  it("uses a generic message when an error response is not JSON", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response("Service unavailable", {
        status: 503,
      })
    );

    await expect(
      fetchDenialInsights({
        dimensions: ["insurance"],
      })
    ).rejects.toThrow("Unable to load denial insights.");
  });
});

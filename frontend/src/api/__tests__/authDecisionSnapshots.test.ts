import { beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedFetch } from "../client";
import { fetchAuthDecisionSnapshots } from "../authDecisionSnapshots";

vi.mock("../client", () => ({
  API_BASE_URL: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

const mockedAuthenticatedFetch = vi.mocked(authenticatedFetch);

describe("authorization decision snapshots API", () => {
  beforeEach(() => {
    mockedAuthenticatedFetch.mockReset();
  });

  it("loads decision snapshots for an authorization", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          snapshots: [
            {
              id: 10,
              outcome: "Denied",
            },
          ],
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    const snapshots = await fetchAuthDecisionSnapshots("42");

    expect(snapshots).toEqual([
      {
        id: 10,
        outcome: "Denied",
      },
    ]);

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/auths/42/decision-snapshots"
    );
  });

  it("returns the backend detail when loading fails", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Auth record not found.",
        }),
        {
          status: 404,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchAuthDecisionSnapshots("42")).rejects.toThrow(
      "Auth record not found."
    );
  });
});

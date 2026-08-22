import { beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedFetch } from "../client";
import { recordSessionActivity } from "../security";

vi.mock("../client", () => ({
  API_BASE_URL: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

const mockedAuthenticatedFetch = vi.mocked(authenticatedFetch);

describe("security API", () => {
  beforeEach(() => {
    mockedAuthenticatedFetch.mockReset();
  });

  it("records authenticated session activity", async () => {
    const expiresAt = "2026-08-22T10:30:00+00:00";

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          expires_at: expiresAt,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(recordSessionActivity()).resolves.toEqual({
      expires_at: expiresAt,
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/security/session/activity",
      {
        method: "POST",
      }
    );
  });

  it("rejects when session activity cannot be recorded", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(null, {
        status: 401,
      })
    );

    await expect(recordSessionActivity()).rejects.toThrow(
      "Unable to record session activity."
    );
  });
});

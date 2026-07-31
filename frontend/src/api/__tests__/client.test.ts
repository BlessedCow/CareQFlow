import { afterEach, describe, expect, it, vi } from "vitest";

describe("API base URL", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("uses same-origin API paths when no override is configured", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "");
    vi.stubEnv("VITE_API_BASE_URL", "");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("");
  });

  it("uses the configured API URL for separate development servers", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "http://localhost:8000");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("removes trailing slashes from the configured API URL", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "http://localhost:8000///");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("supports the legacy API URL environment variable", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "");
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8000/");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("http://127.0.0.1:8000");
  });
});

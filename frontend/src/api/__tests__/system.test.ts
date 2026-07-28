import {
  cancelDatabaseRecovery,
  createRestorePoint,
  fetchApiEndpoints,
  fetchApplicationHealth,
  fetchDatabaseReadiness,
  fetchRecoveryStatus,
  fetchRestorePoints,
  stageDatabaseRecovery,
  verifyRestorePoint,
} from "../system";
import { authenticatedFetch } from "../client";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../client", () => ({
  API_BASE_URL: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

const mockedAuthenticatedFetch = vi.mocked(authenticatedFetch);

describe("system API", () => {
  beforeEach(() => {
    mockedAuthenticatedFetch.mockReset();
  });

  it("loads application health", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          app: "AuthStatus API",
          version: "0.1.0",
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchApplicationHealth()).resolves.toEqual({
      status: "ok",
      app: "AuthStatus API",
      version: "0.1.0",
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/health/live"
    );
  });

  it("loads pending database recovery status", async () => {
    const recovery = {
      backup_filename: "auth_tracker_20260728.db.enc",
      staged_filename: "auth_tracker_20260728.restored.db",
      staged_at: "2026-07-28T04:42:11+00:00",
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          pending: true,
          recovery,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchRecoveryStatus()).resolves.toEqual({
      pending: true,
      recovery,
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/system/backups/recovery"
    );
  });

  it("stages a selected database restore point", async () => {
    const filename = "auth_tracker_20260728.db.enc";

    const recovery = {
      backup_filename: filename,
      staged_filename: "auth_tracker_20260728.restored.db",
      staged_at: "2026-07-28T04:42:11+00:00",
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          recovery,
          staged: true,
        }),
        {
          status: 201,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(stageDatabaseRecovery(filename)).resolves.toEqual({
      recovery,
      staged: true,
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/system/backups/recovery/stage",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename,
        }),
      }
    );
  });

  it("cancels a pending database recovery", async () => {
    const recovery = {
      backup_filename: "auth_tracker_20260728.db.enc",
      staged_filename: "auth_tracker_20260728.restored.db",
      staged_at: "2026-07-28T04:42:11+00:00",
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          recovery,
          canceled: true,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(cancelDatabaseRecovery()).resolves.toEqual({
      recovery,
      canceled: true,
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/system/backups/recovery",
      {
        method: "DELETE",
      }
    );
  });

  it("returns the backend detail when recovery staging fails", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "The selected restore point could not be staged.",
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
      stageDatabaseRecovery("auth_tracker_20260728.db.enc")
    ).rejects.toThrow("The selected restore point could not be staged.");
  });

  it("uses a generic error when recovery cancellation fails without JSON", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response("Service unavailable", {
        status: 503,
      })
    );

    await expect(cancelDatabaseRecovery()).rejects.toThrow(
      "Unable to cancel the staged database recovery."
    );
  });

  it("loads registered API endpoint status", async () => {
    const endpoints = [
      {
        path: "/api/health/live",
        methods: ["GET"],
        group: "ungrouped",
        access: "public",
        status: "operational",
        probeable: true,
      },
      {
        path: "/api/admin/system/backups",
        methods: ["POST"],
        group: "admin-system-backups",
        access: "admin",
        status: "registered",
        probeable: false,
      },
    ];

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          endpoints,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchApiEndpoints()).resolves.toEqual(endpoints);

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/system/endpoints"
    );
  });

  it("returns the backend detail when endpoint inventory fails", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Endpoint monitoring is unavailable.",
        }),
        {
          status: 503,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchApiEndpoints()).rejects.toThrow(
      "Endpoint monitoring is unavailable."
    );
  });

  it("returns unavailable when database readiness is 503", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "unavailable",
        }),
        {
          status: 503,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchDatabaseReadiness()).resolves.toEqual({
      status: "unavailable",
    });
  });

  it("loads encrypted restore points", async () => {
    const backup = {
      filename: "auth_tracker_20260728.db.enc",
      size_bytes: 4096,
      created_at: "2026-07-28T03:16:31+00:00",
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          backups: [backup],
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchRestorePoints()).resolves.toEqual([backup]);
  });

  it("creates a verified restore point", async () => {
    const result = {
      backup: {
        filename: "auth_tracker_20260728.db.enc",
        size_bytes: 4096,
        created_at: "2026-07-28T03:16:31+00:00",
      },
      verified: true,
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(JSON.stringify(result), {
        status: 201,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    await expect(createRestorePoint()).resolves.toEqual(result);

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/system/backups",
      {
        method: "POST",
      }
    );
  });

  it("verifies a selected restore point", async () => {
    const filename = "auth_tracker_20260728.db.enc";

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          filename,
          verified: true,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(verifyRestorePoint(filename)).resolves.toEqual({
      filename,
      verified: true,
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/system/backups/verify",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename,
        }),
      }
    );
  });

  it("returns the backend detail when restore-point creation fails", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Unable to create and verify the restore point.",
        }),
        {
          status: 503,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(createRestorePoint()).rejects.toThrow(
      "Unable to create and verify the restore point."
    );
  });

  it("uses a generic error when a failed response is not JSON", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response("Service unavailable", {
        status: 503,
      })
    );

    await expect(fetchRestorePoints()).rejects.toThrow(
      "Unable to load restore points."
    );
  });
});

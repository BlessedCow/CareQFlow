import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  cancelDatabaseRecovery,
  createRestorePoint,
  fetchApiEndpoints,
  fetchApplicationHealth,
  fetchDatabaseReadiness,
  fetchRecoveryStatus,
  fetchRestorePoints,
  fetchSecurityMonitoringSummary,
  fetchSystemInfo,
  stageDatabaseRecovery,
  verifyAuditIntegrity,
  verifyRestorePoint,
} from "../../api/system";
import { AdminSystemPage } from "../AdminSystemPage";

vi.mock("../../api/system", () => ({
  cancelDatabaseRecovery: vi.fn(),
  createRestorePoint: vi.fn(),
  fetchApiEndpoints: vi.fn(),
  fetchApplicationHealth: vi.fn(),
  fetchDatabaseReadiness: vi.fn(),
  fetchRecoveryStatus: vi.fn(),
  fetchRestorePoints: vi.fn(),
  fetchSecurityMonitoringSummary: vi.fn(),
  fetchSystemInfo: vi.fn(),
  stageDatabaseRecovery: vi.fn(),
  verifyAuditIntegrity: vi.fn(),
  verifyRestorePoint: vi.fn(),
}));

const mockedFetchApplicationHealth = vi.mocked(fetchApplicationHealth);
const mockedFetchDatabaseReadiness = vi.mocked(fetchDatabaseReadiness);
const mockedFetchRestorePoints = vi.mocked(fetchRestorePoints);
const mockedFetchSecurityMonitoringSummary = vi.mocked(
  fetchSecurityMonitoringSummary
);
const mockedFetchSystemInfo = vi.mocked(fetchSystemInfo);
const mockedCreateRestorePoint = vi.mocked(createRestorePoint);
const mockedVerifyRestorePoint = vi.mocked(verifyRestorePoint);
const mockedFetchApiEndpoints = vi.mocked(fetchApiEndpoints);
const mockedFetchRecoveryStatus = vi.mocked(fetchRecoveryStatus);
const mockedStageDatabaseRecovery = vi.mocked(stageDatabaseRecovery);
const mockedCancelDatabaseRecovery = vi.mocked(cancelDatabaseRecovery);
const mockedVerifyAuditIntegrity = vi.mocked(verifyAuditIntegrity);

const existingBackup = {
  filename: "auth_tracker_20260728.db.enc",
  size_bytes: 4096,
  created_at: "2026-07-28T03:16:31+00:00",
};

const emptyRetentionResult = {
  retention_days: 90,
  minimum_count: 5,
  deleted: [],
  protected: [],
  failed: [],
};

describe("AdminSystemPage", () => {
  beforeEach(() => {
    mockedFetchApplicationHealth.mockReset();
    mockedFetchDatabaseReadiness.mockReset();
    mockedFetchRestorePoints.mockReset();
    mockedFetchSystemInfo.mockReset();
    mockedCreateRestorePoint.mockReset();
    mockedVerifyRestorePoint.mockReset();
    mockedFetchApiEndpoints.mockReset();
    mockedFetchRecoveryStatus.mockReset();
    mockedFetchSecurityMonitoringSummary.mockReset();
    mockedStageDatabaseRecovery.mockReset();
    mockedCancelDatabaseRecovery.mockReset();
    mockedVerifyAuditIntegrity.mockReset();

    mockedFetchApplicationHealth.mockResolvedValue({
      status: "ok",
    });

    mockedFetchDatabaseReadiness.mockResolvedValue({
      status: "ok",
    });

    mockedFetchRecoveryStatus.mockResolvedValue({
      pending: false,
      recovery: null,
    });

    mockedFetchRestorePoints.mockResolvedValue([existingBackup]);

    mockedFetchSystemInfo.mockResolvedValue({
      app: "AuthStatus API",
      version: "0.2.0",
    });

    mockedFetchApiEndpoints.mockResolvedValue([
      {
        path: "/api/health/live",
        methods: ["GET"],
        group: "ungrouped",
        access: "public",
        status: "operational",
        probeable: true,
      },
      {
        path: "/api/security/setup-initial-admin",
        methods: ["POST"],
        group: "security",
        access: "initial_setup",
        status: "registered",
        probeable: false,
      },
      {
        path: "/api/auths",
        methods: ["POST"],
        group: "authorizations",
        access: "admin_ur",
        status: "registered",
        probeable: false,
      },
      {
        path: "/api/auths",
        methods: ["GET"],
        group: "authorizations",
        access: "authenticated",
        status: "registered",
        probeable: false,
      },
      {
        path: "/api/admin/system/backups",
        methods: ["POST"],
        group: "admin-system-backups",
        access: "admin",
        status: "registered",
        probeable: false,
      },
    ]);
  });

  it("shows a successful audit integrity verification", async () => {
    mockedVerifyAuditIntegrity.mockResolvedValue({
      valid: true,
      status: "valid",
      checked_events: 42,
      legacy_events: 3,
      failed_event_id: null,
      reason: null,
    });
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Verify Integrity",
      })
    );
  
    expect(await screen.findByText("Integrity verified")).toBeInTheDocument();
  
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  
    expect(mockedVerifyAuditIntegrity).toHaveBeenCalledTimes(1);
  });

  it("shows an audit integrity failure", async () => {
    mockedVerifyAuditIntegrity.mockResolvedValue({
      valid: false,
      status: "invalid",
      checked_events: 7,
      legacy_events: 2,
      failed_event_id: 8,
      reason: "Audit event integrity check failed.",
    });
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Verify Integrity",
      })
    );
  
    expect(
      await screen.findByText("Integrity failure detected")
    ).toBeInTheDocument();
  
    expect(
      screen.getByText("Audit event integrity check failed.")
    ).toBeInTheDocument();
  
    expect(screen.getByText(/Failed event ID:/)).toBeInTheDocument();
    expect(screen.getByText(/Failed event ID:/)).toHaveTextContent("8");
  });

  it("shows normal security monitoring activity", async () => {
    mockedFetchSecurityMonitoringSummary.mockResolvedValue({
      window_hours: 24,
      failed_logins: 1,
      locked_logins: 0,
      failed_mfa: 1,
      total_failures: 2,
      distinct_failure_ips: 1,
      distinct_failure_usernames: 1,
      max_failures_single_username: 1,
      max_failures_single_ip: 2,
      severity: "normal",
    });
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Refresh Monitoring",
      })
    );
  
    expect(
      await screen.findByText("Security activity normal")
    ).toBeInTheDocument();
  
    expect(screen.getByText("Last 24 hours")).toBeInTheDocument();
    expect(screen.getByText("Total failures")).toBeInTheDocument();
  });

  it("shows elevated security monitoring activity", async () => {
    mockedFetchSecurityMonitoringSummary.mockResolvedValue({
      window_hours: 24,
      failed_logins: 2,
      locked_logins: 0,
      failed_mfa: 5,
      total_failures: 7,
      distinct_failure_ips: 2,
      distinct_failure_usernames: 5,
      max_failures_single_username: 1,
      max_failures_single_ip: 5,
      severity: "elevated",
    });
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Refresh Monitoring",
      })
    );
  
    expect(
      await screen.findByText("Elevated security activity")
    ).toBeInTheDocument();
  
    expect(
      screen.getByText(/Highest failures from one IP:/)
    ).toHaveTextContent("5");
  });

  it("shows high security monitoring activity", async () => {
    mockedFetchSecurityMonitoringSummary.mockResolvedValue({
      window_hours: 24,
      failed_logins: 5,
      locked_logins: 1,
      failed_mfa: 0,
      total_failures: 6,
      distinct_failure_ips: 1,
      distinct_failure_usernames: 1,
      max_failures_single_username: 5,
      max_failures_single_ip: 5,
      severity: "high",
    });
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Refresh Monitoring",
      })
    );
  
    expect(
      await screen.findByText("High security activity")
    ).toBeInTheDocument();
  
    expect(
      screen.getByText(/Highest failures for one username:/)
    ).toHaveTextContent("5");
  });

  it("shows an error when security monitoring cannot load", async () => {
    mockedFetchSecurityMonitoringSummary.mockRejectedValue(
      new Error("Security monitoring is unavailable.")
    );
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Refresh Monitoring",
      })
    );
  
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Security monitoring is unavailable."
    );
  
    expect(
      screen.queryByText("Security activity normal")
    ).not.toBeInTheDocument();
  });

  it("shows when the protected audit chain is not initialized", async () => {
    mockedVerifyAuditIntegrity.mockResolvedValue({
      valid: true,
      status: "not_initialized",
      checked_events: 0,
      legacy_events: 5,
      failed_event_id: null,
      reason: null,
    });
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Verify Integrity",
      })
    );
  
    expect(
      await screen.findByText("Protected audit chain not initialized")
    ).toBeInTheDocument();
  
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("shows an error when audit integrity verification cannot run", async () => {
    mockedVerifyAuditIntegrity.mockRejectedValue(
      new Error("Unable to verify audit log integrity.")
    );
  
    render(<AdminSystemPage darkMode={false} />);
  
    fireEvent.click(
      await screen.findByRole("button", {
        name: "Verify Integrity",
      })
    );
  
    expect(
      await screen.findByRole("alert")
    ).toHaveTextContent("Unable to verify audit log integrity.");
  
    expect(
      screen.queryByText("Integrity verified")
    ).not.toBeInTheDocument();
  });

  it("shows that no recovery is currently staged", async () => {
    render(<AdminSystemPage darkMode={false} />);

    expect(
      await screen.findByText("No database recovery is currently staged.")
    ).toBeInTheDocument();
  });

  it("requires confirmation before staging recovery", async () => {
    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Stage Recovery",
      })
    );

    expect(
      screen.getByRole("dialog", {
        name: "Stage Database Recovery?",
      })
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "The active database will not be replaced during this operation."
      )
    ).toBeInTheDocument();

    expect(mockedStageDatabaseRecovery).not.toHaveBeenCalled();
  });

  it("stages a selected restore point after confirmation", async () => {
    const recovery = {
      backup_filename: existingBackup.filename,
      staged_filename: "auth_tracker_20260728.restored.db",
      staged_at: "2026-07-28T04:42:11+00:00",
    };

    mockedStageDatabaseRecovery.mockResolvedValue({
      recovery,
      staged: true,
    });

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Stage Recovery",
      })
    );

    const confirmationDialog = screen.getByRole("dialog", {
      name: "Stage Database Recovery?",
    });

    fireEvent.click(
      within(confirmationDialog).getByRole("button", {
        name: "Stage Recovery",
      })
    );

    expect(await screen.findByText("Recovery pending")).toBeInTheDocument();

    expect(mockedStageDatabaseRecovery).toHaveBeenCalledWith(
      existingBackup.filename
    );
  });

  it("loads an existing staged recovery", async () => {
    mockedFetchRecoveryStatus.mockResolvedValue({
      pending: true,
      recovery: {
        backup_filename: existingBackup.filename,
        staged_filename: "auth_tracker_20260728.restored.db",
        staged_at: "2026-07-28T04:42:11+00:00",
      },
    });

    render(<AdminSystemPage darkMode={false} />);

    expect(await screen.findByText("Recovery pending")).toBeInTheDocument();

    expect(
      screen.getByText("auth_tracker_20260728.restored.db")
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Stage Recovery",
      })
    ).toBeDisabled();
  });

  it("cancels a staged recovery", async () => {
    const recovery = {
      backup_filename: existingBackup.filename,
      staged_filename: "auth_tracker_20260728.restored.db",
      staged_at: "2026-07-28T04:42:11+00:00",
    };

    mockedFetchRecoveryStatus.mockResolvedValue({
      pending: true,
      recovery,
    });

    mockedCancelDatabaseRecovery.mockResolvedValue({
      recovery,
      canceled: true,
    });

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText("Recovery pending");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Cancel Staged Recovery",
      })
    );

    expect(
      await screen.findByText(
        `Staged recovery for ${existingBackup.filename} was canceled.`
      )
    ).toBeInTheDocument();

    expect(
      screen.getByText("No database recovery is currently staged.")
    ).toBeInTheDocument();
  });

  it("loads endpoint status when the inventory is opened", async () => {
    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    expect(screen.queryByText("/api/health/live")).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "View API Endpoints",
      })
    );

    expect(await screen.findByText("/api/health/live")).toBeInTheDocument();

    expect(screen.getByText("/api/admin/system/backups")).toBeInTheDocument();

    expect(screen.getByText("Initial setup")).toBeInTheDocument();
    expect(screen.getByText("Admin + UR")).toBeInTheDocument();

    expect(screen.getByText("Admin + UR + Read Only")).toBeInTheDocument();

    expect(mockedFetchApiEndpoints).toHaveBeenCalledTimes(1);
  });

  it("filters API endpoints by search text", async () => {
    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "View API Endpoints",
      })
    );

    await screen.findByText("/api/health/live");

    fireEvent.change(
      screen.getByRole("searchbox", {
        name: "Search API endpoints",
      }),
      {
        target: {
          value: "backups",
        },
      }
    );

    expect(screen.getByText("/api/admin/system/backups")).toBeInTheDocument();

    expect(screen.queryByText("/api/health/live")).not.toBeInTheDocument();
  });

  it("shows endpoint inventory loading errors", async () => {
    mockedFetchApiEndpoints.mockRejectedValue(
      new Error("Endpoint monitoring is unavailable.")
    );

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "View API Endpoints",
      })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Endpoint monitoring is unavailable."
    );
  });

  it("does not reload endpoint inventory when reopened", async () => {
    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "View API Endpoints",
      })
    );

    await screen.findByText("/api/health/live");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Hide API Endpoints",
      })
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "View API Endpoints",
      })
    );

    expect(screen.getByText("/api/health/live")).toBeInTheDocument();

    expect(mockedFetchApiEndpoints).toHaveBeenCalledTimes(1);
  });

  it("shows health status and encrypted restore points", async () => {
    render(<AdminSystemPage darkMode={false} />);

    expect(
      screen.getByText("Loading system information...")
    ).toBeInTheDocument();

    expect(await screen.findByText("Operational")).toBeInTheDocument();

    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText(existingBackup.filename)).toBeInTheDocument();
    expect(screen.getByText("4.0 KB")).toBeInTheDocument();
  });

  it("creates and displays a verified restore point", async () => {
    const newBackup = {
      filename: "auth_tracker_20260729.db.enc",
      size_bytes: 8192,
      created_at: "2026-07-29T03:16:31+00:00",
    };

    mockedCreateRestorePoint.mockResolvedValue({
      backup: newBackup,
      verified: true,
      retention: emptyRetentionResult,
    });

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Create Restore Point",
      })
    );

    expect(
      await screen.findByText(
        `Restore point ${newBackup.filename} was created and verified.`
      )
    ).toBeInTheDocument();

    expect(screen.getByText(newBackup.filename)).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Verified",
      })
    ).toBeDisabled();

    const retentionSection = screen
      .getByRole("heading", {
        name: "Backup Retention",
      })
      .closest("section");

    expect(retentionSection).not.toBeNull();

    expect(retentionSection).toHaveTextContent(
      "Encrypted restore points are retained for 90 days"
    );

    expect(retentionSection).toHaveTextContent(
      "with at least 5 recent restore points preserved"
    );

    expect(mockedCreateRestorePoint).toHaveBeenCalledTimes(1);
  });

  it("marks a successfully verified restore point as verified", async () => {
    mockedVerifyRestorePoint.mockResolvedValue({
      filename: existingBackup.filename,
      verified: true,
    });

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Verify",
      })
    );

    const dialog = await screen.findByRole("dialog", {
      name: "Restore Point Verified",
    });

    expect(dialog).toHaveTextContent(
      `${existingBackup.filename} verified successfully.`
    );

    expect(
      screen.getByRole("button", {
        name: "Verified",
      })
    ).toBeDisabled();

    expect(mockedVerifyRestorePoint).toHaveBeenCalledWith(
      existingBackup.filename
    );
  });

  it("shows a verification failure and keeps the restore point retryable", async () => {
    mockedVerifyRestorePoint.mockRejectedValue(
      new Error("The encrypted backup failed validation.")
    );

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Verify",
      })
    );

    const dialog = await screen.findByRole("dialog", {
      name: "Verification Failed",
    });

    expect(dialog).toHaveTextContent(
      `${existingBackup.filename} could not be verified: ` +
        "The encrypted backup failed validation."
    );

    fireEvent.click(
      within(dialog).getByRole("button", {
        name: "Close",
      })
    );

    expect(
      screen.getByRole("button", {
        name: "Verify",
      })
    ).toBeEnabled();
  });

  it("shows an error when system information cannot load", async () => {
    mockedFetchApplicationHealth.mockRejectedValue(
      new Error("The CareQueue API is unavailable.")
    );

    render(<AdminSystemPage darkMode={false} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The CareQueue API is unavailable."
    );
  });

  it("shows an empty state when no restore points exist", async () => {
    mockedFetchRestorePoints.mockResolvedValue([]);

    render(<AdminSystemPage darkMode={false} />);

    expect(
      await screen.findByText("No encrypted restore points are available.")
    ).toBeInTheDocument();
  });

  it("disables restore point actions while creating", async () => {
    let resolveCreation:
      | ((value: Awaited<ReturnType<typeof createRestorePoint>>) => void)
      | undefined;

    mockedCreateRestorePoint.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreation = resolve;
        })
    );

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Create Restore Point",
      })
    );

    expect(
      screen.getByRole("button", {
        name: "Creating...",
      })
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Verify",
      })
    ).toBeDisabled();

    resolveCreation?.({
      backup: existingBackup,
      verified: true,
      retention: emptyRetentionResult,
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: "Create Restore Point",
        })
      ).toBeEnabled();
    });
  });

  it("shows files pruned and protected by the retention policy", async () => {
    const newBackup = {
      filename: "auth_tracker_20260729.db.enc",
      size_bytes: 8192,
      created_at: "2026-07-29T03:16:31+00:00",
    };

    mockedCreateRestorePoint.mockResolvedValue({
      backup: newBackup,
      verified: true,
      retention: {
        retention_days: 90,
        minimum_count: 5,
        deleted: ["auth_tracker_20260101_120000_000001.db.enc"],
        protected: ["auth_tracker_20260102_120000_000001.db.enc"],
        failed: [],
      },
    });

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Create Restore Point",
      })
    );

    expect(
      await screen.findByText("auth_tracker_20260101_120000_000001.db.enc")
    ).toBeInTheDocument();

    expect(
      screen.getByText("auth_tracker_20260102_120000_000001.db.enc")
    ).toBeInTheDocument();

    expect(screen.getByText("Deleted restore points")).toBeInTheDocument();

    expect(
      screen.getByText("Protected by pending recovery")
    ).toBeInTheDocument();
  });

  it("shows retention cleanup failures without hiding backup success", async () => {
    const newBackup = {
      filename: "auth_tracker_20260729.db.enc",
      size_bytes: 8192,
      created_at: "2026-07-29T03:16:31+00:00",
    };

    mockedCreateRestorePoint.mockResolvedValue({
      backup: newBackup,
      verified: true,
      retention: {
        retention_days: 90,
        minimum_count: 5,
        deleted: [],
        protected: [],
        failed: ["auth_tracker_20260101_120000_000001.db.enc"],
      },
    });

    render(<AdminSystemPage darkMode={false} />);

    await screen.findByText(existingBackup.filename);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Create Restore Point",
      })
    );

    expect(
      await screen.findByText(
        `Restore point ${newBackup.filename} was created and verified.`
      )
    ).toBeInTheDocument();

    expect(
      screen.getByText("Cleanup could not complete for")
    ).toBeInTheDocument();

    expect(
      screen.getByText("auth_tracker_20260101_120000_000001.db.enc")
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Verified",
      })
    ).toBeDisabled();
  });
});

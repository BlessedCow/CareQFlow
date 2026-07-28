import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
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
} from "../../api/system";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminSystemPage } from "../AdminSystemPage";

vi.mock("../../api/system", () => ({
  cancelDatabaseRecovery: vi.fn(),
  createRestorePoint: vi.fn(),
  fetchApiEndpoints: vi.fn(),
  fetchApplicationHealth: vi.fn(),
  fetchDatabaseReadiness: vi.fn(),
  fetchRecoveryStatus: vi.fn(),
  fetchRestorePoints: vi.fn(),
  stageDatabaseRecovery: vi.fn(),
  verifyRestorePoint: vi.fn(),
}));

const mockedFetchApplicationHealth = vi.mocked(fetchApplicationHealth);
const mockedFetchDatabaseReadiness = vi.mocked(fetchDatabaseReadiness);
const mockedFetchRestorePoints = vi.mocked(fetchRestorePoints);
const mockedCreateRestorePoint = vi.mocked(createRestorePoint);
const mockedVerifyRestorePoint = vi.mocked(verifyRestorePoint);
const mockedFetchApiEndpoints = vi.mocked(fetchApiEndpoints);
const mockedFetchRecoveryStatus = vi.mocked(fetchRecoveryStatus);
const mockedStageDatabaseRecovery = vi.mocked(stageDatabaseRecovery);
const mockedCancelDatabaseRecovery = vi.mocked(cancelDatabaseRecovery);

const existingBackup = {
  filename: "auth_tracker_20260728.db.enc",
  size_bytes: 4096,
  created_at: "2026-07-28T03:16:31+00:00",
};

describe("AdminSystemPage", () => {
  beforeEach(() => {
    mockedFetchApplicationHealth.mockReset();
    mockedFetchDatabaseReadiness.mockReset();
    mockedFetchRestorePoints.mockReset();
    mockedCreateRestorePoint.mockReset();
    mockedVerifyRestorePoint.mockReset();
    mockedFetchApiEndpoints.mockReset();
    mockedFetchRecoveryStatus.mockReset();
    mockedStageDatabaseRecovery.mockReset();
    mockedCancelDatabaseRecovery.mockReset();

    mockedFetchApplicationHealth.mockResolvedValue({
      status: "ok",
      app: "AuthStatus API",
      version: "0.1.0",
    });

    mockedFetchDatabaseReadiness.mockResolvedValue({
      status: "ok",
    });

    mockedFetchRecoveryStatus.mockResolvedValue({
      pending: false,
      recovery: null,
    });

    mockedFetchRestorePoints.mockResolvedValue([existingBackup]);

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
        path: "/api/admin/system/backups",
        methods: ["POST"],
        group: "admin-system-backups",
        access: "admin",
        status: "registered",
        probeable: false,
      },
    ]);
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

    expect(mockedCreateRestorePoint).toHaveBeenCalledTimes(1);
  });

  it("verifies a selected restore point", async () => {
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

    expect(
      await screen.findByText(
        `Restore point ${existingBackup.filename} passed verification.`
      )
    ).toBeInTheDocument();

    expect(mockedVerifyRestorePoint).toHaveBeenCalledWith(
      existingBackup.filename
    );
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
      | ((value: { backup: typeof existingBackup; verified: boolean }) => void)
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
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", {
          name: "Create Restore Point",
        })
      ).toBeEnabled();
    });
  });
});

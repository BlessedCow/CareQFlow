import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  createRestorePoint,
  fetchApplicationHealth,
  fetchDatabaseReadiness,
  fetchRestorePoints,
  verifyRestorePoint,
} from "../../api/system";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminSystemPage } from "../AdminSystemPage";

vi.mock("../../api/system", () => ({
  createRestorePoint: vi.fn(),
  fetchApplicationHealth: vi.fn(),
  fetchDatabaseReadiness: vi.fn(),
  fetchRestorePoints: vi.fn(),
  verifyRestorePoint: vi.fn(),
}));

const mockedFetchApplicationHealth = vi.mocked(fetchApplicationHealth);
const mockedFetchDatabaseReadiness = vi.mocked(fetchDatabaseReadiness);
const mockedFetchRestorePoints = vi.mocked(fetchRestorePoints);
const mockedCreateRestorePoint = vi.mocked(createRestorePoint);
const mockedVerifyRestorePoint = vi.mocked(verifyRestorePoint);

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

    mockedFetchApplicationHealth.mockResolvedValue({
      status: "ok",
      app: "AuthStatus API",
      version: "0.1.0",
    });
    mockedFetchDatabaseReadiness.mockResolvedValue({
      status: "ok",
    });
    mockedFetchRestorePoints.mockResolvedValue([existingBackup]);
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

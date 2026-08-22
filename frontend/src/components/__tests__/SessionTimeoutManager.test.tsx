import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState, type ComponentProps } from "react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import { renewCurrentSession } from "../../api/security";
import { SessionTimeoutManager } from "../SessionTimeoutManager";

vi.mock("../../api/security", () => ({
  renewCurrentSession: vi.fn(),
}));

const BASE_TIME = new Date("2026-07-27T12:00:00.000Z");

const mockedRenewCurrentSession = vi.mocked(renewCurrentSession);

type SessionTimeoutManagerProps = ComponentProps<
  typeof SessionTimeoutManager
>;

function expirationAfter(seconds: number): string {
  return new Date(
    BASE_TIME.getTime() + seconds * 1000
  ).toISOString();
}

function renderSessionTimeoutManager(
  overrides: Partial<SessionTimeoutManagerProps> = {}
) {
  const onSessionRenewed = vi.fn();
  const onSessionExpired = vi.fn();
  const onLogout = vi.fn();

  render(
    <SessionTimeoutManager
      darkMode={false}
      expiresAt={expirationAfter(10 * 60)}
      showTimer={true}
      onSessionRenewed={onSessionRenewed}
      onSessionExpired={onSessionExpired}
      onLogout={onLogout}
      {...overrides}
    />
  );

  return {
    onSessionRenewed,
    onSessionExpired,
    onLogout,
  };
}

function StatefulSessionTimeoutManager() {
  const [expiresAt, setExpiresAt] = useState(
    expirationAfter(5 * 60)
  );

  return (
    <SessionTimeoutManager
      darkMode={false}
      expiresAt={expiresAt}
      showTimer={true}
      onSessionRenewed={setExpiresAt}
      onSessionExpired={vi.fn()}
      onLogout={vi.fn()}
    />
  );
}

function ActivityUpdatedSessionTimeoutManager() {
  const [expiresAt, setExpiresAt] = useState(
    expirationAfter(5 * 60)
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setExpiresAt(expirationAfter(20 * 60))}
      >
        Simulate authenticated activity
      </button>

      <SessionTimeoutManager
        darkMode={false}
        expiresAt={expiresAt}
        showTimer={true}
        onSessionRenewed={setExpiresAt}
        onSessionExpired={vi.fn()}
        onLogout={vi.fn()}
      />
    </>
  );
}

describe("SessionTimeoutManager", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(BASE_TIME);
    mockedRenewCurrentSession.mockReset();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("shows the countdown when the timer preference is enabled", () => {
    renderSessionTimeoutManager({
      expiresAt: expirationAfter(10 * 60),
      showTimer: true,
    });

    expect(
      screen.getByText("Session: 10:00")
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("dialog")
    ).not.toBeInTheDocument();
  });

  it("hides the countdown when the timer preference is disabled", () => {
    renderSessionTimeoutManager({
      expiresAt: expirationAfter(10 * 60),
      showTimer: false,
    });

    expect(
      screen.queryByText(/Session:/)
    ).not.toBeInTheDocument();

    expect(
      screen.queryByRole("dialog")
    ).not.toBeInTheDocument();
  });

  it("shows the warning when five minutes remain", () => {
    renderSessionTimeoutManager({
      expiresAt: expirationAfter(5 * 60),
    });

    expect(
      screen.getByRole("dialog", {
        name: "Your session is about to expire",
      })
    ).toBeInTheDocument();

    expect(
      screen.getByText(/You will be signed out in/)
    ).toHaveTextContent("5:00");
  });

  it("shows the mandatory warning when the countdown is hidden", () => {
    renderSessionTimeoutManager({
      expiresAt: expirationAfter(5 * 60),
      showTimer: false,
    });

    expect(
      screen.queryByText(/Session:/)
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("dialog", {
        name: "Your session is about to expire",
      })
    ).toBeInTheDocument();
  });

  it("allows the user to log out immediately from the warning", () => {
    const { onLogout } = renderSessionTimeoutManager({
      expiresAt: expirationAfter(5 * 60),
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Log out now",
      })
    );

    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it("calls the expiration handler when the countdown reaches zero", () => {
    const { onSessionExpired } = renderSessionTimeoutManager({
      expiresAt: expirationAfter(1),
    });

    expect(onSessionExpired).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(onSessionExpired).toHaveBeenCalledTimes(1);
  });

  it("returns the renewed expiration to the parent", async () => {
    const renewedExpiration = expirationAfter(20 * 60);

    mockedRenewCurrentSession.mockResolvedValue({
      expires_at: renewedExpiration,
    });

    const { onSessionRenewed } = renderSessionTimeoutManager({
      expiresAt: expirationAfter(5 * 60),
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue session",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockedRenewCurrentSession).toHaveBeenCalledTimes(1);
    expect(onSessionRenewed).toHaveBeenCalledWith(
      renewedExpiration
    );
  });

  it("shows an error when session renewal fails", async () => {
    mockedRenewCurrentSession.mockRejectedValue(
      new Error("Renewal failed.")
    );

    renderSessionTimeoutManager({
      expiresAt: expirationAfter(5 * 60),
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue session",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(
      screen.getByRole("alert")
    ).toHaveTextContent(
      "The session could not be extended. Save your work and try again."
    );
  });

  it("disables the warning actions while renewal is in progress", async () => {
    let resolveRenewal:
      | ((value: { expires_at: string }) => void)
      | undefined;

    mockedRenewCurrentSession.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRenewal = resolve;
        })
    );

    renderSessionTimeoutManager({
      expiresAt: expirationAfter(5 * 60),
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue session",
      })
    );

    expect(
      screen.getByRole("button", {
        name: "Extending...",
      })
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Log out now",
      })
    ).toBeDisabled();

    await act(async () => {
      resolveRenewal?.({
        expires_at: expirationAfter(20 * 60),
      });
    });
  });

  it("closes the warning after a successful renewal", async () => {
    mockedRenewCurrentSession.mockResolvedValue({
      expires_at: expirationAfter(20 * 60),
    });

    render(<StatefulSessionTimeoutManager />);

    expect(
      screen.getByRole("dialog", {
        name: "Your session is about to expire",
      })
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue session",
      })
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(
      screen.queryByRole("dialog")
    ).not.toBeInTheDocument();

    expect(
      screen.getByText("Session: 20:00")
    ).toBeInTheDocument();
  });

  it("resets the warning when authenticated activity extends the session", () => {
    render(<ActivityUpdatedSessionTimeoutManager />);
  
    expect(
      screen.getByRole("dialog", {
        name: "Your session is about to expire",
      })
    ).toBeInTheDocument();
  
    expect(
      screen.getByText("Session: 5:00")
    ).toBeInTheDocument();
  
    fireEvent.click(
      screen.getByRole("button", {
        name: "Simulate authenticated activity",
      })
    );
  
    expect(
      screen.queryByRole("dialog")
    ).not.toBeInTheDocument();
  
    expect(
      screen.getByText("Session: 20:00")
    ).toBeInTheDocument();
  });
});

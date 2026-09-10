import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "../../../api/security";
import { AppShell } from "../AppShell";

function userWithRole(role: string): CurrentUser {
  return {
    id: 1,
    username: "user@example.com",
    role,
    is_active: true,
    last_login_at: null,
    password_changed_at: "2026-09-01T00:00:00+00:00",
    must_change_password: false,
    mfa_enabled: false,
    walkthrough_status: "completed",
    walkthrough_step: null,
  };
}

function renderShell(role: string) {
  const onPageChange = vi.fn();

  render(
    <AppShell
      activePage="dashboard"
      darkMode={false}
      currentUser={userWithRole(role)}
      canManageUsers={role === "Admin"}
      onPageChange={onPageChange}
      onToggleDarkMode={vi.fn()}
      onLogout={vi.fn()}
    >
      <div>Page content</div>
    </AppShell>
  );

  return {
    onPageChange,
  };
}

describe("AppShell denial insights navigation", () => {
  it("shows Denial Insights to Admin users", () => {
    renderShell("Admin");

    expect(
      screen.getByRole("button", {
        name: /Denial Insights/i,
      })
    ).toBeInTheDocument();
  });

  it("shows Denial Insights to UR users", () => {
    renderShell("UR");

    expect(
      screen.getByRole("button", {
        name: /Denial Insights/i,
      })
    ).toBeInTheDocument();
  });

  it("hides Denial Insights from Read Only users", () => {
    renderShell("Read Only");

    expect(
      screen.queryByRole("button", {
        name: /Denial Insights/i,
      })
    ).not.toBeInTheDocument();
  });

  it("navigates to the Denial Insights page", () => {
    const { onPageChange } = renderShell("UR");

    fireEvent.click(
      screen.getByRole("button", {
        name: /Denial Insights/i,
      })
    );

    expect(onPageChange).toHaveBeenCalledWith("denial-insights");
  });
});

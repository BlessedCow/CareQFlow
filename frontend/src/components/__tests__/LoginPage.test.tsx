import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  isMfaLoginChallenge,
  loginUser,
  verifyMfaLogin,
  type AuthSession,
} from "../../api/security";
import { LoginPage } from "../LoginPage";

vi.mock("../../api/security", () => ({
  isMfaLoginChallenge: vi.fn(),
  loginUser: vi.fn(),
  verifyMfaLogin: vi.fn(),
}));

const mockedIsMfaLoginChallenge = vi.mocked(isMfaLoginChallenge);
const mockedLoginUser = vi.mocked(loginUser);
const mockedVerifyMfaLogin = vi.mocked(verifyMfaLogin);

const authSession: AuthSession = {
  user: {
    id: 1,
    username: "user@example.com",
    role: "UR",
    is_active: true,
    last_login_at: null,
    password_changed_at: "2026-08-12T00:00:00+00:00",
    must_change_password: false,
    mfa_enabled: false,
  },
  session: {
    expires_at: "2026-08-12T01:00:00+00:00",
  },
};

describe("LoginPage", () => {
  beforeEach(() => {
    mockedIsMfaLoginChallenge.mockReset();
    mockedLoginUser.mockReset();
    mockedVerifyMfaLogin.mockReset();
  });

  it("logs in a user when MFA is not required", async () => {
    const onLogin = vi.fn();

    mockedLoginUser.mockResolvedValue(authSession);
    mockedIsMfaLoginChallenge.mockReturnValue(false);

    render(<LoginPage darkMode={false} onLogin={onLogin} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery staple" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign in",
      })
    );

    await waitFor(() => {
      expect(onLogin).toHaveBeenCalledWith(authSession);
    });

    expect(mockedLoginUser).toHaveBeenCalledWith(
      "user@example.com",
      "correct horse battery staple"
    );
    expect(mockedVerifyMfaLogin).not.toHaveBeenCalled();
  });

  it("shows the MFA code step when login requires MFA", async () => {
    const onLogin = vi.fn();

    mockedLoginUser.mockResolvedValue({
      mfa_required: true,
      mfa_challenge_token: "challenge-token",
      expires_at: "2026-08-12T01:00:00+00:00",
    });
    mockedIsMfaLoginChallenge.mockReturnValue(true);

    render(<LoginPage darkMode={false} onLogin={onLogin} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery staple" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign in",
      })
    );

    expect(
      await screen.findByRole("heading", {
        name: "Enter authentication code",
      })
    ).toBeInTheDocument();

    expect(screen.getByLabelText("Authentication code")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Verify code",
      })
    ).toBeInTheDocument();
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("verifies the MFA code and completes login", async () => {
    const onLogin = vi.fn();

    mockedLoginUser.mockResolvedValue({
      mfa_required: true,
      mfa_challenge_token: "challenge-token",
      expires_at: "2026-08-12T01:00:00+00:00",
    });
    mockedIsMfaLoginChallenge.mockReturnValue(true);
    mockedVerifyMfaLogin.mockResolvedValue(authSession);

    render(<LoginPage darkMode={false} onLogin={onLogin} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery staple" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign in",
      })
    );

    await screen.findByLabelText("Authentication code");

    fireEvent.change(screen.getByLabelText("Authentication code"), {
      target: { value: "123456" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Verify code",
      })
    );

    await waitFor(() => {
      expect(mockedVerifyMfaLogin).toHaveBeenCalledWith(
        "challenge-token",
        "123456",
        false
      );
    });

    expect(onLogin).toHaveBeenCalledWith(authSession);
  });

  it("can remember the device after successful MFA verification", async () => {
    const onLogin = vi.fn();
  
    mockedLoginUser.mockResolvedValue({
      mfa_required: true,
      mfa_challenge_token: "challenge-token",
      expires_at: "2026-08-12T01:00:00+00:00",
    });
    mockedIsMfaLoginChallenge.mockReturnValue(true);
    mockedVerifyMfaLogin.mockResolvedValue(authSession);
  
    render(<LoginPage darkMode={false} onLogin={onLogin} />);
  
    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery staple" },
    });
  
    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign in",
      })
    );
  
    await screen.findByLabelText("Authentication code");
  
    fireEvent.change(screen.getByLabelText("Authentication code"), {
      target: { value: "123456" },
    });
  
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Remember this device for 30 days",
      })
    );
  
    fireEvent.click(
      screen.getByRole("button", {
        name: "Verify code",
      })
    );
  
    await waitFor(() => {
      expect(mockedVerifyMfaLogin).toHaveBeenCalledWith(
        "challenge-token",
        "123456",
        true
      );
    });
  
    expect(onLogin).toHaveBeenCalledWith(authSession);
  });

  it("returns to the password step from the MFA step", async () => {
    mockedLoginUser.mockResolvedValue({
      mfa_required: true,
      mfa_challenge_token: "challenge-token",
      expires_at: "2026-08-12T01:00:00+00:00",
    });
    mockedIsMfaLoginChallenge.mockReturnValue(true);

    render(<LoginPage darkMode={false} onLogin={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery staple" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign in",
      })
    );

    await screen.findByLabelText("Authentication code");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Back to password",
      })
    );

    expect(
      screen.getByRole("heading", {
        name: "Sign in",
      })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Authentication code")
    ).not.toBeInTheDocument();
  });

  it("shows an MFA verification error", async () => {
    mockedLoginUser.mockResolvedValue({
      mfa_required: true,
      mfa_challenge_token: "challenge-token",
      expires_at: "2026-08-12T01:00:00+00:00",
    });
    mockedIsMfaLoginChallenge.mockReturnValue(true);
    mockedVerifyMfaLogin.mockRejectedValue(
      new Error("Invalid authentication code.")
    );

    render(<LoginPage darkMode={false} onLogin={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse battery staple" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign in",
      })
    );

    await screen.findByLabelText("Authentication code");

    fireEvent.change(screen.getByLabelText("Authentication code"), {
      target: { value: "000000" },
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Verify code",
      })
    );

    expect(
      await screen.findByText("Invalid authentication code.")
    ).toBeInTheDocument();
  });
});

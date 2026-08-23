import { describe, expect, it } from "vitest";

import type { CurrentUser } from "../../api/security";
import type { GovernanceStatus } from "../../api/governance";
import { resolveGovernanceAccess } from "../resolveGovernanceAccess";

const user: CurrentUser = {
    id: 1,
    username: "admin@example.com",
    role: "Admin",
    is_active: true,
    must_change_password: false,
    mfa_enabled: false,
    last_login_at: "2026-08-23T09:00:00+00:00",
    password_changed_at: "2026-08-23T09:00:00+00:00",
  };

const incompleteGovernance: GovernanceStatus = {
  required_version: 1,
  current: false,
  attestation: null,
};

const currentGovernance: GovernanceStatus = {
  required_version: 1,
  current: true,
  attestation: {
    id: 1,
    attestation_version: 1,
    organization_name: "Example Facility",
    deployment_mode: "self_hosted",
    accepted_by_user_id: 1,
    accepted_by_username: "admin@example.com",
    accepted_at: "2026-08-23T09:00:00+00:00",
    app_version: "0.2.0",
  },
};

describe("resolveGovernanceAccess", () => {
  it("keeps the application loading while session restoration is pending", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: null,
        governanceStatus: null,
        governanceError: null,
        isCheckingSession: true,
      })
    ).toBe("loading");
  });

  it("returns unauthenticated when there is no current user", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: null,
        governanceStatus: null,
        governanceError: null,
        isCheckingSession: false,
      })
    ).toBe("unauthenticated");
  });

  it("gives required password change priority over governance", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: {
          ...user,
          must_change_password: true,
        },
        governanceStatus: incompleteGovernance,
        governanceError: null,
        isCheckingSession: false,
      })
    ).toBe("password_change_required");
  });

  it("reports governance loading after authentication", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: user,
        governanceStatus: null,
        governanceError: null,
        isCheckingSession: false,
      })
    ).toBe("loading");
  });

  it("reports governance status errors before normal access", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: user,
        governanceStatus: null,
        governanceError: "Unable to load governance status.",
        isCheckingSession: false,
      })
    ).toBe("error");
  });

  it("requires attestation when the current version is incomplete", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: user,
        governanceStatus: incompleteGovernance,
        governanceError: null,
        isCheckingSession: false,
      })
    ).toBe("attestation_required");
  });

  it("allows normal application access only when governance is current", () => {
    expect(
      resolveGovernanceAccess({
        currentUser: user,
        governanceStatus: currentGovernance,
        governanceError: null,
        isCheckingSession: false,
      })
    ).toBe("ready");
  });
});

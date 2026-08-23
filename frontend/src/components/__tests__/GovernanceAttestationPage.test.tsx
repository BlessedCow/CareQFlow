import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  acceptGovernanceAttestation,
  type GovernanceAttestation,
} from "../../api/governance";
import { GovernanceAttestationPage } from "../GovernanceAttestationPage";

vi.mock("../../api/governance", () => ({
  acceptGovernanceAttestation: vi.fn(),
}));

const mockedAcceptGovernanceAttestation = vi.mocked(
  acceptGovernanceAttestation
);

const acceptedAttestation: GovernanceAttestation = {
  id: 1,
  attestation_version: 1,
  organization_name: "Example Facility",
  deployment_mode: "self_hosted",
  accepted_by_user_id: 1,
  accepted_by_username: "admin@example.com",
  accepted_at: "2026-08-23T09:00:00+00:00",
  app_version: "0.2.0",
};

function renderPage({
  onAccepted = vi.fn(),
  onLogout = vi.fn().mockResolvedValue(undefined),
}: {
  onAccepted?: (attestation: GovernanceAttestation) => void;
  onLogout?: () => Promise<void>;
} = {}) {
  render(
    <GovernanceAttestationPage
      darkMode={false}
      username="admin@example.com"
      requiredVersion={1}
      canAccept={true}
      onAccepted={onAccepted}
      onLogout={onLogout}
    />
  );

  return {
    onAccepted,
    onLogout,
  };
}

function completeRequiredFields() {
  fireEvent.change(screen.getByLabelText("Organization or facility name"), {
    target: {
      value: "Example Facility",
    },
  });

  const checkboxes = screen.getAllByRole("checkbox");

  for (const checkbox of checkboxes) {
    fireEvent.click(checkbox);
  }
}

describe("GovernanceAttestationPage", () => {
  beforeEach(() => {
    mockedAcceptGovernanceAttestation.mockReset();
  });

  it("shows the required governance version and signed-in administrator", () => {
    renderPage();

    expect(
      screen.getByRole("heading", {
        name: "Governance attestation",
      })
    ).toBeInTheDocument();

    expect(
      screen.getByText("Required attestation version 1")
    ).toBeInTheDocument();

    expect(
      screen.getByText("Signed in as admin@example.com")
    ).toBeInTheDocument();
  });

  it("requires every acknowledgment before setup can be completed", () => {
    renderPage();

    const submitButton = screen.getByRole("button", {
      name: "Accept and complete setup",
    });

    expect(submitButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Organization or facility name"), {
      target: {
        value: "Example Facility",
      },
    });

    const checkboxes = screen.getAllByRole("checkbox");

    for (const checkbox of checkboxes.slice(0, -1)) {
      fireEvent.click(checkbox);
    }

    expect(submitButton).toBeDisabled();

    fireEvent.click(checkboxes.at(-1)!);

    expect(submitButton).toBeEnabled();
  });

  it("submits all required acknowledgments", async () => {
    const onAccepted = vi.fn();

    mockedAcceptGovernanceAttestation.mockResolvedValue(acceptedAttestation);

    renderPage({
      onAccepted,
    });

    completeRequiredFields();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Accept and complete setup",
      })
    );

    await waitFor(() => {
      expect(mockedAcceptGovernanceAttestation).toHaveBeenCalledWith({
        organization_name: "Example Facility",
        deployment_mode: "self_hosted",
        acknowledge_privacy_security_responsibility: true,
        acknowledge_required_agreements: true,
        acknowledge_authorized_access: true,
        acknowledge_device_and_export_safeguards: true,
        acknowledge_test_data_requirements: true,
      });
    });

    expect(onAccepted).toHaveBeenCalledWith(acceptedAttestation);
  });

  it("submits the managed deployment mode when selected", async () => {
    mockedAcceptGovernanceAttestation.mockResolvedValue({
      ...acceptedAttestation,
      deployment_mode: "managed",
    });

    renderPage();

    completeRequiredFields();

    fireEvent.click(
      screen.getByRole("radio", {
        name: /Managed deployment/i,
      })
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Accept and complete setup",
      })
    );

    await waitFor(() => {
      expect(mockedAcceptGovernanceAttestation).toHaveBeenCalledWith(
        expect.objectContaining({
          deployment_mode: "managed",
        })
      );
    });
  });

  it("shows an API error when attestation fails", async () => {
    mockedAcceptGovernanceAttestation.mockRejectedValue(
      new Error("Unable to record governance attestation.")
    );

    renderPage();

    completeRequiredFields();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Accept and complete setup",
      })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to record governance attestation."
    );
  });

  it("allows the administrator to sign out", async () => {
    const onLogout = vi.fn().mockResolvedValue(undefined);

    renderPage({
      onLogout,
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Sign out",
      })
    );

    await waitFor(() => {
      expect(onLogout).toHaveBeenCalledTimes(1);
    });
  });

  it("explains that acceptance does not itself create a BAA", () => {
    renderPage();

    expect(
      screen.getByText(
        /This acknowledgment does not itself create a Business Associate Agreement/i
      )
    ).toBeInTheDocument();
  });

  it("prevents non-admin users from completing governance", () => {
    render(
      <GovernanceAttestationPage
        darkMode={false}
        username="user@example.com"
        requiredVersion={1}
        canAccept={false}
        onAccepted={vi.fn()}
        onLogout={vi.fn().mockResolvedValue(undefined)}
      />
    );

    expect(
      screen.getByText(
        /An administrator must complete the required governance attestation/i
      )
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("button", {
        name: "Accept and complete setup",
      })
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Sign out",
      })
    ).toBeInTheDocument();
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";

import { authenticatedFetch } from "../client";
import {
  acceptGovernanceAttestation,
  fetchGovernanceAttestationHistory,
  fetchGovernanceStatus,
  type GovernanceAcceptancePayload,
} from "../governance";

vi.mock("../client", () => ({
  API_BASE_URL: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

const mockedAuthenticatedFetch = vi.mocked(authenticatedFetch);

describe("governance API", () => {
  beforeEach(() => {
    mockedAuthenticatedFetch.mockReset();
  });

  it("loads incomplete governance status", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          required_version: 1,
          required_document_revision: "governance-attestation-v1",
          current: false,
          attestation: null,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchGovernanceStatus()).resolves.toEqual({
      required_version: 1,
      required_document_revision: "governance-attestation-v1",
      current: false,
      attestation: null,
    });

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/governance/status"
    );
  });

  it("loads completed governance status", async () => {
    const attestation = {
      id: 7,
      attestation_version: 1,
      organization_name: "Example Facility",
      deployment_mode: "self_hosted",
      accepted_by_user_id: 3,
      accepted_by_username: "admin@example.com",
      accepted_at: "2026-08-23T09:00:00+00:00",
      app_version: "0.2.0",
      document_revision: "governance-attestation-v1",
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          required_version: 1,
          required_document_revision: "governance-attestation-v1",
          current: true,
          attestation,
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await expect(fetchGovernanceStatus()).resolves.toEqual({
      required_version: 1,
      required_document_revision: "governance-attestation-v1",
      current: true,
      attestation,
    });
  });

  it("submits every required governance acknowledgment", async () => {
    const payload: GovernanceAcceptancePayload = {
      organization_name: "Example Facility",
      deployment_mode: "self_hosted",
      acknowledge_privacy_security_responsibility: true,
      acknowledge_required_agreements: true,
      acknowledge_authorized_access: true,
      acknowledge_device_and_export_safeguards: true,
      acknowledge_test_data_requirements: true,
    };

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 7,
          attestation_version: 1,
          organization_name: "Example Facility",
          deployment_mode: "self_hosted",
          accepted_by_user_id: 3,
          accepted_by_username: "admin@example.com",
          accepted_at: "2026-08-23T09:00:00+00:00",
          app_version: "0.2.0",
          document_revision: "governance-attestation-v1",
        }),
        {
          status: 201,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    await acceptGovernanceAttestation(payload);

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/governance/attestations",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );
  });

  it("uses the backend error when governance acceptance fails", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail:
            "The current governance attestation has already been accepted.",
        }),
        {
          status: 409,
          headers: {
            "Content-Type": "application/json",
          },
        }
      )
    );

    const payload: GovernanceAcceptancePayload = {
      organization_name: "Example Facility",
      deployment_mode: "self_hosted",
      acknowledge_privacy_security_responsibility: true,
      acknowledge_required_agreements: true,
      acknowledge_authorized_access: true,
      acknowledge_device_and_export_safeguards: true,
      acknowledge_test_data_requirements: true,
    };

    await expect(acceptGovernanceAttestation(payload)).rejects.toThrow(
      "The current governance attestation has already been accepted."
    );
  });

  it("rejects when governance status cannot be loaded", async () => {
    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(null, {
        status: 401,
      })
    );

    await expect(fetchGovernanceStatus()).rejects.toThrow(
      "Unable to load governance status."
    );
  });

  it("loads governance attestation history", async () => {
    const history = [
      {
        id: 2,
        attestation_version: 2,
        organization_name: "Example Facility",
        deployment_mode: "managed",
        accepted_by_user_id: 1,
        accepted_by_username: "admin@example.com",
        accepted_at: "2026-08-23T10:00:00+00:00",
        app_version: "0.3.0",
        document_revision: "governance-attestation-v2",
      },
      {
        id: 1,
        attestation_version: 1,
        organization_name: "Example Facility",
        deployment_mode: "self_hosted",
        accepted_by_user_id: 1,
        accepted_by_username: "admin@example.com",
        accepted_at: "2026-08-23T09:00:00+00:00",
        app_version: "0.2.0",
        document_revision: "governance-attestation-v1",
      },
    ];

    mockedAuthenticatedFetch.mockResolvedValue(
      new Response(JSON.stringify(history), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    await expect(fetchGovernanceAttestationHistory()).resolves.toEqual(history);

    expect(mockedAuthenticatedFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/governance/attestations"
    );
  });
});

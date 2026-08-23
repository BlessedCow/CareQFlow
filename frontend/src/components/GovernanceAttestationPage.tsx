import { Activity, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";

import {
  acceptGovernanceAttestation,
  type GovernanceAcceptancePayload,
  type GovernanceAttestation,
  type GovernanceDeploymentMode,
} from "../api/governance";
import { cn } from "../utils/cn";

interface GovernanceAttestationPageProps {
  darkMode: boolean;
  username: string;
  requiredVersion: number;
  canAccept: boolean;
  onAccepted: (attestation: GovernanceAttestation) => void;
  onLogout: () => Promise<void>;
}

export function GovernanceAttestationPage({
  darkMode,
  username,
  requiredVersion,
  canAccept,
  onAccepted,
  onLogout,
}: GovernanceAttestationPageProps) {
  const [organizationName, setOrganizationName] = useState("");
  const [deploymentMode, setDeploymentMode] =
    useState<GovernanceDeploymentMode>("self_hosted");

  const [
    acknowledgePrivacySecurityResponsibility,
    setAcknowledgePrivacySecurityResponsibility,
  ] = useState(false);
  const [acknowledgeRequiredAgreements, setAcknowledgeRequiredAgreements] =
    useState(false);
  const [acknowledgeAuthorizedAccess, setAcknowledgeAuthorizedAccess] =
    useState(false);
  const [
    acknowledgeDeviceAndExportSafeguards,
    setAcknowledgeDeviceAndExportSafeguards,
  ] = useState(false);
  const [acknowledgeTestDataRequirements, setAcknowledgeTestDataRequirements] =
    useState(false);

  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const allAcknowledged =
    acknowledgePrivacySecurityResponsibility &&
    acknowledgeRequiredAgreements &&
    acknowledgeAuthorizedAccess &&
    acknowledgeDeviceAndExportSafeguards &&
    acknowledgeTestDataRequirements;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmissionError(null);

    const normalizedOrganizationName = organizationName.trim();

    if (!normalizedOrganizationName) {
      setSubmissionError("Organization name is required.");
      return;
    }

    if (!allAcknowledged) {
      setSubmissionError("All governance acknowledgments must be accepted.");
      return;
    }

    const payload: GovernanceAcceptancePayload = {
      organization_name: normalizedOrganizationName,
      deployment_mode: deploymentMode,
      acknowledge_privacy_security_responsibility: true,
      acknowledge_required_agreements: true,
      acknowledge_authorized_access: true,
      acknowledge_device_and_export_safeguards: true,
      acknowledge_test_data_requirements: true,
    };

    setIsSubmitting(true);

    try {
      const attestation = await acceptGovernanceAttestation(payload);
      onAccepted(attestation);
    } catch (error) {
      setSubmissionError(
        error instanceof Error
          ? error.message
          : "Unable to complete governance attestation."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setSubmissionError(null);
    setIsLoggingOut(true);

    try {
      await onLogout();
    } catch {
      setSubmissionError("Unable to sign out.");
      setIsLoggingOut(false);
    }
  };

  const isBusy = isSubmitting || isLoggingOut;

  const checkboxClassName = "mt-0.5 h-4 w-4 shrink-0 rounded border-gray-300";

  return (
    <main
      className={cn(
        "min-h-screen px-4 py-8 font-sans",
        darkMode ? "bg-gray-950 text-gray-100" : "bg-gray-50 text-gray-900"
      )}
    >
      <section
        className={cn(
          "mx-auto w-full max-w-3xl rounded-2xl border p-6 shadow-xl sm:p-8",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div className="mb-8 flex items-center justify-center">
          <Activity className="mr-2 h-7 w-7 text-blue-500" />
          <span className="text-2xl font-bold tracking-wide">CareQueue</span>
        </div>

        <div className="mb-8 text-center">
          <ShieldCheck className="mx-auto mb-3 h-10 w-10 text-blue-500" />

          <h1 className="mb-2 text-2xl font-semibold">
            Governance attestation
          </h1>

          <p
            className={cn(
              "mx-auto max-w-2xl text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            CareQueue may be used to process protected health information. An
            administrator must confirm the organization&apos;s governance
            responsibilities before normal application access is enabled.
          </p>

          <p
            className={cn(
              "mt-3 text-sm font-medium",
              darkMode ? "text-gray-300" : "text-gray-700"
            )}
          >
            Required attestation version {requiredVersion}
          </p>

          <p
            className={cn(
              "mt-1 break-all text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Signed in as {username}
          </p>
        </div>

        {!canAccept && (
          <div
            className={cn(
              "mb-6 rounded-xl border p-5 text-sm",
              darkMode
                ? "border-amber-800 bg-amber-950/30 text-amber-200"
                : "border-amber-200 bg-amber-50 text-amber-900"
            )}
          >
            An administrator must complete the required governance attestation
            before you can access CareQueue.
          </div>
        )}

        {canAccept && (
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="organization-name"
                className="mb-1 block text-sm font-medium"
              >
                Organization or facility name
              </label>

              <input
                id="organization-name"
                type="text"
                value={organizationName}
                onChange={(event) => setOrganizationName(event.target.value)}
                disabled={isBusy}
                required
                maxLength={200}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                  darkMode
                    ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                    : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
                )}
              />
            </div>

            <fieldset>
              <legend className="mb-2 text-sm font-medium">
                Deployment mode
              </legend>

              <div className="space-y-3">
                <label
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-4",
                    darkMode
                      ? "border-gray-700 bg-gray-950"
                      : "border-gray-200 bg-gray-50"
                  )}
                >
                  <input
                    type="radio"
                    name="deployment-mode"
                    value="self_hosted"
                    checked={deploymentMode === "self_hosted"}
                    onChange={() => setDeploymentMode("self_hosted")}
                    disabled={isBusy}
                    className="mt-1"
                  />

                  <span>
                    <span className="block font-medium">Self-hosted</span>
                    <span
                      className={cn(
                        "mt-1 block text-sm",
                        darkMode ? "text-gray-400" : "text-gray-600"
                      )}
                    >
                      The organization operates and administers its own
                      CareQueue deployment.
                    </span>
                  </span>
                </label>

                <label
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-4",
                    darkMode
                      ? "border-gray-700 bg-gray-950"
                      : "border-gray-200 bg-gray-50"
                  )}
                >
                  <input
                    type="radio"
                    name="deployment-mode"
                    value="managed"
                    checked={deploymentMode === "managed"}
                    onChange={() => setDeploymentMode("managed")}
                    disabled={isBusy}
                    className="mt-1"
                  />

                  <span>
                    <span className="block font-medium">
                      Managed deployment
                    </span>
                    <span
                      className={cn(
                        "mt-1 block text-sm",
                        darkMode ? "text-gray-400" : "text-gray-600"
                      )}
                    >
                      CareQueue is operated or administered on behalf of the
                      organization.
                    </span>
                  </span>
                </label>
              </div>
            </fieldset>

            <div
              className={cn(
                "space-y-4 rounded-xl border p-5",
                darkMode
                  ? "border-gray-700 bg-gray-950"
                  : "border-gray-200 bg-gray-50"
              )}
            >
              <p className="font-medium">Required acknowledgments</p>

              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={acknowledgePrivacySecurityResponsibility}
                  onChange={(event) =>
                    setAcknowledgePrivacySecurityResponsibility(
                      event.target.checked
                    )
                  }
                  disabled={isBusy}
                  className={checkboxClassName}
                />

                <span>
                  I confirm that the organization is responsible for maintaining
                  the privacy and security safeguards required for its use of
                  CareQueue and any PHI or ePHI processed through it.
                </span>
              </label>

              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={acknowledgeRequiredAgreements}
                  onChange={(event) =>
                    setAcknowledgeRequiredAgreements(event.target.checked)
                  }
                  disabled={isBusy}
                  className={checkboxClassName}
                />

                <span>
                  I confirm that any required Business Associate Agreement or
                  other agreement applicable to this deployment has been
                  executed separately where required.
                </span>
              </label>

              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={acknowledgeAuthorizedAccess}
                  onChange={(event) =>
                    setAcknowledgeAuthorizedAccess(event.target.checked)
                  }
                  disabled={isBusy}
                  className={checkboxClassName}
                />

                <span>
                  I confirm that CareQueue access will be limited to authorized
                  users with individual accounts and appropriate access levels.
                </span>
              </label>

              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={acknowledgeDeviceAndExportSafeguards}
                  onChange={(event) =>
                    setAcknowledgeDeviceAndExportSafeguards(
                      event.target.checked
                    )
                  }
                  disabled={isBusy}
                  className={checkboxClassName}
                />

                <span>
                  I understand that devices, backups, exports, screenshots,
                  downloads, and printed material containing sensitive
                  information remain subject to the organization&apos;s
                  safeguards.
                </span>
              </label>

              <label className="flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={acknowledgeTestDataRequirements}
                  onChange={(event) =>
                    setAcknowledgeTestDataRequirements(event.target.checked)
                  }
                  disabled={isBusy}
                  className={checkboxClassName}
                />

                <span>
                  I confirm that test and demonstration environments will not
                  use real PHI unless those environments are appropriately
                  protected.
                </span>
              </label>
            </div>

            <p
              className={cn(
                "text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Completing this attestation records the administrator, timestamp,
              application version, deployment mode, and attestation version.
              This acknowledgment does not itself create a Business Associate
              Agreement.
            </p>

            {submissionError && (
              <p
                role="alert"
                className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500"
              >
                {submissionError}
              </p>
            )}

            <button
              type="submit"
              disabled={isBusy || !allAcknowledged}
              className="w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting
                ? "Completing setup..."
                : "Accept and complete setup"}
            </button>

            <button
              type="button"
              onClick={() => void handleLogout()}
              disabled={isBusy}
              className={cn(
                "w-full rounded-lg border px-4 py-2 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                darkMode
                  ? "border-gray-700 text-gray-300 hover:bg-gray-800"
                  : "border-gray-300 text-gray-700 hover:bg-gray-100"
              )}
            >
              {isLoggingOut ? "Signing out..." : "Sign out"}
            </button>
          </form>
        )}
        {!canAccept && (
          <button
            type="button"
            onClick={() => void handleLogout()}
            disabled={isLoggingOut}
            className={cn(
              "w-full rounded-lg border px-4 py-2 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 text-gray-300 hover:bg-gray-800"
                : "border-gray-300 text-gray-700 hover:bg-gray-100"
            )}
          >
            {isLoggingOut ? "Signing out..." : "Sign out"}
          </button>
        )}
      </section>
    </main>
  );
}

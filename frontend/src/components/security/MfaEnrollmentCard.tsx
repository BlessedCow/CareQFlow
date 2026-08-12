import { ShieldCheck } from "lucide-react";
import QRCode from "qrcode";
import { useEffect, useState, type FormEvent } from "react";

import {
  confirmMfaEnrollment,
  fetchMfaStatus,
  startMfaEnrollment,
} from "../../api/security";
import { cn } from "../../utils/cn";

interface MfaEnrollmentCardProps {
  darkMode: boolean;
  mfaEnabled: boolean;
  onMfaEnabledChange: (enabled: boolean) => void;
}

export function MfaEnrollmentCard({
  darkMode,
  mfaEnabled,
  onMfaEnabledChange,
}: MfaEnrollmentCardProps) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [confirmationCode, setConfirmationCode] = useState("");
  const [manualSecret, setManualSecret] = useState<string | null>(null);
  const [provisioningUri, setProvisioningUri] = useState<string | null>(null);
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState<string | null>(null);
  const [enrollmentPending, setEnrollmentPending] = useState(false);
  const [hasCopiedSecret, setHasCopiedSecret] = useState(false);
  const [hasCopiedUri, setHasCopiedUri] = useState(false);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isStartingEnrollment, setIsStartingEnrollment] = useState(false);
  const [isConfirmingEnrollment, setIsConfirmingEnrollment] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadMfaStatus() {
      setIsLoadingStatus(true);
      setError(null);

      try {
        const status = await fetchMfaStatus();

        if (isMounted) {
          onMfaEnabledChange(status.enabled);
          setEnrollmentPending(status.enrollment_pending);
        }
      } catch (caughtError) {
        if (isMounted) {
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to load MFA status."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingStatus(false);
        }
      }
    }

    void loadMfaStatus();

    return () => {
      isMounted = false;
    };
  }, [onMfaEnabledChange]);

  useEffect(() => {
    let isMounted = true;

    async function generateQrCode() {
      if (!provisioningUri) {
        setQrCodeDataUrl(null);
        return;
      }

      try {
        const dataUrl = await QRCode.toDataURL(provisioningUri, {
          margin: 2,
          scale: 6,
          errorCorrectionLevel: "M",
        });

        if (isMounted) {
          setQrCodeDataUrl(dataUrl);
        }
      } catch {
        if (isMounted) {
          setQrCodeDataUrl(null);
          setError(
            "Unable to generate the QR code. Use the manual secret instead."
          );
        }
      }
    }

    void generateQrCode();

    return () => {
      isMounted = false;
    };
  }, [provisioningUri]);

  const handleStartEnrollment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setHasCopiedSecret(false);
    setHasCopiedUri(false);
    setIsStartingEnrollment(true);

    try {
      const enrollment = await startMfaEnrollment(currentPassword);

      setManualSecret(enrollment.secret);
      setProvisioningUri(enrollment.provisioning_uri);
      setEnrollmentPending(true);
      setCurrentPassword("");
      setConfirmationCode("");
      setMessage(
        "MFA setup started. Add the manual secret to your authenticator app, then enter the current 6-digit code."
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to start MFA enrollment."
      );
    } finally {
      setIsStartingEnrollment(false);
    }
  };

  const handleConfirmEnrollment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsConfirmingEnrollment(true);

    try {
      const result = await confirmMfaEnrollment(confirmationCode);

      onMfaEnabledChange(result.enabled);
      setEnrollmentPending(false);
      setManualSecret(null);
      setProvisioningUri(null);
      setQrCodeDataUrl(null);
      setConfirmationCode("");
      setMessage(null);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to confirm MFA enrollment."
      );
    } finally {
      setIsConfirmingEnrollment(false);
    }
  };

  const handleCopySecret = async () => {
    if (!manualSecret) {
      return;
    }

    try {
      await navigator.clipboard.writeText(manualSecret);
      setHasCopiedSecret(true);
    } catch {
      setError(
        "Unable to copy the manual secret. Select and copy it manually."
      );
    }
  };

  const handleCopyUri = async () => {
    if (!provisioningUri) {
      return;
    }

    try {
      await navigator.clipboard.writeText(provisioningUri);
      setHasCopiedUri(true);
    } catch {
      setError("Unable to copy the setup URI. Select and copy it manually.");
    }
  };

  return (
    <section
      className={cn(
        "rounded-xl border p-5 shadow-sm",
        darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
      )}
    >
      <div className="mb-4 flex items-start gap-3">
        <div
          className={cn(
            "rounded-lg p-2",
            mfaEnabled
              ? darkMode
                ? "bg-green-950/50 text-green-400"
                : "bg-green-50 text-green-600"
              : darkMode
              ? "bg-blue-950/50 text-blue-400"
              : "bg-blue-50 text-blue-600"
          )}
        >
          <ShieldCheck className="h-5 w-5" />
        </div>

        <div>
          <h3 className="text-lg font-semibold">Multi-factor authentication</h3>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Add an authenticator app code requirement when signing in.
          </p>
        </div>
      </div>

      <div
        className={cn(
          "mb-4 rounded-lg border px-3 py-2 text-sm",
          mfaEnabled
            ? darkMode
              ? "border-green-900/70 bg-green-950/30 text-green-200"
              : "border-green-200 bg-green-50 text-green-700"
            : darkMode
            ? "border-gray-800 bg-gray-950 text-gray-300"
            : "border-gray-200 bg-gray-50 text-gray-700"
        )}
      >
        {isLoadingStatus
          ? "Checking MFA status..."
          : mfaEnabled
          ? "MFA is enabled for your account."
          : enrollmentPending
          ? "MFA enrollment is pending confirmation."
          : "MFA is not enabled for your account."}
      </div>

      {message && (
        <p
          className={cn(
            "mb-4 rounded-lg border px-3 py-2 text-sm",
            darkMode
              ? "border-blue-900/70 bg-blue-950/30 text-blue-200"
              : "border-blue-200 bg-blue-50 text-blue-700"
          )}
        >
          {message}
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500"
        >
          {error}
        </p>
      )}

      {!mfaEnabled && !manualSecret && (
        <form className="space-y-4" onSubmit={handleStartEnrollment}>
          <div>
            <label
              htmlFor="mfa-current-password"
              className="mb-1 block text-sm font-medium"
            >
              Current password
            </label>

            <input
              id="mfa-current-password"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              disabled={isStartingEnrollment}
              required
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            />
          </div>

          <button
            type="submit"
            disabled={isStartingEnrollment}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isStartingEnrollment ? "Starting setup..." : "Enable MFA"}
          </button>
        </form>
      )}

      {!mfaEnabled && manualSecret && provisioningUri && (
        <div className="space-y-5">
          <div
            className={cn(
              "rounded-xl border p-4",
              darkMode
                ? "border-gray-800 bg-gray-950/60"
                : "border-gray-200 bg-gray-50"
            )}
          >
            <h4 className="text-sm font-semibold">
              Add CareQueue to your authenticator app
            </h4>

            <div
              className={cn(
                "mt-4 rounded-xl border p-4 text-center",
                darkMode
                  ? "border-gray-800 bg-gray-900"
                  : "border-gray-200 bg-white"
              )}
            >
              <p className="text-sm font-semibold">Scan QR code</p>

              <p
                className={cn(
                  "mt-1 text-xs",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Open your authenticator app and scan this code to add CareQueue.
              </p>

              <div className="mt-4 flex justify-center">
                {qrCodeDataUrl ? (
                  <img
                    src={qrCodeDataUrl}
                    alt="CareQueue MFA setup QR code"
                    className="h-48 w-48 rounded-lg bg-white p-2"
                  />
                ) : (
                  <div
                    className={cn(
                      "flex h-48 w-48 items-center justify-center rounded-lg border text-sm",
                      darkMode
                        ? "border-gray-800 bg-gray-950 text-gray-400"
                        : "border-gray-200 bg-gray-50 text-gray-500"
                    )}
                  >
                    Generating QR code...
                  </div>
                )}
              </div>
            </div>

            <ol
              className={cn(
                "mt-3 list-decimal space-y-2 pl-5 text-sm",
                darkMode ? "text-gray-300" : "text-gray-700"
              )}
            >
              <li>Choose the option to scan a QR code.</li>
              <li>Scan the CareQueue QR code below.</li>
              <li>If scanning does not work, use the manual secret instead.</li>
              <li>Submit the current 6-digit code to finish setup.</li>
            </ol>

            <div className="mt-4 space-y-3">
              <div>
                <label
                  htmlFor="mfa-manual-secret"
                  className="mb-1 block text-sm font-medium"
                >
                  Manual secret
                </label>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    id="mfa-manual-secret"
                    type="text"
                    readOnly
                    value={manualSecret}
                    className={cn(
                      "min-w-0 flex-1 rounded-lg border px-3 py-2 font-mono text-xs",
                      darkMode
                        ? "border-gray-700 bg-gray-950 text-gray-100"
                        : "border-gray-300 bg-white text-gray-900"
                    )}
                    onFocus={(event) => event.currentTarget.select()}
                  />

                  <button
                    type="button"
                    onClick={() => void handleCopySecret()}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-sm font-medium",
                      darkMode
                        ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                        : "border-gray-300 text-gray-700 hover:bg-gray-100"
                    )}
                  >
                    {hasCopiedSecret ? "Copied" : "Copy secret"}
                  </button>
                </div>
              </div>

              <div>
                <label
                  htmlFor="mfa-provisioning-uri"
                  className="mb-1 block text-sm font-medium"
                >
                  Setup URI
                </label>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    id="mfa-provisioning-uri"
                    type="text"
                    readOnly
                    value={provisioningUri}
                    className={cn(
                      "min-w-0 flex-1 rounded-lg border px-3 py-2 font-mono text-xs",
                      darkMode
                        ? "border-gray-700 bg-gray-950 text-gray-100"
                        : "border-gray-300 bg-white text-gray-900"
                    )}
                    onFocus={(event) => event.currentTarget.select()}
                  />

                  <button
                    type="button"
                    onClick={() => void handleCopyUri()}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-sm font-medium",
                      darkMode
                        ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                        : "border-gray-300 text-gray-700 hover:bg-gray-100"
                    )}
                  >
                    {hasCopiedUri ? "Copied" : "Copy URI"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleConfirmEnrollment}>
            <div>
              <label
                htmlFor="mfa-confirmation-code"
                className="mb-1 block text-sm font-medium"
              >
                Authentication code
              </label>

              <input
                id="mfa-confirmation-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={confirmationCode}
                onChange={(event) =>
                  setConfirmationCode(event.target.value.trim())
                }
                disabled={isConfirmingEnrollment}
                required
                maxLength={6}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60",
                  darkMode
                    ? "border-gray-700 bg-gray-950 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </div>

            <button
              type="submit"
              disabled={isConfirmingEnrollment}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isConfirmingEnrollment ? "Confirming..." : "Confirm MFA"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}

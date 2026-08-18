import { MonitorSmartphone } from "lucide-react";
import { useState } from "react";

import { revokeTrustedDevices } from "../../api/security";
import { cn } from "../../utils/cn";

interface TrustedDevicesCardProps {
  darkMode: boolean;
}

export function TrustedDevicesCard({ darkMode }: TrustedDevicesCardProps) {
  const [isRevoking, setIsRevoking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRevoke = async () => {
    setIsRevoking(true);
    setMessage(null);
    setError(null);

    try {
      const result = await revokeTrustedDevices();

      setMessage(
        result.trusted_devices_revoked === 1
          ? "1 remembered device was revoked."
          : `${result.trusted_devices_revoked} remembered devices were revoked.`
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to revoke remembered devices."
      );
    } finally {
      setIsRevoking(false);
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
            darkMode
              ? "bg-blue-950/50 text-blue-400"
              : "bg-blue-50 text-blue-600"
          )}
        >
          <MonitorSmartphone className="h-5 w-5" />
        </div>

        <div>
          <h3 className="text-lg font-semibold">Remembered Devices</h3>

          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Devices remembered during MFA can skip the authentication code for
            30 days after your password is verified.
          </p>
        </div>
      </div>

      <p
        className={cn(
          "mb-4 text-sm",
          darkMode ? "text-gray-300" : "text-gray-700"
        )}
      >
        Revoke all remembered devices if you no longer recognize or trust a
        device. Your current CareQueue session will remain signed in.
      </p>

      {message && (
        <p
          className={cn(
            "mb-4 rounded-lg border px-3 py-2 text-sm",
            darkMode
              ? "border-green-900/70 bg-green-950/30 text-green-200"
              : "border-green-200 bg-green-50 text-green-700"
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

      <button
        type="button"
        onClick={() => void handleRevoke()}
        disabled={isRevoking}
        className={cn(
          "rounded-lg border px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60",
          darkMode
            ? "border-red-900 text-red-300 hover:bg-red-950/40"
            : "border-red-300 text-red-700 hover:bg-red-50"
        )}
      >
        {isRevoking ? "Revoking..." : "Revoke remembered devices"}
      </button>
    </section>
  );
}

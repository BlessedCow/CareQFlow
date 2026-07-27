import { useEffect, useMemo, useRef, useState } from "react";

import { renewCurrentSession } from "../api/security";

interface SessionTimeoutManagerProps {
  darkMode: boolean;
  expiresAt: string;
  showTimer: boolean;
  onSessionRenewed: (expiresAt: string) => void;
  onSessionExpired: () => void;
  onLogout: () => void;
}

const WARNING_THRESHOLD_SECONDS = 5 * 60;

function calculateRemainingSeconds(expiresAt: string): number {
  const expirationTimestamp = Date.parse(expiresAt);

  if (Number.isNaN(expirationTimestamp)) {
    return 0;
  }

  return Math.max(
    0,
    Math.ceil((expirationTimestamp - Date.now()) / 1000)
  );
}

function formatRemainingTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function SessionTimeoutManager({
  darkMode,
  expiresAt,
  showTimer,
  onSessionRenewed,
  onSessionExpired,
  onLogout,
}: SessionTimeoutManagerProps) {
  const [remainingSeconds, setRemainingSeconds] = useState(() =>
    calculateRemainingSeconds(expiresAt)
  );
  const [isRenewing, setIsRenewing] = useState(false);
  const [renewalError, setRenewalError] = useState<string | null>(null);
  const expirationHandledRef = useRef(false);

  useEffect(() => {
    expirationHandledRef.current = false;
    setRemainingSeconds(calculateRemainingSeconds(expiresAt));
    setRenewalError(null);

    const intervalId = window.setInterval(() => {
      setRemainingSeconds(calculateRemainingSeconds(expiresAt));
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [expiresAt]);

  useEffect(() => {
    if (
      remainingSeconds > 0 ||
      expirationHandledRef.current
    ) {
      return;
    }

    expirationHandledRef.current = true;
    onSessionExpired();
  }, [remainingSeconds, onSessionExpired]);

  const formattedRemainingTime = useMemo(
    () => formatRemainingTime(remainingSeconds),
    [remainingSeconds]
  );

  const warningVisible =
    remainingSeconds > 0 &&
    remainingSeconds <= WARNING_THRESHOLD_SECONDS;

  const handleRenewSession = async () => {
    setIsRenewing(true);
    setRenewalError(null);

    try {
      const renewedSession = await renewCurrentSession();
      onSessionRenewed(renewedSession.expires_at);
    } catch {
      setRenewalError(
        "The session could not be extended. Save your work and try again."
      );
    } finally {
      setIsRenewing(false);
    }
  };

  return (
    <>
      {showTimer && remainingSeconds > 0 && (
        <div
          className={[
            "fixed bottom-4 right-4 z-40 rounded-lg border px-3 py-2",
            "text-sm font-medium shadow-lg",
            warningVisible
              ? darkMode
                ? "border-amber-700 bg-amber-950 text-amber-200"
                : "border-amber-300 bg-amber-50 text-amber-900"
              : darkMode
                ? "border-gray-700 bg-gray-900 text-gray-200"
                : "border-gray-200 bg-white text-gray-700",
          ].join(" ")}
          aria-live="polite"
        >
          Session: {formattedRemainingTime}
        </div>
      )}

      {warningVisible && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="session-warning-title"
          aria-describedby="session-warning-description"
        >
          <div
            className={[
              "w-full max-w-md rounded-2xl border p-6 shadow-xl",
              darkMode
                ? "border-gray-700 bg-gray-900 text-gray-100"
                : "border-gray-200 bg-white text-gray-900",
            ].join(" ")}
          >
            <h2
              id="session-warning-title"
              className="text-xl font-semibold"
            >
              Your session is about to expire
            </h2>

            <p
              id="session-warning-description"
              className={[
                "mt-2 text-sm",
                darkMode ? "text-gray-300" : "text-gray-600",
              ].join(" ")}
            >
              You will be signed out in{" "}
              <strong>{formattedRemainingTime}</strong>. Extend your session
              to continue working.
            </p>

            {renewalError && (
              <p
                className={[
                  "mt-4 rounded-lg border px-3 py-2 text-sm",
                  darkMode
                    ? "border-red-900 bg-red-950/50 text-red-200"
                    : "border-red-300 bg-red-50 text-red-800",
                ].join(" ")}
                role="alert"
              >
                {renewalError}
              </p>
            )}

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={onLogout}
                disabled={isRenewing}
                className={[
                  "rounded-lg border px-4 py-2 text-sm font-medium",
                  darkMode
                    ? "border-gray-600 text-gray-200 hover:bg-gray-800"
                    : "border-gray-300 text-gray-700 hover:bg-gray-50",
                  isRenewing ? "cursor-not-allowed opacity-60" : "",
                ].join(" ")}
              >
                Log out now
              </button>

              <button
                type="button"
                onClick={() => void handleRenewSession()}
                disabled={isRenewing}
                className={[
                  "rounded-lg px-4 py-2 text-sm font-medium text-white",
                  isRenewing
                    ? "cursor-not-allowed bg-blue-400"
                    : "bg-blue-600 hover:bg-blue-700",
                ].join(" ")}
              >
                {isRenewing ? "Extending..." : "Continue session"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
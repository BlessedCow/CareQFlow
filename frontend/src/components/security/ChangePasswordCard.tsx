import { KeyRound } from "lucide-react";
import { useState, type FormEvent } from "react";

import { changePassword } from "../../api/security";
import { cn } from "../../utils/cn";

interface ChangePasswordCardProps {
  darkMode: boolean;
  onPasswordChanged: () => void;
}

export function ChangePasswordCard({
  darkMode,
  onPasswordChanged,
}: ChangePasswordCardProps) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmedPassword, setConfirmedPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (newPassword !== confirmedPassword) {
      setError("New passwords do not match.");
      return;
    }

    if (currentPassword === newPassword) {
      setError("New password must be different from the current password.");
      return;
    }

    setIsSubmitting(true);

    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmedPassword("");
      onPasswordChanged();
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to change password."
      );
    } finally {
      setIsSubmitting(false);
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
          <KeyRound className="h-5 w-5" />
        </div>

        <div>
          <h3 className="text-lg font-semibold">Change Password</h3>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Changing your password signs you out of all active CareQFlow
            sessions.
          </p>
        </div>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label
            htmlFor="settings-current-password"
            className="mb-1 block text-sm font-medium"
          >
            Current password
          </label>

          <input
            id="settings-current-password"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            disabled={isSubmitting}
            required
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100"
                : "border-gray-300 bg-white text-gray-900"
            )}
          />
        </div>

        <div>
          <label
            htmlFor="settings-new-password"
            className="mb-1 block text-sm font-medium"
          >
            New password
          </label>

          <input
            id="settings-new-password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            disabled={isSubmitting}
            required
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100"
                : "border-gray-300 bg-white text-gray-900"
            )}
          />
        </div>

        <div>
          <label
            htmlFor="settings-confirm-password"
            className="mb-1 block text-sm font-medium"
          >
            Confirm new password
          </label>

          <input
            id="settings-confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirmedPassword}
            onChange={(event) => setConfirmedPassword(event.target.value)}
            disabled={isSubmitting}
            required
            className={cn(
              "w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-950 text-gray-100"
                : "border-gray-300 bg-white text-gray-900"
            )}
          />
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Changing password..." : "Change password"}
        </button>
      </form>
    </section>
  );
}

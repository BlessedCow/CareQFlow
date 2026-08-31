import { Activity, KeyRound } from "lucide-react";
import { useState, type FormEvent } from "react";

import { changePassword } from "../api/security";
import { cn } from "../utils/cn";

interface RequiredPasswordChangePageProps {
  darkMode: boolean;
  username: string;
  onPasswordChanged: () => void;
  onLogout: () => Promise<void>;
}

export function RequiredPasswordChangePage({
  darkMode,
  username,
  onPasswordChanged,
  onLogout,
}: RequiredPasswordChangePageProps) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmedPassword, setConfirmedPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordError(null);

    if (newPassword !== confirmedPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    if (currentPassword === newPassword) {
      setPasswordError(
        "New password must be different from the temporary password."
      );
      return;
    }

    setIsChangingPassword(true);

    try {
      await changePassword(currentPassword, newPassword);
      onPasswordChanged();
    } catch (error) {
      setPasswordError(
        error instanceof Error ? error.message : "Unable to change password."
      );
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleLogout = async () => {
    setPasswordError(null);
    setIsLoggingOut(true);

    try {
      await onLogout();
    } catch {
      setPasswordError("Unable to sign out.");
      setIsLoggingOut(false);
    }
  };

  const isSubmitting = isChangingPassword || isLoggingOut;

  return (
    <main
      className={cn(
        "flex min-h-screen items-center justify-center px-4 py-8 font-sans",
        darkMode ? "bg-gray-950 text-gray-100" : "bg-gray-50 text-gray-900"
      )}
    >
      <section
        className={cn(
          "w-full max-w-md rounded-2xl border p-8 shadow-xl",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div className="mb-8 flex items-center justify-center">
          <div className="flex items-center">
            <Activity className="mr-2 h-7 w-7 text-blue-500" />
            <span className="text-2xl font-bold tracking-wide">CareQFlow</span>
          </div>
        </div>

        <div className="mb-6 text-center">
          <KeyRound className="mx-auto mb-3 h-10 w-10 text-blue-500" />

          <h1 className="mb-2 text-xl font-semibold">
            Change your temporary password
          </h1>

          <p
            className={cn(
              "text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Your password must be changed before you can access CareQFlow.
          </p>

          <p
            className={cn(
              "mt-2 break-all text-sm font-medium",
              darkMode ? "text-gray-300" : "text-gray-700"
            )}
          >
            {username}
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label
              className="mb-1 block text-sm font-medium"
              htmlFor="current-password"
            >
              Temporary password
            </label>

            <input
              id="current-password"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className={cn(
                "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                  : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
              )}
              disabled={isSubmitting}
              required
            />
          </div>

          <div>
            <label
              className="mb-1 block text-sm font-medium"
              htmlFor="new-password"
            >
              New password
            </label>

            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className={cn(
                "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                  : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
              )}
              disabled={isSubmitting}
              required
            />
          </div>

          <div>
            <label
              className="mb-1 block text-sm font-medium"
              htmlFor="confirm-new-password"
            >
              Confirm new password
            </label>

            <input
              id="confirm-new-password"
              type="password"
              autoComplete="new-password"
              value={confirmedPassword}
              onChange={(event) => setConfirmedPassword(event.target.value)}
              className={cn(
                "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                  : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
              )}
              disabled={isSubmitting}
              required
            />
          </div>

          {passwordError && (
            <p
              role="alert"
              className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500"
            >
              {passwordError}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isChangingPassword ? "Changing password..." : "Change password"}
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void handleLogout()}
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
      </section>
    </main>
  );
}

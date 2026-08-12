import { Activity } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { AuthSession } from "../api/security";
import {
  isMfaLoginChallenge,
  loginUser,
  verifyMfaLogin,
} from "../api/security";
import { cn } from "../utils/cn";

interface LoginPageProps {
  darkMode: boolean;
  onLogin: (authSession: AuthSession) => void;
}

export function LoginPage({ darkMode, onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaChallengeToken, setMfaChallengeToken] = useState<string | null>(
    null
  );
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);

    try {
      if (mfaChallengeToken) {
        const authSession = await verifyMfaLogin(mfaChallengeToken, mfaCode);
        onLogin(authSession);
        return;
      }

      const result = await loginUser(username, password);

      if (isMfaLoginChallenge(result)) {
        setMfaChallengeToken(result.mfa_challenge_token);
        setPassword("");
        setMfaCode("");
        return;
      }

      onLogin(result);
    } catch (error) {
      setLoginError(
        error instanceof Error ? error.message : "Unable to sign in."
      );
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleBackToPassword = () => {
    setMfaChallengeToken(null);
    setMfaCode("");
    setLoginError(null);
  };

  return (
    <main
      className={cn(
        "flex min-h-screen items-center justify-center px-4 font-sans",
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
            <span className="text-2xl font-bold tracking-wide">CareQueue</span>
          </div>
        </div>

        <h1 className="mb-2 text-center text-xl font-semibold">
          {mfaChallengeToken ? "Enter authentication code" : "Sign in"}
        </h1>
        <p
          className={cn(
            "mb-6 text-center text-sm",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          {mfaChallengeToken
            ? "Enter the 6-digit code from your authenticator app."
            : "Use your CareQueue account to continue."}
        </p>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {!mfaChallengeToken && (
            <>
              <div>
                <label
                  className="mb-1 block text-sm font-medium"
                  htmlFor="username"
                >
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                    darkMode
                      ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                      : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
                  )}
                  required
                />
              </div>

              <div>
                <label
                  className="mb-1 block text-sm font-medium"
                  htmlFor="password"
                >
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                    darkMode
                      ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                      : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
                  )}
                  required
                />
              </div>
            </>
          )}

          {mfaChallengeToken && (
            <div>
              <label
                className="mb-1 block text-sm font-medium"
                htmlFor="mfa-code"
              >
                Authentication code
              </label>
              <input
                id="mfa-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(event) => setMfaCode(event.target.value)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 outline-none transition-colors",
                  darkMode
                    ? "border-gray-700 bg-gray-950 text-gray-100 focus:border-blue-500"
                    : "border-gray-300 bg-white text-gray-900 focus:border-blue-500"
                )}
                required
                maxLength={6}
              />
            </div>
          )}

          {loginError && (
            <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-500">
              {loginError}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoggingIn}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoggingIn
              ? mfaChallengeToken
                ? "Verifying..."
                : "Signing in..."
              : mfaChallengeToken
              ? "Verify code"
              : "Sign in"}
          </button>

          {mfaChallengeToken && (
            <button
              type="button"
              onClick={handleBackToPassword}
              disabled={isLoggingIn}
              className={cn(
                "w-full rounded-lg border px-4 py-2 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                darkMode
                  ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                  : "border-gray-300 text-gray-700 hover:bg-gray-100"
              )}
            >
              Back to password
            </button>
          )}
        </form>
      </section>
    </main>
  );
}

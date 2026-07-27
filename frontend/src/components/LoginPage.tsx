import { Activity } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { AuthSession } from "../api/security";
import { loginUser } from "../api/security";
import { cn } from "../utils/cn";

interface LoginPageProps {
  darkMode: boolean;
  onLogin: (authSession: AuthSession) => void;
}

export function LoginPage({ darkMode, onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);

    try {
      const authSession = await loginUser(username, password);
      onLogin(authSession);
    } catch (error) {
      setLoginError(
        error instanceof Error ? error.message : "Unable to sign in."
      );
    } finally {
      setIsLoggingIn(false);
    }
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

        <h1 className="mb-2 text-center text-xl font-semibold">Sign in</h1>
        <p
          className={cn(
            "mb-6 text-center text-sm",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          Use your CareQueue account to continue.
        </p>

        <form className="space-y-4" onSubmit={handleSubmit}>
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
            {isLoggingIn ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}

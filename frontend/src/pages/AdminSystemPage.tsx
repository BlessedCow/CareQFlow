import {
  CheckCircle2,
  CircleAlert,
  Database,
  HardDriveDownload,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  createRestorePoint,
  fetchApplicationHealth,
  fetchDatabaseReadiness,
  fetchRestorePoints,
  verifyRestorePoint,
  type ApplicationHealth,
  type BackupFile,
  type DatabaseReadiness,
} from "../api/system";
import { cn } from "../utils/cn";

interface AdminSystemPageProps {
  darkMode: boolean;
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function AdminSystemPage({ darkMode }: AdminSystemPageProps) {
  const [applicationHealth, setApplicationHealth] =
    useState<ApplicationHealth | null>(null);
  const [databaseReadiness, setDatabaseReadiness] =
    useState<DatabaseReadiness | null>(null);
  const [restorePoints, setRestorePoints] = useState<BackupFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [verifyingFilename, setVerifyingFilename] = useState<string | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadSystemData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [health, readiness, backups] = await Promise.all([
        fetchApplicationHealth(),
        fetchDatabaseReadiness(),
        fetchRestorePoints(),
      ]);

      setApplicationHealth(health);
      setDatabaseReadiness(readiness);
      setRestorePoints(backups);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load system information."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSystemData();
  }, [loadSystemData]);

  const handleCreateRestorePoint = async () => {
    setIsCreating(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await createRestorePoint();

      setRestorePoints((current) => [
        result.backup,
        ...current.filter(
          (backup) => backup.filename !== result.backup.filename
        ),
      ]);

      setSuccessMessage(
        `Restore point ${result.backup.filename} was created and verified.`
      );
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "Unable to create the restore point."
      );
    } finally {
      setIsCreating(false);
    }
  };

  const handleVerifyRestorePoint = async (filename: string) => {
    setVerifyingFilename(filename);
    setError(null);
    setSuccessMessage(null);

    try {
      await verifyRestorePoint(filename);

      setSuccessMessage(`Restore point ${filename} passed verification.`);
    } catch (verifyError) {
      setError(
        verifyError instanceof Error
          ? verifyError.message
          : "Unable to verify the restore point."
      );
    } finally {
      setVerifyingFilename(null);
    }
  };

  const cardClass = cn(
    "rounded-xl border p-5 shadow-sm",
    darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
  );

  if (isLoading) {
    return (
      <div className={cn(cardClass, "flex items-center justify-center py-12")}>
        <RefreshCw className="mr-3 h-5 w-5 animate-spin" />
        <span>Loading system information...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div
          role="alert"
          className={cn(
            "rounded-xl border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900 bg-red-950/40 text-red-200"
              : "border-red-200 bg-red-50 text-red-800"
          )}
        >
          {error}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className={cn(
            "rounded-xl border px-4 py-3 text-sm",
            darkMode
              ? "border-green-900 bg-green-950/40 text-green-200"
              : "border-green-200 bg-green-50 text-green-800"
          )}
        >
          {successMessage}
        </div>
      )}

      <section className="grid gap-6 md:grid-cols-2">
        <div className={cardClass}>
          <div className="mb-4 flex items-center gap-3">
            <Server className="h-6 w-6 text-blue-500" />
            <div>
              <h2 className="text-lg font-semibold">Application Health</h2>
              <p
                className={cn(
                  "text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                CareQueue API process status
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {applicationHealth?.status === "ok" ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <span className="font-medium">Operational</span>
              </>
            ) : (
              <>
                <CircleAlert className="h-5 w-5 text-red-500" />
                <span className="font-medium">Unavailable</span>
              </>
            )}
          </div>

          {applicationHealth && (
            <p
              className={cn(
                "mt-3 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Version {applicationHealth.version}
            </p>
          )}
        </div>

        <div className={cardClass}>
          <div className="mb-4 flex items-center gap-3">
            <Database className="h-6 w-6 text-blue-500" />
            <div>
              <h2 className="text-lg font-semibold">Database Readiness</h2>
              <p
                className={cn(
                  "text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Encrypted database connection status
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {databaseReadiness?.status === "ok" ? (
              <>
                <ShieldCheck className="h-5 w-5 text-green-500" />
                <span className="font-medium">Ready</span>
              </>
            ) : (
              <>
                <CircleAlert className="h-5 w-5 text-red-500" />
                <span className="font-medium">Unavailable</span>
              </>
            )}
          </div>
        </div>
      </section>

      <section className={cardClass}>
        <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <HardDriveDownload className="h-6 w-6 text-blue-500" />
              <h2 className="text-lg font-semibold">Restore Points</h2>
            </div>

            <p
              className={cn(
                "mt-2 max-w-2xl text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Create and verify encrypted database restore points. Creating a
              restore point does not replace the active database.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void loadSystemData()}
              disabled={isCreating || verifyingFilename !== null}
              className={cn(
                "rounded-lg border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                darkMode
                  ? "border-gray-700 hover:bg-gray-800"
                  : "border-gray-300 hover:bg-gray-100"
              )}
            >
              Refresh
            </button>

            <button
              type="button"
              onClick={() => void handleCreateRestorePoint()}
              disabled={isCreating || verifyingFilename !== null}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isCreating ? "Creating..." : "Create Restore Point"}
            </button>
          </div>
        </div>

        {restorePoints.length === 0 ? (
          <div
            className={cn(
              "rounded-lg border border-dashed px-4 py-10 text-center text-sm",
              darkMode
                ? "border-gray-700 text-gray-400"
                : "border-gray-300 text-gray-600"
            )}
          >
            No encrypted restore points are available.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr
                  className={cn(
                    "border-b",
                    darkMode
                      ? "border-gray-800 text-gray-400"
                      : "border-gray-200 text-gray-600"
                  )}
                >
                  <th className="px-3 py-3 font-medium">File</th>
                  <th className="px-3 py-3 font-medium">Created</th>
                  <th className="px-3 py-3 font-medium">Size</th>
                  <th className="px-3 py-3 text-right font-medium">Action</th>
                </tr>
              </thead>

              <tbody>
                {restorePoints.map((backup) => (
                  <tr
                    key={backup.filename}
                    className={cn(
                      "border-b last:border-b-0",
                      darkMode ? "border-gray-800" : "border-gray-100"
                    )}
                  >
                    <td className="max-w-md break-all px-3 py-4 font-medium">
                      {backup.filename}
                    </td>
                    <td className="px-3 py-4">
                      {formatDate(backup.created_at)}
                    </td>
                    <td className="px-3 py-4">
                      {formatFileSize(backup.size_bytes)}
                    </td>
                    <td className="px-3 py-4 text-right">
                      <button
                        type="button"
                        onClick={() =>
                          void handleVerifyRestorePoint(backup.filename)
                        }
                        disabled={isCreating || verifyingFilename !== null}
                        className={cn(
                          "rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                          darkMode
                            ? "border-gray-700 hover:bg-gray-800"
                            : "border-gray-300 hover:bg-gray-100"
                        )}
                      >
                        {verifyingFilename === backup.filename
                          ? "Verifying..."
                          : "Verify"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

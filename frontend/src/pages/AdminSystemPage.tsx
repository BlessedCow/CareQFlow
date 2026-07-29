import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Database,
  HardDriveDownload,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  cancelDatabaseRecovery,
  createRestorePoint,
  fetchApiEndpoints,
  fetchApplicationHealth,
  fetchDatabaseReadiness,
  fetchRecoveryStatus,
  fetchRestorePoints,
  stageDatabaseRecovery,
  verifyRestorePoint,
  type ApiEndpointStatus,
  type ApplicationHealth,
  type BackupFile,
  type BackupRetentionResult,
  type DatabaseReadiness,
  type StagedRecovery,
} from "../api/system";
import { cn } from "../utils/cn";

interface AdminSystemPageProps {
  darkMode: boolean;
}

interface RestorePointVerificationResult {
  filename: string;
  succeeded: boolean;
  message: string;
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
  const [verifiedFilenames, setVerifiedFilenames] = useState<Set<string>>(
    () => new Set()
  );
  const [verificationResult, setVerificationResult] =
    useState<RestorePointVerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [retentionResult, setRetentionResult] =
    useState<BackupRetentionResult | null>(null);
  const [apiEndpoints, setApiEndpoints] = useState<ApiEndpointStatus[]>([]);
  const [isEndpointInventoryOpen, setIsEndpointInventoryOpen] = useState(false);
  const [isLoadingEndpoints, setIsLoadingEndpoints] = useState(false);
  const [endpointSearch, setEndpointSearch] = useState("");
  const [endpointError, setEndpointError] = useState<string | null>(null);
  const [stagedRecovery, setStagedRecovery] = useState<StagedRecovery | null>(
    null
  );
  const [stagingFilename, setStagingFilename] = useState<string | null>(null);
  const [isCancelingRecovery, setIsCancelingRecovery] = useState(false);
  const [recoveryConfirmationFilename, setRecoveryConfirmationFilename] =
    useState<string | null>(null);

  const loadSystemData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [health, readiness, backups, recoveryStatus] = await Promise.all([
        fetchApplicationHealth(),
        fetchDatabaseReadiness(),
        fetchRestorePoints(),
        fetchRecoveryStatus(),
      ]);

      setApplicationHealth(health);
      setDatabaseReadiness(readiness);
      setRestorePoints(backups);
      setStagedRecovery(
        recoveryStatus.pending ? recoveryStatus.recovery : null
      );
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
    setRetentionResult(null);

    try {
      const result = await createRestorePoint();

      setRetentionResult(result.retention);

      setRestorePoints((current) => [
        result.backup,
        ...current.filter(
          (backup) => backup.filename !== result.backup.filename
        ),
      ]);

      if (result.verified) {
        setVerifiedFilenames((current) => {
          const updated = new Set(current);
          updated.add(result.backup.filename);
          return updated;
        });
      }

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
    setVerificationResult(null);

    try {
      const result = await verifyRestorePoint(filename);

      if (!result.verified) {
        throw new Error("The restore point did not pass verification.");
      }

      setVerifiedFilenames((current) => {
        const updated = new Set(current);
        updated.add(filename);
        return updated;
      });

      setVerificationResult({
        filename,
        succeeded: true,
        message: `${filename} verified successfully.`,
      });
    } catch (verifyError) {
      const message =
        verifyError instanceof Error
          ? verifyError.message
          : "Unable to verify the restore point.";

      setVerificationResult({
        filename,
        succeeded: false,
        message: `${filename} could not be verified: ${message}`,
      });
    } finally {
      setVerifyingFilename(null);
    }
  };

  const handleStageRecovery = async () => {
    if (!recoveryConfirmationFilename) {
      return;
    }

    const filename = recoveryConfirmationFilename;

    setStagingFilename(filename);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await stageDatabaseRecovery(filename);

      setStagedRecovery(result.recovery);
      setRecoveryConfirmationFilename(null);
      setSuccessMessage(
        `Restore point ${filename} was staged for database recovery.`
      );
    } catch (stageError) {
      setError(
        stageError instanceof Error
          ? stageError.message
          : "Unable to stage the selected restore point."
      );
    } finally {
      setStagingFilename(null);
    }
  };

  const handleCancelRecovery = async () => {
    setIsCancelingRecovery(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await cancelDatabaseRecovery();

      setStagedRecovery(null);
      setSuccessMessage(
        `Staged recovery for ${result.recovery.backup_filename} was canceled.`
      );
    } catch (cancelError) {
      setError(
        cancelError instanceof Error
          ? cancelError.message
          : "Unable to cancel the staged database recovery."
      );
    } finally {
      setIsCancelingRecovery(false);
    }
  };

  const handleToggleEndpointInventory = async () => {
    if (isEndpointInventoryOpen) {
      setIsEndpointInventoryOpen(false);
      return;
    }

    setIsEndpointInventoryOpen(true);

    if (apiEndpoints.length > 0) {
      return;
    }

    setIsLoadingEndpoints(true);
    setEndpointError(null);

    try {
      const endpoints = await fetchApiEndpoints();
      setApiEndpoints(endpoints);
    } catch (loadError) {
      setEndpointError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load API endpoint status."
      );
    } finally {
      setIsLoadingEndpoints(false);
    }
  };

  const filteredApiEndpoints = useMemo(() => {
    const normalizedSearch = endpointSearch.trim().toLowerCase();

    if (!normalizedSearch) {
      return apiEndpoints;
    }

    return apiEndpoints.filter((endpoint) => {
      const searchableValues = [
        endpoint.path,
        endpoint.group,
        endpoint.access,
        endpoint.status,
        ...endpoint.methods,
      ];

      return searchableValues.some((value) =>
        value.toLowerCase().includes(normalizedSearch)
      );
    });
  }, [apiEndpoints, endpointSearch]);

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

      {retentionResult && (
        <section
          aria-labelledby="backup-retention-result-heading"
          className={cn(
            "rounded-xl border p-4 text-sm",
            retentionResult.failed.length > 0
              ? darkMode
                ? "border-amber-900 bg-amber-950/30"
                : "border-amber-200 bg-amber-50"
              : darkMode
              ? "border-blue-900 bg-blue-950/30"
              : "border-blue-200 bg-blue-50"
          )}
        >
          <div className="flex items-center gap-2">
            {retentionResult.failed.length > 0 ? (
              <CircleAlert className="h-5 w-5 text-amber-500" />
            ) : (
              <ShieldCheck className="h-5 w-5 text-blue-500" />
            )}

            <h2 id="backup-retention-result-heading" className="font-semibold">
              Backup Retention
            </h2>
          </div>

          <p
            className={cn("mt-2", darkMode ? "text-gray-300" : "text-gray-700")}
          >
            Encrypted restore points are retained for{" "}
            <strong>{retentionResult.retention_days} days</strong>, with at
            least <strong>{retentionResult.minimum_count}</strong> recent
            restore points preserved.
          </p>

          <dl className="mt-3 grid gap-3 sm:grid-cols-3">
            <div>
              <dt
                className={cn(
                  "font-medium",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Pruned
              </dt>
              <dd className="mt-1">{retentionResult.deleted.length}</dd>
            </div>

            <div>
              <dt
                className={cn(
                  "font-medium",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Recovery protected
              </dt>
              <dd className="mt-1">{retentionResult.protected.length}</dd>
            </div>

            <div>
              <dt
                className={cn(
                  "font-medium",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Cleanup failures
              </dt>
              <dd className="mt-1">{retentionResult.failed.length}</dd>
            </div>
          </dl>

          {retentionResult.deleted.length > 0 && (
            <div className="mt-3">
              <p className="font-medium">Deleted restore points</p>
              <ul className="mt-1 space-y-1">
                {retentionResult.deleted.map((filename) => (
                  <li key={filename} className="break-all font-mono text-xs">
                    {filename}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {retentionResult.protected.length > 0 && (
            <div className="mt-3">
              <p className="font-medium">Protected by pending recovery</p>
              <ul className="mt-1 space-y-1">
                {retentionResult.protected.map((filename) => (
                  <li key={filename} className="break-all font-mono text-xs">
                    {filename}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {retentionResult.failed.length > 0 && (
            <div className="mt-3">
              <p className="font-medium">Cleanup could not complete for</p>
              <ul className="mt-1 space-y-1">
                {retentionResult.failed.map((failure) => (
                  <li key={failure} className="break-all font-mono text-xs">
                    {failure}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
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

          <button
            type="button"
            onClick={() => void handleToggleEndpointInventory()}
            className={cn(
              "mt-5 flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
              darkMode
                ? "border-gray-700 hover:bg-gray-800"
                : "border-gray-300 hover:bg-gray-100"
            )}
            aria-expanded={isEndpointInventoryOpen}
          >
            {isEndpointInventoryOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}

            {isEndpointInventoryOpen
              ? "Hide API Endpoints"
              : "View API Endpoints"}
          </button>
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

      {isEndpointInventoryOpen && (
        <section className={cardClass}>
          <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">API Endpoint Status</h2>

              <p
                className={cn(
                  "mt-1 text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Operational endpoints are actively probed. Registered endpoints
                were loaded successfully but are not called automatically.
              </p>
            </div>

            <div className="relative w-full sm:w-80">
              <Search
                className={cn(
                  "pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2",
                  darkMode ? "text-gray-500" : "text-gray-400"
                )}
              />

              <input
                type="search"
                aria-label="Search API endpoints"
                value={endpointSearch}
                onChange={(event) => setEndpointSearch(event.target.value)}
                placeholder="Search method, path, group, or status"
                className={cn(
                  "w-full rounded-lg border py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-blue-500",
                  darkMode
                    ? "border-gray-700 bg-gray-950 text-gray-100"
                    : "border-gray-300 bg-white text-gray-900"
                )}
              />
            </div>
          </div>

          {endpointError && (
            <div
              role="alert"
              className={cn(
                "mb-4 rounded-lg border px-4 py-3 text-sm",
                darkMode
                  ? "border-red-900 bg-red-950/40 text-red-200"
                  : "border-red-200 bg-red-50 text-red-800"
              )}
            >
              {endpointError}
            </div>
          )}

          {isLoadingEndpoints ? (
            <div className="flex items-center justify-center py-10">
              <RefreshCw className="mr-3 h-5 w-5 animate-spin" />
              <span>Loading API endpoint status...</span>
            </div>
          ) : filteredApiEndpoints.length === 0 ? (
            <div
              className={cn(
                "rounded-lg border border-dashed px-4 py-10 text-center text-sm",
                darkMode
                  ? "border-gray-700 text-gray-400"
                  : "border-gray-300 text-gray-600"
              )}
            >
              No API endpoints match the current search.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead>
                  <tr
                    className={cn(
                      "border-b",
                      darkMode
                        ? "border-gray-800 text-gray-400"
                        : "border-gray-200 text-gray-600"
                    )}
                  >
                    <th className="px-3 py-3 font-medium">Method</th>
                    <th className="px-3 py-3 font-medium">Path</th>
                    <th className="px-3 py-3 font-medium">Group</th>
                    <th className="px-3 py-3 font-medium">Access</th>
                    <th className="px-3 py-3 font-medium">Status</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredApiEndpoints.map((endpoint) => (
                    <tr
                      key={`${endpoint.methods.join(",")}-${endpoint.path}`}
                      className={cn(
                        "border-b last:border-b-0",
                        darkMode ? "border-gray-800" : "border-gray-100"
                      )}
                    >
                      <td className="px-3 py-4">
                        <span
                          className={cn(
                            "inline-flex rounded-md px-2 py-1 font-mono text-xs font-semibold",
                            darkMode
                              ? "bg-gray-800 text-gray-200"
                              : "bg-gray-100 text-gray-800"
                          )}
                        >
                          {endpoint.methods.join(", ")}
                        </span>
                      </td>

                      <td className="break-all px-3 py-4 font-mono text-xs">
                        {endpoint.path}
                      </td>

                      <td className="px-3 py-4">{endpoint.group}</td>

                      <td className="px-3 py-4 capitalize">
                        {endpoint.access === "admin"
                          ? "Admin"
                          : endpoint.access}
                      </td>

                      <td className="px-3 py-4">
                        <span
                          className={cn(
                            "inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium",
                            endpoint.status === "operational" &&
                              (darkMode
                                ? "bg-green-950 text-green-200"
                                : "bg-green-100 text-green-800"),
                            endpoint.status === "unavailable" &&
                              (darkMode
                                ? "bg-red-950 text-red-200"
                                : "bg-red-100 text-red-800"),
                            endpoint.status === "registered" &&
                              (darkMode
                                ? "bg-blue-950 text-blue-200"
                                : "bg-blue-100 text-blue-800")
                          )}
                        >
                          {endpoint.status === "operational" && (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          )}

                          {endpoint.status === "unavailable" && (
                            <CircleAlert className="h-3.5 w-3.5" />
                          )}

                          {endpoint.status === "operational"
                            ? "Operational"
                            : endpoint.status === "unavailable"
                            ? "Unavailable"
                            : "Registered"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <section className={cardClass}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Database className="h-6 w-6 text-amber-500" />
              <h2 className="text-lg font-semibold">Database Recovery</h2>
            </div>

            <p
              className={cn(
                "mt-2 max-w-2xl text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Staging prepares and validates a database recovery copy. It does
              not replace the active database or interrupt current users.
            </p>
          </div>

          {stagedRecovery && (
            <button
              type="button"
              onClick={() => void handleCancelRecovery()}
              disabled={
                isCancelingRecovery ||
                stagingFilename !== null ||
                isCreating ||
                verifyingFilename !== null
              }
              className={cn(
                "rounded-lg border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                darkMode
                  ? "border-red-800 text-red-300 hover:bg-red-950/40"
                  : "border-red-300 text-red-700 hover:bg-red-50"
              )}
            >
              {isCancelingRecovery ? "Canceling..." : "Cancel Staged Recovery"}
            </button>
          )}
        </div>

        {stagedRecovery ? (
          <div
            className={cn(
              "mt-5 rounded-lg border p-4",
              darkMode
                ? "border-amber-900 bg-amber-950/30"
                : "border-amber-200 bg-amber-50"
            )}
          >
            <div className="flex items-center gap-2 font-medium">
              <CircleAlert className="h-5 w-5 text-amber-500" />
              Recovery pending
            </div>

            <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
              <div>
                <dt
                  className={cn(
                    "font-medium",
                    darkMode ? "text-gray-400" : "text-gray-600"
                  )}
                >
                  Restore point
                </dt>
                <dd className="mt-1 break-all">
                  {stagedRecovery.backup_filename}
                </dd>
              </div>

              <div>
                <dt
                  className={cn(
                    "font-medium",
                    darkMode ? "text-gray-400" : "text-gray-600"
                  )}
                >
                  Staged database
                </dt>
                <dd className="mt-1 break-all">
                  {stagedRecovery.staged_filename}
                </dd>
              </div>

              <div>
                <dt
                  className={cn(
                    "font-medium",
                    darkMode ? "text-gray-400" : "text-gray-600"
                  )}
                >
                  Staged
                </dt>
                <dd className="mt-1">{formatDate(stagedRecovery.staged_at)}</dd>
              </div>
            </dl>
          </div>
        ) : (
          <div
            className={cn(
              "mt-5 rounded-lg border border-dashed px-4 py-8 text-center text-sm",
              darkMode
                ? "border-gray-700 text-gray-400"
                : "border-gray-300 text-gray-600"
            )}
          >
            No database recovery is currently staged.
          </div>
        )}
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
                    <td className="px-3 py-4">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            void handleVerifyRestorePoint(backup.filename)
                          }
                          disabled={
                            verifiedFilenames.has(backup.filename) ||
                            isCreating ||
                            verifyingFilename !== null ||
                            stagingFilename !== null ||
                            isCancelingRecovery
                          }
                          className={cn(
                            "rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
                            verifiedFilenames.has(backup.filename)
                              ? darkMode
                                ? "border-green-800 bg-green-950/40 text-green-300"
                                : "border-green-300 bg-green-50 text-green-700"
                              : darkMode
                              ? "border-gray-700 hover:bg-gray-800 disabled:opacity-60"
                              : "border-gray-300 hover:bg-gray-100 disabled:opacity-60"
                          )}
                        >
                          {verifyingFilename === backup.filename
                            ? "Verifying..."
                            : verifiedFilenames.has(backup.filename)
                            ? "Verified"
                            : "Verify"}
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            setRecoveryConfirmationFilename(backup.filename)
                          }
                          disabled={
                            stagedRecovery !== null ||
                            isCreating ||
                            verifyingFilename !== null ||
                            stagingFilename !== null ||
                            isCancelingRecovery
                          }
                          className={cn(
                            "rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                            darkMode
                              ? "border-amber-800 text-amber-300 hover:bg-amber-950/40"
                              : "border-amber-300 text-amber-700 hover:bg-amber-50"
                          )}
                        >
                          {stagingFilename === backup.filename
                            ? "Staging..."
                            : "Stage Recovery"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {verificationResult && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="verification-result-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        >
          <div
            className={cn(
              "w-full max-w-lg rounded-xl border p-6 shadow-xl",
              darkMode
                ? "border-gray-700 bg-gray-900"
                : "border-gray-200 bg-white"
            )}
          >
            <div className="flex items-start gap-3">
              {verificationResult.succeeded ? (
                <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-green-500" />
              ) : (
                <CircleAlert className="mt-0.5 h-6 w-6 shrink-0 text-red-500" />
              )}

              <div>
                <h2
                  id="verification-result-title"
                  className="text-lg font-semibold"
                >
                  {verificationResult.succeeded
                    ? "Restore Point Verified"
                    : "Verification Failed"}
                </h2>

                <p
                  className={cn(
                    "mt-3 break-words text-sm",
                    darkMode ? "text-gray-300" : "text-gray-700"
                  )}
                >
                  {verificationResult.message}
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setVerificationResult(null)}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm font-medium text-white",
                  verificationResult.succeeded
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-red-600 hover:bg-red-700"
                )}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {recoveryConfirmationFilename && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="stage-recovery-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        >
          <div
            className={cn(
              "w-full max-w-lg rounded-xl border p-6 shadow-xl",
              darkMode
                ? "border-gray-700 bg-gray-900"
                : "border-gray-200 bg-white"
            )}
          >
            <h2 id="stage-recovery-title" className="text-lg font-semibold">
              Stage Database Recovery?
            </h2>

            <p
              className={cn(
                "mt-3 text-sm",
                darkMode ? "text-gray-300" : "text-gray-700"
              )}
            >
              CareQueue will decrypt and validate this restore point into a
              separate staged database:
            </p>

            <p className="mt-3 break-all rounded-lg bg-black/5 p-3 font-mono text-xs dark:bg-white/5">
              {recoveryConfirmationFilename}
            </p>

            <p
              className={cn(
                "mt-3 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              The active database will not be replaced during this operation.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setRecoveryConfirmationFilename(null)}
                disabled={stagingFilename !== null}
                className={cn(
                  "rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-60",
                  darkMode
                    ? "border-gray-700 hover:bg-gray-800"
                    : "border-gray-300 hover:bg-gray-100"
                )}
              >
                Keep Current Database
              </button>

              <button
                type="button"
                onClick={() => void handleStageRecovery()}
                disabled={stagingFilename !== null}
                className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-60"
              >
                {stagingFilename ? "Staging..." : "Stage Recovery"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

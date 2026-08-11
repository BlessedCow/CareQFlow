import { useState, useMemo } from "react";
import { AuthRequest } from "../types/auth";
import { format } from "date-fns";
import { cn } from "../utils/cn";
import { ArrowUpDown, Eye, Pencil, Search, Trash2 } from "lucide-react";
import type { WorkflowViewMode } from "../hooks/useWorkflowViewMode";

interface DataTableProps {
  data: AuthRequest[];
  darkMode: boolean;
  onView?: (auth: AuthRequest) => void;
  onEdit?: (auth: AuthRequest) => void;
  onDelete?: (auth: AuthRequest) => void;
  deletingId?: string | null;
  showActions?: boolean;
  workflowViewMode?: WorkflowViewMode;
}

type SortField = keyof Pick<
  AuthRequest,
  | "date"
  | "patientId"
  | "payer"
  | "facility"
  | "status"
  | "requestedDays"
  | "approvedDays"
>;
type SortOrder = "asc" | "desc";

function parseDateOnly(value?: string | null) {
  if (!value) {
    return null;
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date;
}

function formatDateOnly(value?: string | null) {
  const date = parseDateOnly(value);

  if (!date) {
    return "Not set";
  }

  return format(date, "MMM d, yyyy");
}

function isClosedStatus(status: AuthRequest["status"]) {
  return ["Completed", "Discharged", "No PA Required"].includes(status);
}

function calculateDaysUntil(value?: string | null) {
  const date = parseDateOnly(value);

  if (!date) {
    return null;
  }

  const today = new Date();
  const startOfToday = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate()
  );
  const startOfDate = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate()
  );
  const millisecondsPerDay = 1000 * 60 * 60 * 24;

  return Math.ceil(
    (startOfDate.getTime() - startOfToday.getTime()) / millisecondsPerDay
  );
}

function getScheduleCue(row: AuthRequest) {
  const reviewDaysUntil = calculateDaysUntil(row.reviewDueDate);
  const lcdDaysUntil = calculateDaysUntil(row.authEndDate);

  if (["Completed", "Discharged", "No PA Required"].includes(row.status)) {
    return "Closed";
  }

  if (reviewDaysUntil !== null && reviewDaysUntil < 0) {
    return `Overdue review ${Math.abs(reviewDaysUntil)}d`;
  }

  if (reviewDaysUntil === 0) {
    return "Review due today";
  }

  if (reviewDaysUntil !== null && reviewDaysUntil <= 7) {
    return `Review due in ${reviewDaysUntil}d`;
  }

  if (lcdDaysUntil !== null && lcdDaysUntil < 0) {
    return `LCD passed ${Math.abs(lcdDaysUntil)}d`;
  }

  if (lcdDaysUntil === 0) {
    return "LCD today";
  }

  if (lcdDaysUntil !== null && lcdDaysUntil <= 7) {
    return `LCD in ${lcdDaysUntil}d`;
  }

  if (!row.reviewDueDate && !row.authEndDate) {
    return "No schedule date";
  }

  return "Scheduled";
}

function getDaysConfirmationCue(row: AuthRequest) {
  if (Number(row.approvedDays) > 0) {
    return "Confirmed from approved days";
  }

  if (Number(row.requestedDays) > 0) {
    return "Days not confirmed";
  }

  return "No days recorded";
}

function getScheduleCueColor(row: AuthRequest, darkMode: boolean) {
  const reviewDaysUntil = calculateDaysUntil(row.reviewDueDate);
  const lcdDaysUntil = calculateDaysUntil(row.authEndDate);

  if (["Completed", "Discharged", "No PA Required"].includes(row.status)) {
    return darkMode ? "text-gray-500" : "text-gray-500";
  }

  if (
    (reviewDaysUntil !== null && reviewDaysUntil < 0) ||
    (lcdDaysUntil !== null && lcdDaysUntil < 0)
  ) {
    return darkMode ? "text-red-300" : "text-red-700";
  }

  if (
    (reviewDaysUntil !== null && reviewDaysUntil <= 7) ||
    (lcdDaysUntil !== null && lcdDaysUntil <= 7)
  ) {
    return darkMode ? "text-amber-300" : "text-amber-700";
  }

  if (!row.reviewDueDate && !row.authEndDate) {
    return darkMode ? "text-gray-500" : "text-gray-500";
  }

  return darkMode ? "text-emerald-300" : "text-emerald-700";
}

function calculateTurnaroundDays(
  submittedAt?: string | null,
  decisionAt?: string | null
) {
  if (!submittedAt || !decisionAt) {
    return "Pending";
  }

  const submittedDate = new Date(submittedAt);
  const decisionDate = new Date(decisionAt);

  if (
    Number.isNaN(submittedDate.getTime()) ||
    Number.isNaN(decisionDate.getTime())
  ) {
    return "Pending";
  }

  const millisecondsPerDay = 1000 * 60 * 60 * 24;
  const difference = decisionDate.getTime() - submittedDate.getTime();
  const days = Math.max(0, Math.ceil(difference / millisecondsPerDay));

  return `${days} day${days === 1 ? "" : "s"}`;
}

function calculateDaysSince(date: Date) {
  const today = new Date();
  const startOfToday = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate()
  );
  const startOfDate = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate()
  );
  const millisecondsPerDay = 1000 * 60 * 60 * 24;

  return Math.max(
    0,
    Math.floor(
      (startOfToday.getTime() - startOfDate.getTime()) / millisecondsPerDay
    )
  );
}

function getWorkflowCue(row: AuthRequest) {
  const status = String(row.status);
  const daysSinceAuthDate = calculateDaysSince(row.date);

  if (status === "Pending") {
    return daysSinceAuthDate === 0
      ? "Pending today"
      : `Pending ${daysSinceAuthDate}d`;
  }

  if (status === "P2P") {
    return "Peer review needed";
  }

  if (status === "Appealed") {
    return "Appeal pending";
  }

  if (status === "Denied") {
    return "Follow-up needed";
  }

  if (
    status === "Approved" &&
    row.requestedDays > 0 &&
    row.approvedDays > 0 &&
    row.approvedDays < row.requestedDays
  ) {
    return "Partial approval";
  }

  if (status === "Approved") {
    return "Complete";
  }

  if (status === "No PA Required") {
    return "No PA required";
  }

  if (status === "Completed") {
    return "Completed";
  }

  if (status === "Discharged") {
    return "Discharged";
  }

  return "Review status";
}

function getWorkflowCueColor(status: AuthRequest["status"], darkMode: boolean) {
  const cleanStatus = String(status);

  if (cleanStatus === "Pending") {
    return darkMode ? "text-amber-300" : "text-amber-700";
  }

  if (cleanStatus === "P2P") {
    return darkMode ? "text-blue-300" : "text-blue-700";
  }

  if (cleanStatus === "Appealed") {
    return darkMode ? "text-purple-300" : "text-purple-700";
  }

  if (cleanStatus === "Denied") {
    return darkMode ? "text-red-300" : "text-red-700";
  }

  if (cleanStatus === "Approved" || cleanStatus === "No PA Required") {
    return darkMode ? "text-emerald-300" : "text-emerald-700";
  }

  return darkMode ? "text-gray-400" : "text-gray-600";
}

export function DataTable({
  data,
  darkMode,
  onView,
  onEdit,
  onDelete,
  deletingId,
  showActions = true,
  workflowViewMode = "relaxed",
}: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(
    null
  );
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;
  const handleSort = (field: SortField) => {
    setConfirmingDeleteId(null);
    setCurrentPage(1);

    if (field === sortField) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const isDetailedView = workflowViewMode === "detailed";
  const emptyStateColSpan = showActions
    ? isDetailedView
      ? 8
      : 6
    : isDetailedView
    ? 7
    : 5;

  const filteredAndSortedData = useMemo(() => {
    return data
      .filter((item) => {
        const searchLower = searchTerm.toLowerCase();
        return (
          item.patientId.toLowerCase().includes(searchLower) ||
          item.memberId.toLowerCase().includes(searchLower) ||
          item.authNumber.toLowerCase().includes(searchLower) ||
          item.groupNumber.toLowerCase().includes(searchLower) ||
          item.facility.toLowerCase().includes(searchLower) ||
          item.urSpecialist.toLowerCase().includes(searchLower) ||
          item.payer.toLowerCase().includes(searchLower)
        );
      })
      .sort((a, b) => {
        let aVal: any = a[sortField];
        let bVal: any = b[sortField];

        if (sortField === "date") {
          aVal = a.date.getTime();
          bVal = b.date.getTime();
        }

        if (aVal < bVal) return sortOrder === "asc" ? -1 : 1;
        if (aVal > bVal) return sortOrder === "asc" ? 1 : -1;
        return 0;
      });
  }, [data, searchTerm, sortField, sortOrder]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredAndSortedData.length / pageSize)
  );
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedData = filteredAndSortedData.slice(startIndex, endIndex);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Approved":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-400";
      case "Denied":
        return "bg-rose-100 text-rose-800 dark:bg-rose-500/20 dark:text-rose-400";
      case "Pending":
        return "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-400";
      case "P2P":
        return "bg-purple-100 text-purple-800 dark:bg-purple-500/20 dark:text-purple-400";
      case "Appealed":
        return "bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-400";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
    }
  };

  const thClass = cn(
    "px-4 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer group",
    darkMode
      ? "text-gray-400 bg-gray-900 border-gray-800"
      : "text-gray-500 bg-gray-50 border-gray-200"
  );

  const tdClass = cn(
    "px-4 py-3 text-sm whitespace-nowrap border-t",
    darkMode ? "border-gray-800" : "border-gray-100"
  );

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4 relative shrink-0">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search
            className={cn(
              "h-4 w-4",
              darkMode ? "text-gray-500" : "text-gray-400"
            )}
          />
        </div>
        <input
          type="text"
          placeholder="Search patient, member ID, auth number, facility..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setCurrentPage(1);
            setConfirmingDeleteId(null);
          }}
          className={cn(
            "w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors",
            darkMode
              ? "bg-gray-800 border-gray-700 text-gray-200 placeholder-gray-500"
              : "bg-white border-gray-300 text-gray-900 placeholder-gray-400"
          )}
        />
      </div>

      <div className="overflow-x-auto flex-1 min-h-[300px]">
        <table className="min-w-full w-full">
          <thead>
            <tr>
              <th className={thClass} onClick={() => handleSort("date")}>
                <div className="flex items-center">
                  Date{" "}
                  <ArrowUpDown className="ml-1 w-3 h-3 opacity-50 group-hover:opacity-100" />
                </div>
              </th>
              <th className={thClass} onClick={() => handleSort("patientId")}>
                <div className="flex items-center">
                  Patient{" "}
                  <ArrowUpDown className="ml-1 w-3 h-3 opacity-50 group-hover:opacity-100" />
                </div>
              </th>
              <th className={thClass} onClick={() => handleSort("facility")}>
                <div className="flex items-center">
                  Facility{" "}
                  <ArrowUpDown className="ml-1 w-3 h-3 opacity-50 group-hover:opacity-100" />
                </div>
              </th>
              <th className={thClass} onClick={() => handleSort("status")}>
                <div className="flex items-center">
                  Status{" "}
                  <ArrowUpDown className="ml-1 w-3 h-3 opacity-50 group-hover:opacity-100" />
                </div>
              </th>
              <th className={thClass}>
                <div className="flex items-center">Days (Req/Appr)</div>
              </th>
              {isDetailedView && (
                <th className={thClass}>
                  <div className="flex items-center">Schedule</div>
                </th>
              )}
              {isDetailedView && (
                <th className={thClass}>
                  <div className="flex items-center">Turnaround</div>
                </th>
              )}
              {showActions && (
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row) => (
              <tr
                key={row.id}
                onClick={() => {
                  if (!showActions && onView) {
                    onView(row);
                  }
                }}
                onKeyDown={(event) => {
                  if (
                    !showActions &&
                    onView &&
                    (event.key === "Enter" || event.key === " ")
                  ) {
                    event.preventDefault();
                    onView(row);
                  }
                }}
                tabIndex={!showActions && onView ? 0 : undefined}
                role={!showActions && onView ? "button" : undefined}
                className={cn(
                  "transition-colors",
                  !showActions && onView ? "cursor-pointer" : "",
                  darkMode ? "hover:bg-gray-800/50" : "hover:bg-gray-50"
                )}
              >
                <td className={tdClass}>{format(row.date, "MMM d, yyyy")}</td>
                <td className={tdClass}>
                  <div className="font-medium">{row.patientId}</div>
                  <div
                    className={cn(
                      "text-xs",
                      darkMode ? "text-gray-500" : "text-gray-500"
                    )}
                  >
                    {row.payer}
                  </div>

                  {row.authNumber && (
                    <div
                      className={cn(
                        "text-xs",
                        darkMode ? "text-gray-500" : "text-gray-500"
                      )}
                    >
                      Auth/Ref: {row.authNumber}
                    </div>
                  )}
                </td>
                <td className={tdClass}>{row.facility}</td>
                <td className={tdClass}>
                  <div className="flex flex-col gap-1">
                    <span
                      className={cn(
                        "w-fit px-2.5 py-1 rounded-full text-xs font-medium",
                        getStatusColor(row.status)
                      )}
                    >
                      {row.status}
                    </span>

                    <span
                      className={cn(
                        "text-xs font-medium",
                        getWorkflowCueColor(row.status, darkMode)
                      )}
                    >
                      {getWorkflowCue(row)}
                    </span>
                  </div>
                </td>
                <td className={tdClass}>
                  <span
                    className={cn(
                      "text-sm",
                      row.approvedDays < row.requestedDays &&
                        row.status === "Approved"
                        ? "text-amber-500 font-medium"
                        : ""
                    )}
                  >
                    {row.requestedDays} /{" "}
                    {row.status === "Pending" ? "-" : row.approvedDays}
                  </span>
                </td>

                {isDetailedView && (
                  <td className={tdClass}>
                    {isClosedStatus(row.status) ? (
                      <div className="flex flex-col gap-1">
                        <span
                          className={cn(
                            "text-xs font-medium",
                            darkMode ? "text-gray-300" : "text-gray-700"
                          )}
                        >
                          Status: {row.status}
                        </span>
                        <span
                          className={cn(
                            "text-xs",
                            darkMode ? "text-gray-400" : "text-gray-500"
                          )}
                        >
                          Authorization closed
                        </span>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-1">
                        <div className="text-xs">
                          <span
                            className={
                              darkMode ? "text-gray-400" : "text-gray-500"
                            }
                          >
                            Review Due:{" "}
                          </span>
                          <span>{formatDateOnly(row.reviewDueDate)}</span>
                        </div>

                        <span
                          className={cn(
                            "text-xs font-medium",
                            getScheduleCueColor(row, darkMode)
                          )}
                        >
                          {getScheduleCue(row)}
                        </span>

                        <span
                          className={cn(
                            "text-xs",
                            darkMode ? "text-gray-400" : "text-gray-500"
                          )}
                        >
                          {getDaysConfirmationCue(row)}
                        </span>
                      </div>
                    )}
                  </td>
                )}

                {isDetailedView && (
                  <td className={tdClass}>
                    {calculateTurnaroundDays(row.submittedAt, row.decisionAt)}
                  </td>
                )}
                {showActions && (
                  <td
                    onClick={(event) => event.stopPropagation()}
                    className={cn(tdClass, "text-right")}
                  >
                    <div className="flex items-center justify-end gap-3">
                      {onView && (
                        <button
                          type="button"
                          onClick={() => onView(row)}
                          className={cn(
                            "inline-flex items-center gap-1 font-medium transition-colors",
                            darkMode
                              ? "text-gray-300 hover:text-white"
                              : "text-gray-600 hover:text-gray-900"
                          )}
                          aria-label={`View authorization record for ${row.patientId}`}
                        >
                          <Eye className="h-4 w-4" />
                          <span>View</span>
                        </button>
                      )}

                      {onEdit && (
                        <button
                          type="button"
                          onClick={() => onEdit(row)}
                          className={cn(
                            "inline-flex items-center gap-1 font-medium transition-colors",
                            darkMode
                              ? "text-blue-400 hover:text-blue-300"
                              : "text-blue-600 hover:text-blue-700"
                          )}
                          aria-label={`Edit authorization record for ${row.patientId}`}
                        >
                          <Pencil className="h-4 w-4" />
                          <span>Edit</span>
                        </button>
                      )}

                      {onDelete &&
                        (confirmingDeleteId === row.id ? (
                          <div className="flex items-center gap-2">
                            <span
                              className={cn(
                                "text-xs",
                                darkMode ? "text-gray-400" : "text-gray-500"
                              )}
                            >
                              Delete?
                            </span>

                            <button
                              type="button"
                              onClick={() => {
                                onDelete(row);
                                setConfirmingDeleteId(null);
                              }}
                              disabled={deletingId === row.id}
                              className={cn(
                                "text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                                darkMode
                                  ? "text-red-400 hover:text-red-300"
                                  : "text-red-600 hover:text-red-700"
                              )}
                              aria-label={`Confirm delete authorization record for ${row.patientId}`}
                            >
                              {deletingId === row.id ? "Deleting..." : "Yes"}
                            </button>

                            <button
                              type="button"
                              onClick={() => setConfirmingDeleteId(null)}
                              disabled={deletingId === row.id}
                              className={cn(
                                "text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                                darkMode
                                  ? "text-gray-400 hover:text-gray-300"
                                  : "text-gray-600 hover:text-gray-800"
                              )}
                              aria-label={`Cancel delete authorization record for ${row.patientId}`}
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmingDeleteId(row.id)}
                            disabled={deletingId === row.id}
                            className={cn(
                              "inline-flex items-center gap-1 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                              darkMode
                                ? "text-red-400 hover:text-red-300"
                                : "text-red-600 hover:text-red-700"
                            )}
                            aria-label={`Delete authorization record for ${row.patientId}`}
                          >
                            <Trash2 className="h-4 w-4" />
                            <span>
                              {deletingId === row.id ? "Deleting..." : "Delete"}
                            </span>
                          </button>
                        ))}
                    </div>
                  </td>
                )}
              </tr>
            ))}

            {filteredAndSortedData.length === 0 && (
              <tr>
                <td
                  colSpan={emptyStateColSpan}
                  className={cn(
                    "px-4 py-8 text-center text-sm",
                    darkMode ? "text-gray-500" : "text-gray-500"
                  )}
                >
                  No matching records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {filteredAndSortedData.length > pageSize && (
        <div
          className={cn(
            "mt-4 flex flex-col gap-3 border-t pt-4 text-sm sm:flex-row sm:items-center sm:justify-between",
            darkMode
              ? "border-gray-800 text-gray-300"
              : "border-gray-200 text-gray-600"
          )}
        >
          <div>
            Showing{" "}
            <span className="font-medium">
              {startIndex + 1}-
              {Math.min(endIndex, filteredAndSortedData.length)}
            </span>{" "}
            of{" "}
            <span className="font-medium">{filteredAndSortedData.length}</span>{" "}
            authorizations
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setCurrentPage((page) => Math.max(1, page - 1));
                setConfirmingDeleteId(null);
              }}
              disabled={safeCurrentPage === 1}
              className={cn(
                "rounded-lg border px-3 py-1.5 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                darkMode
                  ? "border-gray-700 bg-gray-900 text-gray-200 hover:bg-gray-800"
                  : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
              )}
            >
              Previous
            </button>

            <span
              className={cn(
                "px-2",
                darkMode ? "text-gray-400" : "text-gray-500"
              )}
            >
              Page {safeCurrentPage} of {totalPages}
            </span>

            <button
              type="button"
              onClick={() => {
                setCurrentPage((page) => Math.min(totalPages, page + 1));
                setConfirmingDeleteId(null);
              }}
              disabled={safeCurrentPage === totalPages}
              className={cn(
                "rounded-lg border px-3 py-1.5 font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                darkMode
                  ? "border-gray-700 bg-gray-900 text-gray-200 hover:bg-gray-800"
                  : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
              )}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Clock,
  FileWarning,
  RefreshCw,
} from "lucide-react";

import { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";
import {
  DatedWorkflowItems,
  type DatedWorkflowItem,
} from "./upcomingWorkflow/DatedWorkflowItems";

import {
  WorkflowStatusItems,
  type WorkflowStatusItem,
} from "./upcomingWorkflow/WorkflowStatusItems";

interface UpcomingWorkflowCardProps {
  data: AuthRequest[];
  darkMode: boolean;
}

type WorkflowFilterKey =
  | "reviewDue"
  | "lcd"
  | "pending"
  | "p2p"
  | "appeals"
  | "denied"
  | "approved";

type WorkflowFilterSettings = Record<WorkflowFilterKey, boolean>;

const DEFAULT_WORKFLOW_FILTER_SETTINGS: WorkflowFilterSettings = {
  reviewDue: true,
  lcd: true,
  pending: true,
  p2p: true,
  appeals: true,
  denied: true,
  approved: true,
};

const WORKFLOW_FILTER_STORAGE_KEY = "carequeue.upcomingWorkflowFilters";

const WORKFLOW_FILTER_LABELS: Record<WorkflowFilterKey, string> = {
  reviewDue: "Review Due",
  lcd: "LCD",
  pending: "Pending Auths",
  p2p: "P2P Needed",
  appeals: "Appeals Pending",
  denied: "Denied Auths",
  approved: "Approved Auths",
};

function loadWorkflowFilterSettings(): WorkflowFilterSettings {
  try {
    const storedValue = window.localStorage.getItem(
      WORKFLOW_FILTER_STORAGE_KEY
    );

    if (!storedValue) {
      return DEFAULT_WORKFLOW_FILTER_SETTINGS;
    }

    const parsedValue = JSON.parse(
      storedValue
    ) as Partial<WorkflowFilterSettings>;

    return {
      ...DEFAULT_WORKFLOW_FILTER_SETTINGS,
      ...parsedValue,
    };
  } catch {
    return DEFAULT_WORKFLOW_FILTER_SETTINGS;
  }
}

function parseDateOnly(value?: string) {
  if (!value) {
    return null;
  }

  const [year, month, day] = value.split("-").map(Number);

  if (!year || !month || !day) {
    return null;
  }

  return new Date(year, month - 1, day);
}

function startOfToday() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function getDaysUntil(value?: string) {
  const date = parseDateOnly(value);

  if (!date) {
    return null;
  }

  const millisecondsPerDay = 24 * 60 * 60 * 1000;
  return Math.round(
    (date.getTime() - startOfToday().getTime()) / millisecondsPerDay
  );
}

function formatDate(value?: string) {
  const date = parseDateOnly(value);

  if (!date) {
    return "No date";
  }

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isActiveWorkflowStatus(item: AuthRequest) {
  return !["Completed", "Discharged", "No PA Required"].includes(item.status);
}

function getDatedWorkflowItems(
  data: AuthRequest[],
  workflowFilters: WorkflowFilterSettings
): DatedWorkflowItem[] {
  const items: DatedWorkflowItem[] = [];

  data.filter(isActiveWorkflowStatus).forEach((auth) => {
    const reviewDaysUntil = getDaysUntil(auth.reviewDueDate);
    const lcdDaysUntil = getDaysUntil(auth.authEndDate);
    const shouldShowReviewDue =
      workflowFilters.reviewDue &&
      reviewDaysUntil !== null &&
      reviewDaysUntil <= 7;
    const shouldShowLcd =
      workflowFilters.lcd && lcdDaysUntil !== null && lcdDaysUntil <= 7;
    const lcdMatchesReviewDue =
      Boolean(auth.reviewDueDate) && auth.reviewDueDate === auth.authEndDate;

    if (shouldShowReviewDue) {
      items.push({
        filterKey: "reviewDue",
        auth,
        label: "Review Due",
        dateLabel: formatDate(auth.reviewDueDate),
        daysUntil: reviewDaysUntil,
        tone: reviewDaysUntil < 0 ? "overdue" : "due",
      });
    }

    if (shouldShowLcd && !lcdMatchesReviewDue) {
      items.push({
        filterKey: "lcd",
        auth,
        label: "LCD",
        dateLabel: formatDate(auth.authEndDate),
        daysUntil: lcdDaysUntil,
        tone: lcdDaysUntil < 0 ? "overdue" : "due",
      });
    }
  });

  return items
    .sort((firstItem, secondItem) => firstItem.daysUntil - secondItem.daysUntil)
    .slice(0, 5);
}

function getWorkflowItems(
  data: AuthRequest[],
  datedItems: DatedWorkflowItem[],
  workflowFilters: WorkflowFilterSettings
): WorkflowStatusItem[] {
  const overdueCount = datedItems.filter((item) => item.daysUntil < 0).length;
  const dueSoonCount = datedItems.filter((item) => item.daysUntil >= 0).length;

  const pendingCount = data.filter((item) => item.status === "Pending").length;
  const p2pCount = data.filter((item) => item.status === "P2P").length;
  const appealedCount = data.filter(
    (item) => item.status === "Appealed"
  ).length;
  const deniedCount = data.filter((item) => item.status === "Denied").length;
  const approvedCount = data.filter(
    (item) => item.status === "Approved"
  ).length;

  const items: WorkflowStatusItem[] = [];

  if (workflowFilters.reviewDue || workflowFilters.lcd) {
    items.push(
      {
        label: "Overdue Items",
        count: overdueCount,
        description: "Review dates or LCDs that have already passed.",
        icon: AlertCircle,
        tone: "overdue",
      },
      {
        label: "Due Soon",
        count: dueSoonCount,
        description: "Reviews or LCDs due within the next 7 days.",
        icon: CalendarClock,
        tone: "due",
      }
    );
  }

  if (workflowFilters.pending) {
    items.push({
      label: "Pending Auths",
      count: pendingCount,
      description: "Awaiting payer response or next action.",
      icon: Clock,
      tone: "pending",
    });
  }

  if (workflowFilters.p2p) {
    items.push({
      label: "P2P Needed",
      count: p2pCount,
      description: "Peer review or escalation workflow needed.",
      icon: AlertCircle,
      tone: "p2p",
    });
  }

  if (workflowFilters.appeals) {
    items.push({
      label: "Appeals Pending",
      count: appealedCount,
      description: "Cases currently in appeal status.",
      icon: RefreshCw,
      tone: "appeal",
    });
  }

  if (workflowFilters.denied) {
    items.push({
      label: "Denied Auths",
      count: deniedCount,
      description: "Denied cases that may need follow-up.",
      icon: FileWarning,
      tone: "denied",
    });
  }

  if (workflowFilters.approved) {
    items.push({
      label: "Approved Auths",
      count: approvedCount,
      description: "Completed approvals in the selected filters.",
      icon: CheckCircle2,
      tone: "complete",
    });
  }

  return items;
}

function getToneClasses(
  tone: WorkflowStatusItem["tone"] | DatedWorkflowItem["tone"],
  darkMode: boolean
) {
  if (tone === "overdue") {
    return darkMode
      ? "border-red-900/70 bg-red-950/40 text-red-200"
      : "border-red-200 bg-red-50 text-red-700";
  }

  if (tone === "due") {
    return darkMode
      ? "border-orange-900/70 bg-orange-950/40 text-orange-200"
      : "border-orange-200 bg-orange-50 text-orange-700";
  }

  if (tone === "pending") {
    return darkMode
      ? "border-amber-900/60 bg-amber-950/30 text-amber-200"
      : "border-amber-200 bg-amber-50 text-amber-700";
  }

  if (tone === "p2p") {
    return darkMode
      ? "border-blue-900/60 bg-blue-950/30 text-blue-200"
      : "border-blue-200 bg-blue-50 text-blue-700";
  }

  if (tone === "appeal") {
    return darkMode
      ? "border-purple-900/60 bg-purple-950/30 text-purple-200"
      : "border-purple-200 bg-purple-50 text-purple-700";
  }

  if (tone === "denied") {
    return darkMode
      ? "border-red-900/60 bg-red-950/30 text-red-200"
      : "border-red-200 bg-red-50 text-red-700";
  }

  return darkMode
    ? "border-emerald-900/60 bg-emerald-950/30 text-emerald-200"
    : "border-emerald-200 bg-emerald-50 text-emerald-700";
}

export function UpcomingWorkflowCard({
  data,
  darkMode,
}: UpcomingWorkflowCardProps) {
  const [workflowFilters, setWorkflowFilters] =
    useState<WorkflowFilterSettings>(loadWorkflowFilterSettings);

  useEffect(() => {
    window.localStorage.setItem(
      WORKFLOW_FILTER_STORAGE_KEY,
      JSON.stringify(workflowFilters)
    );
  }, [workflowFilters]);

  const datedWorkflowItems = getDatedWorkflowItems(data, workflowFilters);
  const workflowItems = getWorkflowItems(
    data,
    datedWorkflowItems,
    workflowFilters
  );

  const handleToggleWorkflowFilter = (filterKey: WorkflowFilterKey) => {
    setWorkflowFilters((currentFilters) => ({
      ...currentFilters,
      [filterKey]: !currentFilters[filterKey],
    }));
  };

  const handleResetWorkflowFilters = () => {
    setWorkflowFilters(DEFAULT_WORKFLOW_FILTER_SETTINGS);
  };

  if (data.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center">
        <p
          className={cn(
            "text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          No workflow items found for the selected filters.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <details
        className={cn(
          "rounded-xl border px-4 py-3 text-sm",
          darkMode
            ? "border-gray-800 bg-gray-950/50"
            : "border-gray-200 bg-gray-50"
        )}
      >
        <summary className="cursor-pointer font-semibold">
          Filter workflow items
        </summary>

        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {(
            Object.entries(WORKFLOW_FILTER_LABELS) as [
              WorkflowFilterKey,
              string
            ][]
          ).map(([filterKey, label]) => (
            <label
              key={filterKey}
              className={cn(
                "flex cursor-pointer items-center justify-between gap-3 rounded-lg border px-3 py-2",
                darkMode
                  ? "border-gray-800 bg-gray-900 text-gray-200"
                  : "border-gray-200 bg-white text-gray-700"
              )}
            >
              <span>{label}</span>
              <input
                type="checkbox"
                checked={workflowFilters[filterKey]}
                onChange={() => handleToggleWorkflowFilter(filterKey)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </label>
          ))}
        </div>

        <button
          type="button"
          onClick={handleResetWorkflowFilters}
          className={cn(
            "mt-3 rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
            darkMode
              ? "border-gray-700 text-gray-200 hover:bg-gray-800"
              : "border-gray-300 text-gray-700 hover:bg-gray-100"
          )}
        >
          Reset workflow filters
        </button>
      </details>

      <DatedWorkflowItems
        items={datedWorkflowItems}
        darkMode={darkMode}
        getToneClasses={getToneClasses}
      />

      <WorkflowStatusItems
        items={workflowItems}
        darkMode={darkMode}
        getToneClasses={getToneClasses}
      />
    </div>
  );
}

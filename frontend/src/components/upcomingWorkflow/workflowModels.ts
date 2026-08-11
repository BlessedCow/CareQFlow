import type { LucideIcon } from "lucide-react";
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Clock,
  FileWarning,
  RefreshCw,
} from "lucide-react";

import type { AuthRequest } from "../../types/auth";

export type WorkflowFilterKey =
  | "reviewDue"
  | "lcd"
  | "pending"
  | "p2p"
  | "appeals"
  | "denied"
  | "approved";

export type WorkflowFilterSettings = Record<WorkflowFilterKey, boolean>;

export interface DatedWorkflowItem {
  filterKey: "reviewDue" | "lcd";
  auth: AuthRequest;
  label: string;
  dateLabel: string;
  daysUntil: number;
  tone: "due" | "overdue";
}

export interface WorkflowStatusItem {
  label: string;
  count: number;
  description: string;
  icon: LucideIcon;
  tone:
    | "pending"
    | "p2p"
    | "appeal"
    | "denied"
    | "complete"
    | "due"
    | "overdue";
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

export function getDatedWorkflowItems(
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

export function getWorkflowItems(
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

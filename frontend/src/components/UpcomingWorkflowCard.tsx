import { useEffect, useState } from "react";

import { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";
import { DatedWorkflowItems } from "./upcomingWorkflow/DatedWorkflowItems";

import { WorkflowStatusItems } from "./upcomingWorkflow/WorkflowStatusItems";

import { WorkflowFilterControls } from "./upcomingWorkflow/WorkflowFilterControls";

import {
  getDatedWorkflowItems,
  getWorkflowItems,
  type DatedWorkflowItem,
  type WorkflowFilterKey,
  type WorkflowFilterSettings,
  type WorkflowStatusItem,
} from "./upcomingWorkflow/workflowModels";

interface UpcomingWorkflowCardProps {
  data: AuthRequest[];
  darkMode: boolean;
}

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
      <WorkflowFilterControls
        workflowFilters={workflowFilters}
        darkMode={darkMode}
        onToggleFilter={handleToggleWorkflowFilter}
        onResetFilters={handleResetWorkflowFilters}
      />

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

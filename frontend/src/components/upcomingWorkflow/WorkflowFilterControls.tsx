import { cn } from "../../utils/cn";

import type {
    WorkflowFilterKey,
    WorkflowFilterSettings,
  } from "./workflowModels";

interface WorkflowFilterControlsProps {
  workflowFilters: WorkflowFilterSettings;
  darkMode: boolean;
  onToggleFilter: (filterKey: WorkflowFilterKey) => void;
  onResetFilters: () => void;
}

const WORKFLOW_FILTER_LABELS: Record<WorkflowFilterKey, string> = {
  reviewDue: "Review Due",
  lcd: "LCD",
  pending: "Pending Auths",
  p2p: "P2P Needed",
  appeals: "Appeals Pending",
  denied: "Denied Auths",
  approved: "Approved Auths",
};

export function WorkflowFilterControls({
  workflowFilters,
  darkMode,
  onToggleFilter,
  onResetFilters,
}: WorkflowFilterControlsProps) {
  return (
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
              onChange={() => onToggleFilter(filterKey)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
          </label>
        ))}
      </div>

      <button
        type="button"
        onClick={onResetFilters}
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
  );
}

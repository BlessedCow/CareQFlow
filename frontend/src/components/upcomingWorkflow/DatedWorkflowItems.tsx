import { cn } from "../../utils/cn";
import type { DatedWorkflowItem } from "./workflowModels";

interface DatedWorkflowItemsProps {
  items: DatedWorkflowItem[];
  darkMode: boolean;
  getToneClasses: (
    tone: DatedWorkflowItem["tone"],
    darkMode: boolean
  ) => string;
}

function getDatePhrase(daysUntil: number) {
  if (daysUntil < 0) {
    return `${Math.abs(daysUntil)} day${
      Math.abs(daysUntil) === 1 ? "" : "s"
    } overdue`;
  }

  if (daysUntil === 0) {
    return "Due today";
  }

  if (daysUntil === 1) {
    return "Due tomorrow";
  }

  return `Due in ${daysUntil} days`;
}

export function DatedWorkflowItems({
  items,
  darkMode,
  getToneClasses,
}: DatedWorkflowItemsProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p
        className={cn(
          "text-xs font-semibold uppercase tracking-wide",
          darkMode ? "text-gray-400" : "text-gray-500"
        )}
      >
        Next date-based items
      </p>

      {items.map((item) => (
        <div
          key={`${item.auth.id}-${item.filterKey}-${item.dateLabel}`}
          className={cn(
            "rounded-xl border px-4 py-3 text-sm",
            getToneClasses(item.tone, darkMode)
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold">
                {item.label}: {item.auth.patientId}
              </p>

              <p className="mt-1 text-xs opacity-80">
                {item.auth.facility} • {item.auth.loc} • {item.auth.payer}
              </p>
            </div>

            <div className="text-right">
              <p className="text-xs font-semibold">{item.dateLabel}</p>

              <p className="mt-1 text-xs opacity-80">
                {getDatePhrase(item.daysUntil)}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

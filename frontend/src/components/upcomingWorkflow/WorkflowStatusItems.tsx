import type { LucideIcon } from "lucide-react";

import { cn } from "../../utils/cn";

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

interface WorkflowStatusItemsProps {
  items: WorkflowStatusItem[];
  darkMode: boolean;
  getToneClasses: (
    tone: WorkflowStatusItem["tone"],
    darkMode: boolean
  ) => string;
}

export function WorkflowStatusItems({
  items,
  darkMode,
  getToneClasses,
}: WorkflowStatusItemsProps) {
  const hasActiveItems = items.some((item) => item.count > 0);

  return (
    <>
      <div className="space-y-3">
        {items.map((item) => {
          const Icon = item.icon;

          return (
            <div
              key={item.label}
              className={cn(
                "rounded-xl border px-4 py-3 transition-colors",
                item.count > 0
                  ? getToneClasses(item.tone, darkMode)
                  : darkMode
                  ? "border-gray-800 bg-gray-950/40 text-gray-500"
                  : "border-gray-200 bg-gray-50 text-gray-500"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <Icon className="mt-0.5 h-5 w-5 shrink-0" />

                  <div>
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="mt-1 text-xs opacity-80">
                      {item.description}
                    </p>
                  </div>
                </div>

                <span className="text-2xl font-bold leading-none">
                  {item.count}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {!hasActiveItems && (
        <p
          className={cn(
            "pt-2 text-center text-sm",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        >
          No active follow-up items in the selected workflow filters.
        </p>
      )}
    </>
  );
}

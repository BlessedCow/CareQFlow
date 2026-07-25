import { Calendar, Filter } from "lucide-react";

import { cn } from "../utils/cn";

export type WorkQueueFilter =
  | "All"
  | "Needs Action"
  | "Pending"
  | "P2P"
  | "Appealed"
  | "Denied"
  | "Approved"
  | "Partial Approvals";

  export type LocFilter =
  | "All"
  | "DTX"
  | "RTC"
  | "PHP"
  | "IOP"
  | "UNKNOWN";

interface FiltersProps {
  dateRange: "7d" | "30d" | "90d" | "all";
  setDateRange: (val: "7d" | "30d" | "90d" | "all") => void;
  selectedFacility: string;
  setSelectedFacility: (val: string) => void;
  facilities: string[];
  selectedInsurance: string;
  setSelectedInsurance: (val: string) => void;
  insurances: string[];
  selectedLoc: LocFilter;
  setSelectedLoc: (val: LocFilter) => void;
  selectedWorkQueue: WorkQueueFilter;
  setSelectedWorkQueue: (val: WorkQueueFilter) => void;
  darkMode: boolean;
  onClearFilters: () => void;
}

export default function Filters({
  dateRange,
  setDateRange,
  selectedFacility,
  setSelectedFacility,
  facilities,
  selectedInsurance,
  setSelectedInsurance,
  insurances,
  selectedLoc,
  setSelectedLoc,
  selectedWorkQueue,
  setSelectedWorkQueue,
  darkMode,
  onClearFilters,
}: FiltersProps) {
  const selectClasses = cn(
    "appearance-none rounded-lg border py-2 pl-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors",
    darkMode
      ? "bg-gray-900 border-gray-700 text-gray-200"
      : "bg-white border-gray-300 text-gray-800"
  );

  const labelClasses = cn(
    "mb-1 block text-xs font-medium",
    darkMode ? "text-gray-400" : "text-gray-600"
  );

  const hasActiveFilters =
    dateRange !== "30d" ||
    selectedFacility !== "All" ||
    selectedInsurance !== "All" ||
    selectedLoc !== "All" ||
    selectedWorkQueue !== "All";

  const filterSummary = [
    `Date: ${
      dateRange === "7d"
        ? "Last 7 Days"
        : dateRange === "90d"
        ? "Last 90 Days"
        : "Last 30 Days"
    }`,
    `Facility: ${selectedFacility}`,
    `Insurance: ${selectedInsurance}`,
    `LOC: ${selectedLoc === "All" ? "All LOCs" : selectedLoc}`,
    `Queue: ${selectedWorkQueue}`,
  ].join(" • ");

  return (
    <div
      className={cn(
        "grid gap-4 rounded-xl border p-4 shadow-sm md:grid-cols-2 xl:grid-cols-6 xl:items-end",
        darkMode ? "bg-gray-900/50 border-gray-800" : "bg-white border-gray-200"
      )}
    >
      <div className="flex items-end gap-2">
        <Calendar
          className={cn(
            "mb-2 h-5 w-5",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        />

        <div className="min-w-0 flex-1">
          <label className={labelClasses}>Date Range</label>
          <div className="relative">
            <select
              value={dateRange}
              onChange={(event) =>
                setDateRange(event.target.value as "7d" | "30d" | "90d" | "all")
              }
              className={cn(selectClasses, "w-full")}
            >
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="all">All</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
              <svg
                className="h-4 w-4 fill-current"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
              >
                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-end gap-2">
        <Filter
          className={cn(
            "mb-2 h-5 w-5",
            darkMode ? "text-gray-400" : "text-gray-500"
          )}
        />

        <div className="min-w-0 flex-1">
          <label className={labelClasses}>Facility</label>
          <div className="relative">
            <select
              value={selectedFacility}
              onChange={(event) => setSelectedFacility(event.target.value)}
              className={cn(selectClasses, "w-full")}
            >
              {facilities.map((facility) => (
                <option key={facility} value={facility}>
                  {facility}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
              <svg
                className="h-4 w-4 fill-current"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
              >
                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col">
        <label className={labelClasses}>Insurance</label>
        <div className="relative">
          <select
            value={selectedInsurance}
            onChange={(event) => setSelectedInsurance(event.target.value)}
            className={cn(selectClasses, "w-full")}
          >
            {insurances.map((insurance) => (
              <option key={insurance} value={insurance}>
                {insurance}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
            <svg
              className="h-4 w-4 fill-current"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
            >
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="flex flex-col">
        <label className={labelClasses}>Level of Care</label>
        <div className="relative">
          <select
            value={selectedLoc}
            onChange={(event) =>
              setSelectedLoc(event.target.value as LocFilter)
            }
            className={cn(selectClasses, "w-full")}
          >
            <option value="All">All LOCs</option>
            <option value="DTX">DTX</option>
            <option value="RTC">RTC</option>
            <option value="PHP">PHP</option>
            <option value="IOP">IOP</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
            <svg
              className="h-4 w-4 fill-current"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
            >
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="flex flex-col">
        <label className={labelClasses}>Work Queue</label>
        <div className="relative">
          <select
            value={selectedWorkQueue}
            onChange={(event) =>
              setSelectedWorkQueue(event.target.value as WorkQueueFilter)
            }
            className={cn(selectClasses, "w-full")}
          >
            <option value="All">All</option>
            <option value="Needs Action">Needs Action</option>
            <option value="Pending">Pending</option>
            <option value="P2P">P2P</option>
            <option value="Appealed">Appealed</option>
            <option value="Denied">Denied</option>
            <option value="Approved">Approved</option>
            <option value="Completed">Completed</option>
            <option value="Discharged">Discharged</option>
            <option value="Partial Approvals">Partial Approvals</option>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
            <svg
              className="h-4 w-4 fill-current"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
            >
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className={labelClasses}>Active Filters</label>

        <span
          className={cn(
            "text-xs leading-5",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          {filterSummary}
        </span>

        <button
          type="button"
          onClick={onClearFilters}
          disabled={!hasActiveFilters}
          className={cn(
            "w-fit rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
            darkMode
              ? "border-gray-700 text-gray-200 hover:bg-gray-800"
              : "border-gray-300 text-gray-700 hover:bg-gray-100"
          )}
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
}

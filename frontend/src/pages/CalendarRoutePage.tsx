import { CalendarPage } from "../components/CalendarPage";
import Filters, {
  type LocFilter,
  type WorkQueueFilter,
} from "../components/Filters";
import type { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";

type DateRange = "7d" | "30d" | "90d" | "all";

interface CalendarRoutePageProps {
  darkMode: boolean;
  isLoadingAuths: boolean;
  authsError: string | null;
  dateRange: DateRange;
  setDateRange: (value: DateRange) => void;
  selectedFacility: string;
  setSelectedFacility: (value: string) => void;
  facilities: string[];
  selectedInsurance: string;
  setSelectedInsurance: (value: string) => void;
  insurances: string[];
  selectedLoc: LocFilter;
  setSelectedLoc: (value: LocFilter) => void;
  selectedWorkQueue: WorkQueueFilter;
  setSelectedWorkQueue: (value: WorkQueueFilter) => void;
  onClearFilters: () => void;
  filteredData: AuthRequest[];
  onSelectAuth: (auth: AuthRequest) => void;
}

export function CalendarRoutePage({
  darkMode,
  isLoadingAuths,
  authsError,
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
  onClearFilters,
  filteredData,
  onSelectAuth,
}: CalendarRoutePageProps) {
  return (
    <>
      {isLoadingAuths && (
        <div
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-blue-900/60 bg-blue-950/30 text-blue-200"
              : "border-blue-200 bg-blue-50 text-blue-700"
          )}
        >
          Loading authorization records...
        </div>
      )}

      {authsError && (
        <div
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900/60 bg-red-950/30 text-red-200"
              : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          {authsError}
        </div>
      )}

      <Filters
        dateRange={dateRange}
        setDateRange={setDateRange}
        selectedFacility={selectedFacility}
        setSelectedFacility={setSelectedFacility}
        facilities={facilities}
        selectedInsurance={selectedInsurance}
        setSelectedInsurance={setSelectedInsurance}
        insurances={insurances}
        selectedLoc={selectedLoc}
        setSelectedLoc={setSelectedLoc}
        selectedWorkQueue={selectedWorkQueue}
        setSelectedWorkQueue={setSelectedWorkQueue}
        darkMode={darkMode}
        onClearFilters={onClearFilters}
      />

      <CalendarPage
        data={filteredData}
        darkMode={darkMode}
        onSelectAuth={onSelectAuth}
      />
    </>
  );
}

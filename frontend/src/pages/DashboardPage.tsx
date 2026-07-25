import { AuthRequest } from "../types/auth";
import { LOCChart, TrendChart } from "../components/Charts";
import { DataTable } from "../components/DataTable";
import Filters, {
  type LocFilter,
  type WorkQueueFilter,
} from "../components/Filters";
import KPICards from "../components/KPICards";
import { UpcomingWorkflowCard } from "../components/UpcomingWorkflowCard";
import type { WorkflowViewMode } from "../hooks/useWorkflowViewMode";
import { cn } from "../utils/cn";

type DateRange = "7d" | "30d" | "90d" | "all";

type DashboardCardKey =
  | "kpis"
  | "trends"
  | "levelOfCare"
  | "upcomingWorkflow"
  | "recentAuthorizations";

type DashboardCardSettings = Record<DashboardCardKey, boolean>;

interface DashboardPageProps {
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
  dashboardCardSettings: DashboardCardSettings;
  filteredData: AuthRequest[];
  comparisonFilteredData: AuthRequest[];
  comparisonPeriodLabel: string;
  onViewAuth: (auth: AuthRequest) => void;
  workflowViewMode: WorkflowViewMode;
}

export function DashboardPage({
  darkMode,
  workflowViewMode,
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
  dashboardCardSettings,
  filteredData,
  comparisonFilteredData,
  comparisonPeriodLabel,
  onViewAuth,
}: DashboardPageProps) {
  return (
    <>
      {isLoadingAuths && (
        <div
          className={cn(
            "rounded-xl border p-4 text-sm",
            darkMode
              ? "border-gray-800 bg-gray-900 text-gray-300"
              : "border-gray-200 bg-white text-gray-700"
          )}
        >
          Loading authorization records from AuthStatus...
        </div>
      )}

      {authsError && (
        <div
          className={cn(
            "rounded-xl border p-4 text-sm",
            darkMode
              ? "border-rose-900 bg-rose-950/40 text-rose-200"
              : "border-rose-200 bg-rose-50 text-rose-700"
          )}
        >
          Unable to load AuthStatus backend data: {authsError}
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

      {dashboardCardSettings.kpis && (
        <div className="space-y-2">
          <KPICards
            data={filteredData}
            comparisonData={comparisonFilteredData}
            darkMode={darkMode}
          />
          <p
            className={cn(
              "text-xs",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            {comparisonPeriodLabel}
          </p>
        </div>
      )}

      {(dashboardCardSettings.trends || dashboardCardSettings.levelOfCare) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {dashboardCardSettings.trends && (
            <div
              className={cn(
                "rounded-xl border p-5 shadow-sm lg:col-span-2",
                darkMode
                  ? "border-gray-800 bg-gray-900"
                  : "border-gray-200 bg-white"
              )}
            >
              <h3 className="mb-4 text-lg font-semibold">
                Authorization Trends
              </h3>
              <TrendChart data={filteredData} darkMode={darkMode} />
            </div>
          )}

          {dashboardCardSettings.levelOfCare && (
            <div
              className={cn(
                "rounded-xl border p-5 shadow-sm",
                darkMode
                  ? "border-gray-800 bg-gray-900"
                  : "border-gray-200 bg-white"
              )}
            >
              <h3 className="mb-4 text-lg font-semibold">
                Level of Care Breakdown
              </h3>
              <LOCChart
                data={filteredData}
                darkMode={darkMode}
                onLocDoubleClick={(loc) => {
                  const nextLoc = loc as LocFilter;
                  setSelectedLoc(selectedLoc === nextLoc ? "All" : nextLoc);
                }}
              />
            </div>
          )}
        </div>
      )}

      {(dashboardCardSettings.upcomingWorkflow ||
        dashboardCardSettings.recentAuthorizations) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {dashboardCardSettings.upcomingWorkflow && (
            <div
              className={cn(
                "rounded-xl border p-5 shadow-sm",
                darkMode
                  ? "border-gray-800 bg-gray-900"
                  : "border-gray-200 bg-white"
              )}
            >
              <h3 className="mb-1 text-lg font-semibold">Upcoming Workflow</h3>
              <p
                className={cn(
                  "mb-4 text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Due dates and status-based follow-up items for the selected
                filters.
              </p>
              <UpcomingWorkflowCard data={filteredData} darkMode={darkMode} />
            </div>
          )}

          {dashboardCardSettings.recentAuthorizations && (
            <div
              className={cn(
                "flex flex-col overflow-hidden rounded-xl border p-5 shadow-sm",
                darkMode
                  ? "border-gray-800 bg-gray-900"
                  : "border-gray-200 bg-white"
              )}
            >
              <h3 className="mb-4 shrink-0 text-lg font-semibold">
                Recent Authorizations
              </h3>
              <p
                className={cn(
                  "mb-4 text-sm",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                Select a row to view authorization details.
              </p>
              <DataTable
                data={filteredData}
                darkMode={darkMode}
                onView={onViewAuth}
                showActions={false}
                workflowViewMode={workflowViewMode}
              />
            </div>
          )}
        </div>
      )}
    </>
  );
}

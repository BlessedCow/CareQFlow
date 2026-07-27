import { useState } from "react";
import { cn } from "../utils/cn";
import type { WorkflowViewMode } from "../hooks/useWorkflowViewMode";
import { ChangePasswordCard } from "../components/security/ChangePasswordCard";
import type { RegisteredOptionCategory } from "../api/registeredOptions";

type DashboardCardKey =
  | "kpis"
  | "trends"
  | "levelOfCare"
  | "upcomingWorkflow"
  | "recentAuthorizations";

type DashboardCardSettings = Record<DashboardCardKey, boolean>;

interface WorkflowViewSettingsCardProps {
  darkMode: boolean;
  workflowViewMode: WorkflowViewMode;
  onWorkflowViewModeChange: (value: WorkflowViewMode) => void;
}

function WorkflowViewSettingsCard({
  darkMode,
  workflowViewMode,
  onWorkflowViewModeChange,
}: WorkflowViewSettingsCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5 shadow-sm",
        darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
      )}
    >
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Workflow View</h3>
        <p
          className={cn(
            "mt-1 text-sm",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          Choose how much operational detail appears in workflow tables.
        </p>
      </div>

      <div className="grid gap-3">
        {[
          {
            value: "relaxed",
            label: "Relaxed View",
            description:
              "Cleaner tables with fewer schedule and turnaround details.",
          },
          {
            value: "detailed",
            label: "Detailed View",
            description:
              "Show schedule dates, LCD cues, turnaround, and workflow metadata.",
          },
        ].map((item) => (
          <label
            key={item.value}
            className={cn(
              "flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 text-sm",
              workflowViewMode === item.value
                ? darkMode
                  ? "border-blue-700 bg-blue-950/30"
                  : "border-blue-300 bg-blue-50"
                : darkMode
                ? "border-gray-800 bg-gray-950 text-gray-200"
                : "border-gray-200 bg-gray-50 text-gray-700"
            )}
          >
            <input
              type="radio"
              name="workflowViewMode"
              value={item.value}
              checked={workflowViewMode === item.value}
              onChange={() =>
                onWorkflowViewModeChange(item.value as WorkflowViewMode)
              }
              className="mt-1 h-4 w-4 border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>
              <span className="block font-medium">{item.label}</span>
              <span
                className={cn(
                  "mt-1 block text-xs",
                  darkMode ? "text-gray-400" : "text-gray-600"
                )}
              >
                {item.description}
              </span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

const DASHBOARD_CARD_LABELS: Record<DashboardCardKey, string> = {
  kpis: "KPI Cards",
  trends: "Authorization Trends",
  levelOfCare: "Level of Care Breakdown",
  upcomingWorkflow: "Upcoming Workflow",
  recentAuthorizations: "Recent Authorizations",
};

interface RegisteredListCardProps {
  darkMode: boolean;
  category: RegisteredOptionCategory;
  title: string;
  description: string;
  placeholder: string;
  value: string;
  onValueChange: (value: string) => void;
  items: string[];
  onAdd: () => Promise<void>;
  onRemove: (value: string) => Promise<void>;
  canManage: boolean;
  isLoading: boolean;
  savingCategory: RegisteredOptionCategory | null;
  deletingOptionId: number | null;
  isProtectedOption: (
    category: RegisteredOptionCategory,
    name: string
  ) => boolean;
}

function RegisteredListCard({
  darkMode,
  category,
  title,
  description,
  placeholder,
  value,
  onValueChange,
  items,
  onAdd,
  onRemove,
  canManage,
  isLoading,
  savingCategory,
  deletingOptionId,
  isProtectedOption,
}: RegisteredListCardProps) {
  const [confirmingRemoveItem, setConfirmingRemoveItem] = useState<
    string | null
  >(null);

  const isSaving = savingCategory === category;
  const isDeleting = deletingOptionId !== null;

  return (
    <div
      className={cn(
        "rounded-xl border p-6",
        darkMode ? "border-gray-800 bg-gray-900/50" : "border-gray-200 bg-white"
      )}
    >
      <h3
        className={cn(
          "mb-2 text-lg font-semibold",
          darkMode ? "text-white" : "text-gray-900"
        )}
      >
        {title}
      </h3>

      <p
        className={cn(
          "mb-4 text-sm",
          darkMode ? "text-gray-400" : "text-gray-600"
        )}
      >
        {description}
      </p>

      {canManage && (
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            value={value}
            onChange={(event) => {
              onValueChange(event.target.value);
              setConfirmingRemoveItem(null);
            }}
            placeholder={placeholder}
            disabled={isSaving || isDeleting}
            className={cn(
              "min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60",
              darkMode
                ? "border-gray-700 bg-gray-900 text-gray-100 placeholder-gray-500"
                : "border-gray-300 bg-white text-gray-900 placeholder-gray-400"
            )}
          />

          <button
            type="button"
            disabled={isSaving || isDeleting || !value.trim()}
            onClick={() => {
              void onAdd();
              setConfirmingRemoveItem(null);
            }}
            className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? "Adding..." : "Add"}
          </button>
        </div>
      )}

      {isLoading && (
        <p
          className={cn(
            "mb-3 text-sm",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          Loading options...
        </p>
      )}

      <div className="space-y-2">
        {items.map((item) => {
          const isProtected = isProtectedOption(category, item);
          const canRemoveItem = canManage && !isProtected;

          return (
            <div
              key={item}
              className={cn(
                "flex items-center justify-between rounded-lg border px-3 py-2 text-sm",
                darkMode
                  ? "border-gray-800 bg-gray-950/60"
                  : "border-gray-200 bg-gray-50"
              )}
            >
              <span>{item}</span>

              {isProtected ? (
                <span
                  className={cn(
                    "text-xs font-medium",
                    darkMode ? "text-gray-500" : "text-gray-500"
                  )}
                >
                  Built in
                </span>
              ) : canRemoveItem ? (
                confirmingRemoveItem === item ? (
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-xs",
                        darkMode ? "text-gray-400" : "text-gray-500"
                      )}
                    >
                      Remove?
                    </span>

                    <button
                      type="button"
                      disabled={isDeleting}
                      onClick={() => {
                        void onRemove(item);
                        setConfirmingRemoveItem(null);
                      }}
                      className={cn(
                        darkMode
                          ? "text-red-400 hover:text-red-300"
                          : "text-red-600 hover:text-red-700",
                        isDeleting && "cursor-not-allowed opacity-50"
                      )}
                    >
                      Yes
                    </button>

                    <button
                      type="button"
                      disabled={isDeleting}
                      onClick={() => setConfirmingRemoveItem(null)}
                      className={cn(
                        darkMode
                          ? "text-gray-400 hover:text-gray-300"
                          : "text-gray-600 hover:text-gray-800",
                        isDeleting && "cursor-not-allowed opacity-50"
                      )}
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={() => setConfirmingRemoveItem(item)}
                    className={cn(
                      darkMode
                        ? "text-red-400 hover:text-red-300"
                        : "text-red-600 hover:text-red-700",
                      isDeleting && "cursor-not-allowed opacity-50"
                    )}
                  >
                    Remove
                  </button>
                )
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface DashboardCardsSettingsCardProps {
  darkMode: boolean;
  dashboardCardSettings: DashboardCardSettings;
  onToggleDashboardCard: (cardKey: DashboardCardKey) => void;
  onResetDashboardCards: () => void;
}

function DashboardCardsSettingsCard({
  darkMode,
  dashboardCardSettings,
  onToggleDashboardCard,
  onResetDashboardCards,
}: DashboardCardsSettingsCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5 shadow-sm",
        darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">Dashboard Cards</h3>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Choose which cards appear on the Dashboard.
          </p>
        </div>

        <button
          type="button"
          onClick={onResetDashboardCards}
          className={cn(
            "rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
            darkMode
              ? "border-gray-700 text-gray-200 hover:bg-gray-800"
              : "border-gray-300 text-gray-700 hover:bg-gray-100"
          )}
        >
          Reset
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {(
          Object.entries(DASHBOARD_CARD_LABELS) as [DashboardCardKey, string][]
        ).map(([cardKey, label]) => (
          <label
            key={cardKey}
            className={cn(
              "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm",
              darkMode
                ? "border-gray-800 bg-gray-950 text-gray-200"
                : "border-gray-200 bg-gray-50 text-gray-700"
            )}
          >
            <span className="font-medium">{label}</span>
            <input
              type="checkbox"
              checked={dashboardCardSettings[cardKey]}
              onChange={() => onToggleDashboardCard(cardKey)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
          </label>
        ))}
      </div>
    </div>
  );
}

interface SessionDisplaySettingsCardProps {
  darkMode: boolean;
  showSessionTimer: boolean;
  onShowSessionTimerChange: (value: boolean) => void;
}

function SessionDisplaySettingsCard({
  darkMode,
  showSessionTimer,
  onShowSessionTimerChange,
}: SessionDisplaySettingsCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5 shadow-sm",
        darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
      )}
    >
      <h3 className="text-lg font-semibold">Session Display</h3>

      <p
        className={cn(
          "mt-1 text-sm",
          darkMode ? "text-gray-400" : "text-gray-600"
        )}
      >
        Optionally show the remaining session time in the bottom right corner.
        Security warnings will still appear when this is hidden.
      </p>

      <label
        className={cn(
          "mt-4 flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 text-sm",
          darkMode
            ? "border-gray-800 bg-gray-950 text-gray-200"
            : "border-gray-200 bg-gray-50 text-gray-700"
        )}
      >
        <input
          type="checkbox"
          checked={showSessionTimer}
          onChange={(event) => onShowSessionTimerChange(event.target.checked)}
          className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />

        <span>
          <span className="block font-medium">Show session countdown</span>
          <span
            className={cn(
              "mt-1 block text-xs",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            This preference is off by default and stores no session or patient
            information.
          </span>
        </span>
      </label>
    </div>
  );
}

interface SettingsPageProps {
  darkMode: boolean;

  newFacilityName: string;
  setNewFacilityName: (value: string) => void;
  registeredFacilities: string[];
  onAddFacility: () => Promise<void>;
  onRemoveFacility: (value: string) => Promise<void>;

  newInsuranceName: string;
  setNewInsuranceName: (value: string) => void;
  registeredInsurances: string[];
  onAddInsurance: () => Promise<void>;
  onRemoveInsurance: (value: string) => Promise<void>;

  newWebPortalName: string;
  setNewWebPortalName: (value: string) => void;
  registeredWebPortals: string[];
  onAddWebPortal: () => Promise<void>;
  onRemoveWebPortal: (value: string) => Promise<void>;

  isLoadingRegisteredOptions: boolean;
  registeredOptionsError: string | null;
  savingCategory: RegisteredOptionCategory | null;
  deletingOptionId: number | null;
  isProtectedOption: (
    category: RegisteredOptionCategory,
    name: string
  ) => boolean;
  canManageRegisteredOptions: boolean;

  dashboardCardSettings: DashboardCardSettings;
  onToggleDashboardCard: (cardKey: DashboardCardKey) => void;
  onResetDashboardCards: () => void;

  workflowViewMode: WorkflowViewMode;
  onWorkflowViewModeChange: (value: WorkflowViewMode) => void;

  showSessionTimer: boolean;
  onShowSessionTimerChange: (value: boolean) => void;

  onPasswordChanged: () => void;
}

export function SettingsPage({
  darkMode,
  newFacilityName,
  setNewFacilityName,
  registeredFacilities,
  onAddFacility,
  onRemoveFacility,
  newInsuranceName,
  setNewInsuranceName,
  registeredInsurances,
  onAddInsurance,
  onRemoveInsurance,
  newWebPortalName,
  setNewWebPortalName,
  registeredWebPortals,
  onAddWebPortal,
  onRemoveWebPortal,
  isLoadingRegisteredOptions,
  registeredOptionsError,
  savingCategory,
  deletingOptionId,
  isProtectedOption,
  canManageRegisteredOptions,
  dashboardCardSettings,
  onToggleDashboardCard,
  onResetDashboardCards,
  workflowViewMode,
  onWorkflowViewModeChange,
  showSessionTimer,
  onShowSessionTimerChange,
  onPasswordChanged,
}: SettingsPageProps) {
  const [isPasswordChangeOpen, setIsPasswordChangeOpen] = useState(false);

  return (
    <div className="space-y-6">
      {registeredOptionsError && (
        <div
          role="alert"
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            darkMode
              ? "border-red-900/60 bg-red-950/40 text-red-200"
              : "border-red-200 bg-red-50 text-red-700"
          )}
        >
          {registeredOptionsError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <RegisteredListCard
          darkMode={darkMode}
          category="facility"
          title="Registered Facilities"
          description="Facilities available when creating authorization records."
          placeholder="Add facility"
          value={newFacilityName}
          onValueChange={setNewFacilityName}
          items={registeredFacilities}
          onAdd={onAddFacility}
          onRemove={onRemoveFacility}
          canManage={canManageRegisteredOptions}
          isLoading={isLoadingRegisteredOptions}
          savingCategory={savingCategory}
          deletingOptionId={deletingOptionId}
          isProtectedOption={isProtectedOption}
        />

        <RegisteredListCard
          darkMode={darkMode}
          category="insurance"
          title="Registered Insurances"
          description="Insurance options available when creating authorization records."
          placeholder="Add insurance"
          value={newInsuranceName}
          onValueChange={setNewInsuranceName}
          items={registeredInsurances}
          onAdd={onAddInsurance}
          onRemove={onRemoveInsurance}
          canManage={canManageRegisteredOptions}
          isLoading={isLoadingRegisteredOptions}
          savingCategory={savingCategory}
          deletingOptionId={deletingOptionId}
          isProtectedOption={isProtectedOption}
        />

        <div className="space-y-6">
          <RegisteredListCard
            darkMode={darkMode}
            category="web_portal"
            title="Web Portals"
            description="Portal options available for web portal submissions."
            placeholder="Add portal"
            value={newWebPortalName}
            onValueChange={setNewWebPortalName}
            items={registeredWebPortals}
            onAdd={onAddWebPortal}
            onRemove={onRemoveWebPortal}
            canManage={canManageRegisteredOptions}
            isLoading={isLoadingRegisteredOptions}
            savingCategory={savingCategory}
            deletingOptionId={deletingOptionId}
            isProtectedOption={isProtectedOption}
          />

          <WorkflowViewSettingsCard
            darkMode={darkMode}
            workflowViewMode={workflowViewMode}
            onWorkflowViewModeChange={onWorkflowViewModeChange}
          />

          <SessionDisplaySettingsCard
            darkMode={darkMode}
            showSessionTimer={showSessionTimer}
            onShowSessionTimerChange={onShowSessionTimerChange}
          />

          <DashboardCardsSettingsCard
            darkMode={darkMode}
            dashboardCardSettings={dashboardCardSettings}
            onToggleDashboardCard={onToggleDashboardCard}
            onResetDashboardCards={onResetDashboardCards}
          />
        </div>
      </div>

      <section
        className={cn(
          "rounded-xl border shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <button
          type="button"
          onClick={() =>
            setIsPasswordChangeOpen((currentValue) => !currentValue)
          }
          aria-expanded={isPasswordChangeOpen}
          className={cn(
            "flex w-full items-center justify-between gap-4 rounded-xl px-5 py-4 text-left transition-colors",
            darkMode ? "hover:bg-gray-800/70" : "hover:bg-gray-50"
          )}
        >
          <div>
            <h2 className="font-semibold">Account Security</h2>
            <p
              className={cn(
                "mt-1 text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              Change your CareQueue password and sign out of active sessions.
            </p>
          </div>

          <span
            className={cn(
              "shrink-0 text-sm font-medium",
              darkMode ? "text-blue-400" : "text-blue-600"
            )}
          >
            {isPasswordChangeOpen ? "Hide" : "Change password"}
          </span>
        </button>

        {isPasswordChangeOpen && (
          <div
            className={cn(
              "border-t p-5",
              darkMode ? "border-gray-800" : "border-gray-200"
            )}
          >
            <ChangePasswordCard
              darkMode={darkMode}
              onPasswordChanged={onPasswordChanged}
            />
          </div>
        )}
      </section>
    </div>
  );
}

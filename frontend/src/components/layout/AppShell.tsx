import {
  Activity,
  AlertTriangle,
  Bell,
  CalendarDays,
  FileText,
  LayoutDashboard,
  LogOut,
  Moon,
  ScrollText,
  ServerCog,
  Settings,
  Sun,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import type { AppPage } from "../../types/navigation";
import { cn } from "../../utils/cn";
import type { CurrentUser } from "../../api/security";

interface AppShellProps {
  activePage: AppPage;
  darkMode: boolean;
  currentUser: CurrentUser;
  canManageUsers: boolean;
  children: ReactNode;
  onPageChange: (page: AppPage) => void;
  onToggleDarkMode: () => void;
  onLogout: () => void;
}

const navigationItems: {
  page: AppPage;
  label: string;
  icon: typeof LayoutDashboard;
}[] = [
  {
    page: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    page: "authorizations",
    label: "Authorizations",
    icon: FileText,
  },
  {
    page: "denials-pipeline",
    label: "Denials / P2P / Retro",
    icon: AlertTriangle,
  },
  {
    page: "calendar",
    label: "Calendar",
    icon: CalendarDays,
  },
  {
    page: "settings",
    label: "Settings",
    icon: Settings,
  },
];

const adminNavigationItems: {
  page: AppPage;
  label: string;
  icon: typeof LayoutDashboard;
}[] = [
  {
    page: "adminUsers",
    label: "Users",
    icon: Users,
  },
  {
    page: "adminAudit",
    label: "Audit Log",
    icon: ScrollText,
  },
  {
    page: "adminSystem",
    label: "System",
    icon: ServerCog,
  },
];

const PAGE_TITLES: Record<AppPage, string> = {
  dashboard: "Dashboard",
  authorizations: "Authorizations",
  "denials-pipeline": "Denials / P2P / Retro",
  calendar: "Calendar",
  settings: "Settings",
  adminUsers: "Users",
  adminAudit: "Audit Log",
  adminSystem: "System",
};

const PAGE_DESCRIPTIONS: Record<AppPage, string> = {
  dashboard: "Authorization performance and workload overview",
  authorizations: "View and manage authorization records",
  "denials-pipeline":
    "Track denials, peer reviews, appeals, and retro auth follow-up",
  calendar: "Track review dates and LCDs",
  settings: "Configure CareQueue preferences",
  adminUsers: "Manage local CareQueue users and roles",
  adminAudit: "Review recorded security and workflow activity",
  adminSystem: "Monitor health and manage encrypted restore points",
};

export function AppShell({
  activePage,
  darkMode,
  currentUser,
  canManageUsers,
  children,
  onPageChange,
  onToggleDarkMode,
  onLogout,
}: AppShellProps) {
  const userInitials = currentUser.username.slice(0, 2).toUpperCase();
  return (
    <div
      className={cn(
        "flex min-h-screen font-sans",
        darkMode ? "dark bg-gray-900 text-gray-100" : "bg-gray-50 text-gray-900"
      )}
    >
      <aside
        className={cn(
          "hidden w-64 flex-col border-r md:flex",
          darkMode ? "border-gray-800 bg-gray-950" : "border-gray-200 bg-white"
        )}
      >
        <div className="flex h-16 items-center border-b border-inherit px-6">
          <Activity className="mr-2 h-6 w-6 text-blue-500" />
          <span className="text-lg font-bold tracking-wide">CareQueue</span>
        </div>
        <nav className="flex-1 space-y-2 px-4 py-6">
          {[
            ...navigationItems,
            ...(canManageUsers ? adminNavigationItems : []),
          ].map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.page;

            return (
              <button
                key={item.page}
                type="button"
                data-walkthrough={`nav-${item.page}`}
                onClick={() => onPageChange(item.page)}
                className={cn(
                  "flex w-full items-center rounded-lg px-3 py-2 text-left transition-colors",
                  isActive
                    ? darkMode
                      ? "bg-blue-900/20 text-blue-400"
                      : "bg-blue-50 text-blue-600"
                    : darkMode
                    ? "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )}
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-inherit p-4">
          <button
            type="button"
            onClick={onLogout}
            className={cn(
              "flex w-full items-center rounded-lg px-3 py-2 text-left transition-colors",
              darkMode
                ? "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            )}
          >
            <LogOut className="mr-3 h-5 w-5" />
            Logout
          </button>
        </div>
      </aside>

      <main className="flex h-screen flex-1 flex-col overflow-hidden">
        <header
          className={cn(
            "flex h-16 shrink-0 items-center justify-between border-b px-6",
            darkMode
              ? "border-gray-800 bg-gray-950"
              : "border-gray-200 bg-white"
          )}
        >
          <div className="flex items-center md:hidden">
            <Activity className="mr-2 h-6 w-6 text-blue-500" />
            <span className="text-lg font-bold tracking-wide">CareQueue</span>
          </div>

          <div className="hidden md:block">
            <h1 className="text-xl font-semibold">{PAGE_TITLES[activePage]}</h1>
            <p
              className={cn(
                "text-sm",
                darkMode ? "text-gray-400" : "text-gray-600"
              )}
            >
              {PAGE_DESCRIPTIONS[activePage]}
            </p>
          </div>

          <div className="flex items-center space-x-4">
            <button
              type="button"
              className={cn(
                "rounded-full p-2 transition-colors",
                darkMode
                  ? "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <Bell className="h-5 w-5" />
            </button>

            <button
              type="button"
              data-walkthrough="theme-toggle"
              aria-label={
                darkMode ? "Switch to light mode" : "Switch to dark mode"
              }
              onClick={onToggleDarkMode}
              className={cn(
                "rounded-full p-2 transition-colors",
                darkMode
                  ? "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              {darkMode ? (
                <Sun className="h-5 w-5" />
              ) : (
                <Moon className="h-5 w-5" />
              )}
            </button>

            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-sm font-semibold text-white"
              title={`${currentUser.username} (${currentUser.role})`}
            >
              {userInitials}
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-7xl space-y-6">{children}</div>
        </div>
      </main>
    </div>
  );
}

import type { AuthRequest } from "../../types/auth";
import { cn } from "../../utils/cn";

interface SelectedAuthorizationBannerProps {
  selectedAuth: AuthRequest;
  darkMode: boolean;
}

export function SelectedAuthorizationBanner({
  selectedAuth,
  darkMode,
}: SelectedAuthorizationBannerProps) {
  return (
    <div
      className={cn(
        "mb-6 rounded-xl border p-4",
        darkMode
          ? "border-amber-800 bg-amber-950/30"
          : "border-amber-200 bg-amber-50"
      )}
    >
      <div className="text-sm font-semibold">Selected authorization</div>

      <div
        className={cn(
          "mt-1 text-sm",
          darkMode ? "text-amber-100" : "text-amber-800"
        )}
      >
        {selectedAuth.patientId} • {selectedAuth.facility} •{" "}
        {selectedAuth.payer} • {selectedAuth.loc}
      </div>

      <p
        className={cn(
          "mt-2 text-xs",
          darkMode ? "text-amber-200/80" : "text-amber-700"
        )}
      >
        Update denial, P2P, appeal, or retro auth details for this authorization.
      </p>
    </div>
  );
}
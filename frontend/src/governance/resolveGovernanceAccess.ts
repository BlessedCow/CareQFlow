import type { CurrentUser } from "../api/security";
import type { GovernanceStatus } from "../api/governance";

export type GovernanceAccessState =
  | "unauthenticated"
  | "password_change_required"
  | "loading"
  | "error"
  | "attestation_required"
  | "ready";

interface ResolveGovernanceAccessInput {
  currentUser: CurrentUser | null;
  governanceStatus: GovernanceStatus | null;
  governanceError: string | null;
  isCheckingSession: boolean;
}

export function resolveGovernanceAccess({
  currentUser,
  governanceStatus,
  governanceError,
  isCheckingSession,
}: ResolveGovernanceAccessInput): GovernanceAccessState {
  if (isCheckingSession) {
    return "loading";
  }

  if (!currentUser) {
    return "unauthenticated";
  }

  if (currentUser.must_change_password) {
    return "password_change_required";
  }

  if (governanceError) {
    return "error";
  }

  if (!governanceStatus) {
    return "loading";
  }

  if (!governanceStatus.current) {
    return "attestation_required";
  }

  return "ready";
}

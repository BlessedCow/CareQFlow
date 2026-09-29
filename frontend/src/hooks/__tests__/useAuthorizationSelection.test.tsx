import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AuthRequest } from "../../types/auth";
import { useAuthorizationSelection } from "../useAuthorizationSelection";

function createHook() {
  const resetNewAuthForm = vi.fn();
  const loadAuthIntoForm = vi.fn();
  const loadLocChangeAuthForm = vi.fn();
  const resetTimelineEventForm = vi.fn();
  const clearAuthEvents = vi.fn();
  const loadAuthEvents = vi.fn().mockResolvedValue(undefined);

  const hook = renderHook(() =>
    useAuthorizationSelection({
      resetNewAuthForm,
      loadAuthIntoForm,
      loadLocChangeAuthForm,
      resetTimelineEventForm,
      clearAuthEvents,
      loadAuthEvents,
    })
  );

  return {
    ...hook,
    resetNewAuthForm,
    resetTimelineEventForm,
    clearAuthEvents,
  };
}

describe("useAuthorizationSelection", () => {
  it("clears patient-specific selection state", async () => {
    const {
      result,
      resetNewAuthForm,
      resetTimelineEventForm,
      clearAuthEvents,
    } = createHook();

    const auth = {
      id: "auth-1",
      patientId: "Sensitive Patient",
    } as AuthRequest;

    await act(async () => {
      await result.current.handleStartViewAuth(auth);
    });

    expect(result.current.viewingAuth).toBe(auth);

    act(() => {
      result.current.clearAuthorizationSelection();
    });

    expect(result.current.viewingAuth).toBeNull();
    expect(result.current.editingAuthId).toBeNull();
    expect(result.current.showAddAuthForm).toBe(false);
    expect(resetNewAuthForm).toHaveBeenCalled();
    expect(resetTimelineEventForm).toHaveBeenCalled();
    expect(clearAuthEvents).toHaveBeenCalled();
  });

  it("clears an authorization being edited", async () => {
    const { result } = createHook();

    const auth = {
      id: "auth-1",
      patientId: "Sensitive Patient",
    } as AuthRequest;

    await act(async () => {
      await result.current.handleStartEditAuth(auth);
    });

    expect(result.current.editingAuthId).toBe("auth-1");
    expect(result.current.showAddAuthForm).toBe(true);

    act(() => {
      result.current.clearAuthorizationSelection();
    });

    expect(result.current.editingAuthId).toBeNull();
    expect(result.current.viewingAuth).toBeNull();
    expect(result.current.showAddAuthForm).toBe(false);
  });
});

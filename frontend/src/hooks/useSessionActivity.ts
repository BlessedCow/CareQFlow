import { useEffect, useRef } from "react";

import { recordSessionActivity } from "../api/security";

const ACTIVITY_THROTTLE_MS = 60_000;

export function useSessionActivity(enabled: boolean): void {
  const lastRecordedAtRef = useRef(0);
  const requestInFlightRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      lastRecordedAtRef.current = 0;
      requestInFlightRef.current = false;
      return;
    }

    const handleActivity = () => {
      const now = Date.now();

      if (
        requestInFlightRef.current ||
        now - lastRecordedAtRef.current < ACTIVITY_THROTTLE_MS
      ) {
        return;
      }

      lastRecordedAtRef.current = now;
      requestInFlightRef.current = true;

      void recordSessionActivity()
        .catch(() => {
          // The existing session timeout flow remains authoritative.
        })
        .finally(() => {
          requestInFlightRef.current = false;
        });
    };

    window.addEventListener("keydown", handleActivity);
    window.addEventListener("pointerdown", handleActivity);
    window.addEventListener("wheel", handleActivity, {
      passive: true,
    });

    return () => {
      window.removeEventListener("keydown", handleActivity);
      window.removeEventListener("pointerdown", handleActivity);
      window.removeEventListener("wheel", handleActivity);
    };
  }, [enabled]);
}

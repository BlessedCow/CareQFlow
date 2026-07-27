import { useEffect, useState } from "react";

const SESSION_TIMER_STORAGE_KEY = "carequeue.showSessionTimer";

export function useSessionTimerPreference() {
  const [showSessionTimer, setShowSessionTimer] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.localStorage.getItem(SESSION_TIMER_STORAGE_KEY) === "true";
  });

  useEffect(() => {
    window.localStorage.setItem(
      SESSION_TIMER_STORAGE_KEY,
      String(showSessionTimer)
    );
  }, [showSessionTimer]);

  return {
    showSessionTimer,
    setShowSessionTimer,
  };
}

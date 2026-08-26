import { useEffect, useState } from "react";

const THEME_STORAGE_KEY = "carequeue.darkMode";

function loadDarkModePreference(): boolean {
  try {
    const storedValue = window.localStorage.getItem(THEME_STORAGE_KEY);

    if (storedValue === "true") {
      return true;
    }

    if (storedValue === "false") {
      return false;
    }

    return true;
  } catch {
    return true;
  }
}

export function useThemePreference() {
  const [darkMode, setDarkMode] = useState(loadDarkModePreference);

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, String(darkMode));
    } catch {
      // Theme preference persistence is best effort.
    }
  }, [darkMode]);

  return {
    darkMode,
    setDarkMode,
  };
}
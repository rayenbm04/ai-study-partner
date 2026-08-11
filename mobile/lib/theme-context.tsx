/**
 * Light/dark mode. Defaults to the device scheme, but a manual choice made
 * in Settings overrides it and persists (same storage module as auth
 * tokens — this is a plain preference, not a credential, but SecureStore
 * works fine for a single short string and it's already wired for
 * web/native).
 */
import { colorScheme as nativewindColorScheme } from "nativewind";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useColorScheme } from "react-native";

import { darkColors, lightColors, type ColorScheme } from "../constants/theme";
import { storage } from "./storage";

const THEME_PREFERENCE_KEY = "theme_preference";

type ThemePreference = "system" | "light" | "dark";

type ThemeContextValue = {
  colors: ColorScheme;
  isDark: boolean;
  preference: ThemePreference;
  setDark: (dark: boolean) => void;
  useSystemTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [preference, setPreference] = useState<ThemePreference>("system");

  useEffect(() => {
    storage.getItem(THEME_PREFERENCE_KEY).then((stored) => {
      if (stored === "light" || stored === "dark") setPreference(stored);
    });
  }, []);

  const isDark = preference === "system" ? systemScheme === "dark" : preference === "dark";

  // Mirrors isDark into NativeWind's own colorScheme so RNR components
  // (styled with Tailwind `dark:` classes, not this context) stay in sync
  // with the same preference — old and new UI kits share one dark-mode
  // source of truth during the migration off the old kit.
  useEffect(() => {
    nativewindColorScheme.set(isDark ? "dark" : "light");
  }, [isDark]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      colors: isDark ? darkColors : lightColors,
      isDark,
      preference,
      setDark: (dark: boolean) => {
        const next: ThemePreference = dark ? "dark" : "light";
        setPreference(next);
        storage.setItem(THEME_PREFERENCE_KEY, next);
      },
      useSystemTheme: () => {
        setPreference("system");
        storage.deleteItem(THEME_PREFERENCE_KEY);
      },
    }),
    [isDark, preference]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme() must be used within a ThemeProvider");
  return ctx;
}

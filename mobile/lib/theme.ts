import { DarkTheme, DefaultTheme, type Theme } from "@react-navigation/native";

// Mirrors frontend/app/globals.css (mauve/base-nova shadcn preset) —
// converted from OKLCH to HSL via scripts/oklch-to-hsl.mjs so mobile and
// web share one palette. Keep the two in sync by hand; there's no shared
// theme source between the Expo and Next.js apps yet.
export const THEME = {
  light: {
    background: "hsl(0 0% 100%)",
    foreground: "hsl(0 0% 3.9%)",
    card: "hsl(0 0% 100%)",
    cardForeground: "hsl(0 0% 3.9%)",
    popover: "hsl(0 0% 100%)",
    popoverForeground: "hsl(0 0% 3.9%)",
    primary: "hsl(24.7 100% 36.7%)",
    primaryForeground: "hsl(48 100% 96.1%)",
    secondary: "hsl(0 0% 96.1%)",
    secondaryForeground: "hsl(0 0% 9%)",
    muted: "hsl(0 0% 96.1%)",
    mutedForeground: "hsl(0 0% 45.1%)",
    accent: "hsl(0 0% 96.1%)",
    accentForeground: "hsl(0 0% 9%)",
    destructive: "hsl(357.1 100% 45.3%)",
    border: "hsl(0 0% 89.8%)",
    input: "hsl(0 0% 89.8%)",
    ring: "hsl(0 0% 63.1%)",
    radius: "0.875rem",
    chart1: "hsl(47 100% 59.4%)",
    chart2: "hsl(36.4 100% 49.8%)",
    chart3: "hsl(30.1 100% 44.1%)",
    chart4: "hsl(24.7 100% 36.7%)",
    chart5: "hsl(23.8 100% 29.6%)",
  },
  dark: {
    background: "hsl(0 0% 3.9%)",
    foreground: "hsl(0 0% 98%)",
    card: "hsl(0 0% 9%)",
    cardForeground: "hsl(0 0% 98%)",
    popover: "hsl(0 0% 9%)",
    popoverForeground: "hsl(0 0% 98%)",
    primary: "hsl(23.8 100% 29.6%)",
    primaryForeground: "hsl(48 100% 96.1%)",
    secondary: "hsl(0 0% 14.9%)",
    secondaryForeground: "hsl(0 0% 98%)",
    muted: "hsl(0 0% 14.9%)",
    mutedForeground: "hsl(0 0% 63.1%)",
    accent: "hsl(0 0% 14.9%)",
    accentForeground: "hsl(0 0% 98%)",
    destructive: "hsl(358.8 100% 69.6%)",
    border: "hsl(0 0% 13.5%)",
    input: "hsl(0 0% 18.3%)",
    ring: "hsl(0 0% 45.1%)",
    radius: "0.875rem",
    chart1: "hsl(47 100% 59.4%)",
    chart2: "hsl(36.4 100% 49.8%)",
    chart3: "hsl(30.1 100% 44.1%)",
    chart4: "hsl(24.7 100% 36.7%)",
    chart5: "hsl(23.8 100% 29.6%)",
  },
};

export const NAV_THEME: Record<"light" | "dark", Theme> = {
  light: {
    ...DefaultTheme,
    colors: {
      background: THEME.light.background,
      border: THEME.light.border,
      card: THEME.light.card,
      notification: THEME.light.destructive,
      primary: THEME.light.primary,
      text: THEME.light.foreground,
    },
  },
  dark: {
    ...DarkTheme,
    colors: {
      background: THEME.dark.background,
      border: THEME.dark.border,
      card: THEME.dark.card,
      notification: THEME.dark.destructive,
      primary: THEME.dark.primary,
      text: THEME.dark.foreground,
    },
  },
};

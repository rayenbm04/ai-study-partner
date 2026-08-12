import { DarkTheme, DefaultTheme, type Theme } from "@react-navigation/native";

// Mirrors frontend/app/globals.css (mauve/base-nova shadcn preset) —
// converted from OKLCH to HSL via scripts/oklch-to-hsl.mjs so mobile and
// web share one palette. Keep the two in sync by hand; there's no shared
// theme source between the Expo and Next.js apps yet.
export const THEME = {
  light: {
    background: "hsl(0 0% 100%)",
    foreground: "hsl(300 14.3% 4.1%)",
    card: "hsl(0 0% 100%)",
    cardForeground: "hsl(300 14.3% 4.1%)",
    popover: "hsl(0 0% 100%)",
    popoverForeground: "hsl(300 14.3% 4.1%)",
    primary: "hsl(24.7 100% 36.7%)",
    primaryForeground: "hsl(48 100% 96.1%)",
    secondary: "hsl(240 4.8% 95.9%)",
    secondaryForeground: "hsl(240 5.9% 10%)",
    muted: "hsl(300 7.7% 94.9%)",
    mutedForeground: "hsl(293.3 7.9% 44.7%)",
    accent: "hsl(300 7.7% 94.9%)",
    accentForeground: "hsl(292.5 15.4% 10.2%)",
    destructive: "hsl(357.1 100% 45.3%)",
    border: "hsl(300 5.9% 90%)",
    input: "hsl(300 5.9% 90%)",
    ring: "hsl(294.5 6% 64.1%)",
    radius: "0.875rem",
    chart1: "hsl(47 100% 59.4%)",
    chart2: "hsl(36.4 100% 49.8%)",
    chart3: "hsl(30.1 100% 44.1%)",
    chart4: "hsl(24.7 100% 36.7%)",
    chart5: "hsl(23.8 100% 29.6%)",
  },
  dark: {
    background: "hsl(300 14.3% 4.1%)",
    foreground: "hsl(0 0% 98%)",
    card: "hsl(292.5 15.4% 10.2%)",
    cardForeground: "hsl(0 0% 98%)",
    popover: "hsl(292.5 15.4% 10.2%)",
    popoverForeground: "hsl(0 0% 98%)",
    primary: "hsl(23.8 100% 29.6%)",
    primaryForeground: "hsl(48 100% 96.1%)",
    secondary: "hsl(240 3.7% 15.9%)",
    secondaryForeground: "hsl(0 0% 98%)",
    muted: "hsl(289.1 14.3% 15.1%)",
    mutedForeground: "hsl(294.5 6% 64.1%)",
    accent: "hsl(289.1 14.3% 15.1%)",
    accentForeground: "hsl(0 0% 98%)",
    destructive: "hsl(358.8 100% 69.6%)",
    border: "hsl(300 3.9% 13.7%)",
    input: "hsl(300 2.7% 18.5%)",
    ring: "hsl(293.3 7.9% 44.7%)",
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

/**
 * Design tokens for AI Study Coach — "Organic" system.
 *
 * Warm cream/ink palette, terracotta-amber accent, olive-sage for success
 * states. Caprasimo (display serif) for headings/big numbers, Figtree for
 * everything else. Pill-shaped buttons/inputs, large soft-shadowed cards —
 * no hard borders, ombres diffuses instead (see the design import this was
 * pulled from). Light and dark palettes share the same key shape so
 * ThemeContext (lib/theme-context.tsx) can switch between them at runtime.
 */

export type ColorScheme = { [K in keyof typeof lightColors]: string };

export const lightColors = {
  background: "#F8F3EA",
  backgroundAlt: "#F4EFE5",
  surface: "#FFFFFF",
  surfaceAlt: "#F4EFE5",

  border: "#EFE6D6",
  borderStrong: "#DCD2C0",

  textPrimary: "#201E1D",
  textSecondary: "#5F584D",
  textMuted: "#8A8172",
  textOnPrimary: "#FFFFFF",
  textOnAccent: "#201E1D",

  // Primary — near-ink CTA pill, matching the mockup's main call-to-action
  // buttons (never the amber accent, which stays a highlight color).
  primary: "#201E1D",
  primaryDark: "#000000",
  primaryLight: "#FDF0DA",

  // Accent — warm amber. Streaks, due-today badges, progress rings,
  // selection outlines, the chat FAB.
  accent: "#E0982B",
  accentDark: "#A66A14",
  accentLight: "#FDF0DA",

  // Secondary accent — olive sage, used for "mastered"/correct states.
  sage: "#7A8A5E",
  sageDark: "#4E5C36",
  sageLight: "#E9EDE0",

  success: "#7A8A5E",
  successLight: "#E9EDE0",
  error: "#C0553F",
  errorLight: "#F9E7E1",
  warning: "#A66A14",

  shadow: "rgba(32,30,29,0.08)",
  shadowStrong: "rgba(32,30,29,0.18)",
  overlay: "rgba(20,18,17,0.44)",
  cardBack: "#201E1D",
  cardBackText: "#F8F3EA",
} as const;

export const darkColors: ColorScheme = {
  background: "#151311",
  backgroundAlt: "#1B1815",
  surface: "#221F1C",
  surfaceAlt: "#2B2723",

  border: "#332E28",
  borderStrong: "#443D34",

  textPrimary: "#F4EEE3",
  textSecondary: "#BEB4A5",
  textMuted: "#8E8578",
  textOnPrimary: "#1B1815",
  textOnAccent: "#1B1815",

  primary: "#E0982B",
  primaryDark: "#C67139",
  primaryLight: "#3A2C18",

  accent: "#E0982B",
  accentDark: "#EBB765",
  accentLight: "#3A2C18",

  sage: "#9FB182",
  sageDark: "#B4C595",
  sageLight: "#2A3124",

  success: "#8FA36C",
  successLight: "#25301E",
  error: "#E08A72",
  errorLight: "#3A211B",
  warning: "#EBB765",

  shadow: "rgba(0,0,0,0.45)",
  shadowStrong: "rgba(0,0,0,0.6)",
  overlay: "rgba(10,9,8,0.6)",
  cardBack: "#E0982B",
  cardBackText: "#1B1815",
} as const;

// Kept for any code that still imports the static default (light) palette
// directly instead of useTheme(). Prefer useTheme() in components.
export const colors = lightColors;

export const fontSizes = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 18,
  xl: 22,
  xxl: 28,
  display: 34,
  hero: 42,
} as const;

export const fontWeights = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

// Figtree (body) + Caprasimo (display serif) are loaded via
// @expo-google-fonts/* in app/_layout.tsx; these are the family names those
// packages register.
export const fontFamilies = {
  regular: "Figtree_400Regular",
  medium: "Figtree_500Medium",
  semibold: "Figtree_600SemiBold",
  bold: "Figtree_700Bold",
  display: "Caprasimo_400Regular",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const radii = {
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  full: 999,
} as const;

/** Soft, ink-tinted shadow — pass the active scheme's `shadow`/`shadowStrong`. */
export function cardShadow(color: string) {
  return {
    shadowColor: color,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 20,
    elevation: 4,
  } as const;
}

// Legacy export kept for anything not yet migrated to useTheme().
export const shadows = {
  card: cardShadow(lightColors.shadow),
} as const;

/**
 * Design tokens for AI Study Coach.
 *
 * Palette direction (from design review): warm beige/white backgrounds,
 * violet as the primary interactive color, amber as the accent/highlight
 * color (due-today badges, streaks, "top pick" style callouts). Deliberately
 * no mascot/illustration system yet — icons only for now (see
 * docs/DESIGN.md in this folder... actually see the mobile README).
 *
 * Single font family (Inter) throughout, per the "modern sans-serif only"
 * decision — no serif/display font to load or keep visually consistent
 * across screen sizes.
 */

export const colors = {
  // Backgrounds — warm, not pure white/gray, per "beige-white" direction.
  background: "#FAF6EF",
  backgroundAlt: "#F3ECDF", // slightly deeper beige, for section backgrounds
  surface: "#FFFFFF", // cards, sheets, inputs — sits on top of background
  surfaceAlt: "#F6F1E7", // subtle card variant when a card sits on `surface`

  border: "#E7DECD",
  borderStrong: "#D8CBB2",

  // Text
  textPrimary: "#241F19",
  textSecondary: "#6E6558",
  textMuted: "#9C9284",
  textOnPrimary: "#FFFFFF",
  textOnAccent: "#241F19", // amber is light enough to need dark text on top

  // Primary — violet. Used for primary buttons, links, active tab, selection.
  primary: "#6E4FE8",
  primaryDark: "#5B3FD1", // pressed state
  primaryLight: "#EFE9FD", // selected-row background, subtle highlight fill

  // Accent — amber. Used for badges, streaks, "due today," highlights —
  // never for a primary CTA, so it stays a highlight color, not a second
  // primary competing with violet.
  accent: "#F2A93B",
  accentDark: "#D98F1F",
  accentLight: "#FBEBD1",

  // Semantic — kept muted/warm so they sit next to amber+violet without
  // clashing (avoid saturated stock green/red).
  success: "#4C9A6A",
  successLight: "#E4F2E8",
  error: "#D9614C",
  errorLight: "#FBE7E3",
  warning: "#D98F1F",
} as const;

export const fontSizes = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 18,
  xl: 22,
  xxl: 28,
  display: 34,
} as const;

export const fontWeights = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

// Inter is loaded via @expo-google-fonts/inter in app/_layout.tsx; these are
// the family names that package registers.
export const fontFamilies = {
  regular: "Inter_400Regular",
  medium: "Inter_500Medium",
  semibold: "Inter_600SemiBold",
  bold: "Inter_700Bold",
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
  md: 12,
  lg: 16,
  xl: 24,
  full: 999,
} as const;

export const shadows = {
  card: {
    shadowColor: "#241F19",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
} as const;

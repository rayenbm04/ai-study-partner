import { Text as RNText, type TextProps } from "react-native";

import { fontFamilies, fontSizes } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";

type Variant = "hero" | "display" | "title" | "subtitle" | "body" | "label" | "caption";

const VARIANT_BASE: Record<Variant, { fontSize: number; lineHeight: number; fontFamily: string; tone: "primary" | "secondary" | "muted" }> = {
  hero: { fontSize: fontSizes.hero, lineHeight: fontSizes.hero * 1.15, fontFamily: fontFamilies.display, tone: "primary" },
  display: { fontSize: fontSizes.display, lineHeight: fontSizes.display * 1.15, fontFamily: fontFamilies.display, tone: "primary" },
  title: { fontSize: fontSizes.xl, lineHeight: fontSizes.xl * 1.25, fontFamily: fontFamilies.semibold, tone: "primary" },
  subtitle: { fontSize: fontSizes.lg, lineHeight: fontSizes.lg * 1.3, fontFamily: fontFamilies.semibold, tone: "primary" },
  body: { fontSize: fontSizes.base, lineHeight: fontSizes.base * 1.5, fontFamily: fontFamilies.regular, tone: "primary" },
  label: { fontSize: fontSizes.sm, lineHeight: fontSizes.sm * 1.3, fontFamily: fontFamilies.medium, tone: "secondary" },
  caption: { fontSize: fontSizes.xs, lineHeight: fontSizes.xs * 1.4, fontFamily: fontFamilies.regular, tone: "muted" },
};

/** Themed text — variant picks the type scale, color follows light/dark
 * automatically unless overridden via `style`. `display`/`hero` render in
 * Caprasimo (the display serif); everything else in Figtree. */
export function Text({ variant = "body", style, ...props }: TextProps & { variant?: Variant }) {
  const { colors } = useTheme();
  const base = VARIANT_BASE[variant];
  const color = base.tone === "primary" ? colors.textPrimary : base.tone === "secondary" ? colors.textSecondary : colors.textMuted;

  return (
    <RNText
      style={[{ fontSize: base.fontSize, lineHeight: base.lineHeight, fontFamily: base.fontFamily, color }, style]}
      {...props}
    />
  );
}

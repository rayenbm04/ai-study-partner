import { Text as RNText, type TextProps } from "react-native";

import { colors, fontFamilies, fontSizes } from "../../constants/theme";

type Variant = "display" | "title" | "body" | "label" | "caption";

const VARIANT_STYLES: Record<Variant, { fontSize: number; fontFamily: string; color: string }> = {
  display: { fontSize: fontSizes.display, fontFamily: fontFamilies.bold, color: colors.textPrimary },
  title: { fontSize: fontSizes.xl, fontFamily: fontFamilies.semibold, color: colors.textPrimary },
  body: { fontSize: fontSizes.base, fontFamily: fontFamilies.regular, color: colors.textPrimary },
  label: { fontSize: fontSizes.sm, fontFamily: fontFamilies.medium, color: colors.textSecondary },
  caption: { fontSize: fontSizes.xs, fontFamily: fontFamilies.regular, color: colors.textMuted },
};

export function Text({ variant = "body", style, ...props }: TextProps & { variant?: Variant }) {
  return <RNText style={[VARIANT_STYLES[variant], style]} {...props} />;
}

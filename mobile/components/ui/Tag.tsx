import { StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";

import { fontFamilies, fontSizes, radii, spacing } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";
import { Text } from "./Text";

type Tone = "accent" | "sage" | "neutral" | "error";

/** Small pill label — due-count badges, mastery chips, citation chips,
 * document-status chips. */
export function Tag({ label, tone = "neutral", style }: { label: string; tone?: Tone; style?: StyleProp<ViewStyle> }) {
  const { colors } = useTheme();
  const toneStyle: Record<Tone, { bg: string; fg: string }> = {
    accent: { bg: colors.accentLight, fg: colors.accentDark },
    sage: { bg: colors.sageLight, fg: colors.sageDark },
    neutral: { bg: colors.surfaceAlt, fg: colors.textSecondary },
    error: { bg: colors.errorLight, fg: colors.error },
  };
  const t = toneStyle[tone];
  return (
    <View style={[styles.base, { backgroundColor: t.bg }, style]}>
      <Text style={{ fontFamily: fontFamilies.semibold, fontSize: fontSizes.xs, color: t.fg }}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radii.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    alignSelf: "flex-start",
  },
});

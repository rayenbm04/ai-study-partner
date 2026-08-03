import { ActivityIndicator, Pressable, StyleSheet, type StyleProp, type ViewStyle } from "react-native";

import { fontFamilies, fontSizes, radii, spacing } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";
import { Text } from "./Text";

type Variant = "primary" | "accent" | "secondary" | "ghost";

export function Button({
  label,
  onPress,
  variant = "primary",
  disabled = false,
  loading = false,
  style,
}: {
  label: string;
  onPress: () => void;
  variant?: Variant;
  disabled?: boolean;
  loading?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const isDisabled = disabled || loading;

  const variantStyle: Record<Variant, { backgroundColor: string; borderColor?: string; textColor: string }> = {
    primary: { backgroundColor: colors.primary, textColor: colors.textOnPrimary },
    accent: { backgroundColor: colors.accent, textColor: colors.textOnAccent },
    secondary: { backgroundColor: colors.surface, textColor: colors.textPrimary },
    ghost: { backgroundColor: "transparent", textColor: colors.accentDark },
  };
  const v = variantStyle[variant];

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor: v.backgroundColor },
        variant === "secondary" && { shadowColor: colors.shadow, ...SHADOW },
        isDisabled && styles.disabled,
        pressed && !isDisabled && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.textColor} />
      ) : (
        <Text style={[styles.label, { color: v.textColor }]}>{label}</Text>
      )}
    </Pressable>
  );
}

const SHADOW = {
  shadowOffset: { width: 0, height: 6 },
  shadowOpacity: 1,
  shadowRadius: 16,
  elevation: 3,
};

const styles = StyleSheet.create({
  base: {
    height: 56,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  label: {
    fontSize: fontSizes.base,
    fontFamily: fontFamilies.semibold,
  },
  disabled: {
    opacity: 0.5,
  },
  pressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
});

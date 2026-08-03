import { StyleSheet, TextInput, View, type TextInputProps } from "react-native";

import { fontFamilies, fontSizes, radii, spacing } from "../../constants/theme";
import { useTheme } from "../../lib/theme-context";
import { Text } from "./Text";

export function TextField({
  label,
  error,
  style,
  multiline,
  ...props
}: TextInputProps & { label?: string; error?: string | null }) {
  const { colors } = useTheme();
  return (
    <View style={style}>
      {label ? (
        <Text variant="label" style={styles.label}>
          {label}
        </Text>
      ) : null}
      <TextInput
        placeholderTextColor={colors.textMuted}
        multiline={multiline}
        style={[
          styles.input,
          {
            backgroundColor: colors.surfaceAlt,
            color: colors.textPrimary,
            borderColor: error ? colors.error : "transparent",
          },
          multiline && styles.multiline,
        ]}
        {...props}
      />
      {error ? (
        <Text variant="caption" style={[styles.error, { color: colors.error }]}>
          {error}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    marginBottom: spacing.xs,
    marginLeft: spacing.sm,
  },
  input: {
    minHeight: 56,
    borderRadius: radii.full,
    borderWidth: 1.5,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontSize: fontSizes.base,
    fontFamily: fontFamilies.regular,
  },
  multiline: {
    borderRadius: radii.lg,
    minHeight: 90,
    textAlignVertical: "top",
  },
  error: {
    marginTop: spacing.xs,
    marginLeft: spacing.sm,
  },
});
